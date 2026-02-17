import os
import time
import threading
import logging
import tiktoken
from typing import Optional, List, Any, Callable
from constants import FILE_SEPARATOR, CACHE_MAX_SIZE, CACHE_MAX_MEMORY_MB, ERROR_HANDLING_ENABLED, SECURITY_ENABLED, TEMPLATE_XML

# Initialize tokenizer
try:
    tokenizer = tiktoken.get_encoding("cl100k_base")
except Exception as e:
    logging.warning(f"Failed to initialize tiktoken: {e}. Falling back to approximate token counting.")
    tokenizer = None
from lru_cache import ThreadSafeLRUCache
from path_utils import normalize_for_cache, get_relative_path
from exceptions import FileOperationError, RepositoryError
from error_handler import handle_error, safe_execute
from security import validate_file_size, validate_content_security, neutralize_urls

def get_file_content(file_path: str, content_cache: ThreadSafeLRUCache, lock: threading.Lock, read_errors: List[str], deleted_files: Optional[List[str]] = None) -> Optional[str]:
    # Use normalized path for cache keys for cross-platform consistency
    normalized_path = normalize_for_cache(file_path)
    
    # Check cache (LRU cache handles its own locking)
    cached_content = content_cache.get(normalized_path)
    if cached_content is not None:
        return cached_content

    # Enhanced security validation (only for suspicious files)
    if SECURITY_ENABLED:
        # Only validate file size for normal repository files
        is_valid, error = validate_file_size(file_path)
        if not is_valid:
            with lock:
                read_errors.append(f"Size: {file_path} - {error}")
            return None

    try:
        # Use original case-sensitive file_path for OS file operations
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
            # Additional content security validation (only for suspicious content)
            if SECURITY_ENABLED:
                # Only validate content for files that might be dangerous
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext in ['.html', '.htm', '.xml', '.svg']:
                    is_valid, error = validate_content_security(content, "file")
                    if not is_valid:
                        with lock:
                            read_errors.append(f"Content: {file_path} - {error}")
                        return None
            
            # Store in LRU cache (handles its own locking)
            content_cache.put(normalized_path, content)
            return content
    except FileNotFoundError:
        if deleted_files is not None:
            with lock:
                deleted_files.append(file_path)
            logging.debug(f"File missing (deleted): {file_path}")
        else:
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

def generate_content(files_to_include: set, repo_path: str, lock: threading.Lock, completion_callback: Callable, content_cache: ThreadSafeLRUCache, read_errors: List[str], progress_callback: Optional[Callable] = None, gui: Optional[Any] = None, template_format: str = "Markdown (Grok)") -> None:
    try:
        start_time = time.time()
        content_parts = []
        
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
    deleted_files = []

    for file_path in sorted_files:
        # Check for shutdown during processing
        if gui and hasattr(gui, '_shutdown_requested') and gui._shutdown_requested:
            logging.info("Shutdown requested during content generation, aborting")
            return
        
        logging.debug(f"Processing file: {file_path}")
        
        file_content = get_file_content(file_path, content_cache, lock, read_errors, deleted_files=deleted_files)

        if file_content is not None:
            logging.info(f"[PREVIEW] Successfully read {os.path.basename(file_path)} ({len(file_content):,} chars)")
        else:
            logging.warning(f"[PREVIEW] Failed to read {os.path.basename(file_path)}")

        if file_content is not None:
            # Apply URL neutralization if setting is enabled
            if gui and gui.settings.get('app', 'sanitize_urls', 0) == 1:
                file_content = neutralize_urls(file_content)
            
            rel_path = get_relative_path(file_path, repo_path) or file_path
            
            if template_format == TEMPLATE_XML:
                content_parts.append(f'<file path="{rel_path}">\n<![CDATA[\n{file_content}\n]]>\n</file>\n')
            else:
                # Default to Markdown
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
    logging.info(f"Content generation complete for {len(files_to_include)} files in {end_time - start_time:.2f} seconds. Tokens: {token_count}")
    logging.info(f"[PREVIEW] All files processed. Calling completion callback with {len(final_content):,} chars")
    completion_callback(final_content, token_count, read_errors, deleted_files)