# CodeBase - Project Board

**Version 6.7.0** — A Linux desktop tool for preparing codebase content for LLM prompts and code reviews. Scan repositories, select files, preview combined content, and copy to clipboard with one click.

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

## Quick Polish (Priority)
✅ **#7 Toast Notifications** — Modern, non-blocking toast notifications (success / info / warning / error); thread-safe via task_queue; replaced blocking messagebox for errors/warnings where appropriate.
✅ **Git Status panel UX** — Panel uses full vertical height; collapsible Staged/Changes sections; listbox height and scrollbars adapt to content.
✅ **Deleted/missing files** — Preview and copy never fail due to missing files; deleted files shown in Content tab as red strikethrough with [DELETED]; Git panel shows "D" for deleted; error summary groups "Deleted files (not copied)".
✅ **Cancel during preview + loading messages** — Cancel button works during both scan and preview; phased messages: "Scanning repository...", "Refreshing repository...", "Building tree...", "Generating preview..."; cancel during preview shows toast "Preview generation cancelled." and hides overlay.
✅ **#3 Full type hints + mypy --strict** — Comprehensive type hints across core modules (constants, exceptions, path_utils, lru_cache, settings, security, error_handler, content_manager, file_scanner); handlers and tabs started; `mypy.ini` with strict + explicit_package_bases; external libs use `# type: ignore[import-untyped]` where stubs missing.

## Changelog
- **6.7.0** — Full type hints (mypy --strict) on core modules; version bump for code quality gate.
- **6.6.0** — Toast notifications (non-blocking); Git Status panel full-height + collapsible sections; graceful deleted/missing file handling (preview + copy); Cancel during preview + contextual loading messages; QC-audited.

## Next (optional)
- Complete mypy --strict on remaining files (file_handler, gui, panels, widgets, tests); Sprint 1 (Dependency Graph Engine).
- When typing `gui.py`: wrap all handler/tab imports in `if TYPE_CHECKING:` to avoid circular imports.

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
