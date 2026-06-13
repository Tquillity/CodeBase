# AI Contribution Guidelines for CodeBase

This document outlines the architectural standards, coding conventions, and rules for AI agents modifying the **CodeBase** project.

## 1. Project Overview
**CodeBase** is a local repository manager and content generator built with **Python** and **Tkinter (ttkbootstrap)**. It allows users to scan local repos, view structure/content, and copy data for LLM prompting. It is **cross-platform** and runs on both **Linux and Windows**.

## 2. Tech Stack & Libraries
*   **UI Framework:** `ttkbootstrap` (Theme: `darkly` by default). Do not use standard `tkinter` widgets unless strictly necessary for functionality not present in `ttkbootstrap`.
*   **Threading:** `threading` module. **Never** run file I/O or heavy processing on the main UI thread. Use the `gui.task_queue` pattern or `gui.register_background_thread`.
*   **Icons/DnD:** `tkinterdnd2` for drag-and-drop.
*   **Build System:** PyInstaller (both platforms) + FPM → RPM on Linux (`build_linux.py`); PyInstaller `--onefile` → `.exe` on Windows (`build_windows.py`).

## 3. Architecture & File Structure
*   **`main.py`**: Entry point. Handles signal trapping and global exception logging.
*   **`gui.py`**: Main `RepoPromptGUI` class. Manages layout and high-level orchestration.
*   **`tabs/`**: UI components separated by functional tab (e.g., `content_tab.py`, `structure_tab.py`).
*   **`panels/`**: Collapsible side panels (e.g., git status, module analysis).
*   **`handlers/`**: Business logic separated by domain (e.g., `repo_handler.py`, `copy_handler.py`, `search_handler.py`).
*   **`file_handler.py`**, **`search_handler.py`**, **`file_list_handler.py`**: Root-level handler modules (file I/O, search, file-list generation).
*   **`constants.py`**: All configuration constants, default values, and version strings. **Update VERSION here.**
*   **`assets/`**: Binary assets (icons).

## 4. Coding Standards

### UI Updates
*   **Thread Safety:** Tkinter is **not** thread-safe.
*   *Correct:* Use `gui.task_queue.put((callback, args))` or `root.after()` to update UI from a background thread.
*   *Incorrect:* Calling `label.config(text=...)` directly inside a `threading.Thread`.

### Error Handling
*   Use the centralized `error_handler.py`.
*   Wrap complex logic in `try/except` blocks that catch specific exceptions (`FileOperationError`, `RepositoryError`, `OSError`).
*   Prefer specific exceptions over bare `except Exception`. Bare `except Exception` is only acceptable at top-level worker entry points with `logging.exception`.
*   Use `gui.show_status_message(msg, error=True)` for user feedback.

### Logging
*   Use `logging_config.py`.
*   Do not use `print()` statements for debugging; use `logging.debug()`, `logging.info()`, or `logging.error()`.

### Path Handling
*   **Cross-platform:** CodeBase runs on **Linux and Windows**. **Never** hard-code `/` separators or assume POSIX paths.
*   **Always** build paths with `os.path.join` / `os.sep` / `pathlib` — never string concatenation with `/`.
*   **Canonical internal forms** (see `path_utils.py`):
    *   `normalize_path` → forward-slash separators, original case (display, gitignore matching, path building). Forward slashes are valid in Win32 file APIs.
    *   `normalize_for_cache` → `os.path.normcase` form (case-folded on Windows). Use for **cache keys and any case-insensitive path comparison** — Windows filesystems are case-insensitive.
    *   `is_path_within_base` → use for containment checks; it is drive- and case-aware.
*   **Platform-specific code** (signals, DPI, icons, drive enumeration) must be guarded by `sys.platform == "win32"` / `os.name == "nt"` so the other platform is unaffected.

## 5. Build & Release
*   **Linux:** Use `build_linux.py` (PyInstaller + `fpm` → RPM). Installer: `install.sh`.
*   **Windows:** Use `build_windows.py` (PyInstaller `--onefile` → `dist\CodeBase.exe`, using `assets/icon.ico`). Installer: `install.ps1` (Start Menu / Desktop shortcuts, per-user).
*   **Versioning:** When updating the application version, update `constants.py`.

## 6. Testing
*   If adding new features, ensure they work with the "Live Reload" script (`live_reload.py`).
*   Respect the `security_enabled` setting (`gui.settings.get('app', 'security_enabled', 0)`) when implementing file reading features.