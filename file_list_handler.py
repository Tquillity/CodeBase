import os
import threading
from content_manager import generate_content

def generate_list_content(files_to_copy, repo_path, lock, completion_callback, content_cache, list_read_errors):
    thread = threading.Thread(target=generate_content, args=(files_to_copy, repo_path, lock, completion_callback, content_cache, list_read_errors), daemon=True)
    thread.start()