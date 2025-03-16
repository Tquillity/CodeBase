# CodeBase v2.0

**CodeBase** is a GUI tool to scan local repository folders, view their structure and contents, and copy them to your clipboard. Built with Python and Tkinter, it’s designed for developers working with codebases.

## Features
- **Must Haves**:
  - Refresh button on main page.
  - Close buttons and ESC key for all popups.
  - Persistent repo settings between sessions.
  - Select/deselect files and folders in "Folder Structure" tab for copying.
  - Click files in "Folder Structure" to jump to content.
  - "Copy All" button (prompt, code, structure).
  - Dynamic "Expand/Collapse" button based on folder state.
  - TAB key to switch between tabs.
  - "Settings" tab for default tab and folder expansion.
- **Nice to Haves**:
  - Close dialogs with both Enter keys (main and NumPad).

## Dependencies
- Python 3.7+
- Tkinter
- `watchdog`, `pyperclip`, `appdirs` (install via `pip`)

## Installation
1. Extract `CodeBase.tar.gz`.
2. Run `sudo ./install.sh` from the extracted directory.
3. Launch via application menu or `CodeBase` command.

## Usage
1. **Select a Repository**: 
   - Click "Select Repo Folder" (Ctrl+R) or use the shortcut.
   - Choose a directory (e.g., `/home/user/my_project`).
   - The app loads the repo, showing a progress bar during loading.
2. **View Contents**: 
   - Switch to the "Content Preview" tab to see file contents.
   - Example: Loading `/home/user/my_project` shows all text files’ contents.
3. **Copy Structure**: 
   - Click "Copy Structure" (Ctrl+S) to copy the folder tree to your clipboard.
   - Example output: 