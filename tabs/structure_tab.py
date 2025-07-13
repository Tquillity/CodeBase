import tkinter as tk
from tkinter import ttk
from widgets import Tooltip
import logging
import os

class StructureTab(tk.Frame):
    def __init__(self, parent, gui, file_handler, settings, show_unloaded_var):
        super().__init__(parent)
        self.gui = gui
        self.file_handler = file_handler
        self.settings = settings
        self.show_unloaded_var = show_unloaded_var
        self.colors = gui.colors
        self.expand_collapse_var = tk.BooleanVar(value=True)
        self.setup_ui()

    def setup_ui(self):
        self.structure_button_frame = tk.Frame(self, bg=self.colors['bg'])
        self.structure_button_frame.pack(side=tk.TOP, fill='x', pady=5)

        self.expand_collapse_button = self.gui.create_button(self.structure_button_frame, "Expand All", self.toggle_expand_collapse, "Expand/collapse all folders in the tree")
        self.expand_collapse_button.pack(side=tk.LEFT, padx=10)

        self.show_unloaded_checkbox = tk.Checkbutton(self.structure_button_frame, text="Mark Unselected Files", variable=self.show_unloaded_var,
                                                     command=self.update_tree_strikethrough, bg=self.colors['bg'], fg=self.colors['fg'],
                                                     selectcolor=self.colors['bg_accent'], anchor='w',
                                                     activebackground=self.colors['bg'], activeforeground=self.colors['fg'])
        self.show_unloaded_checkbox.pack(side=tk.LEFT, padx=5)
        Tooltip(self.show_unloaded_checkbox, "Apply visual marker (strikethrough) to text files currently not selected for inclusion")

        style = ttk.Style()
        style.configure("Custom.Treeview", background=self.colors['bg_accent'], foreground=self.colors['fg'],
                        fieldbackground=self.colors['bg_accent'], borderwidth=0, rowheight=25)
        style.map("Custom.Treeview", background=[('selected', self.colors['btn_bg'])])
        style.layout("Custom.Treeview", [('Custom.Treeview.treearea', {'sticky': 'nswe'})])

        self.tree = ttk.Treeview(self, columns=("path", "checkbox"), show="tree headings",
                                 style="Custom.Treeview", selectmode="browse")
        self.tree.column("#0", width=400, anchor='w')
        self.tree.column("path", width=0, stretch=tk.NO)
        self.tree.column("checkbox", width=40, anchor="center", stretch=tk.NO)
        self.tree.heading("#0", text="Name", anchor='w')
        self.tree.heading("checkbox", text="Sel")

        unloaded_font = ('TkDefaultFont', -1, 'overstrike') if self.gui.high_contrast_mode.get() else (None, -10, 'overstrike')
        self.tree.tag_configure('folder', foreground=self.colors['folder'])
        self.tree.tag_configure('file_selected', foreground=self.colors['file_selected'])
        self.tree.tag_configure('file_unloaded', foreground=self.colors['file_unloaded'], font=unloaded_font)
        self.tree.tag_configure('file_default', foreground=self.colors['file_default'])
        self.tree.tag_configure('file_nontext', foreground=self.colors['file_nontext'])
        self.tree.tag_configure('error', foreground=self.colors['status'])
        self.tree.tag_configure('empty', foreground=self.colors['file_nontext'])
        self.tree.tag_configure("highlight", background=self.colors['highlight_bg'], foreground=self.colors['highlight_fg'])
        self.tree.tag_configure("focused_highlight", background=self.colors['focused_highlight_bg'], foreground=self.colors['focused_highlight_fg'])

        tree_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)

        tree_scrollbar.pack(side="right", fill="y", pady=(0,5))
        self.tree.pack(side="left", fill="both", expand=True, padx=(5,0), pady=(0,5))

        self.tree.bind('<Button-1>', self.handle_tree_click)
        self.tree.bind('<Double-1>', self.handle_tree_double_click)
        self.tree.bind('<<TreeviewOpen>>', self.handle_tree_open)

    def reconfigure_colors(self, colors):
        self.colors = colors
        self.structure_button_frame.config(bg=colors['bg'])
        self.expand_collapse_button.config(bg=colors['btn_bg'], fg=colors['btn_fg'])
        self.show_unloaded_checkbox.config(bg=colors['bg'], fg=colors['fg'], selectcolor=colors['bg_accent'])
        style = ttk.Style()
        style.configure("Custom.Treeview", background=colors['bg_accent'], foreground=colors['fg'], fieldbackground=colors['bg_accent'])
        style.map("Custom.Treeview", background=[('selected', colors['btn_bg'])])
        self.tree.tag_configure('folder', foreground=colors['folder'])
        unloaded_font = ('TkDefaultFont', -1, 'overstrike') if self.gui.high_contrast_mode.get() else (None, -10, 'overstrike')
        self.tree.tag_configure('file_selected', foreground=colors['file_selected'])
        self.tree.tag_configure('file_unloaded', foreground=colors['file_unloaded'], font=unloaded_font)
        self.tree.tag_configure('file_default', foreground=colors['file_default'])
        self.tree.tag_configure('file_nontext', foreground=colors['file_nontext'])
        self.tree.tag_configure("highlight", background=colors['highlight_bg'], foreground=colors['highlight_fg'])
        self.tree.tag_configure("focused_highlight", background=colors['focused_highlight_bg'], foreground=colors['focused_highlight_fg'])

    def populate_tree(self, root_dir):
        # NEW_LOG
        logging.info(f"StructureTab: Populating tree with root: {root_dir}")
        self.tree.delete(*self.tree.get_children())
        if not root_dir or not os.path.exists(root_dir):
            logging.warning("populate_tree called with invalid root_dir")
            return
        root_basename = os.path.basename(root_dir)
        initial_state = "☑"
        root_id = self.tree.insert("", "end", text=f"📁 {root_basename}",
                                      values=(root_dir, initial_state), open=False, tags=('folder',))
        self.tree.insert(root_id, "end", text="Loading...", tags=('dummy',))
        self.apply_initial_expansion()

    def apply_initial_expansion(self):
        if not self.tree.get_children(): return

        expansion_mode = self.settings.get('app', 'expansion', 'Collapsed')
        root_item = self.tree.get_children("")[0]

        if expansion_mode == 'Expanded':
            self.file_handler.expand_all()
        elif expansion_mode == 'Levels':
            try:
                levels = int(self.settings.get('app', 'levels', '1'))
                self.file_handler.expand_levels(levels, root_item)
            except ValueError:
                self.file_handler.expand_levels(1, root_item)
        else:
             self.file_handler.collapse_all()
             self.tree.item(root_item, open=False)

        self.update_expand_collapse_button()

    def handle_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell": return

        column = self.tree.identify_column(event.x)
        if column != "#2": return

        item_id = self.tree.identify_row(event.y)
        if not item_id: return

        self.file_handler.toggle_selection(event)

    def handle_tree_double_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        item_id = self.tree.identify_row(event.y)
        if not item_id: return

        col = self.tree.identify_column(event.x)

        if col == "#0":
            tags = self.tree.item(item_id)['tags']
            if 'folder' in tags:
                 pass
            elif any(t in tags for t in ['file_selected', 'file_default', 'file_unloaded', 'file_nontext']):
                 self.jump_to_file_content(item_id)

    def handle_tree_open(self, event):
        item_id = self.tree.focus()
        # NEW_LOG
        logging.debug(f"Tree open event for {item_id}")
        if item_id and 'folder' in self.tree.item(item_id)['tags']:
            self.file_handler.expand_folder(item_id)

    def jump_to_file_content(self, item_id):
        if self.gui.is_loading:
            self.gui.show_status_message("Loading in progress...", error=True); return
        try:
             item_data = self.tree.item(item_id)
             values = item_data['values']
             tags = item_data['tags']
             if not values or not tags: return

             if any(t in tags for t in ['file_selected', 'file_default', 'file_unloaded']):
                 file_path = values[0]
                 try:
                     rel_path = os.path.relpath(file_path, self.gui.current_repo_path)
                 except ValueError:
                     rel_path = file_path

                 self.gui.notebook.select(0)
                 self.gui.root.update_idletasks()

                 self.gui.content_tab.content_text.config(state=tk.NORMAL)
                 pos = self.gui.content_tab.content_text.search(f"File: {rel_path}", "1.0", tk.END, exact=True)
                 if pos:
                     self.gui.content_tab.content_text.tag_remove("focused_highlight", "1.0", tk.END)
                     end_pos = self.gui.content_tab.content_text.search("\n", pos, tk.END)
                     if end_pos:
                          self.gui.content_tab.content_text.tag_add("focused_highlight", pos, end_pos)
                     self.gui.content_tab.center_match((pos, end_pos))
                     self.gui.show_status_message(f"Jumped to {os.path.basename(file_path)}")
                 else:
                     self.gui.show_status_message(f"Content for {os.path.basename(file_path)} not found in preview.", error=True)
                 self.gui.content_tab.content_text.config(state=tk.DISABLED)
        except Exception as e:
             logging.error(f"Error jumping to file content: {e}")
             self.gui.show_status_message("Error jumping to content.", error=True)

    def toggle_expand_collapse(self):
        if self.gui.is_loading: self.gui.show_status_message("Loading...", error=True); return
        if not self.tree.get_children(): return

        is_currently_expanded = self.expand_collapse_button.cget('text') == "Collapse All"

        if is_currently_expanded:
            self.gui.show_status_message("Collapsing folders...")
            self.file_handler.collapse_all()
            self.expand_collapse_button.config(text="Expand All")
            self.gui.show_status_message("Folders collapsed.")
        else:
            self.gui.show_status_message("Expanding folders (may take time)...")
            self.gui.root.config(cursor="watch")
            self.gui.root.update()
            self.file_handler.expand_all()
            self.gui.root.config(cursor="")
            self.expand_collapse_button.config(text="Collapse All")
            self.gui.show_status_message("Folders expanded.")

    def generate_folder_structure_text(self):
        root_items = self.tree.get_children("")
        if not root_items:
            return ""

        # NEW_LOG
        logging.info("Generating folder structure text")
        include_icons = self.settings.get('app', 'include_icons', 1) == 1

        structure_lines = []

        def traverse(item_id, indent="", prefix=""):
            item_info = self.tree.item(item_id)
            item_text_raw = item_info["text"]
            item_tags = item_info["tags"]
            item_values = item_info["values"]

            if 'dummy' in item_tags or 'error' in item_tags or 'empty' in item_tags:
                if 'empty' in item_tags:
                     display_text = "(empty)"
                else:
                    return

            elif not include_icons and len(item_text_raw) > 2 and item_text_raw[1] == ' ':
                 display_text = item_text_raw[2:]
            else:
                 display_text = item_text_raw
            
            # NEW_LOG
            logging.debug(f"Traversing item: {item_id}, text: {display_text}")

            structure_lines.append(f"{indent}{prefix}{display_text}")

            children = self.tree.get_children(item_id)
            if 'folder' in item_tags and children:
                is_loaded = not (len(children) == 1 and 'dummy' in self.tree.item(children[0])['tags'])

                if is_loaded:
                    for i, child_id in enumerate(children):
                        sub_prefix = "└── " if i == len(children) - 1 else "├── "
                        sub_indent = indent + ("    " if i == len(children) - 1 else "│   ")
                        traverse(child_id, sub_indent, sub_prefix)

        if root_items:
             traverse(root_items[0])

        return "\n".join(structure_lines)

    def update_tree_strikethrough(self):
        if not self.tree.get_children(): return

        show_unloaded = self.show_unloaded_var.get() == 1
        # NEW_LOG
        logging.debug(f"Updating strikethrough, show_unloaded: {show_unloaded}")
        with self.file_handler.lock:
            loaded_files_copy = set(self.file_handler.loaded_files)

        def update_item(item_id):
            if not self.tree.exists(item_id): return

            item_data = self.tree.item(item_id)
            values = item_data["values"]
            tags = list(item_data["tags"])

            if 'folder' in tags or 'error' in tags or 'dummy' in tags or 'empty' in tags:
                 pass
            elif values and len(values) > 0:
                 item_path = values[0]
                 # FIX: Normalize path for comparison with the set
                 item_path_norm = os.path.normcase(item_path)
                 is_selected = item_path_norm in loaded_files_copy

                 if 'file_selected' in tags: tags.remove('file_selected')
                 if 'file_default' in tags: tags.remove('file_default')
                 if 'file_unloaded' in tags: tags.remove('file_unloaded')

                 if 'file_nontext' not in tags:
                     if is_selected:
                         tags.append('file_selected')
                     elif show_unloaded:
                         tags.append('file_unloaded')
                     else:
                         tags.append('file_default')
                 
                 # NEW_LOG
                 logging.debug(f"Updated tags for {item_id}: {tags}")
                 self.tree.item(item_id, tags=tuple(tags))

            for child in self.tree.get_children(item_id):
                update_item(child)

        for root_item in self.tree.get_children(""):
            update_item(root_item)

    def update_expand_collapse_button(self):
        if not self.tree.get_children():
            self.expand_collapse_button.config(text="Expand All", state=tk.DISABLED)
            return

        self.expand_collapse_button.config(state=tk.NORMAL)

        all_expanded = self.tree.item(self.tree.get_children("")[0])['open']

        if all_expanded:
            self.expand_collapse_button.config(text="Collapse All")
        else:
            self.expand_collapse_button.config(text="Expand All")

    def perform_search(self, query, case_sensitive, whole_word):
        matches = []
        if self.tree.get_children():
             def collect_matches(item):
                 item_text = self.tree.item(item)["text"]
                 search_in = item_text.lower() if not case_sensitive else item_text
                 query_term = query.lower() if not case_sensitive else query
                 if query_term in search_in:
                     matches.append(item)
                 for child in self.tree.get_children(item):
                     collect_matches(child)
             collect_matches(self.tree.get_children("")[0])
        return matches

    def highlight_all_matches(self, matches):
        for i, match_data in enumerate(matches):
            self.highlight_match(match_data, is_focused=False)

    def highlight_match(self, match_data, is_focused=True):
        highlight_tag = "focused_highlight" if is_focused else "highlight"
        other_highlight_tag = "highlight" if is_focused else "focused_highlight"
        item_id = match_data
        tags = list(self.tree.item(item_id)["tags"])
        if other_highlight_tag in tags: tags.remove(other_highlight_tag)
        if highlight_tag not in tags: tags.append(highlight_tag)
        self.tree.item(item_id, tags=tuple(tags))

    def center_match(self, match_data):
        item_id = match_data
        self.tree.see(item_id)
        self.tree.selection_set(item_id)

    def clear_highlights(self):
        if self.tree.get_children():
             def clear_recursive(item):
                 tags = list(self.tree.item(item)["tags"])
                 updated = False
                 if "highlight" in tags: tags.remove("highlight"); updated = True
                 if "focused_highlight" in tags: tags.remove("focused_highlight"); updated = True
                 if updated: self.tree.item(item, tags=tuple(tags))
                 for child in self.tree.get_children(item):
                     clear_recursive(child)
             clear_recursive(self.tree.get_children("")[0])

    def clear(self):
        self.tree.delete(*self.tree.get_children())