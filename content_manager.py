# content_manager.py
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Callable, Optional

import tiktoken
from constants import (
    ERROR_HANDLING_ENABLED,
    TEMPLATE_XML,
    FILE_SEPARATOR,
)
from content_generation_context import ContentGenerationContext
from lru_cache import ThreadSafeLRUCache
from path_utils import as_cache_path, get_relative_path
from exceptions import FileOperationError
from error_handler import handle_error
from security import (
    neutralize_urls,
    validate_content_security,
    validate_file_size,
)

__all__ = ["get_file_content", "generate_content", "FILE_SEPARATOR"]

# Cache entries: (content, mtime_ns, size_bytes)
CacheEntry = tuple[str, int, int]

try:
    tokenizer: Optional[Any] = tiktoken.get_encoding("cl100k_base")
except Exception as e:
    logging.warning(
        f"Failed to initialize tiktoken: {e}. Falling back to approximate token counting."
    )
    tokenizer = None


def _cached_content_if_valid(
    file_path: str,
    normalized_path: str,
    content_cache: ThreadSafeLRUCache,
) -> Optional[str]:
    """Return cached content when mtime/size still match; invalidate stale entries."""
    cached_entry = content_cache.get(normalized_path)
    if cached_entry is None:
        return None
    if not (isinstance(cached_entry, tuple) and len(cached_entry) == 3):
        content_cache.delete(normalized_path)
        return None

    cached_content, cached_mtime_ns, cached_size = cached_entry
    try:
        stat = os.stat(file_path)
    except FileNotFoundError:
        content_cache.delete(normalized_path)
        return None

    if stat.st_mtime_ns == cached_mtime_ns and stat.st_size == cached_size:
        return str(cached_content)

    content_cache.delete(normalized_path)
    return None


def get_file_content(
    file_path: str,
    content_cache: ThreadSafeLRUCache,
    lock: threading.Lock,
    read_errors: list[str],
    deleted_files: Optional[list[str]] = None,
    *,
    security_enabled: bool = False,
    max_file_size: Optional[int] = None,
) -> Optional[str]:
    normalized_path = str(as_cache_path(file_path))

    cached_content = _cached_content_if_valid(file_path, normalized_path, content_cache)
    if cached_content is not None:
        return cached_content

    if security_enabled:
        is_valid, err_msg = validate_file_size(file_path, max_size=max_file_size)
        if not is_valid:
            with lock:
                read_errors.append(f"Size: {file_path} - {err_msg}")
            return None

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()

            if security_enabled:
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext in ['.html', '.htm', '.xml', '.svg']:
                    is_valid, err_msg = validate_content_security(content, "file")
                    if not is_valid:
                        with lock:
                            read_errors.append(f"Content: {file_path} - {err_msg}")
                        return None

            stat = os.stat(file_path)
            entry: CacheEntry = (content, stat.st_mtime_ns, stat.st_size)
            content_cache.put(normalized_path, entry)
            return content
    except FileNotFoundError:
        if deleted_files is not None:
            with lock:
                deleted_files.append(file_path)
            logging.debug(f"File missing (deleted): {file_path}")
        else:
            with lock:
                read_errors.append(f"Not Found: {file_path}")
    except PermissionError:
        error = FileOperationError(
            f"Permission denied: {file_path}",
            file_path=file_path,
            operation="read",
            details={"error_type": "PermissionError"},
        )
        if ERROR_HANDLING_ENABLED:
            handle_error(error, "get_file_content", show_ui=False)
        with lock:
            read_errors.append(f"Permission Denied: {file_path}")
    except UnicodeDecodeError:
        error = FileOperationError(
            f"Cannot decode file (likely binary): {file_path}",
            file_path=file_path,
            operation="read",
            details={"error_type": "UnicodeDecodeError"},
        )
        if ERROR_HANDLING_ENABLED:
            handle_error(error, "get_file_content", show_ui=False)
        with lock:
            read_errors.append(f"Encoding Error: {file_path}")
    except Exception as e:
        error = FileOperationError(
            f"Unexpected error reading {file_path}: {str(e)}",
            file_path=file_path,
            operation="read",
            details={"error_type": type(e).__name__, "original_error": str(e)},
        )
        if ERROR_HANDLING_ENABLED:
            handle_error(error, "get_file_content", show_ui=False)
        with lock:
            read_errors.append(f"Read Error: {file_path} ({e})")

    return None


