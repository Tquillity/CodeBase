from __future__ import annotations

import threading
from typing import Any, Callable, Set

from content_manager import generate_content


def generate_list_content(
    gui: Any,
    files_to_copy: Set[str],
    repo_path: str | None,
    lock: Any,
    completion_callback: Callable[[str, int, list[str], list[str]], None],
    content_cache: Any,
    list_read_errors: list[str],
) -> None:
    current_format = gui.settings.get('app', 'copy_format', "Markdown (Grok)")

    def wrapped_completion(content: str, token_count: int, errors: list[str], deleted_files: list[str] | None = None) -> None:
        gui.task_queue.put((completion_callback, (content, token_count, errors, deleted_files or [])))

    thread = threading.Thread(
        target=generate_content,
        args=(files_to_copy, repo_path, lock, wrapped_completion, content_cache, list_read_errors, None, gui, current_format),
        daemon=True,
    )
    thread.start()