import ttkbootstrap as ttk
import signal
import sys
import logging
import tkinter as tk
from tkinterdnd2 import TkinterDnD, DND_FILES
from gui import RepoPromptGUI
from logging_config import setup_logging
from constants import DEFAULT_LOG_LEVEL, LOG_FILE_PATH, LOG_TO_FILE, LOG_TO_CONSOLE, LOG_FORMAT

class DnDWindow(ttk.Window, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = None
        try:
            self.TkdndVersion = TkinterDnD._require(self)
        except (RuntimeError, tk.TclError) as e:
            logging.warning(f"Drag and drop library could not be loaded: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logging.info(f"Received signal {signum}, initiating graceful shutdown...")
    if hasattr(signal_handler, 'app') and signal_handler.app:
        signal_handler.app.on_close()
    sys.exit(0)

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
    try:
        root = DnDWindow(themename="darkly")
        if not getattr(root, 'TkdndVersion', None):
            logging.warning("System Tcl version incompatible with TkinterDnD. Drag & Drop disabled.")
    except Exception as e:
        logging.error(f"Critical DnD initialization failure: {e}. Falling back to standard window.")
        root = ttk.Window(themename="darkly")

    app = RepoPromptGUI(root)
    
    # Store app reference for signal handler
    signal_handler.app = app
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received, shutting down...")
        app.on_close()
    except Exception as e:
        logging.error(f"Unexpected error in main loop: {e}")
        app.on_close()
        raise