# widgets/toast.py
# Non-blocking toast notifications for CodeBase (VS Code / Claude style).

import tkinter as tk
import ttkbootstrap as ttk

# Toast type -> (bootstyle key, default duration ms)
TOAST_CONFIG = {
    "success": ("success", 4000),
    "info": ("info", 4000),
    "warning": ("warning", 6000),
    "error": ("danger", 8000),
}


class ToastManager:
    """
    Manages stackable, auto-dismiss, click-to-dismiss toast notifications.
    Thread-safe: call show() from main thread only (use gui.task_queue from workers).
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self._toasts: list[tk.Toplevel] = []
        self._offset_y = 0
        self._pad = 12
        self._max_width = 380

    def show(self, message: str, toast_type: str = "info", duration: int | None = None) -> None:
        """
        Display a single toast. Must be called from the main thread
        (queue via gui.task_queue if calling from a background thread).
        """
        toast_type = (toast_type or "info").lower()
        if toast_type not in TOAST_CONFIG:
            toast_type = "info"
        style_key, default_duration = TOAST_CONFIG[toast_type]
        duration = duration if duration is not None else default_duration

        style = ttk.Style()
        # Resolve theme color (ttkbootstrap uses style.colors)
        try:
            color = getattr(style.colors, style_key, None) or style.colors.primary
        except Exception:
            color = "#375a7f"

        tw = tk.Toplevel(self.root)
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-topmost", True)
        tw.configure(background=color)

        # Inner frame for padding and click-to-dismiss
        inner = tk.Frame(tw, bg=color, padx=14, pady=10)
        inner.pack(fill=tk.BOTH, expand=True)
        inner.bind("<Button-1>", lambda e: self._dismiss(tw))

        label = tk.Label(
            inner,
            text=message,
            font=("Arial", 10),
            fg=style.colors.fg if hasattr(style.colors, "fg") else "#ececec",
            bg=color,
            wraplength=self._max_width,
            justify=tk.LEFT,
            cursor="hand2",
        )
        label.pack(anchor="w")
        label.bind("<Button-1>", lambda e: self._dismiss(tw))

        tw.update_idletasks()
        w = min(tw.winfo_reqwidth(), self._max_width + 28)
        h = tw.winfo_reqheight()
        tw.geometry(f"{w}x{h}")

        self._toasts.append(tw)
        self._reposition_remaining()
        if duration > 0:
            self.root.after(duration, lambda: self._dismiss(tw))

    def _dismiss(self, tw: tk.Toplevel) -> None:
        if tw.winfo_exists():
            try:
                tw.destroy()
            except tk.TclError:
                pass
        if tw in self._toasts:
            self._toasts.remove(tw)
        self._reposition_remaining()

    def _reposition_remaining(self) -> None:
        """Stack all toasts bottom-right, newest at bottom."""
        rx = self.root.winfo_rootx()
        rw = self.root.winfo_width()
        ry = self.root.winfo_rooty()
        rh = self.root.winfo_height()
        y = ry + rh - self._pad
        for tw in reversed(self._toasts):
            if not tw.winfo_exists():
                continue
            h = tw.winfo_height()
            w = tw.winfo_width()
            y -= h + self._pad
            try:
                tw.geometry(f"+{rx + rw - w - self._pad}+{y}")
            except tk.TclError:
                pass
