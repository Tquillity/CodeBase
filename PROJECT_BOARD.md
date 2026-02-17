# CodeBase - Project Board

**Version 6.5.0** — A Linux desktop tool for preparing codebase content for LLM prompts and code reviews. Scan repositories, select files, preview combined content, and copy to clipboard with one click.

## Overview
Linux desktop application for scanning local repositories, selecting files, and copying combined content to clipboard for LLM prompts and code reviews.

## Tech Stack
- **Language**: Python 3
- **GUI Framework**: Tkinter + ttkbootstrap
- **Platform**: Linux
- **Dependencies**: See `requirements.txt`

## Key Features
- 🔍 Repository scanning with `.gitignore` support
- 📁 File selection via tree view
- 👁️ Content preview with syntax highlighting
- 📋 Copy selected content/structure to clipboard
- ⚙️ Configurable exclusions and settings
- 🔄 Live reload utility for development

## Quick Start
```bash
# Development
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py

# User Install
./install.sh
```

## Project Status
✅ Core functionality complete  
✅ Test suite available (`pytest`)  
✅ Security checks implemented (`security.py`)  
✅ Settings management (`settings.py`)

## Key Files
- `main.py` - Application entry point
- `gui.py` - Main GUI implementation
- `file_scanner.py` - Repository scanning
- `content_manager.py` - Content generation
- `handlers/` - Feature handlers (copy, git, repo, search)

## Testing
```bash
python3 -m pytest
```
