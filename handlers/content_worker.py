# handlers/content_worker.py
"""Canonical background worker for generate_content (thread + error envelope).

All UI-facing content generation (preview, copy, git copy, file-list copy) should
call ``start_content_generation`` rather than spawning threads directly. The worker:

1. Builds ``ContentGenerationContext`` from ``gui.settings`` and abort flags.
2. Runs ``generate_content`` on a registered daemon thread.
3. On uncaught exceptions, invokes ``on_complete`` with an error message so callers
   can hide loading overlays and show feedback (via ``task_queue`` marshaling).

``on_complete`` is called on the worker thread; callers must queue UI updates.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

from content_generation_context import build_content_context_from_gui
from content_manager import (
    CancelledCallback,
    ProgressCallback,
    generate_content,
)


def start_content_generation(
    gui: Any,
    *,
    files: set[str],
    repo_path: Optional[str],
    lock: threading.Lock,
    content_cache: Any,
    template_format: str,
    on_complete: Callable[[str, int, list[str], Optional[list[str]]], None],
    progress_callback: Optional[ProgressCallback] = None,
    cancelled_callback: Optional[CancelledCallback] = None,
    thread_name: str = "ContentGen",
    error_prefix: str = "Content generation failed",
) -> None:
    """Run ``generate_content`` on a daemon thread with a top-level error envelope.

    Args:
        gui: RepoPromptGUI (or test mock) with ``settings``, abort flags, and
            ``register_background_thread``.
        files: Absolute paths to include in generated output.
        repo_path: Repository root for relative path display.
        lock: File-handler lock passed through to ``generate_content``.
        content_cache: Thread-safe LRU cache for file reads.
        template_format: Markdown or XML template key from settings.
        on_complete: Worker-thread callback; queue UI work via ``gui.task_queue``.
        progress_callback: Optional progress reporter (preview path).
        cancelled_callback: Optional callback when user cancels preview generation.
        thread_name: Registered thread name for shutdown diagnostics.
        error_prefix: Prefix for error strings when the worker catches an exception.
    """
    context = build_content_context_from_gui(gui)

    def worker() -> None:
        try:
            generate_content(
                files,
                repo_path or "",
                lock,
                on_complete,
                content_cache,
                context,
                progress_callback,
                template_format,
                cancelled_callback=cancelled_callback,
            )
        except Exception as e:
            logging.exception("%s: %s", error_prefix, e)
            on_complete("", 0, [f"{error_prefix}: {e}"], [])

    thread = threading.Thread(target=worker, name=thread_name, daemon=True)
    gui.register_background_thread(thread)
    thread.start()
