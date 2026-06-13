from __future__ import annotations

import logging
import tkinter as tk
from typing import TYPE_CHECKING, Any, Optional, cast

import pyperclip  # type: ignore[import-untyped]
import knowledge_graph as kg
from constants import ERROR_MESSAGE_DURATION
from handlers.content_worker import start_content_generation

if TYPE_CHECKING:
    from gui import RepoPromptGUI


class CopyHandler:
    gui: Any

    def __init__(self, gui: Any) -> None:
        self.gui = gui

    def copy_contents(self) -> None:
        gui = cast("RepoPromptGUI", self.gui)
        if gui.is_loading:
            gui.show_status_message("Loading...", error=True)
            return
        with gui.file_handler.lock:
            if not gui.file_handler.loaded_files:
                gui.show_status_message("No files selected to copy.", error=True)
                return

        gui.show_loading_state("Preparing content for clipboard...")
        prompt = gui.base_prompt_tab.base_prompt_text.get("1.0", tk.END).strip() if gui.prepend_var.get() else ""
        current_format = gui.settings.get('app', 'copy_format', "Markdown (Grok)")
        with gui.file_handler.lock:
            files_to_copy = set(gui.file_handler.loaded_files)

        repo_path = gui.current_repo_path
        if not repo_path:
            gui.hide_loading_state()
            gui.show_status_message("No repository loaded.", error=True)
            return

        def completion(content: str, token_count: int, errors: list[str], deleted_files: Optional[list[str]] = None) -> None:
            gui.task_queue.put((
                self._handle_copy_completion_final,
                (
                    prompt,
                    content,
                    None,
                    errors,
                    "Copied selected file contents" if not errors else "Copy failed with errors",
                    deleted_files or [],
                    list(files_to_copy),
                    repo_path,
                ),
            ))

        start_content_generation(
            gui,
            files=files_to_copy,
            repo_path=repo_path,
            lock=gui.file_handler.lock,
            content_cache=gui.file_handler.content_cache,
            template_format=current_format,
            on_complete=completion,
            thread_name="CopyContents",
            error_prefix="Copy contents failed",
        )

    def copy_structure(self) -> None:
        gui = cast("RepoPromptGUI", self.gui)
        if gui.is_loading:
            gui.show_status_message("Loading...", error=True)
            return
        if not gui.structure_tab.tree.get_children():
            gui.show_status_message("No structure to copy.", error=True)
            return

        try:
            structure_text = gui.structure_tab.generate_folder_structure_text()
            if not structure_text:
                gui.show_status_message("Generated structure is empty.", error=True)
                return
            pyperclip.copy(structure_text)
            gui.show_status_message("Folder structure copied to clipboard.")
        except Exception as e:
            logging.error(f"Error generating/copying structure: {e}", exc_info=True)
            gui.show_status_message("Error copying structure!", error=True)
            gui.show_toast(f"Could not copy structure: {e}", toast_type="error")

    def copy_all(self) -> None:
        gui = cast("RepoPromptGUI", self.gui)
        if gui.is_loading:
            gui.show_status_message("Loading...", error=True)
            return
        with gui.file_handler.lock:
            no_files = not gui.file_handler.loaded_files
        no_structure = not gui.structure_tab.tree.get_children()
        no_prompt = not gui.base_prompt_tab.base_prompt_text.get("1.0", tk.END).strip()

        if no_files and no_structure and no_prompt:
            gui.show_status_message("Nothing to copy.", error=True)
            return

        gui.show_loading_state("Preparing combined content for clipboard...")
        prompt = gui.base_prompt_tab.base_prompt_text.get("1.0", tk.END).strip()
        structure = gui.structure_tab.generate_folder_structure_text() if not no_structure else ""
        current_format = gui.settings.get('app', 'copy_format', "Markdown (Grok)")

        with gui.file_handler.lock:
            files_to_copy = set(gui.file_handler.loaded_files) if not no_files else set()

        repo_path = gui.current_repo_path

        if files_to_copy:
            if not repo_path:
                gui.hide_loading_state()
                gui.show_status_message("No repository loaded.", error=True)
                return

            def completion(content: str, token_count: int, errors: list[str], deleted_files: Optional[list[str]] = None) -> None:
                gui.task_queue.put((
                    self._handle_copy_completion_final,
                    (
                        prompt,
                        content,
                        structure,
                        errors,
                        "Copied All (Prompt, Content, Structure)" if not errors else "Copy All failed with errors",
                        deleted_files or [],
                        list(files_to_copy),
                        repo_path,
                    ),
                ))

            start_content_generation(
                gui,
                files=files_to_copy,
                repo_path=repo_path,
                lock=gui.file_handler.lock,
                content_cache=gui.file_handler.content_cache,
                template_format=current_format,
                on_complete=completion,
                thread_name="CopyAll",
                error_prefix="Copy all failed",
            )
        else:
            self._handle_copy_completion_final(
                prompt=prompt,
                content="",
                structure=structure,
                errors=[],
                status_message="Copied All (Prompt, Structure)",
                deleted_files=[],
                files_copied=None,
                repo_path=repo_path,
            )

    def _handle_copy_completion_final(
        self,
        prompt: str,
        content: str,
        structure: Any,
        errors: list[str],
        status_message: str,
        deleted_files: Optional[list[str]] = None,
        files_copied: Optional[list[str]] = None,
        repo_path: Optional[str] = None,
    ) -> None:
        deleted_files = deleted_files or []
        gui = cast("RepoPromptGUI", self.gui)
        gui.hide_loading_state()

        if not errors and files_copied and repo_path:
            try:
                kg.record_copy_event(repo_path, files_copied)
            except Exception as e:
                logging.warning("Failed to record copy event in knowledge graph: %s", e, exc_info=True)

        if errors:
            error_msg = "Errors occurred during content preparation for copy."
            error_msg += f" Files: {'; '.join(errors[:3])}"
            gui.show_status_message(error_msg, error=True, duration=ERROR_MESSAGE_DURATION)
            gui.show_toast(error_msg, toast_type="warning")
        elif deleted_files:
            gui.show_toast(f"{len(deleted_files)} deleted file(s) not copied.", toast_type="info")

        final_parts = []
        if prompt:
            final_parts.append(prompt)

        if content:
            if final_parts:
                final_parts.append("\n\n---\n\n")
            final_parts.append(content.rstrip())

        if structure:
            if final_parts:
                final_parts.append("\n\n---\n\n")
            final_parts.append("Folder Structure:\n")
            final_parts.append(structure)

        final_string = "".join(final_parts)

        if not final_string and not errors:
            gui.show_status_message("Nothing generated to copy.", error=True)
            return

        try:
            pyperclip.copy(final_string)
            gui.show_status_message(status_message)
        except Exception as e:
            logging.error(f"Error copying to clipboard: {e}", exc_info=True)
            gui.show_status_message("Error copying to clipboard!", error=True)
            gui.show_toast(f"Could not copy combined content to clipboard: {e}", toast_type="error")
