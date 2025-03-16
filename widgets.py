import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        self.id = None
        self.widget.bind("<Enter>", self.schedule_show)
        self.widget.bind("<Leave>", self.hide_tip)

    def schedule_show(self, event):
        if self.id:
            self.widget.after_cancel(self.id)
        self.id = self.widget.after(500, lambda: self.show_tip(event))

    def show_tip(self, event):
        if self.tip:
            return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tip, text=self.text, bg="#ffffe0", relief="solid", borderwidth=1)
        label.pack()
        self.tip.update_idletasks()
        tip_width = self.tip.winfo_width()
        tip_height = self.tip.winfo_height()
        screen_width = self.tip.winfo_screenwidth()
        screen_height = self.tip.winfo_screenheight()
        if x + tip_width > screen_width:
            x = screen_width - tip_width
        if y + tip_height > screen_height:
            y = screen_height - tip_height
        self.tip.wm_geometry(f"+{x}+{y}")

    def hide_tip(self, event):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        if self.tip:
            self.tip.destroy()
            self.tip = None

class FolderDialog:
    def __init__(self, parent, recent_folders):
        self.parent = parent
        self.recent_folders = recent_folders
        self.selected_folder = None

    def show(self):
        dialog = tk.Toplevel(self.parent)
        dialog.title("Select Repository Folder")
        dialog.geometry("400x300")
        dialog.configure(bg='#add8e6')
        dialog.bind('<Escape>', lambda e: dialog.destroy())

        tk.Label(dialog, text="Select Repository Folder", font=("Arial", 12, "bold"), bg='#add8e6', fg='#2b2b2b').pack(pady=10)
        folder_var = tk.StringVar()

        tk.Label(dialog, text="Recent Folders:", bg='#add8e6', fg='#2b2b2b').pack(pady=5)
        list_frame = tk.Frame(dialog, bg='#2b2b2b', relief="groove", borderwidth=2)
        list_frame.pack(pady=5, padx=20, fill="x")

        def truncate_path(path, max_length=45):
            return "…/" + path[-(max_length - 3):] if len(path) > max_length else path

        selected_label = None
        def select_folder(event, label, folder):
            nonlocal selected_label
            folder_var.set(folder)
            if selected_label and selected_label != label:
                selected_label.config(bg=selected_label.default_bg, fg='#ffffff')
            label.config(bg='#add8e6', fg='#2b2b2b')
            selected_label = label

        def double_click_select(event, folder):
            folder_var.set(folder)
            confirm()

        def refresh_folder_list():
            for widget in list_frame.winfo_children():
                widget.destroy()
            for i, folder in enumerate(self.recent_folders[:5]):
                truncated = truncate_path(folder)
                bg_color = '#3c3c3c' if i % 2 == 0 else '#4a4a4a'
                item_frame = tk.Frame(list_frame, bg=bg_color)
                item_frame.pack(fill="x", padx=5, pady=2)
                folder_label = tk.Label(item_frame, text=truncated, bg=bg_color, fg='#ffffff', cursor="hand2", anchor="w")
                folder_label.default_bg = bg_color
                folder_label.pack(side="left", fill="x", expand=True)
                folder_label.bind("<Button-1>", lambda e, l=folder_label, f=folder: select_folder(e, l, f))
                folder_label.bind("<Double-1>", lambda e, f=folder: double_click_select(e, f))
                remove_btn = tk.Label(item_frame, text="✕", bg=bg_color, fg='#FF4500', cursor="hand2")
                remove_btn.pack(side="right", padx=(5, 0))
                remove_btn.bind("<Button-1>", lambda e, f=folder: remove_folder(f))
                remove_btn.bind("<Enter>", lambda e, b=remove_btn: b.config(fg="#FF6347"))
                remove_btn.bind("<Leave>", lambda e, b=remove_btn: b.config(fg="#FF4500"))
                Tooltip(remove_btn, f"Remove {truncated} from recent folders")

        def remove_folder(folder):
            if folder in self.recent_folders:
                self.recent_folders.remove(folder)
                self.parent.file_handler.save_recent_folders()
                refresh_folder_list()

        refresh_folder_list()

        def browse_folder():
            folder = filedialog.askdirectory()
            if folder:
                folder_var.set(folder)

        tk.Button(dialog, text="Browse", command=browse_folder, bg='#4a4a4a', fg='#ffffff').pack(pady=10)

        def confirm():
            selected = folder_var.get()
            if selected:
                for folder in self.recent_folders:
                    if truncate_path(folder) == selected:
                        selected = folder
                        break
                self.selected_folder = selected
                dialog.destroy()
            else:
                messagebox.showwarning("No Selection", "Please select a folder.")

        tk.Button(dialog, text="OK", command=confirm, bg='#4a4a4a', fg='#ffffff').pack(pady=5)
        tk.Button(dialog, text="Close", command=dialog.destroy, bg='#4a4a4a', fg='#ffffff').pack(pady=5)
        dialog.bind('<Return>', lambda e: confirm())
        dialog.bind('<KP_Enter>', lambda e: confirm())

        dialog.transient(self.parent)
        dialog.grab_set()
        self.parent.wait_window(dialog)
        return self.selected_folder

