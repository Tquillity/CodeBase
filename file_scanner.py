# file_scanner.py
import os
import fnmatch
import mimetypes
import time
import logging
from path_utils import normalize_path, get_relative_path
from exceptions import RepositoryError, FileOperationError, SecurityError
from error_handler import handle_error, safe_execute
from constants import ERROR_HANDLING_ENABLED, MAX_FILE_SIZE

def yield_repo_files(repo_path, ignore_patterns, gui):
    """
    Generator that yields all non-ignored file paths in the repository.
    """
    for dirpath, dirnames, filenames in os.walk(repo_path, topdown=True):
        logging.debug(f"Scanning directory: {dirpath} (dirs: {len(dirnames)}, files: {len(filenames)})")
        # Filter ignored directories early to avoid walking them
        dirnames[:] = [d for d in dirnames if not is_ignored_path(os.path.join(dirpath, d), repo_path, ignore_patterns, gui)]
        
        for filename in filenames:
            file_path_abs = os.path.join(dirpath, filename)
            if not is_ignored_path(file_path_abs, repo_path, ignore_patterns, gui):
                yield file_path_abs

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

        # Use unified generator for file discovery
        for file_path_abs in yield_repo_files(repo_path, ignore_patterns, gui):
            file_count += 1
            # Update progress periodically
            if file_count % 50 == 0:  # Update every 50 files
                elapsed = time.time() - start_time
                message = f"Scanning... {file_count} files ({elapsed:.1f}s)"
                gui.root.after(0, progress_callback, message)

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
    logging.debug(f"Parsed ignore patterns: {ignore_patterns}")
    return default_ignores + ignore_patterns

def is_ignored_path(path, repo_root, ignore_list, gui):
    rel_path = None
    try:
        rel_path = get_relative_path(path, repo_root)
        if rel_path is None:
            return False
        logging.debug(f"Checking if ignored: {path} (rel: {rel_path})")
        rel_path_parts = rel_path.split('/')
        path_basename = os.path.basename(path)

        for pattern in ignore_list:
            if fnmatch.fnmatch(path_basename, pattern) or fnmatch.fnmatch(rel_path, pattern):
                logging.debug(f"Ignored '{path}' due to pattern: {pattern}")
                return True
            if pattern.endswith('/') and os.path.isdir(path) and fnmatch.fnmatch(rel_path + '/', pattern):
                logging.debug(f"Ignored directory '{path}' due to pattern: {pattern}")
                return True
            if pattern.endswith('/') and fnmatch.fnmatch(rel_path, pattern.rstrip('/')):
                 if os.path.isfile(path):
                      logging.debug(f"Ignored file-as-dir '{path}' due to pattern: {pattern}")
                      return True

        if gui.settings.get('app', 'exclude_node_modules', 1) == 1 and 'node_modules' in rel_path_parts:
            logging.debug(f"Ignored '{path}' due to node_modules setting")
            return True
        if gui.settings.get('app', 'exclude_dist', 1) == 1 and 'dist' in rel_path_parts:
            logging.debug(f"Ignored '{path}' due to dist setting")
            return True
        if gui.settings.get('app', 'exclude_coverage', 1) == 1 and any(part.lower() in ['coverage', 'htmlcov', 'cov_html'] for part in rel_path_parts):
            logging.debug(f"Ignored '{path}' due to coverage setting")
            return True
        
        # Virtual environment check
        if any(part in rel_path_parts for part in ['venv', 'env', 'ENV']):
            logging.debug(f"Ignored '{path}' (virtual environment)")
            return True
        
        # Check for test file exclusion
        exclude_test_files_setting = gui.settings.get('app', 'exclude_test_files', 0)
        if exclude_test_files_setting == 1 and is_test_file(path, rel_path):
            logging.info(f"Ignored '{path}' due to test file exclusion setting (exclude_test_files={exclude_test_files_setting})")
            return True
        elif exclude_test_files_setting == 0 and is_test_file(path, rel_path):
            logging.info(f"Including test file '{path}' (exclude_test_files={exclude_test_files_setting})")

    except ValueError:
         # This can happen if path is not within repo_root
         if '.git' in path.split(os.sep): return True
         if gui.settings.get('app', 'exclude_node_modules', 1) == 1 and 'node_modules' in path.split(os.sep): return True
         if gui.settings.get('app', 'exclude_dist', 1) == 1 and 'dist' in path.split(os.sep): return True
         if gui.settings.get('app', 'exclude_coverage', 1) == 1 and any(part.lower() in ['coverage', 'htmlcov', 'cov_html'] for part in path.split(os.sep)): return True
         if gui.settings.get('app', 'exclude_test_files', 0) == 1 and is_test_file(path, None): return True
    except Exception as e:
        logging.warning(f"Error during is_ignored check for {path}: {e}")

    return False

