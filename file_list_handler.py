from __future__ import annotations

from typing import Any, Callable, Set

from handlers.content_worker import start_content_generation


def generate_list_content(
    gui: Any,
    files_to_copy: Set[str],
    repo_path: str | None,
    lock: Any,
    completion_callback: Callable[[str, int, list[str], list[str]], None],
    content_cache: Any,
) -> None:
    current_format = gui.settings.get('app', 'copy_format', "Markdown (Grok)")

    def wrapped_completion(content: str, token_count: int, errors: list[str], deleted_files: list[str] | None = None) -> None:
        gui.task_queue.put((completion_callback, (content, token_count, errors, deleted_files or [])))

    start_content_generation(
        gui,
        files=set(files_to_copy),
        repo_path=repo_path,
        lock=lock,
        content_cache=content_cache,
        template_format=current_format,
        on_complete=wrapped_completion,
        thread_name="FileListCopy",
        error_prefix="File list copy failed",
    )
