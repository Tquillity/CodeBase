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