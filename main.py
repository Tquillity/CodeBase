from __future__ import annotations

import logging
import signal
import sys
from typing import Any, Optional

import tkinter as tk
import ttkbootstrap as ttk
from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore[import-untyped]

from constants import DEFAULT_LOG_LEVEL, LOG_FILE_PATH, LOG_FORMAT, LOG_TO_CONSOLE, LOG_TO_FILE
from gui import RepoPromptGUI
from logging_config import setup_logging


class DnDWindow(ttk.Window, TkinterDnD.DnDWrapper):  # type: ignore[misc]
    TkdndVersion: Optional[Any]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Set the window class name to match the .desktop file for Linux desktop integration
        if 'className' not in kwargs:
            kwargs['className'] = 'CodeBase'
        super().__init__(*args, **kwargs)
        self.TkdndVersion = None
        try:
            self.TkdndVersion = TkinterDnD._require(self)
        except (RuntimeError, tk.TclError) as e:
            logging.warning(f"Drag and drop library could not be loaded: {e}")

def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    logging.info(f"Received signal {signum}, initiating graceful shutdown...")
    app = getattr(signal_handler, "app", None)
    if app:
        app.on_close()
    sys.exit(0)


signal_handler.app = None  # type: ignore[attr-defined]

if __name__ == "__main__":
    # Setup centralized logging configuration
    setup_logging(
        level=DEFAULT_LOG_LEVEL,
        log_file=LOG_FILE_PATH if LOG_TO_FILE else None,
        console_output=LOG_TO_CONSOLE,
        format_string=LOG_FORMAT
    )

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Try to initialize with DnD support
    root: Any
    try:
        # Pass className for desktop integration
        root = DnDWindow(themename="darkly")
        if not getattr(root, 'TkdndVersion', None):
            logging.warning("System Tcl version incompatible with TkinterDnD. Drag & Drop disabled.")
    except Exception as e:
        logging.error(f"Critical DnD initialization failure: {e}. Falling back to standard window.")
        # Pass className for desktop integration
        root = ttk.Window(themename="darkly", className="CodeBase")

    app = RepoPromptGUI(root)
    
    # Store app reference for signal handler
    signal_handler.app = app  # type: ignore[attr-defined]
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received, shutting down...")
        app.on_close()
    except Exception as e:
        logging.error(f"Unexpected error in main loop: {e}")
        app.on_close()
        raise
