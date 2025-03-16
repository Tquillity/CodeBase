import os
import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class RestartHandler(FileSystemEventHandler):
    def __init__(self, script):
        self.script = script
        self.process = None
        self.last_update_time = 0
        self.debounce_delay = 5  # 5 seconds delay
        self.start_script()

    def start_script(self):
        if self.process:
            self.process.terminate()
        self.process = subprocess.Popen([sys.executable, self.script])

    def on_modified(self, event):
        # Check if the event is for a file (not a directory) and ignore non-relevant files if desired
        if not event.is_directory:
            current_time = time.time()
            # Only restart if 5 seconds have passed since the last update
            if current_time - self.last_update_time >= self.debounce_delay:
                print(f"Detected change in {event.src_path}. Restarting {self.script}...")
                self.start_script()
                self.last_update_time = current_time

if __name__ == "__main__":
    script_to_run = "main.py"  # The script to run and restart
    watch_dir = os.path.dirname(os.path.abspath(script_to_run))  # Directory to watch
    event_handler = RestartHandler(script_to_run)
    observer = Observer()
    observer.schedule(event_handler, path=watch_dir, recursive=False)  # Set recursive=True if subdirectories should be watched
    observer.start()
    print(f"Watching for changes in directory {watch_dir}...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()