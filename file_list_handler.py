import os
import threading
from content_manager import generate_content

def generate_list_content(gui, files_to_copy, repo_path, lock, completion_callback, content_cache, list_read_errors):
    # FIX: Get format from settings
    current_format = gui.settings.get('app', 'copy_format', "Markdown (Grok)")

    # FIX: Added 'gui' parameter to access task_queue in threaded callback
    def wrapped_completion(content, token_count, errors):
        # FIX: Queue the callback execution in the main thread
        gui.task_queue.put((completion_callback, (content, token_count, errors)))

    # FIX: Pass current_format to generate_content
    thread = threading.Thread(target=generate_content, args=(files_to_copy, repo_path, lock, wrapped_completion, content_cache, list_read_errors, None, gui, current_format), daemon=True)
    thread.start()