CompletionCallback = Callable[[str, int, list[str], list[str]], None]
ProgressCallback = Callable[[int, int, float], None]
CancelledCallback = Callable[[], None]


def _handle_abort(
    context: ContentGenerationContext,
    completion_callback: CompletionCallback,
    cancelled_callback: Optional[CancelledCallback],
) -> None:
    if context.should_abort_cancel() and cancelled_callback is not None:
        cancelled_callback()
        return
    completion_callback("", 0, [], [])


def generate_content(
    files_to_include: set[str],
    repo_path: str,
    lock: threading.Lock,
    completion_callback: CompletionCallback,
    content_cache: ThreadSafeLRUCache,
    context: Optional[ContentGenerationContext] = None,
    progress_callback: Optional[ProgressCallback] = None,
    template_format: str = "Markdown (Grok)",
    cancelled_callback: Optional[CancelledCallback] = None,
) -> None:
    ctx = context or ContentGenerationContext()
    start_time = time.time()
    content_parts: list[str] = []
    operation_errors: list[str] = []

    if ctx.should_abort_shutdown() or ctx.should_abort_cancel():
        logging.info("Aborting content generation before start")
        _handle_abort(ctx, completion_callback, cancelled_callback)
        return

    sorted_files = sorted(list(files_to_include))
    total_files = len(sorted_files)
    processed_count = 0
    deleted_files: list[str] = []

    for file_path in sorted_files:
        if ctx.should_abort_shutdown() or ctx.should_abort_cancel():
            logging.info("Aborting content generation during file loop")
            _handle_abort(ctx, completion_callback, cancelled_callback)
            return

        logging.debug(f"Processing file: {file_path}")

        file_content = get_file_content(
            file_path,
            content_cache,
            lock,
            operation_errors,
            deleted_files=deleted_files,
            security_enabled=ctx.security_enabled,
            max_file_size=ctx.max_file_size,
        )

        if file_content is not None:
            logging.info(f"[PREVIEW] Successfully read {os.path.basename(file_path)} ({len(file_content):,} chars)")
        else:
            logging.warning(f"[PREVIEW] Failed to read {os.path.basename(file_path)}")

        if file_content is not None:
            if ctx.sanitize_urls:
                file_content = neutralize_urls(file_content)

            rel_path = get_relative_path(file_path, repo_path) or file_path

            if template_format == TEMPLATE_XML:
                content_parts.append(f'<file path="{rel_path}">\n<![CDATA[\n{file_content}\n]]>\n</file>\n')
            else:
                ext = os.path.splitext(rel_path)[1].lstrip('.')
                content_parts.append(f"File: {rel_path}\nContent:\n```{ext}\n{file_content}\n```\n")

        processed_count += 1
        elapsed = time.time() - start_time
        if progress_callback:
            progress_callback(processed_count, total_files, elapsed)

    final_content = FILE_SEPARATOR.join(content_parts)

    if tokenizer:
        try:
            token_count = len(tokenizer.encode(final_content))
        except Exception as e:
            logging.error(f"Error counting tokens with tiktoken: {e}")
            token_count = len(final_content.split())
    else:
        token_count = len(final_content.split())

    end_time = time.time()
    logging.info(
        f"Content generation complete for {len(files_to_include)} files in "
        f"{end_time - start_time:.2f} seconds. Tokens: {token_count}"
    )
    logging.info(f"[PREVIEW] All files processed. Calling completion callback with {len(final_content):,} chars")
    completion_callback(final_content, token_count, operation_errors, deleted_files)
