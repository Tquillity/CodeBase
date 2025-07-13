import os
import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import signal
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RestartHandler(FileSystemEventHandler):
    def __init__(self, script_to_watch, script_to_run):
        self.script_to_watch = script_to_watch # The script whose changes trigger restart
        self.script_to_run = script_to_run     # The script to execute (e.g., main.py)
        self.process = None
        self.last_restart_time = 0
        self.debounce_delay = 2  # 2 seconds delay to avoid rapid restarts
        self.start_script()

    def start_script(self):
        self.stop_script() # Ensure previous process is stopped
        try:
            logging.info(f"Starting {self.script_to_run}...")
            self.process = subprocess.Popen([sys.executable, self.script_to_run])
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
            # Check if the modified file is the one we are watching or related
            # You might want more sophisticated checks depending on project structure
            if event.src_path.endswith(".py"): # Simple check for any Python file change
                current_time = time.time()
                # Debounce: Only restart if enough time has passed since the last restart
                if current_time - self.last_restart_time >= self.debounce_delay:
                    logging.info(f"Detected change in {event.src_path}. Restarting {self.script_to_run}...")
                    self.start_script()
                    self.last_restart_time = current_time
                else:
                    logging.info(f"Change detected in {event.src_path}, but debouncing restart.")

if __name__ == "__main__":
    # Configuration
    script_to_run = "main.py"  # The main application script
    # Determine the directory containing the script_to_run to watch
    # Watch the directory of *this* script (live_reload.py) by default,
    # assuming main.py and others are siblings or in subdirs. Adjust if needed.
    watch_dir = os.path.dirname(os.path.abspath(__file__))

    logging.info(f"Watching directory: {watch_dir} for changes to trigger restart of {script_to_run}")
    logging.info(f"Monitoring script: {script_to_run}") # Log which script is being run

    event_handler = RestartHandler(script_to_watch=None, script_to_run=script_to_run) # Pass both params

    observer = Observer()
    # Watch recursively for changes in any .py files within the directory
    observer.schedule(event_handler, path=watch_dir, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received, stopping observer and script...")
        observer.stop()
        event_handler.stop_script() # Ensure the child process is stopped on exit
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        observer.stop()
        event_handler.stop_script() # Ensure the child process is stopped on exit

    observer.join()
    logging.info("Live reload finished.")