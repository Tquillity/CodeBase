# CodeBase

**Version 6.5.0**

CodeBase is a Linux desktop application that scans a local source repository, lets you select files, previews the combined content, and copies the result to the clipboard for use in LLM prompts or code reviews.

## Features

- Repository scanning with ignore rules (`.gitignore`) and configurable exclusions
- File selection via a tree view
- Content preview with syntax highlighting
- Copy selected content / structure to clipboard
- Live reload utility for development (`live_reload.py`)

## Requirements

- Linux
- Python 3
- Tkinter (system package)

## Install (Developer)

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-dev.txt
```

Run the app:

```bash
python3 main.py
```

## Install (User)

Use the installer script:

```bash
./install.sh
```

## Tests

```bash
python3 -m pytest
```

## Security Notes

The application reads local repository files and can enforce size/content safety checks before including them in generated output. Security-related behavior is centralized in `security.py` and governed by settings/constants.

## License

See `LICENSE`.

