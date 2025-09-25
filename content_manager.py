import os
import time
import threading
import logging
from constants import FILE_SEPARATOR, CACHE_MAX_SIZE, CACHE_MAX_MEMORY_MB, ERROR_HANDLING_ENABLED
from lru_cache import ThreadSafeLRUCache
from path_utils import normalize_for_cache, get_relative_path
from exceptions import FileOperationError, RepositoryError
from error_handler import handle_error, safe_execute

def get_file_content(file_path, content_cache, lock, read_errors):
    # Use normalized path for cache keys for cross-platform consistency
    normalized_path = normalize_for_cache(file_path)
    
    # Check cache (LRU cache handles its own locking)
    cached_content = content_cache.get(normalized_path)
    if cached_content is not None:
        return cached_content

    try:
        # FIX: Use the original, case-sensitive file_path for opening the file.
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            # Store in LRU cache (handles its own locking)
            content_cache.put(normalized_path, content)
            return content
    except FileNotFoundError as e:
        error = FileOperationError(
            f"File not found: {file_path}",
            file_path=file_path,
            operation="read",
            details={"error_type": "FileNotFoundError"}
        )
        if ERROR_HANDLING_ENABLED:
            handle_error(error, "get_file_content", show_ui=False)
        with lock:
            read_errors.append(f"Not Found: {file_path}")
    except PermissionError as e:
        error = FileOperationError(
            f"Permission denied: {file_path}",
            file_path=file_path,
            operation="read",
            details={"error_type": "PermissionError"}
        )
        if ERROR_HANDLING_ENABLED:
            handle_error(error, "get_file_content", show_ui=False)
        with lock:
            read_errors.append(f"Permission Denied: {file_path}")
    except UnicodeDecodeError as e:
        error = FileOperationError(
            f"Cannot decode file (likely binary): {file_path}",
            file_path=file_path,
            operation="read",
            details={"error_type": "UnicodeDecodeError"}
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
            details={"error_type": type(e).__name__, "original_error": str(e)}
        )
        if ERROR_HANDLING_ENABLED:
            handle_error(error, "get_file_content", show_ui=False)
        with lock:
            read_errors.append(f"Read Error: {file_path} ({e})")

    return None

def generate_content(files_to_include, repo_path, lock, completion_callback, content_cache, read_errors, progress_callback=None, gui=None):
    try:
        start_time = time.time()
        content_parts = []
        # Create a local list for errors found during this specific generation
        local_read_errors = []
        
        # Check if shutdown was requested
        if gui and hasattr(gui, '_shutdown_requested') and gui._shutdown_requested:
            logging.info("Shutdown requested, aborting content generation")
            return
        
        # Clear the shared read_errors list before starting a new generation
        with lock:
            read_errors.clear()
    except Exception as e:
        error = RepositoryError(
            f"Failed to initialize content generation: {str(e)}",
            repo_path=repo_path,
            operation="generate_content",
            details={"error_type": type(e).__name__}
        )
        if ERROR_HANDLING_ENABLED:
            handle_error(error, "generate_content", show_ui=True)
        return

    sorted_files = sorted(list(files_to_include))
    total_files = len(sorted_files)
    processed_count = 0

    for file_path in sorted_files:
        # Check for shutdown during processing
        if gui and hasattr(gui, '_shutdown_requested') and gui._shutdown_requested:
            logging.info("Shutdown requested during content generation, aborting")
            return
            
        # The get_file_content function will append to the shared read_errors list
        file_content = get_file_content(file_path, content_cache, lock, read_errors)
        
        if file_content is not None:
            rel_path = get_relative_path(file_path, repo_path) or file_path
            ext = os.path.splitext(rel_path)[1].lstrip('.')
            content_parts.append(f"File: {rel_path}\nContent:\n```{ext}\n{file_content}\n```\n")

        processed_count += 1
        elapsed = time.time() - start_time
        if progress_callback:
            progress_callback(processed_count, total_files, elapsed)

    final_content = FILE_SEPARATOR.join(content_parts)
    token_count = len(final_content.split())
    end_time = time.time()
    logging.info(f"Content generation complete for {len(files_to_include)} files in {end_time - start_time:.2f} seconds. Tokens: {token_count}")

    # Pass the collected errors from this run to the callback
    completion_callback(final_content, token_count, read_errors)