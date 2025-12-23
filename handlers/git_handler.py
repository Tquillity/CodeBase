import threading
import subprocess
import logging
import pyperclip
import os
from exceptions import RepositoryError

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

