import os
import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import signal
import logging
from logging_config import setup_logging, get_logger
from constants import DEFAULT_LOG_LEVEL, LOG_TO_FILE, LOG_TO_CONSOLE, LOG_FILE_PATH, LOG_FORMAT

# Files to ignore during live reload to prevent unnecessary restarts
IGNORE_PATTERNS = [
    '__pycache__',
    '.git',
    '.pytest_cache',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '.DS_Store',
    'Thumbs.db',
    'codebase_debug.log',
    '*.tmp',
    '*.temp'
]

# Setup logging for live reload
setup_logging(
    level=DEFAULT_LOG_LEVEL,
    log_file=LOG_FILE_PATH if LOG_TO_FILE else None,
    console_output=LOG_TO_CONSOLE,
    format_string=LOG_FORMAT
)

class RestartHandler(FileSystemEventHandler):
    def __init__(self, script_to_watch, script_to_run):
        self.script_to_watch = script_to_watch # The script whose changes trigger restart
        self.script_to_run = script_to_run     # The script to execute (e.g., main.py)
        self.process = None
        self.logger = get_logger(__name__)
        self.last_restart_time = 0
        self.debounce_delay = 2  # 2 seconds delay to avoid rapid restarts
        self.start_script()
        
    def should_ignore_file(self, file_path):
        """Check if a file should be ignored based on patterns."""
        import fnmatch
        for pattern in IGNORE_PATTERNS:
            if fnmatch.fnmatch(file_path, pattern) or pattern in file_path:
                return True
        return False

    def start_script(self):
        self.stop_script() # Ensure previous process is stopped
        try:
            logging.info(f"Starting {self.script_to_run}...")
            # Use python3 explicitly to avoid Node.js conflicts
            python_cmd = "python3" if os.name != 'nt' else "python"
            self.process = subprocess.Popen([python_cmd, self.script_to_run])
            logging.info(f"Started process {self.process.pid}")
        except FileNotFoundError:
            logging.error(f"Error: Could not find Python executable '{sys.executable}' or script '{self.script_to_run}'")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Error starting script {self.script_to_run}: {e}")
            sys.exit(1)

    def stop_script(self):
        if self.process and self.process.poll() is None: # Check if process exists and is running
            logging.info(f"Attempting to terminate process {self.process.pid}...")
            try:
                # Try SIGTERM first (graceful shutdown)
                self.process.terminate()
                try:
                    # Wait a short time for termination
                    self.process.wait(timeout=2)
                    logging.info(f"Process {self.process.pid} terminated gracefully.")
                except subprocess.TimeoutExpired:
                    # If terminate didn't work, force kill
                    logging.warning(f"Process {self.process.pid} did not terminate, killing...")
                    self.process.kill()
                    self.process.wait() # Wait for kill to complete
                    logging.info(f"Process {self.process.pid} killed.")
            except ProcessLookupError:
                logging.warning(f"Process {self.process.pid} lookup failed, likely already stopped.")
            except Exception as e:
                logging.error(f"Error stopping process {self.process.pid}: {e}")
            finally:
                self.process = None

    def on_modified(self, event):
        # Only act on file modifications, ignore directories
        if not event.is_directory:
            # Check if the file should be ignored
            if self.should_ignore_file(event.src_path):
                return
                
            # Check if the modified file is a Python file or important config file
            if (event.src_path.endswith(".py") or 
                event.src_path.endswith(".txt") or 
                event.src_path.endswith(".json") or
                event.src_path.endswith(".yaml") or
                event.src_path.endswith(".yml")):
                
                current_time = time.time()
                # Debounce: Only restart if enough time has passed since the last restart
                if current_time - self.last_restart_time >= self.debounce_delay:
                    logging.info(f"🔄 Detected change in {event.src_path}. Restarting {self.script_to_run}...")
                    self.start_script()
                    self.last_restart_time = current_time
                else:
                    logging.info(f"⏳ Change detected in {event.src_path}, but debouncing restart.")
            else:
                logging.debug(f"📁 Ignoring non-Python file change: {event.src_path}")

if __name__ == "__main__":
    # Configuration
    script_to_run = "main.py"  # The main application script
    # Determine the directory containing the script_to_run to watch
    # Watch the directory of *this* script (live_reload.py) by default,
    # assuming main.py and others are siblings or in subdirs. Adjust if needed.
    watch_dir = os.path.dirname(os.path.abspath(__file__))

    print("🚀 CodeBase Live Reload Development Server")
    print("=" * 50)
    print(f"📁 Watching directory: {watch_dir}")
    print(f"🎯 Monitoring script: {script_to_run}")
    print(f"🎨 UI Framework: ttkbootstrap (modern themes)")
    print(f"⏱️  Debounce delay: 2 seconds")
    print("=" * 50)
    print("💡 Tip: The app will automatically restart when you save Python files")
    print("🛑 Press Ctrl+C to stop the development server")
    print("=" * 50)

    logging.info(f"Watching directory: {watch_dir} for changes to trigger restart of {script_to_run}")
    logging.info(f"Monitoring script: {script_to_run}") # Log which script is being run
    logging.info("CodeBase Live Reload Development Server started with ttkbootstrap support")

    event_handler = RestartHandler(script_to_watch=None, script_to_run=script_to_run) # Pass both params

    observer = Observer()
    # Watch recursively for changes in any .py files within the directory
    observer.schedule(event_handler, path=watch_dir, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 KeyboardInterrupt received, stopping development server...")
        logging.info("KeyboardInterrupt received, stopping observer and script...")
        observer.stop()
        event_handler.stop_script() # Ensure the child process is stopped on exit
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        logging.error(f"An unexpected error occurred: {e}")
        observer.stop()
        event_handler.stop_script() # Ensure the child process is stopped on exit

    observer.join()
    print("✅ CodeBase Live Reload Development Server stopped.")
    logging.info("Live reload finished.")