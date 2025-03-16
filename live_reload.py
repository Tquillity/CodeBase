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
        self.start_script()

    def start_script(self):
        if self.process:
            self.process.terminate()
        self.process = subprocess.Popen([sys.executable, self.script])

    def on_modified(self, event):
        if event.src_path.endswith(self.script):
            print(f"Detected change in {self.script}. Restarting...")
            self.start_script()

if __name__ == "__main__":
    script_to_watch = "main.py"  # Watches main.py for v2.0
    event_handler = RestartHandler(script_to_watch)
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(os.path.abspath(script_to_watch)), recursive=False)
    observer.start()
    print(f"Watching for changes in {script_to_watch}...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()