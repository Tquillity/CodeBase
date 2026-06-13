from __future__ import annotations

import logging
import os
import signal
import sys
from typing import Any, Optional

import tkinter as tk
import ttkbootstrap as ttk
from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore[import-untyped]

from constants import (
    DEFAULT_LOG_LEVEL,
    LOG_FORMAT,
    LOG_TO_CONSOLE,
    LOG_TO_FILE,
    get_log_file_path,
)
from gui import RepoPromptGUI
from logging_config import setup_logging


class DnDWindow(ttk.Window, TkinterDnD.DnDWrapper):  # type: ignore[misc]
    TkdndVersion: Optional[Any]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Set the window class name to match the .desktop file for Linux desktop
        # integration. Harmless on Windows (Tk ignores className there).
        if 'className' not in kwargs:
            kwargs['className'] = 'CodeBase'
        super().__init__(*args, **kwargs)
        self.TkdndVersion = None
        try:
            self.TkdndVersion = TkinterDnD._require(self)
        except (RuntimeError, tk.TclError) as e:
            logging.warning(f"Drag and drop library could not be loaded: {e}")


def init_platform() -> None:
    """Windows-only pre-window setup. No-op on other platforms.

    Must run BEFORE the first Tk window is created:
      * Per-monitor DPI awareness so Tk text is not bitmap-stretched (blurry)
        on scaled (125%/150%/200%) Windows displays.
      * An explicit AppUserModelID so the taskbar uses our icon and groups
        windows correctly instead of treating us as a generic python.exe.
    """
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll
    except Exception:
        return
    try:
        windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception as e:
            logging.debug(f"Could not set DPI awareness: {e}")
    try:
        windll.shell32.SetCurrentProcessExplicitAppUserModelID("Mikael.CodeBase")
    except Exception:
        pass


def set_window_icon(window: Any) -> None:
    """Set the window/taskbar icon, platform-appropriately.

    Windows needs a real ``.ico`` via ``iconbitmap``; other platforms use the
    PNG via ``iconphoto``. Asset path resolves correctly whether running from
    source or from a PyInstaller bundle (``sys._MEIPASS``).
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    assets = os.path.join(base, "assets")
    try:
        if sys.platform == "win32":
            ico = os.path.join(assets, "icon.ico")
            if os.path.exists(ico):
                window.iconbitmap(ico)
        else:
            png = os.path.join(assets, "icon.png")
            if os.path.exists(png):
                window.iconphoto(True, tk.PhotoImage(file=png))
    except tk.TclError as e:
        logging.debug(f"Could not set window icon: {e}")


def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    logging.info(f"Received signal {signum}, initiating graceful shutdown...")
    app = getattr(signal_handler, "app", None)
    if app:
        app.on_close()
    else:
        logging.warning("Shutdown signal received before application initialized")
    sys.exit(0)


def setup_signal_handlers() -> None:
    """Register graceful-shutdown handlers for signals that are actually
    delivered on the current platform.

    On Windows, SIGTERM exists only as a constant and is never delivered to a
    handler under normal termination; the deliverable signals are SIGINT
    (Ctrl+C) and SIGBREAK (Ctrl+Break / console close). The reliable shutdown
    hook on every platform is the window-close protocol (WM_DELETE_WINDOW ->
    on_close), which the GUI binds itself.
    """
    signal.signal(signal.SIGINT, signal_handler)
    if sys.platform == "win32":
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, signal_handler)
    else:
        signal.signal(signal.SIGTERM, signal_handler)


signal_handler.app = None  # type: ignore[attr-defined]

if __name__ == "__main__":
    # Windows DPI / taskbar setup must happen before any Tk window exists.
    init_platform()

    # Setup centralized logging configuration
    setup_logging(
        level=DEFAULT_LOG_LEVEL,
        log_file=get_log_file_path() if LOG_TO_FILE else None,
        console_output=LOG_TO_CONSOLE,
        format_string=LOG_FORMAT
    )

    # Set up signal handlers for graceful shutdown (platform-aware)
    setup_signal_handlers()

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

    set_window_icon(root)

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
