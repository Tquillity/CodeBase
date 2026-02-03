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
        self.script_to_watch = script_to_watch
        self.script_to_run = script_to_run
        self.process = None
        self.logger = get_logger(__name__)
        self.last_restart_time = 0
        self.debounce_delay = 2
        self.start_script()
        
    def should_ignore_file(self, file_path):
        """Check if a file should be ignored based on patterns."""
        import fnmatch
        for pattern in IGNORE_PATTERNS:
            if fnmatch.fnmatch(file_path, pattern) or pattern in file_path:
                return True
        return False

    def start_script(self):
        self.stop_script()
        try:
            logging.info(f"Starting {self.script_to_run}...")
            # Use python3 strictly for Linux environment
            # Set environment variable to indicate this is a live reload instance
            env = os.environ.copy()
            env['CODEBASE_LIVE_RELOAD'] = '1'
            self.process = subprocess.Popen(["python3", self.script_to_run], env=env)
            logging.info(f"Started process {self.process.pid}")
        except FileNotFoundError:
            logging.error(f"Error: Could not find Python executable '{sys.executable}' or script '{self.script_to_run}'")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Error starting script {self.script_to_run}: {e}")
            sys.exit(1)

    def stop_script(self):
        if self.process and self.process.poll() is None:
            logging.info(f"Attempting to terminate process {self.process.pid}...")
            try:
                # Graceful shutdown with SIGTERM
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                    logging.info(f"Process {self.process.pid} terminated gracefully.")
                except subprocess.TimeoutExpired:
                    # Force kill if SIGTERM fails
                    logging.warning(f"Process {self.process.pid} did not terminate, killing...")
                    self.process.kill()
                    self.process.wait()
                    logging.info(f"Process {self.process.pid} killed.")
            except ProcessLookupError:
                logging.warning(f"Process {self.process.pid} lookup failed, likely already stopped.")
            except Exception as e:
                logging.error(f"Error stopping process {self.process.pid}: {e}")
            finally:
                self.process = None

    def on_modified(self, event):
        if not event.is_directory:
            if self.should_ignore_file(event.src_path):
                return
                
            # Restart on changes to source or configuration files
            if (event.src_path.endswith(".py") or 
                event.src_path.endswith(".txt") or 
                event.src_path.endswith(".json") or
                event.src_path.endswith(".yaml") or
                event.src_path.endswith(".yml")):
                
                current_time = time.time()
                # Use debounce to prevent rapid restart loops
                if current_time - self.last_restart_time >= self.debounce_delay:
                    logging.info(f"🔄 Detected change in {event.src_path}. Restarting {self.script_to_run}...")
                    self.start_script()
                    self.last_restart_time = current_time
                else:
                    logging.info(f"⏳ Change detected in {event.src_path}, but debouncing restart.")
            else:
                logging.debug(f"📁 Ignoring non-Python file change: {event.src_path}")

if __name__ == "__main__":
    script_to_run = "main.py"
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
    logging.info("CodeBase Live Reload Development Server started with ttkbootstrap support")

    event_handler = RestartHandler(script_to_watch=None, script_to_run=script_to_run)

    observer = Observer()
    observer.schedule(event_handler, path=watch_dir, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 KeyboardInterrupt received, stopping development server...")
        logging.info("KeyboardInterrupt received, stopping observer and script...")
        observer.stop()
        event_handler.stop_script()
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        logging.error(f"An unexpected error occurred: {e}")
        observer.stop()
        event_handler.stop_script()

    observer.join()
    print("✅ CodeBase Live Reload Development Server stopped.")
    logging.info("Live reload finished.")