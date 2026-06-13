# Changelog

All notable user-facing changes to CodeBase are documented here.

## Unreleased

### Fixed
- Content cache now invalidates when files are edited on disk — Copy/Copy All sends current content without requiring Refresh.
- Copy Contents and Copy All run file reads on a background thread — the GUI stays responsive on large repositories.
- Virtual environment exclusion now correctly matches `.venv` and `venv` without hiding legitimate `env/` or `.env/` source directories.
- Whole Word search uses proper word boundaries and no longer crashes on regex metacharacters in queries.
- Global Ctrl+C / Ctrl+A / Ctrl+S shortcuts no longer override native text-widget editing when a text field has focus.
