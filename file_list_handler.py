import os
import threading
from content_manager import generate_content

def generate_list_content(gui, files_to_copy, repo_path, lock, completion_callback, content_cache, list_read_errors):
    # FIX: Added 'gui' parameter to access task_queue in threaded callback
    def wrapped_completion(content, token_count, errors):
        # FIX: Queue the callback execution in the main thread
        gui.task_queue.put((completion_callback, (content, token_count, errors)))

    thread = threading.Thread(target=generate_content, args=(files_to_copy, repo_path, lock, wrapped_completion, content_cache, list_read_errors), daemon=True)
    thread.start()