class SettingsDialog:
    def __init__(self, parent, file_handler, settings):
        self.parent = parent
        self.file_handler = file_handler
        self.settings = settings

    def show(self):
        dialog = tk.Toplevel(self.parent)
        dialog.title("Repo Folder Settings")
        dialog.geometry("860x645")
        dialog.configure(bg='#2b2b2b')
        dialog.bind('<Escape>', lambda e: dialog.destroy())

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        style = ttk.Style()
        style.configure("Settings.TNotebook", background='#2b2b2b')
        style.configure("Settings.TNotebook.Tab", background='#3c3c3c', foreground='#ffffff')
        style.map("Settings.TNotebook.Tab", background=[('selected', '#add8e6')], foreground=[('selected', '#2b2b2b')])
        notebook.configure(style="Settings.TNotebook")

        ext_frame = tk.Frame(notebook, bg='#2b2b2b')
        notebook.add(ext_frame, text="File Extensions")
        ext_canvas = tk.Canvas(ext_frame, bg='#2b2b2b')
        ext_scrollbar = ttk.Scrollbar(ext_frame, orient="vertical", command=ext_canvas.yview)
        ext_scrollable_frame = tk.Frame(ext_canvas, bg='#2b2b2b')
        ext_scrollable_frame.bind("<Configure>", lambda e: ext_canvas.configure(scrollregion=ext_canvas.bbox("all")))
        ext_canvas.create_window((0, 0), window=ext_scrollable_frame, anchor="nw")
        ext_canvas.configure(yscrollcommand=ext_scrollbar.set)
        ext_canvas.pack(side="left", fill="both", expand=True)
        ext_scrollbar.pack(side="right", fill="y")
        tk.Label(ext_scrollable_frame, text="Select file extensions:", bg='#2b2b2b', fg='#ffffff').grid(row=0, column=0, columnspan=3, pady=5)
        for i, ext in enumerate(sorted(self.file_handler.text_extensions_default)):
            row = (i // 9) + 1
            col = i % 9
            cb = tk.Checkbutton(ext_scrollable_frame, text=ext, variable=self.file_handler.text_extensions_enabled[ext], bg='#2b2b2b', fg='#ffffff', selectcolor='#4a4a4a')
            cb.grid(row=row, column=col, sticky="w", padx=5, pady=2)

        exclude_frame = tk.Frame(notebook, bg='#2b2b2b')
        notebook.add(exclude_frame, text="Exclude Files")
        tk.Label(exclude_frame, text="Select files to exclude:", bg='#2b2b2b', fg='#ffffff').grid(row=0, column=0, pady=5)
        for i, file in enumerate(sorted(self.file_handler.exclude_files_default.keys())):
            cb = tk.Checkbutton(exclude_frame, text=file, variable=self.file_handler.exclude_files[file], bg='#2b2b2b', fg='#ffffff', selectcolor='#4a4a4a')
            cb.grid(row=i+1, column=0, sticky="w", padx=10, pady=2)

        def apply():
            self.settings.save_repo_settings(self.file_handler.text_extensions_enabled, self.file_handler.exclude_files)
            if self.file_handler.repo_path:
                self.file_handler.load_repo(self.file_handler.repo_path)
            dialog.destroy()

        tk.Button(dialog, text="Apply & Refresh", command=apply, bg='#4a4a4a', fg='#ffffff').pack(pady=5)
        tk.Button(dialog, text="Close", command=dialog.destroy, bg='#4a4a4a', fg='#ffffff').pack(pady=5)
        dialog.transient(self.parent)
        dialog.grab_set()
        self.parent.wait_window(dialog)