# CodeBase

**Version 7.5.0**

CodeBase is a cross-platform desktop application (Linux and Windows) that scans a local source repository, lets you select files, previews the combined content, and copies the result to the clipboard for use in LLM prompts or code reviews.

## Features

- Repository scanning with ignore rules (`.gitignore`) and configurable exclusions
- File selection via a tree view
- **Module Analysis** — Multi-language dependency graph (Python, JavaScript/TypeScript, Rust, Java, C/C++, Go, etc.): regex-based import detection, folder-as-module grouping, impact scores (in-degree centrality), hierarchical clustering, and one-click selection of modules or clusters in the file tree
- **Persistent Knowledge Graph** — SQLite-backed memory of repos, clusters, and copy history (path hashes only) for local recommendations without external APIs
- **Optimal Prompt Builder** — Knapsack-style selection of highest-impact files within a token budget (e.g. 80% of max content length) for efficient LLM prompting
- **Selective Git Copy** — Choose specific staged or unstaged files to include in prompts (checkboxes in the Git Status panel)
- Content preview with syntax highlighting
- Copy selected content / structure to clipboard
- Live reload utility for development (`live_reload.py`)

## Requirements

- Linux or Windows
- Python 3.10+
- Tkinter (bundled with the official Windows installer; on Linux install the system `python3-tk` package)

## Install (Developer)

Create a virtual environment and install dependencies.

**Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-dev.txt
python3 main.py
```

**Windows (PowerShell):**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python main.py
```

## Build

**Linux** (produces an RPM; requires [`fpm`](https://fpm.readthedocs.io)):

```bash
python3 build_linux.py
```

**Windows** (produces `dist\CodeBase.exe` via PyInstaller):

```powershell
python build_windows.py
```

## Install (User)

**Linux** — use the installer script:

```bash
./install.sh
```

**Windows** — build the executable, then run the installer (creates Start Menu / Desktop shortcuts under your user profile, no admin required):

```powershell
python build_windows.py
powershell -ExecutionPolicy Bypass -File install.ps1 -Desktop
```

## Tests

```bash
python -m pytest
```

The test suite runs on both Linux and Windows. Tests that exercise the Linux-only
installer (`install.sh`) are skipped automatically on Windows.

## Security Notes

The application reads local repository files and can enforce size/content safety checks before including them in generated output. Security-related behavior is centralized in `security.py` and governed by settings/constants.

## License

See `LICENSE`.

## Changelog

User-facing changes are documented in [`CHANGELOG.md`](CHANGELOG.md).

