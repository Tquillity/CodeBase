import threading
import subprocess
import logging
import pyperclip
import os
from exceptions import RepositoryError
from content_manager import generate_content

class GitHandler:
    def __init__(self, gui):
        self.gui = gui

    def get_git_diff(self, repo_path):
        """
        Runs `git diff HEAD` in the specified repository path.
        Returns the diff output string or raises an error.
        """
        if not os.path.exists(os.path.join(repo_path, '.git')):
            raise RepositoryError("Not a git repository", repo_path=repo_path)

        try:
            # Run git diff HEAD
            # Using capture_output=True to capture stdout/stderr
            # text=True to get string output instead of bytes
            result = subprocess.run(
                ['git', 'diff', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            # git command returned non-zero exit code
            raise RepositoryError(f"Git command failed: {e.stderr}", repo_path=repo_path)
        except FileNotFoundError:
            # git executable not found
            raise RepositoryError("Git executable not found. Please ensure git is installed.", repo_path=repo_path)
        except Exception as e:
            raise RepositoryError(f"Unexpected error running git diff: {str(e)}", repo_path=repo_path)

    def copy_diff(self):
        """
        Runs get_git_diff in a background thread and copies result to clipboard.
        """
        if not self.gui.current_repo_path:
            self.gui.show_status_message("No repository loaded.", error=True)
            return

        self.gui.show_loading_state("Generating git diff...")
        
        def _worker():
            try:
                diff_content = self.get_git_diff(self.gui.current_repo_path)
                
                if not diff_content.strip():
                    self.gui.task_queue.put((self.gui.show_status_message, ("No changes detected (git diff is empty).",)))
                    self.gui.task_queue.put((self.gui.hide_loading_state, ()))
                    return

                # Success - copy to clipboard (must happen in main thread usually, but pyperclip is often thread safe enough or we can queue it)
                # Better to queue the copy action to be safe and UI update
                self.gui.task_queue.put((self._finish_copy, (diff_content,)))
                
            except RepositoryError as e:
                self.gui.task_queue.put((self.gui.show_status_message, (str(e), 5000, True)))
                self.gui.task_queue.put((self.gui.hide_loading_state, ()))
            except Exception as e:
                logging.error(f"Error in copy_diff worker: {e}")
                self.gui.task_queue.put((self.gui.show_status_message, (f"Error generating diff: {e}", 5000, True)))
                self.gui.task_queue.put((self.gui.hide_loading_state, ()))

        thread = threading.Thread(target=_worker, daemon=True)
        self.gui.register_background_thread(thread)
        thread.start()

    def _finish_copy(self, content):
        """
        Called from main thread via task_queue to actually copy content and update UI.
        """
        try:
            pyperclip.copy(content)
            self.gui.show_status_message("Git diff copied to clipboard!")
        except Exception as e:
            self.gui.show_status_message(f"Failed to copy to clipboard: {e}", error=True)
        finally:
            self.gui.hide_loading_state()

    def get_git_status(self, repo_path: str = None) -> dict:
        """Return clean status dict for UI + copy operations."""
        if repo_path is None:
            repo_path = self.gui.current_repo_path
        if not repo_path or not os.path.exists(os.path.join(repo_path, '.git')):
            return {'staged': [], 'changes': [], 'branch': '—'}

        try:
            # --porcelain=v1 gives a 2-character status code
            result = subprocess.run(
                ['git', 'status', '--porcelain=v1', '--branch', '--untracked-files=all'],
                cwd=repo_path, capture_output=True, text=True, timeout=5, check=True
            )
            lines = result.stdout.strip().splitlines()
            branch = "main"
            staged = []
            changes = []

            for line in lines:
                if line.startswith('## '):
                    branch = line.split('...')[0][3:].strip() or "main"
                    continue
                if len(line) < 3:
                    continue

                # XY PATH
                # X = Index (Staged), Y = Work tree (Unstaged)
                x_status = line[0]
                y_status = line[1]
                path = line[3:].strip()

                # Handle renames (R  old -> new)
                if " -> " in path:
                    path = path.split(" -> ")[-1]

                full_path = os.path.join(repo_path, path)

                # 1. Check if staged (X is not space and not ?)
                if x_status not in (' ', '?'):
                    staged.append(full_path)

                # 2. Check if unstaged (Y is not space) OR untracked (??)
                if y_status != ' ' or (x_status == '?' and y_status == '?'):
                    changes.append(full_path)

            return {
                'staged': sorted(list(set(staged))),
                'changes': sorted(list(set(changes))),
                'branch': branch
            }
        except Exception as e:
            logging.warning(f"Git status failed: {e}")
            return {'staged': [], 'changes': [], 'branch': 'error'}

    def copy_staged_changes(self):
        """Copy full content of all staged files (formatted)."""
        status = self.get_git_status()
        if not status['staged']:
            self.gui.show_status_message("No staged changes to copy", error=True)
            return
        self._copy_file_list(status['staged'], "Staged Changes")

    def copy_unstaged_changes(self):
        """Copy full content of all unstaged changes."""
        status = self.get_git_status()
        if not status['changes']:
            self.gui.show_status_message("No unstaged changes to copy", error=True)
            return
        self._copy_file_list(status['changes'], "Unstaged Changes")

    def _copy_file_list(self, file_paths: list, title: str):
        """Shared helper — uses existing content pipeline (threaded)."""
        if not file_paths:
            return
        if not self.gui.current_repo_path:
            self.gui.show_status_message("No repository loaded.", error=True)
            return
        repo_path = self.gui.current_repo_path
        current_format = self.gui.settings.get('app', 'copy_format', "Markdown (Grok)")
        fh = self.gui.file_handler
        count = len(file_paths)
        title_lower = title.lower()

        def _finish(content, errors):
            self.gui.hide_loading_state()
            if errors:
                self.gui.show_status_message("Failed to copy changes", error=True)
            else:
                try:
                    pyperclip.copy(content)
                    self.gui.show_status_message(f"Copied {count} {title_lower} to clipboard", duration=3000)
                    logging.info(f"Copied {count} files ({title})")
                except Exception as e:
                    logging.error(f"Copy to clipboard failed: {e}")
                    self.gui.show_status_message("Failed to copy to clipboard", error=True)

        def completion(content, token_count, errors):
            self.gui.task_queue.put((_finish, (content, errors)))

        self.gui.show_loading_state(f"Preparing {title_lower}...")
        thread = threading.Thread(
            target=generate_content,
            args=(set(file_paths), repo_path, fh.lock, completion, fh.content_cache, fh.read_errors, None, self.gui, current_format),
            daemon=True
        )
        self.gui.register_background_thread(thread)
        thread.start()