def is_text_file(file_path, gui):
    try:
        # Check file size first
        try:
            if os.path.getsize(file_path) > MAX_FILE_SIZE:
                logging.debug(f"Not text: '{file_path}' exceeds MAX_FILE_SIZE")
                return False
        except OSError:
            return False

        ext = os.path.splitext(file_path)[1].lower()
        # Explicitly skip known binary extensions
        if ext in ['.so', '.bin', '.dylib', '.pyc', '.pyo']:
             logging.debug(f"Not text: '{file_path}' has binary extension")
             return False

        logging.debug(f"Determining if text: {file_path} (ext: {ext})")
        from file_handler import FileHandler
        text_extensions_settings = gui.settings.get('app', 'text_extensions', {ext: 1 for ext in FileHandler.text_extensions_default})
        
        # Helper for null byte check
        def has_null_bytes(path):
            try:
                with open(path, 'rb') as f:
                    return b'\x00' in f.read(1024)
            except Exception:
                return False

        if ext in text_extensions_settings and text_extensions_settings[ext] == 1:
            filename = os.path.basename(file_path)
            exclude_files_settings = gui.settings.get('app', 'exclude_files', {})
            if filename in exclude_files_settings and exclude_files_settings[filename] == 1:
                logging.debug(f"Not text: '{file_path}' is in exclude_files setting")
                return False
            
            # Null byte check
            if has_null_bytes(file_path):
                logging.debug(f"Not text: '{file_path}' contains null bytes (binary)")
                return False

            logging.debug(f"Text by extension setting: {ext}")
            return True

        if ext in text_extensions_settings and text_extensions_settings[ext] == 0:
            logging.debug(f"Not text: extension '{ext}' is disabled in settings")
            return False

        mime_type, encoding = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith('text/'):
            filename = os.path.basename(file_path)
            exclude_files_settings = gui.settings.get('app', 'exclude_files', {})
            if filename in exclude_files_settings and exclude_files_settings[filename] == 1:
                logging.debug(f"Not text: '{file_path}' (MIME: {mime_type}) is in exclude_files setting")
                return False
            
            # Null byte check
            if has_null_bytes(file_path):
                logging.debug(f"Not text: '{file_path}' contains null bytes (binary)")
                return False

            logging.debug(f"Text by MIME: {mime_type}")
            return True

    except Exception as e:
        logging.warning(f"Could not determine if {file_path} is text: {e}")
    
    logging.debug(f"Not text: {file_path} (default case)")
    return False

def is_test_file(file_path, rel_path):
    """Check if a file is a test file based on common test file patterns."""
    try:
        filename = os.path.basename(file_path).lower()
        rel_path_lower = rel_path.lower() if rel_path else ""
        
        # Common test file patterns
        test_patterns = [
            # Test directories
            'test', 'tests', 'testing', 'spec', 'specs', '__tests__', 'test_',
            # Test file prefixes/suffixes
            'test_', '_test', '.test.', '.spec.', '_spec',
            # Common test file names
            'test.py', 'tests.py', 'test.js', 'tests.js', 'test.ts', 'tests.ts',
            'test.rb', 'tests.rb', 'test.go', 'tests.go', 'test.java', 'tests.java',
            'test.php', 'tests.php', 'test.c', 'tests.c', 'test.cpp', 'tests.cpp',
            'test.rs', 'tests.rs', 'test.swift', 'tests.swift', 'test.kt', 'tests.kt',
            'test.scala', 'tests.scala', 'test.clj', 'tests.clj', 'test.ex', 'tests.ex',
            'test.exs', 'tests.exs', 'test.erl', 'tests.erl', 'test.hs', 'tests.hs',
            'test.ml', 'tests.ml', 'test.fs', 'tests.fs', 'test.f90', 'tests.f90',
            'test.pl', 'tests.pl', 'test.pm', 'tests.pm', 'test.t', 'tests.t',
            'test.sh', 'tests.sh', 'test.bat', 'tests.bat', 'test.ps1', 'tests.ps1'
        ]
        
        # Check if any part of the path contains test patterns
        for pattern in test_patterns:
            if pattern in rel_path_lower or pattern in filename:
                return True
                
        return False
        
    except Exception as e:
        logging.warning(f"Error checking if {file_path} is test file: {e}")
        return False