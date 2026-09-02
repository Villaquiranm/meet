#!/usr/bin/env python3
"""Fold the changelog.d fragments into CHANGELOG.md under a new version.

Every pull request drops its entry in changelog.d/<type>/<name>.md instead of
editing CHANGELOG.md, so two pull requests never touch the same file. This
script is what turns those fragments back into a release section.

Usage:
    bin/assemble-changelog.py 1.31.0 2026-09-02
    bin/assemble-changelog.py --check          # validate fragments only
"""

import argparse
import pathlib
import re
import sys

# Keep a Changelog section order.
SECTIONS = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
MAX_LINE_LENGTH = 80
UNRELEASED = "## [Unreleased]"

# Output helpers, matching bin/prepare-release.sh which calls this script.
# CI forbids print statements in the code base, hence the explicit writes.
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"


def write(message):
    sys.stdout.write(f"{message}\n")


def print_info(message):
    write(f"{GREEN}[INFO]{NC} {message}")


def print_error(message):
    write(f"{RED}[ERROR]{NC} {message}")


def print_warning(message):
    write(f"{YELLOW}[WARNING]{NC} {message}")


def read_fragments(fragments_dir):
    """Return {section: [entry lines]}, sorted by file name within a section."""
    entries = {}
    used_files = []
    for section in SECTIONS:
        directory = fragments_dir / section.lower()
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            lines = [
                line.rstrip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if not lines:
                continue
            entries.setdefault(section, []).extend(lines)
            used_files.append(path)
    return entries, used_files


def validate(entries, used_files):
    """Fragments must be markdown list items that fit the changelog line limit."""
    errors = []
    for section, lines in entries.items():
        for line in lines:
            if not line.startswith("- "):
                errors.append(f"{section}: not a markdown list item: {line!r}")
            if len(line) >= MAX_LINE_LENGTH:
                errors.append(f"{section}: line is {len(line)} chars (max 79): {line!r}")
    for path in used_files:
        if path.parent.name not in [section.lower() for section in SECTIONS]:
            errors.append(f"{path}: unknown change type {path.parent.name!r}")
    return errors


def split_unreleased(text):
    """Return (header, unreleased_body, rest), or None if there is no section."""
    start = text.find(UNRELEASED)
    if start == -1:
        return None
    body_start = start + len(UNRELEASED)
    next_version = re.search(r"^## \[", text[body_start:], flags=re.MULTILINE)
    body_end = body_start + next_version.start() if next_version else len(text)
    return text[:start], text[body_start:body_end], text[body_end:]


def parse_body(body):
    """Parse the entries already written inline under [Unreleased]."""
    entries = {}
    section = None
    for line in body.splitlines():
        heading = re.match(r"^### (.+?)\s*$", line)
        if heading:
            section = heading.group(1)
            entries.setdefault(section, [])
        elif line.strip() and section:
            entries[section].append(line.rstrip())
    return entries


def merge(inline, fragments):
    """Inline entries first, then fragments, in canonical section order."""
    merged = {}
    for section in SECTIONS + [s for s in inline if s not in SECTIONS]:
        lines = inline.get(section, []) + fragments.get(section, [])
        if lines:
            merged[section] = lines
    return merged


def render(version, date, entries):
    out = [f"## [{version}] - {date}", ""]
    for section, lines in entries.items():
        out += [f"### {section}", ""] + lines + [""]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", help="version being released, e.g. 1.31.0")
    parser.add_argument("date", nargs="?", help="release date, YYYY-MM-DD")
    parser.add_argument("--changelog", default="CHANGELOG.md", type=pathlib.Path)
    parser.add_argument("--fragments", default="changelog.d", type=pathlib.Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="only validate the fragments, do not touch the changelog",
    )
    args = parser.parse_args()

    fragments, used_files = read_fragments(args.fragments)

    errors = validate(fragments, used_files)
    if errors:
        for error in errors:
            print_error(error)
        return 1

    if args.check:
        print_info(f"{len(used_files)} changelog fragment(s) are valid.")
        return 0

    if not args.version or not args.date:
        parser.error("version and date are required unless --check is given")

    text = args.changelog.read_text(encoding="utf-8")
    sections = split_unreleased(text)
    if sections is None:
        print_error(f"Could not find the {UNRELEASED} section in {args.changelog}!")
        return 1
    header, body, rest = sections
    entries = merge(parse_body(body), fragments)

    if not entries:
        print_warning("No changelog entries found for this release.")

    args.changelog.write_text(
        f"{header}{UNRELEASED}\n\n{render(args.version, args.date, entries)}\n{rest.lstrip(chr(10))}",
        encoding="utf-8",
    )

    for path in used_files:
        path.unlink()

    total = sum(len(lines) for lines in entries.values())
    print_info(
        f"Wrote {total} entrie(s) to {args.changelog} "
        f"and removed {len(used_files)} fragment(s)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
