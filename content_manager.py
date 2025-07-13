import os
import time
import threading
import logging

FILE_SEPARATOR = "===FILE_SEPARATOR===\n"

def get_file_content(file_path, content_cache, lock, read_errors):
    # Use normalized path for cache keys for cross-platform consistency
    normalized_path = os.path.normcase(file_path)
    with lock:
        if normalized_path in content_cache:
            return content_cache[normalized_path]

    try:
        # FIX: Use the original, case-sensitive file_path for opening the file.
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            with lock:
                # Still use the normalized path for the cache key
                content_cache[normalized_path] = content
            return content
    except FileNotFoundError:
        logging.error(f"File not found during read: {file_path}")
        read_errors.append(f"Not Found: {file_path}")
    except PermissionError:
        logging.error(f"Permission denied during read: {file_path}")
        read_errors.append(f"Permission Denied: {file_path}")
    except UnicodeDecodeError:
        logging.warning(f"Cannot decode file (likely binary): {file_path}")
        read_errors.append(f"Encoding Error: {file_path}")
    except Exception as e:
        logging.error(f"Error reading {file_path}: {str(e)}")
        read_errors.append(f"Read Error: {file_path} ({e})")

    return None

def generate_content(files_to_include, repo_path, lock, completion_callback, content_cache, read_errors):
    start_time = time.time()
    content_parts = []
    # Create a local list for errors found during this specific generation
    local_read_errors = []
    
    # Clear the shared read_errors list before starting a new generation
    read_errors.clear()

    sorted_files = sorted(list(files_to_include))
    total_files = len(sorted_files)
    processed_count = 0

    for file_path in sorted_files:
        # The get_file_content function will append to the shared read_errors list
        file_content = get_file_content(file_path, content_cache, lock, read_errors)
        
        if file_content is not None:
            try:
                rel_path = os.path.relpath(file_path, repo_path)
            except ValueError:
                rel_path = file_path
            ext = os.path.splitext(rel_path)[1].lstrip('.')
            content_parts.append(f"File: {rel_path}\nContent:\n```{ext}\n{file_content}\n```\n")

        processed_count += 1

    final_content = FILE_SEPARATOR.join(content_parts)
    token_count = len(final_content.split())
    end_time = time.time()
    logging.info(f"Content generation complete for {len(files_to_include)} files in {end_time - start_time:.2f} seconds. Tokens: {token_count}")

    # Pass the collected errors from this run to the callback
    completion_callback(final_content, token_count, read_errors)