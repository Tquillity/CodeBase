import pyperclip
import logging
import tkinter as tk
from content_manager import generate_content
from constants import ERROR_MESSAGE_DURATION

class CopyHandler:
    def __init__(self, gui):
        self.gui = gui

    def copy_contents(self):
        if self.gui.is_loading: self.gui.show_status_message("Loading...", error=True); return
        with self.gui.file_handler.lock:
             if not self.gui.file_handler.loaded_files:
                  self.gui.show_status_message("No files selected to copy.", error=True); return

        self.gui.show_loading_state("Preparing content for clipboard...")
        prompt = self.gui.base_prompt_tab.base_prompt_text.get("1.0", tk.END).strip() if self.gui.prepend_var.get() else ""
        
        # FIX: Get current format
        current_format = self.gui.settings.get('app', 'copy_format', "Markdown (Grok)")
        
        with self.gui.file_handler.lock:
            files_to_copy = set(self.gui.file_handler.loaded_files)

        completion_lambda = lambda content, token_count, errors: self._handle_copy_completion_final(
            prompt=prompt,
            content=content,
            structure=None,
            errors=errors,
            status_message="Copied selected file contents" if not errors else "Copy failed with errors"
        )

        # FIX: Pass current_format as the last argument
        generate_content(files_to_copy, self.gui.current_repo_path, self.gui.file_handler.lock, completion_lambda, self.gui.file_handler.content_cache, self.gui.file_handler.read_errors, None, self.gui, current_format)

    def copy_structure(self):
        if self.gui.is_loading: self.gui.show_status_message("Loading...", error=True); return
        if not self.gui.structure_tab.tree.get_children():
             self.gui.show_status_message("No structure to copy.", error=True); return

        try:
            structure_text = self.gui.structure_tab.generate_folder_structure_text()
            if not structure_text:
                 self.gui.show_status_message("Generated structure is empty.", error=True)
                 return
            pyperclip.copy(structure_text)
            self.gui.show_status_message("Folder structure copied to clipboard.")
        except Exception as e:
            logging.error(f"Error generating/copying structure: {e}", exc_info=True)
            self.gui.show_status_message("Error copying structure!", error=True)
            self.gui.show_toast(f"Could not copy structure: {e}", toast_type="error")

    def copy_all(self):
        if self.gui.is_loading: self.gui.show_status_message("Loading...", error=True); return
        with self.gui.file_handler.lock:
             no_files = not self.gui.file_handler.loaded_files
        no_structure = not self.gui.structure_tab.tree.get_children()
        no_prompt = not self.gui.base_prompt_tab.base_prompt_text.get("1.0", tk.END).strip()

        if no_files and no_structure and no_prompt:
             self.gui.show_status_message("Nothing to copy.", error=True); return

        self.gui.show_loading_state("Preparing combined content for clipboard...")

        prompt = self.gui.base_prompt_tab.base_prompt_text.get("1.0", tk.END).strip()
        structure = self.gui.structure_tab.generate_folder_structure_text() if not no_structure else ""
        
        # FIX: Get current format
        current_format = self.gui.settings.get('app', 'copy_format', "Markdown (Grok)")

        with self.gui.file_handler.lock:
             files_to_copy = set(self.gui.file_handler.loaded_files) if not no_files else set()

        completion_lambda = lambda content, token_count, errors, deleted_files=None: self._handle_copy_completion_final(
            prompt=prompt,
            content=content,
            structure=structure,
            errors=errors,
            status_message="Copied All (Prompt, Content, Structure)" if not errors else "Copy All failed with errors",
            deleted_files=deleted_files or []
        )

        if files_to_copy:
            # FIX: Pass current_format as the last argument
            generate_content(files_to_copy, self.gui.current_repo_path, self.gui.file_handler.lock, completion_lambda, self.gui.file_handler.content_cache, self.gui.file_handler.read_errors, None, self.gui, current_format)
        else:
            self._handle_copy_completion_final(prompt=prompt, content="", structure=structure, errors=[], status_message="Copied All (Prompt, Structure)", deleted_files=[])

    def _handle_copy_completion_final(self, prompt, content, structure, errors, status_message, deleted_files=None):
         deleted_files = deleted_files or []
         self.gui.hide_loading_state()

         if errors:
             error_msg = "Errors occurred during content preparation for copy."
             error_msg += f" Files: {'; '.join(errors[:3])}"
             self.gui.show_status_message(error_msg, error=True, duration=ERROR_MESSAGE_DURATION)
             self.gui.show_toast(error_msg, toast_type="warning")
         elif deleted_files:
             self.gui.show_toast(f"{len(deleted_files)} deleted file(s) not copied.", toast_type="info")

         final_parts = []
         if prompt:
             final_parts.append(prompt)

         if content:
             if final_parts: final_parts.append("\n\n---\n\n")
             final_parts.append(content.rstrip())

         if structure:
             if final_parts: final_parts.append("\n\n---\n\n")
             final_parts.append("Folder Structure:\n")
             final_parts.append(structure)

         final_string = "".join(final_parts)

         if not final_string and not errors:
              self.gui.show_status_message("Nothing generated to copy.", error=True)
              return

         try:
             pyperclip.copy(final_string)
             self.gui.show_status_message(status_message)
         except Exception as e:
             logging.error(f"Error copying to clipboard: {e}", exc_info=True)
             self.gui.show_status_message("Error copying to clipboard!", error=True)
             self.gui.show_toast(f"Could not copy combined content to clipboard: {e}", toast_type="error")