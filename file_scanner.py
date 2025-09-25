# file_scanner.py
import os
import fnmatch
import mimetypes
import time
import logging
from path_utils import normalize_path, get_relative_path
from exceptions import RepositoryError, FileOperationError, SecurityError
from error_handler import handle_error, safe_execute
from constants import ERROR_HANDLING_ENABLED

def scan_repo(folder, gui, progress_callback, completion_callback, lock):
    try:
        start_time = time.time()
        abs_path = os.path.abspath(folder)
        if not os.path.commonpath([abs_path, os.path.expanduser("~")]).startswith(os.path.expanduser("~")):
            gui.root.after(0, completion_callback, None, None, set(), set(), ["Security Error: Access outside user directory is not allowed."])
            return

        repo_path = abs_path
        ignore_patterns = parse_gitignore(os.path.join(repo_path, '.gitignore'))

        scanned_files_temp = set()
        loaded_files_temp = set()
        errors = []
        file_count = 0

        # Use a single pass with os.walk for responsiveness
        for dirpath, dirnames, filenames in os.walk(repo_path, topdown=True):
            logging.debug(f"Scanning directory: {dirpath} (dirs: {len(dirnames)}, files: {len(filenames)})")
            # Filter ignored directories early to avoid walking them
            dirnames[:] = [d for d in dirnames if not is_ignored_path(os.path.join(dirpath, d), repo_path, ignore_patterns, gui)]
            logging.debug(f"After ignore filter: {len(dirnames)} dirs remain")

            for filename in filenames:
                file_count += 1
                # Update progress periodically
                if file_count % 50 == 0:  # Update every 50 files
                    elapsed = time.time() - start_time
                    message = f"Scanning... {file_count} files ({elapsed:.1f}s)"
                    gui.root.after(0, progress_callback, message)

                file_path_abs = os.path.join(dirpath, filename)
                if is_ignored_path(file_path_abs, repo_path, ignore_patterns, gui):
                    logging.debug(f"Ignored file: {file_path_abs}")
                    continue
                
                if is_text_file(file_path_abs, gui):
                    logging.debug(f"Text file found: {file_path_abs}")
                    scanned_files_temp.add(file_path_abs)
                    loaded_files_temp.add(file_path_abs)
                else:
                    logging.debug(f"Non-text file: {file_path_abs}")

        end_time = time.time()
        logging.info(f"Scan summary: {file_count} total files, {len(scanned_files_temp)} text files, {len(errors)} errors")
        logging.info(f"Scan complete for {repo_path}. Found {len(scanned_files_temp)} text files out of {file_count} total files in {end_time - start_time:.2f} seconds.")

        gui.root.after(0, completion_callback, repo_path, ignore_patterns, scanned_files_temp, loaded_files_temp, errors)

    except Exception as e:
        error = RepositoryError(
            f"Unexpected error during repository scan: {str(e)}",
            repo_path=folder,
            operation="scan_repo",
            details={"error_type": type(e).__name__, "original_error": str(e)}
        )
        if ERROR_HANDLING_ENABLED:
            handle_error(error, "scan_repo", show_ui=True)
        gui.root.after(0, completion_callback, None, None, set(), set(), [f"Unexpected scan error: {e}"])


def parse_gitignore(gitignore_path):
    ignore_patterns = []
    default_ignores = ['.git']
    # NEW_LOG
    logging.debug(f"Parsing .gitignore at {gitignore_path}")
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, 'r', encoding='utf-8', errors='ignore') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ignore_patterns.append(line)
        except Exception as e:
            logging.warning(f"Could not read .gitignore file {gitignore_path}: {e}")
    # NEW_LOG
    logging.debug(f"Parsed ignore patterns: {ignore_patterns}")
    return default_ignores + ignore_patterns

def is_ignored_path(path, repo_root, ignore_list, gui):
    rel_path = None
    try:
        rel_path = get_relative_path(path, repo_root)
        if rel_path is None:
            return False
        # NEW_LOG
        logging.debug(f"Checking if ignored: {path} (rel: {rel_path})")
        rel_path_parts = rel_path.replace('\\', '/').split('/')
        path_basename = os.path.basename(path)

        for pattern in ignore_list:
            if fnmatch.fnmatch(path_basename, pattern) or fnmatch.fnmatch(rel_path.replace('\\', '/'), pattern):
                # NEW_LOG
                logging.debug(f"Ignored '{path}' due to pattern: {pattern}")
                return True
            if pattern.endswith('/') and os.path.isdir(path) and fnmatch.fnmatch(rel_path.replace('\\', '/') + '/', pattern):
                # NEW_LOG
                logging.debug(f"Ignored directory '{path}' due to pattern: {pattern}")
                return True
            if pattern.endswith('/') and fnmatch.fnmatch(rel_path.replace('\\', '/'), pattern.rstrip('/')):
                 if os.path.isfile(path):
                      # NEW_LOG
                      logging.debug(f"Ignored file-as-dir '{path}' due to pattern: {pattern}")
                      return True

        if gui.settings.get('app', 'exclude_node_modules', 1) == 1 and 'node_modules' in rel_path_parts:
            # NEW_LOG
            logging.debug(f"Ignored '{path}' due to node_modules setting")
            return True
        if gui.settings.get('app', 'exclude_dist', 1) == 1 and 'dist' in rel_path_parts:
            # NEW_LOG
            logging.debug(f"Ignored '{path}' due to dist setting")
            return True

    except ValueError:
         # This can happen if path is not within repo_root, e.g. a different drive on Windows
         if '.git' in path.split(os.sep): return True
         if gui.settings.get('app', 'exclude_node_modules', 1) == 1 and 'node_modules' in path.split(os.sep): return True
         if gui.settings.get('app', 'exclude_dist', 1) == 1 and 'dist' in path.split(os.sep): return True
    except Exception as e:
        logging.warning(f"Error during is_ignored check for {path}: {e}")

    return False

def is_text_file(file_path, gui):
    try:
        ext = os.path.splitext(file_path)[1].lower()
        # NEW_LOG
        logging.debug(f"Determining if text: {file_path} (ext: {ext})")
        from file_handler import FileHandler
        text_extensions_settings = gui.settings.get('app', 'text_extensions', {ext: 1 for ext in FileHandler.text_extensions_default})
        
        if ext in text_extensions_settings and text_extensions_settings[ext] == 1:
             filename = os.path.basename(file_path)
             exclude_files_settings = gui.settings.get('app', 'exclude_files', {})
             if filename in exclude_files_settings and exclude_files_settings[filename] == 1:
                 # NEW_LOG
                 logging.debug(f"Not text: '{file_path}' is in exclude_files setting")
                 return False
             # NEW_LOG
             logging.debug(f"Text by extension setting: {ext}")
             return True

        if ext in text_extensions_settings and text_extensions_settings[ext] == 0:
             # NEW_LOG
             logging.debug(f"Not text: extension '{ext}' is disabled in settings")
             return False

        mime_type, encoding = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith('text/'):
             filename = os.path.basename(file_path)
             exclude_files_settings = gui.settings.get('app', 'exclude_files', {})
             if filename in exclude_files_settings and exclude_files_settings[filename] == 1:
                 # NEW_LOG
                 logging.debug(f"Not text: '{file_path}' (MIME: {mime_type}) is in exclude_files setting")
                 return False
             # NEW_LOG
             logging.debug(f"Text by MIME: {mime_type}")
             return True

    except Exception as e:
        logging.warning(f"Could not determine if {file_path} is text: {e}")
    
    # NEW_LOG
    logging.debug(f"Not text: {file_path} (default case)")
    return False