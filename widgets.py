import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os # For path manipulation in FolderDialog
from constants import TOOLTIP_DELAY, TOOLTIP_WRAP_LENGTH, DIALOG_MIN_WIDTH


class Tooltip:
    """ Creates a tooltip for a given widget. """
    def __init__(self, widget, text, bg='#ffffe0', delay=TOOLTIP_DELAY, relief="solid", borderwidth=1):
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

        self.tip_window = tw = tk.Toplevel(self.widget)
        # Make it borderless and stay on top
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        # Make it appear above other windows (may vary by WM)
        tw.wm_attributes("-topmost", True)

        label = tk.Label(tw, text=self.text, justify='left',
                       background=self.tooltip_bg, relief=self.relief, borderwidth=self.borderwidth,
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
    def __init__(self, parent, recent_folders, colors, on_delete_callback=None):
        self.parent = parent
        self.recent_folders = recent_folders
        self.colors = colors
        self.on_delete_callback = on_delete_callback
        self.selected_folder = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Select Repository Folder")
        min_width = DIALOG_MIN_WIDTH
        min_height = 400
        self.dialog.minsize(min_width, min_height)
        self.dialog.geometry(f"{min_width}x{min_height}")
        self.dialog.configure(bg=self.colors['bg'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())

        self.dialog.grid_rowconfigure(1, weight=1)
        self.dialog.grid_columnconfigure(0, weight=1)

        tk.Label(self.dialog, text="Select or Enter Repository Folder", font=("Arial", 12, "bold"),
                 bg=self.colors['bg'], fg=self.colors['fg']).grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky="w")

        # --- Scrollable list area ---
        canvas_frame = tk.Frame(self.dialog, bg=self.colors['bg_accent'], bd=1, relief="sunken")
        canvas_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_frame, bg=self.colors['bg_accent'], highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.list_frame = tk.Frame(self.canvas, bg=self.colors['bg_accent'])
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")

        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)

        self.populate_recent_list()

        # --- Manual Entry ---
        entry_frame = tk.Frame(self.dialog, bg=self.colors['bg'])
        entry_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        entry_frame.grid_columnconfigure(0, weight=1)

        self.folder_var = tk.StringVar()
        self.folder_entry = tk.Entry(entry_frame, textvariable=self.folder_var, width=50,
                                     bg=self.colors['bg_accent'], fg=self.colors['fg'], insertbackground=self.colors['fg'])
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        Tooltip(self.folder_entry, "Selected path (or type/paste path here)")

        browse_button = tk.Button(entry_frame, text="Browse...", command=self.browse_folder,
                                  bg=self.colors['btn_bg'], fg=self.colors['btn_fg'])
        browse_button.grid(row=0, column=1)

        # --- Action Buttons ---
        button_frame = tk.Frame(self.dialog, bg=self.colors['bg'])
        button_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky="e")

        ok_button = tk.Button(button_frame, text="   OK   ", command=self.confirm,
                              bg=self.colors['btn_bg'], fg=self.colors['btn_fg'])
        ok_button.pack(side=tk.RIGHT, padx=10)

        cancel_button = tk.Button(button_frame, text=" Cancel ", command=self.dialog.destroy,
                                  bg=self.colors['btn_bg'], fg=self.colors['btn_fg'])
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
            tk.Label(self.list_frame, text="No recent folders.", bg=self.colors['bg_accent'], fg=self.colors['file_nontext']).pack(pady=10)
        else:
            for folder in self.recent_folders:
                self._create_list_item(folder)

    def _create_list_item(self, folder_path):
        item_frame = tk.Frame(self.list_frame, bg=self.colors['bg_accent'])
        item_frame.pack(fill="x", expand=True)

        delete_button = tk.Button(item_frame, text="🗑", command=lambda p=folder_path, f=item_frame: self._delete_item(p, f),
                                  bg=self.colors['btn_bg'], fg=self.colors['status'], relief="flat", activebackground=self.colors['btn_hover'])
        delete_button.pack(side=tk.LEFT, padx=(5, 10))
        Tooltip(delete_button, f"Remove '{folder_path}' from recent list")

        path_label = tk.Label(item_frame, text=folder_path, anchor="w",
                              bg=self.colors['bg_accent'], fg=self.colors['fg'])
        path_label.pack(side=tk.LEFT, fill="x", expand=True)

        # Bind clicks for selection
        path_label.bind("<Button-1>", lambda e, p=folder_path: self.on_label_click(p))
        item_frame.bind("<Button-1>", lambda e, p=folder_path: self.on_label_click(p))
        path_label.bind("<Double-Button-1>", lambda e, p=folder_path: self.on_label_double_click(p))

    def on_label_click(self, folder_path):
        self.folder_var.set(folder_path)

    def on_label_double_click(self, folder_path):
        self.folder_var.set(folder_path)
        self.confirm()

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
            initial_dir = os.path.expanduser("~")
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