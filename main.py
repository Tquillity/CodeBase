import ttkbootstrap as ttk
import signal
import sys
import logging
from gui import RepoPromptGUI

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logging.info(f"Received signal {signum}, initiating graceful shutdown...")
    if hasattr(signal_handler, 'app') and signal_handler.app:
        signal_handler.app.on_close()
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
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