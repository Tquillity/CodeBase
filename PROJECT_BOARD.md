# CodeBase - Project Board

**Version 7.3.0** — A Linux desktop tool for preparing codebase content for LLM prompts and code reviews. Scan repositories, select files, preview combined content, and copy to clipboard with one click.

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
- 📊 **Module Analysis** — Multi-language dependency graph (Python, JS/TS, Rust, Java, C/C++, Go, etc.), regex-based imports, folder-as-module, impact scores, one-click module selection
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
✅ **Sprint 2: Hierarchical Clustering** — scipy-based clustering, dendrogram, Select This Cluster.  
✅ **Sprint 3: Knowledge Graph & Intelligent Prompt Builder** — SQLite persistent memory, knapsack-style optimal prompt, local recommendations (Insights panel).

## Quick Polish (Priority)
✅ **#7 Toast Notifications** — Modern, non-blocking toast notifications (success / info / warning / error); thread-safe via task_queue; replaced blocking messagebox for errors/warnings where appropriate.
✅ **Git Status panel UX** — Panel uses full vertical height; collapsible Staged/Changes sections; listbox height and scrollbars adapt to content.
✅ **Deleted/missing files** — Preview and copy never fail due to missing files; deleted files shown in Content tab as red strikethrough with [DELETED]; Git panel shows "D" for deleted; error summary groups "Deleted files (not copied)".
✅ **Cancel during preview + loading messages** — Cancel button works during both scan and preview; phased messages: "Scanning repository...", "Refreshing repository...", "Building tree...", "Generating preview..."; cancel during preview shows toast "Preview generation cancelled." and hides overlay.
✅ **#3 Full type hints + mypy --strict** — Comprehensive type hints across core modules (constants, exceptions, path_utils, lru_cache, settings, security, error_handler, content_manager, file_scanner); handlers and tabs started; `mypy.ini` with strict + explicit_package_bases; external libs use `# type: ignore[import-untyped]` where stubs missing.

## Changelog
- **7.3.0** — Root-anchored `.gitignore` entries such as `/.cypress-cache/` are now respected during scans, preventing accidental cache ingestion and token spikes. Local desktop installation also supports the bundled SVG icon for app menu integration.
- **7.2.0** — SQLite Knowledge Graph, persistent copy history, knapsack-style optimal prompt building, and local module recommendations (Insights panel). Git Status panel selection checkboxes (selective copy for staged/unstaged files). Grok API removed; local heuristics retained.
- **7.0.0** — Module Analysis Sprint 2: hierarchical clusters, dendrogram, Select This Cluster.
- **6.9.0** — Module Analysis multi-language: regex-based imports for Python, JS/TS, Rust, Java, C/C++, Go, etc.; folder-as-module heuristic; in-degree centrality impact.
- **6.8.0** — Sprint 1: Module Analysis tab (dependency graph, impact scores, Select This Module).
- **6.7.0** — Full type hints (mypy --strict) on core modules.
- **6.6.0** — Toast notifications; Git Status panel; deleted-file handling; Cancel during preview.

## Next (optional)
- Sprint 4: Cross-Repository Semantic Search (local embeddings).
- Further "Offline Intelligence" features; optional UI polish.

## Key Files
- `main.py` - Application entry point
- `gui.py` - Main GUI implementation
- `module_analyzer.py` - Multi-language dependency graph engine (regex imports, folder-as-module, networkx)
- `tabs/module_analysis_tab.py` - Module Analysis tab UI
- `file_scanner.py` - Repository scanning
- `content_manager.py` - Content generation
- `handlers/` - Feature handlers (copy, git, repo, search)

## Testing
```bash
python3 -m pytest
```
