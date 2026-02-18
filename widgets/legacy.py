# widgets/legacy.py - Tooltip and FolderDialog (moved from root widgets.py for package layout)
from __future__ import annotations

import os
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, Any, Callable, List, Optional, cast

import tkinter as tk
import ttkbootstrap as ttk

from constants import DIALOG_MIN_WIDTH, TOOLTIP_DELAY, TOOLTIP_WRAP_LENGTH

if TYPE_CHECKING:
    from gui import RepoPromptGUI


class Tooltip:
    """ Creates a tooltip for a given widget. """
    widget: tk.Misc
    text: str
    tooltip_bg: str
    delay: int
    relief: str
    borderwidth: int
    tip_window: Optional[tk.Toplevel]
    id: Optional[str]
    x_offset: int
    y_offset: int

    def __init__(
        self,
        widget: tk.Misc,
        text: str,
        bg: str = '#2b2b2b',
        delay: int = TOOLTIP_DELAY,
        relief: str = "solid",
        borderwidth: int = 1,
    ) -> None:
        self.widget = widget
        self.text = text
        self.tooltip_bg = bg
        self.delay = delay
        self.relief = relief
        self.borderwidth = borderwidth
        self.tip_window = None
        self.id = None
        self.x_offset = 20
        self.y_offset = 10

        self.widget.bind("<Enter>", self.schedule_show, add='+')
        self.widget.bind("<Leave>", self.hide_tip, add='+')
        self.widget.bind("<ButtonPress>", self.hide_tip, add='+')
        self.widget.bind("<FocusIn>", self.schedule_show, add='+')
        self.widget.bind("<FocusOut>", self.hide_tip, add='+')

    def schedule_show(self, event: Optional[tk.Event[Any]] = None) -> None:
        self.hide_tip()
        self.id = self.widget.after(self.delay, self.show_tip)

    def show_tip(self, event: Optional[tk.Event[Any]] = None) -> None:
        if self.tip_window or not self.text:
            return
        x, y = self.widget.winfo_pointerxy()
        x += self.x_offset
        y += self.y_offset
        self.tip_window = tw = ttk.Toplevel(cast(Any, self.widget))
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.wm_attributes("-topmost", True)
        label = tk.Label(tw, text=self.text, justify='left',
                       background=self.tooltip_bg,
                       foreground="#ffffff",
                       relief=self.relief, borderwidth=self.borderwidth,  # type: ignore[arg-type]
                       wraplength=TOOLTIP_WRAP_LENGTH)
        label.pack(ipadx=5, ipady=3)
        tw.update_idletasks()
        tip_width = tw.winfo_width()
        tip_height = tw.winfo_height()
        screen_width = tw.winfo_screenwidth()
        screen_height = tw.winfo_screenheight()
        if x + tip_width > screen_width:
            x = screen_width - tip_width - self.x_offset
        if y + tip_height > screen_height:
            y = self.widget.winfo_rooty() - tip_height - 5
        tw.wm_geometry(f"+{x}+{y}")

    def hide_tip(self, event: Optional[tk.Event[Any]] = None) -> None:
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class FolderDialog:
    """ Custom dialog for selecting folders, showing recent folders with a delete option. """
    parent: tk.Misc
    recent_folders: List[str]
    gui: Optional[RepoPromptGUI]
    on_delete_callback: Optional[Callable[[str], None]]
    default_start_folder: str
    selected_folder: Optional[str]
    dialog: ttk.Toplevel
    canvas: ttk.Canvas
    list_frame: ttk.Frame
    folder_var: tk.StringVar
    folder_entry: ttk.Entry

    def __init__(
        self,
        parent: tk.Misc,
        recent_folders: List[str],
        on_delete_callback: Optional[Callable[[str], None]] = None,
        default_start_folder: Optional[str] = None,
        gui: Optional[RepoPromptGUI] = None,
    ) -> None:
        self.parent = parent
        self.recent_folders = recent_folders
        self.gui = gui
        self.on_delete_callback = on_delete_callback
        self.default_start_folder = default_start_folder or os.path.expanduser("~")
        self.selected_folder = None
        self.dialog = ttk.Toplevel(cast(Any, parent))
        self.dialog.title("Select Repository Folder")
        min_width = DIALOG_MIN_WIDTH
        min_height = 400
        self.dialog.minsize(min_width, min_height)
        self.dialog.geometry(f"{min_width}x{min_height}")
        self.dialog.transient(cast(Any, parent))
        self.dialog.grab_set()
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())
        self.dialog.grid_rowconfigure(1, weight=1)
        self.dialog.grid_columnconfigure(0, weight=1)
        ttk.Label(self.dialog, text="Select or Enter Repository Folder", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky="w")
        canvas_frame = ttk.Frame(self.dialog)
        canvas_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas = ttk.Canvas(canvas_frame, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.list_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.list_frame.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Button-4>', lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind('<Button-5>', lambda e: self.canvas.yview_scroll(1, "units"))
        self.list_frame.bind('<Button-4>', lambda e: self.canvas.yview_scroll(-1, "units"))
        self.list_frame.bind('<Button-5>', lambda e: self.canvas.yview_scroll(1, "units"))
        self.populate_recent_list()
        entry_frame = ttk.Frame(self.dialog)
        entry_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        entry_frame.grid_columnconfigure(0, weight=1)
        self.folder_var = ttk.StringVar()
        self.folder_entry = ttk.Entry(entry_frame, textvariable=self.folder_var, width=50)
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        Tooltip(self.folder_entry, "Selected path (or type/paste path here)")
        browse_button = ttk.Button(entry_frame, text="Browse...", command=self.browse_folder, bootstyle="primary")
        browse_button.grid(row=0, column=1)
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky="e")
        ok_button = ttk.Button(button_frame, text="   OK   ", command=self.confirm, bootstyle="success")
        ok_button.pack(side=tk.RIGHT, padx=10)
        cancel_button = ttk.Button(button_frame, text=" Cancel ", command=self.dialog.destroy, bootstyle="secondary")
        cancel_button.pack(side=tk.RIGHT)
        self.dialog.bind('<Return>', lambda e: self.confirm())
        self.dialog.bind('<KP_Enter>', lambda e: self.confirm())

    def _on_mousewheel(self, event: tk.Event[Any]) -> None:
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def populate_recent_list(self) -> None:
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        if not self.recent_folders:
            ttk.Label(self.list_frame, text="No recent folders.").pack(pady=10)
        else:
            for folder in self.recent_folders:
                self._create_list_item(folder)

    def _create_list_item(self, folder_path: str) -> None:
        item_frame = ttk.Frame(self.list_frame, bootstyle="secondary")
        item_frame.pack(fill="x", expand=True)
        setattr(item_frame, 'folder_path', folder_path)
        delete_button = ttk.Button(item_frame, text="×", command=lambda p=folder_path, f=item_frame: self._delete_item(p, f),
                                  bootstyle="danger-outline", width=3)
        delete_button.pack(side=tk.LEFT, padx=(5, 10))
        Tooltip(delete_button, f"Remove '{folder_path}' from recent list")
        path_label = ttk.Label(item_frame, text=folder_path, anchor="w", bootstyle="secondary")
        path_label.pack(side=tk.LEFT, fill="x", expand=True)
        setattr(item_frame, 'path_label', path_label)
        path_label.bind("<Button-1>", lambda e, p=folder_path: self.on_label_click(p))  # type: ignore[misc]
        item_frame.bind("<Button-1>", lambda e, p=folder_path: self.on_label_click(p))  # type: ignore[misc]
        path_label.bind("<Double-Button-1>", lambda e, p=folder_path: self.on_label_double_click(p))  # type: ignore[misc]

    def on_label_click(self, folder_path: str) -> None:
        self.folder_var.set(folder_path)
        self._highlight_selected_item(folder_path)

    def on_label_double_click(self, folder_path: str) -> None:
        self.folder_var.set(folder_path)
        self.confirm()

    def _highlight_selected_item(self, selected_folder_path: str) -> None:
        # Clear highlight from all items first, then set only the selected one.
        # Using a neutral style for unselected ensures the previous primary highlight is removed.
        for widget in self.list_frame.winfo_children():
            w = cast(Any, widget)
            if hasattr(widget, 'folder_path') and hasattr(widget, 'path_label'):
                if w.folder_path == selected_folder_path:
                    w.configure(bootstyle="primary")
                    w.path_label.configure(bootstyle="primary")
                else:
                    w.configure(bootstyle="secondary")
                    w.path_label.configure(bootstyle="secondary")

    def _delete_item(self, folder_path: str, frame_widget: ttk.Frame) -> None:
        if self.on_delete_callback:
            self.on_delete_callback(folder_path)
        if folder_path in self.recent_folders:
            self.recent_folders.remove(folder_path)
        frame_widget.destroy()
        self.list_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def browse_folder(self) -> None:
        initial_dir = self.folder_var.get()
        if not os.path.isdir(initial_dir):
            initial_dir = self.default_start_folder
        folder = filedialog.askdirectory(parent=self.dialog, title="Select Repository Directory", initialdir=initial_dir)
        if folder:
            self.folder_var.set(folder)

    def confirm(self) -> None:
        selected = self.folder_var.get().strip()
        if not selected:
            if self.gui:
                self.gui.show_toast("Please select or enter a folder path.", toast_type="warning")
            else:
                messagebox.showwarning("No Folder Selected", "Please select or enter a folder path.", parent=self.dialog)
            return
        if not os.path.isdir(selected):
            if self.gui:
                self.gui.show_toast(f"The specified path does not exist or is not a directory: {selected}", toast_type="error")
            else:
                messagebox.showerror("Invalid Path", f"The specified path does not exist or is not a directory:\n{selected}", parent=self.dialog)
            return
        self.selected_folder = os.path.abspath(selected)
        self.dialog.destroy()

    def show(self) -> Optional[str]:
        self.dialog.wait_window()
        return self.selected_folder
