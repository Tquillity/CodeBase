from __future__ import annotations

import logging
import os
import subprocess
import threading
from typing import TYPE_CHECKING, Any, Optional, cast

import pyperclip  # type: ignore[import-untyped]
from content_manager import generate_content
from exceptions import RepositoryError

if TYPE_CHECKING:
    from gui import RepoPromptGUI


class GitHandler:
    gui: Any

    def __init__(self, gui: Any) -> None:
        self.gui = gui

    def get_git_diff(self, repo_path: str) -> str:
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
            err = (e.stderr or "")
            if "bad revision 'HEAD'" in err or "ambiguous argument 'HEAD'" in err:
                return "No commits yet. Initial commit pending."
            raise RepositoryError(f"Git command failed: {e.stderr}", repo_path=repo_path)
        except FileNotFoundError:
            # git executable not found
            raise RepositoryError("Git executable not found. Please ensure git is installed.", repo_path=repo_path)
        except Exception as e:
            raise RepositoryError(f"Unexpected error running git diff: {str(e)}", repo_path=repo_path)

    def copy_diff(self) -> None:
        """
        Runs get_git_diff in a background thread and copies result to clipboard.
        """
        gui = cast("RepoPromptGUI", self.gui)
        if not gui.current_repo_path:
            gui.show_status_message("No repository loaded.", error=True)
            return

        gui.show_loading_state("Generating git diff...")

        def _worker() -> None:
            g = cast("RepoPromptGUI", self.gui)
            repo_path = g.current_repo_path
            if not repo_path:
                return
            try:
                diff_content = self.get_git_diff(repo_path)
                if not diff_content.strip():
                    g.task_queue.put((g.show_status_message, ("No changes detected (git diff is empty).",)))
                    g.task_queue.put((g.hide_loading_state, ()))
                    return
                g.task_queue.put((self._finish_copy, (diff_content,)))
            except RepositoryError as e:
                g.task_queue.put((g.show_status_message, (str(e), 5000, True)))
                g.task_queue.put((g.hide_loading_state, ()))
            except Exception as e:
                logging.error(f"Error in copy_diff worker: {e}")
                g.task_queue.put((g.show_status_message, (f"Error generating diff: {e}", 5000, True)))
                g.task_queue.put((g.hide_loading_state, ()))

        thread = threading.Thread(target=_worker, daemon=True)
        gui.register_background_thread(thread)
        thread.start()

    def _finish_copy(self, content: str) -> None:
        """
        Called from main thread via task_queue to actually copy content and update UI.
        """
        gui = cast("RepoPromptGUI", self.gui)
        try:
            pyperclip.copy(content)
            gui.show_status_message("Git diff copied to clipboard!")
        except Exception as e:
            gui.show_status_message(f"Failed to copy to clipboard: {e}", error=True)
        finally:
            gui.hide_loading_state()

    def get_git_status(self, repo_path: str | None = None) -> dict[str, Any]:
        """Return clean status dict for UI + copy operations."""
        gui = cast("RepoPromptGUI", self.gui)
        if repo_path is None:
            repo_path = gui.current_repo_path
        if not repo_path or not os.path.exists(os.path.join(repo_path, '.git')):
            return {'staged': [], 'changes': [], 'staged_deleted': set(), 'changes_deleted': set(), 'branch': '—'}

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
            staged_deleted = set()
            changes_deleted = set()

            for line in lines:
                if line.startswith('## '):
                    branch = line.split('...')[0][3:].strip() or "main"
                    continue
                if len(line) < 3:
                    continue

                # XY PATH; D = deleted
                x_status = line[0]
                y_status = line[1]
                path = line[3:].strip()
                if " -> " in path:
                    path = path.split(" -> ")[-1]
                full_path = os.path.join(repo_path, path)
                is_deleted = (x_status == 'D' or y_status == 'D')

                if x_status not in (' ', '?'):
                    staged.append(full_path)
                    if is_deleted:
                        staged_deleted.add(full_path)
                if y_status != ' ' or (x_status == '?' and y_status == '?'):
                    changes.append(full_path)
                    if is_deleted:
                        changes_deleted.add(full_path)

            return {
                'staged': sorted(list(set(staged))),
                'changes': sorted(list(set(changes))),
                'staged_deleted': staged_deleted,
                'changes_deleted': changes_deleted,
                'branch': branch
            }
        except Exception as e:
            logging.warning(f"Git status failed: {e}")
            return {'staged': [], 'changes': [], 'staged_deleted': set(), 'changes_deleted': set(), 'branch': 'error'}

    def copy_staged_changes(self) -> None:
        """Copy full content of staged files that are currently selected (☑) in the Git Status panel."""
        gui = cast("RepoPromptGUI", self.gui)
        paths = gui.git_panel.get_selected_staged_paths()
        if not paths:
            gui.show_status_message("No staged files selected to copy", error=True)
            return
        self._copy_file_list(paths, "Staged Changes")

    def copy_unstaged_changes(self) -> None:
        """Copy full content of unstaged change files that are currently selected (☑) in the Git Status panel."""
        gui = cast("RepoPromptGUI", self.gui)
        paths = gui.git_panel.get_selected_changes_paths()
        if not paths:
            gui.show_status_message("No unstaged files selected to copy", error=True)
            return
        self._copy_file_list(paths, "Unstaged Changes")

    def _copy_file_list(self, file_paths: list[str], title: str) -> None:
        """Shared helper — uses existing content pipeline (threaded)."""
        gui = cast("RepoPromptGUI", self.gui)
        if not file_paths:
            return
        if not gui.current_repo_path:
            gui.show_status_message("No repository loaded.", error=True)
            return
        repo_path = gui.current_repo_path
        current_format = gui.settings.get('app', 'copy_format', "Markdown (Grok)")
        fh = gui.file_handler
        count = len(file_paths)
        title_lower = title.lower()

        def _finish(content: str, errors: list[str]) -> None:
            gui.hide_loading_state()
            if errors:
                gui.show_status_message("Failed to copy changes", error=True)
            else:
                try:
                    pyperclip.copy(content)
                    gui.show_status_message(f"Copied {count} {title_lower} to clipboard", duration=3000)
                    logging.info(f"Copied {count} files ({title})")
                except Exception as e:
                    logging.error(f"Copy to clipboard failed: {e}")
                    gui.show_status_message("Failed to copy to clipboard", error=True)

        def completion(
            content: str,
            token_count: int,
            errors: list[str],
            deleted_files: Optional[list[str]] = None,
        ) -> None:
            gui.task_queue.put((_finish, (content, errors)))

        gui.show_loading_state(f"Preparing {title_lower}...")
        thread = threading.Thread(
            target=generate_content,
            args=(set(file_paths), repo_path, fh.lock, completion, fh.content_cache, fh.read_errors, None, gui, current_format),
            daemon=True
        )
        gui.register_background_thread(thread)
        thread.start()

