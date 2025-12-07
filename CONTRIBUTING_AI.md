# AI Contribution Guidelines for CodeBase

This document outlines the architectural standards, coding conventions, and rules for AI agents modifying the **CodeBase** project.

## 1. Project Overview
**CodeBase** is a local repository manager and content generator built with **Python** and **Tkinter (ttkbootstrap)**. It allows users to scan local repos, view structure/content, and copy data for LLM prompting.

## 2. Tech Stack & Libraries
*   **UI Framework:** `ttkbootstrap` (Theme: `darkly` by default). Do not use standard `tkinter` widgets unless strictly necessary for functionality not present in `ttkbootstrap`.
*   **Threading:** `threading` module. **Never** run file I/O or heavy processing on the main UI thread. Use the `gui.task_queue` pattern or `gui.register_background_thread`.
*   **Icons/DnD:** `tkinterdnd2` for drag-and-drop.
*   **Build System:** PyInstaller + FPM (Linux) / Inno Setup (Windows).

## 3. Architecture & File Structure
*   **`main.py`**: Entry point. Handles signal trapping and global exception logging.
*   **`gui.py`**: Main `RepoPromptGUI` class. Manages layout and high-level orchestration.
*   **`tabs/`**: UI components separated by functional tab (e.g., `content_tab.py`, `structure_tab.py`).
*   **`handlers/`**: Business logic separated by domain (e.g., `file_handler.py`, `repo_handler.py`, `search_handler.py`).
*   **`constants.py`**: All configuration constants, default values, and version strings. **Update VERSION here.**
*   **`assets/`**: Binary assets (icons).

## 4. Coding Standards

### UI Updates
*   **Thread Safety:** Tkinter is **not** thread-safe.
*   *Correct:* Use `gui.task_queue.put((callback, args))` or `root.after()` to update UI from a background thread.
*   *Incorrect:* Calling `label.config(text=...)` directly inside a `threading.Thread`.

### Error Handling
*   Use the centralized `error_handler.py`.
*   Wrap complex logic in `try/except` blocks that catch specific exceptions (`FileOperationError`, `RepositoryError`).
*   Use `gui.show_status_message(msg, error=True)` for user feedback.

### Logging
*   Use `logging_config.py`.
*   Do not use `print()` statements for debugging; use `logging.debug()`, `logging.info()`, or `logging.error()`.

### Path Handling
*   **Always** use `os.path.join` or `path_utils.normalize_path`.
*   Assume cross-platform compatibility (Windows/Linux/macOS).

## 5. Build & Release
*   **Linux:** Use `build_linux.py`. Requires `fpm`.
*   **Windows:** Use `build_windows.py`. Requires `ISCC.exe` (Inno Setup).
*   **Versioning:** When updating the application version, update `constants.py`.

## 6. Testing
*   If adding new features, ensure they work with the "Live Reload" script (`live_reload.py`).
*   Respect the `SECURITY_ENABLED` constants when implementing file reading features.