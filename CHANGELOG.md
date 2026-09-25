# Changelog

## Unreleased

- `--selftest` no longer eats the clipboard. It used to leave its test string
  there, so a command whose whole point is reassurance destroyed whatever you
  had copied. It now reads the clipboard first and puts it back, and says so
  when the content was not text and could not be restored.
- The exe is built and run in GitHub Actions on every push, with the same
  PyInstaller flags as `exe-olustur.bat`, so the binary no longer has to be
  taken on trust.
- Removed 41 lines of dead code from `diller.py` — an uninstall path and a
  listing helper that nothing ever called — and two translation strings that
  were unused, one of which had also become wrong.
- Three new checks in the test suite: unused translation keys, `SyntaxWarning`
  anywhere in the source, and functions nobody calls. Each was verified by
  reintroducing the bug it is meant to catch.

## 1.0.0

First public release.

- Global hotkeys: capture to clipboard, capture and edit, re-grab last area,
  stacking mode
- Text layout modes: keep lines, join wrapped lines, single paragraph,
  keep indentation (code), table (Markdown)
- Editable history that survives restarts
- 35 OCR languages installable from the Languages tab
- English / Turkish interface
- Multi-monitor and per-monitor DPI support
