# Changelog fragments

Every pull request adds its changelog entry as a **new file in this
directory** instead of editing `CHANGELOG.md`. Two pull requests therefore
never touch the same file, and changelog merge conflicts cannot happen.

## Adding an entry

Create a file under the directory matching your change type:

```
changelog.d/added/1660-1080p-sending-resolution.md
```

Available types (from [Keep a Changelog](https://keepachangelog.com/en/1.0.0)):
`added`, `changed`, `deprecated`, `removed`, `fixed`, `security`.

The file contains the entry exactly as it should appear in `CHANGELOG.md`,
as one or more markdown list items:

```markdown
- ✨(frontend) add 1080p sending resolution option #1660
```

Same conventions as before: gitmoji, scope, then the pull request id.
Each line must stay under 80 characters.

The file name is only used to sort entries within a section, so pick
something stable — the pull request id followed by a short slug works well.

## Releasing

`bin/prepare-release.sh` folds every fragment into `CHANGELOG.md` under the
new version, then deletes the fragment files. Nothing to do by hand.
