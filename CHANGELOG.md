# Changelog

All notable user-facing changes to CodeBase are documented here.

## Unreleased

## 7.5.0 — 2026-06-13

### Added
- Cross-platform Windows support integrated (`build_windows.py`, `install.ps1`) alongside existing Linux build and installer.

### Fixed
- Content cache now invalidates when files are edited on disk — Copy/Copy All sends current content without requiring Refresh.
- Copy Contents and Copy All run file reads on a background thread — the GUI stays responsive on large repositories.
- Virtual environment exclusion now correctly matches `.venv` and `venv` without hiding legitimate `env/` or `.env/` source directories.
- Whole Word search uses proper word boundaries and no longer crashes on regex metacharacters in queries.
- Global Ctrl+C / Ctrl+A / Ctrl+S shortcuts no longer override native text-widget editing when a text field has focus.
- Knowledge graph path hashes are case-stable on Windows (uses `normalize_for_cache`).
- `scanned_text_files` and `loaded_files` now share the same `normalize_path` form for consistent tree filtering.
- Module Analysis fallback text uses a cross-platform monospace font stack.
- Toast text color follows the active theme foreground instead of hardcoded white.
- PyInstaller version pinned on Windows builds (`>=6.0.0,<7`), matching Linux.
- Settings defaults aligned with `constants.py`; removed dead `SECURITY_ENABLED` constant.
- Centralized async content generation via `handlers/content_worker.py`; `ContentGenerationContext` decouples policy from `generate_content`.

## 7.3.0

- Root-anchored `.gitignore` entries such as `/.cypress-cache/` are now respected during scans.
- Local desktop installation supports the bundled SVG icon for app menu integration.
