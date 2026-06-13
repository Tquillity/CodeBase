# gui_lifecycle.py
"""Shutdown, thread cleanup, and resource teardown for RepoPromptGUI."""
from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Any

import knowledge_graph as kg


def register_background_thread(gui: Any, thread: threading.Thread) -> None:
    gui._background_threads.append(thread)
    logging.debug("Registered background thread: %s", thread.name)


def wait_for_threads(gui: Any, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    for thread in list(gui._background_threads):
        remaining = max(0.0, deadline - time.time())
        if remaining <= 0:
            break
        thread.join(timeout=remaining)


def cleanup_resources(gui: Any) -> None:
    logging.info("Cleaning up resources...")

    try:
        kg.close_connection()
        logging.info("Knowledge graph connection closed.")
    except Exception as e:
        logging.error("Error closing knowledge graph: %s", e)

    try:
        if hasattr(gui.file_handler, "content_cache"):
            gui.file_handler.content_cache.clear()
            logging.info("Content cache cleared.")
    except Exception as e:
        logging.error("Error clearing content cache: %s", e)

    try:
        if hasattr(gui.repo_handler, "content_cache"):
            gui.repo_handler.content_cache.clear()
            logging.info("Repo handler cache cleared.")
    except Exception as e:
        logging.error("Error clearing repo handler cache: %s", e)

    wait_for_threads(gui, timeout=5.0)

    try:
        while not gui.task_queue.empty():
            try:
                gui.task_queue.get_nowait()
            except queue.Empty:
                break
        logging.info("Task queue cleared.")
    except Exception as e:
        logging.error("Error clearing task queue: %s", e)

    try:
        gui.list_selected_files.clear()
        gui.list_read_errors.clear()
        logging.info("File lists cleared.")
    except Exception as e:
        logging.error("Error clearing file lists: %s", e)
