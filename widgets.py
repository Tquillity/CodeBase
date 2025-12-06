import ttkbootstrap as ttk
import tkinter as tk
from tkinter import filedialog, messagebox
import os # For path manipulation in FolderDialog
from constants import TOOLTIP_DELAY, TOOLTIP_WRAP_LENGTH, DIALOG_MIN_WIDTH


class Tooltip:
    """ Creates a tooltip for a given widget. """
    # Changed default bg to a dark grey to match the 'darkly' theme
    def __init__(self, widget, text, bg='#2b2b2b', delay=TOOLTIP_DELAY, relief="solid", borderwidth=1):
        self.widget = widget
        self.text = text
        self.tooltip_bg = bg
        self.delay = delay
        self.relief = relief
        self.borderwidth = borderwidth
        self.tip_window = None
        self.id = None
        self.x_offset = 20
        self.y_offset = 10 # Position below the cursor slightly

        self.widget.bind("<Enter>", self.schedule_show, add='+')
        self.widget.bind("<Leave>", self.hide_tip, add='+')
        self.widget.bind("<ButtonPress>", self.hide_tip, add='+') # Hide on click

    def schedule_show(self, event=None):
        """Schedules the tooltip display after a delay."""
        self.hide_tip() # Hide any existing tip first
        self.id = self.widget.after(self.delay, self.show_tip)

    def show_tip(self, event=None):
        """Displays the tooltip window."""
        if self.tip_window or not self.text: # Don't show if already visible or no text
            return

        # Get cursor position relative to screen
        x, y = self.widget.winfo_pointerxy()
        x += self.x_offset
        y += self.y_offset

        self.tip_window = tw = ttk.Toplevel(self.widget)
        # Make it borderless and stay on top
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        # Make it appear above other windows (may vary by WM)
        tw.wm_attributes("-topmost", True)

        # FIX: Use tk.Label instead of ttk.Label to strictly enforce colors
        # Background: Dark Grey (from __init__)
        # Foreground: White (explicitly set)
        label = tk.Label(tw, text=self.text, justify='left',
                       background=self.tooltip_bg, 
                       foreground="#ffffff", # Force white text
                       relief=self.relief, borderwidth=self.borderwidth,
                       wraplength=TOOLTIP_WRAP_LENGTH) # Wrap text if too long
        label.pack(ipadx=5, ipady=3) # Add internal padding

        # Adjust position if tooltip goes off-screen
        tw.update_idletasks() # Calculate actual size
        tip_width = tw.winfo_width()
        tip_height = tw.winfo_height()
        screen_width = tw.winfo_screenwidth()
        screen_height = tw.winfo_screenheight()

        if x + tip_width > screen_width:
            x = screen_width - tip_width - self.x_offset # Move left
        if y + tip_height > screen_height:
            y = self.widget.winfo_rooty() - tip_height - 5 # Move above widget

        tw.wm_geometry(f"+{x}+{y}")

    def hide_tip(self, event=None):
        """Hides the tooltip window."""
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class FolderDialog:
    """ Custom dialog for selecting folders, showing recent folders with a delete option. """
    def __init__(self, parent, recent_folders, on_delete_callback=None, default_start_folder=None):
        self.parent = parent
        self.recent_folders = recent_folders
        # Colors now managed by ttkbootstrap theme
        self.on_delete_callback = on_delete_callback
        self.default_start_folder = default_start_folder or os.path.expanduser("~")
        self.selected_folder = None
        self.dialog = ttk.Toplevel(parent)
        self.dialog.title("Select Repository Folder")
        min_width = DIALOG_MIN_WIDTH
        min_height = 400
        self.dialog.minsize(min_width, min_height)
        self.dialog.geometry(f"{min_width}x{min_height}")
        # Background color now managed by ttkbootstrap theme
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())

        self.dialog.grid_rowconfigure(1, weight=1)
        self.dialog.grid_columnconfigure(0, weight=1)

        ttk.Label(self.dialog, text="Select or Enter Repository Folder", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky="w")

        # --- Scrollable list area ---
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

        self.populate_recent_list()

        # --- Manual Entry ---
        entry_frame = ttk.Frame(self.dialog)
        entry_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        entry_frame.grid_columnconfigure(0, weight=1)

        self.folder_var = ttk.StringVar()
        self.folder_entry = ttk.Entry(entry_frame, textvariable=self.folder_var, width=50)
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        Tooltip(self.folder_entry, "Selected path (or type/paste path here)")

        browse_button = ttk.Button(entry_frame, text="Browse...", command=self.browse_folder, bootstyle="primary")
        browse_button.grid(row=0, column=1)

        # --- Action Buttons ---
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky="e")

        ok_button = ttk.Button(button_frame, text="   OK   ", command=self.confirm, bootstyle="success")
        ok_button.pack(side=tk.RIGHT, padx=10)

        cancel_button = ttk.Button(button_frame, text=" Cancel ", command=self.dialog.destroy, bootstyle="secondary")
        cancel_button.pack(side=tk.RIGHT)

        self.dialog.bind('<Return>', lambda e: self.confirm())
        self.dialog.bind('<KP_Enter>', lambda e: self.confirm())

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def populate_recent_list(self):
        # Clear existing items
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if not self.recent_folders:
            ttk.Label(self.list_frame, text="No recent folders.").pack(pady=10)
        else:
            for folder in self.recent_folders:
                self._create_list_item(folder)

    def _create_list_item(self, folder_path):
        item_frame = ttk.Frame(self.list_frame)
        item_frame.pack(fill="x", expand=True)
        
        # Store reference to item frame for highlighting
        item_frame.folder_path = folder_path

        delete_button = ttk.Button(item_frame, text="×", command=lambda p=folder_path, f=item_frame: self._delete_item(p, f),
                                  bootstyle="danger-outline", width=3)
        delete_button.pack(side=tk.LEFT, padx=(5, 10))
        Tooltip(delete_button, f"Remove '{folder_path}' from recent list")

        path_label = ttk.Label(item_frame, text=folder_path, anchor="w")
        path_label.pack(side=tk.LEFT, fill="x", expand=True)
        
        # Store reference to path label for highlighting
        item_frame.path_label = path_label

        # Bind clicks for selection
        path_label.bind("<Button-1>", lambda e, p=folder_path: self.on_label_click(p))
        item_frame.bind("<Button-1>", lambda e, p=folder_path: self.on_label_click(p))
        path_label.bind("<Double-Button-1>", lambda e, p=folder_path: self.on_label_double_click(p))

    def on_label_click(self, folder_path):
        self.folder_var.set(folder_path)
        self._highlight_selected_item(folder_path)

    def on_label_double_click(self, folder_path):
        self.folder_var.set(folder_path)
        self.confirm()

    def _highlight_selected_item(self, selected_folder_path):
        """Highlight the selected folder item and unhighlight others."""
        for widget in self.list_frame.winfo_children():
            if hasattr(widget, 'folder_path') and hasattr(widget, 'path_label'):
                if widget.folder_path == selected_folder_path:
                    # Highlight selected item using ttkbootstrap styling
                    widget.configure(bootstyle="primary")
                    widget.path_label.configure(bootstyle="primary")
                else:
                    # Unhighlight other items
                    widget.configure(bootstyle="")
                    widget.path_label.configure(bootstyle="")

    def _delete_item(self, folder_path, frame_widget):
        if self.on_delete_callback:
            self.on_delete_callback(folder_path)
        
        # Also remove from the local list for immediate UI update
        if folder_path in self.recent_folders:
            self.recent_folders.remove(folder_path)
        
        frame_widget.destroy()
        # Repack to fix any gaps if needed, though destroy should be enough
        self.list_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def browse_folder(self):
        initial_dir = self.folder_var.get()
        if not os.path.isdir(initial_dir):
            initial_dir = self.default_start_folder
        folder = filedialog.askdirectory(parent=self.dialog, title="Select Repository Directory", initialdir=initial_dir)
        if folder:
            self.folder_var.set(folder)

    def confirm(self):
        selected = self.folder_var.get().strip()
        if not selected:
            messagebox.showwarning("No Folder Selected", "Please select or enter a folder path.", parent=self.dialog)
            return
        if not os.path.isdir(selected):
            messagebox.showerror("Invalid Path", f"The specified path does not exist or is not a directory:\n{selected}", parent=self.dialog)
            return
        self.selected_folder = os.path.abspath(selected)
        self.dialog.destroy()

    def show(self):
        self.dialog.wait_window()
        return self.selected_folder