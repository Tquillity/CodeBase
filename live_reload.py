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
        self.last_restart = 0
        self.start_script()

    def start_script(self):
        if self.process:
            self.process.terminate()
        self.process = subprocess.Popen([sys.executable, self.script])

    def on_modified(self, event):
        if event.src_path.endswith(self.script):
            current_time = time.time()
            if current_time - self.last_restart < 0.5:  # Debounce: wait 0.5s
                return
            print(f"Detected change in {self.script}. Restarting...")
            self.start_script()
            self.last_restart = current_time

if __name__ == "__main__":
    files_to_watch = ["main.py", "gui.py", "file_handler.py", "widgets.py", "settings.py"]
    event_handler = RestartHandler("main.py")  # Still restarts main.py
    observer = Observer()
    for file in files_to_watch:
        if os.path.exists(file):  # Ensure file exists to avoid errors
            observer.schedule(event_handler, path=os.path.dirname(os.path.abspath(file)), recursive=False)
    observer.start()
    print(f"Watching for changes in {', '.join(files_to_watch)}...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()