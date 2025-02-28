# CodeBase

**CodeBase** is a simple GUI tool to scan local repository folders, view their folder structure and file contents, and copy them to your clipboard with ease. Built with Python and Tkinter, this application is designed for developers and anyone working with codebases for easier extraction and use with AI.

---

## Features

- Browse and select a repository folder.
- View file contents and folder structure in a tabbed interface.
- Copy contents or structure to the clipboard with optional base prompt text.
- Dark mode UI for comfortable use.
- Save and load custom prompt templates.

---

## Dependencies

Before installing CodeBase, ensure the following dependencies are installed on your system:

- Python 3.7+  
- Tkinter (for the GUI)  
- Required Python packages (installable via `pip`):
  - watchdog
  - pyperclip
  - appdirs

---

## Installation

1. **Download the Package**  
   Download the `CodeBase.tar.gz` file from the [release page].

2. **Extract the Archive**  
   Extract the package to a directory of your choice:
   tar -xzf CodeBase.tar.gz

3. **Run the Installation Script**  
   Navigate to the extracted `CodeBase` directory:
   cd CodeBase  
   Run the `install.sh` script to install the application:
   sudo ./install.sh  
   The script will:
   - Copy the application files to `/opt/codebase/`.
   - Create a desktop entry for the application in `/usr/share/applications/`.
   - Ensure the application is executable and ready to use.

4. **Update the Desktop Database**  
   After installation, update your desktop database to make the application discoverable in your system's application menu:
   sudo update-desktop-database

5. **Launch the Application**  
   - Open CodeBase from your application menu by searching for "CodeBase."
   - Alternatively, run it from the terminal using:
     codebase

---

## Usage Guide

### Selecting a Repository

1. Click the "Select Repo Folder" button or press Ctrl+R.
2. Choose a repository folder from the recent folders list or browse to a new location.
3. The application will scan the repository and display its contents.

### Viewing Content

- The "Content Preview" tab shows the content of all text files in the repository.
- The "Folder Structure" tab displays the repository's directory structure.
- Double-click on folders to expand them.

### Copying Content

- Click "Copy Contents" or press Ctrl+C to copy all file contents to the clipboard.
- Check "Prepend Base Prompt" to include the text from the Base Prompt tab.
- Click "Copy Structure" or press Ctrl+S to copy the folder structure to the clipboard.
- Toggle "Include Icons in Structure" to include or exclude folder/file icons.

### Using Base Prompts

- Enter your custom prompt text in the "Base Prompt" tab.
- Save templates for reuse with "Save Template" (Ctrl+S).
- Load existing templates with "Load Template" (Ctrl+L).
- Delete unwanted templates with "Delete Template."

### Clearing Data

- Use "Clear" to reset the current tab.
- Use "Clear All" to reset all tabs.

---

## Acknowledgments

- Built with Python and Tkinter.