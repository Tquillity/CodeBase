from tkinter import ttk
from colors import (
    COLOR_BG, COLOR_FG, COLOR_BG_ACCENT, COLOR_BTN_BG, COLOR_BTN_FG,
    COLOR_BTN_HOVER, COLOR_HEADER, COLOR_STATUS, COLOR_FOLDER,
    COLOR_FILE_SELECTED, COLOR_FILE_UNLOADED, COLOR_FILE_DEFAULT,
    COLOR_FILE_NONTEXT, COLOR_HIGHLIGHT_BG, COLOR_HIGHLIGHT_FG,
    COLOR_FOCUSED_HIGHLIGHT_BG, COLOR_FOCUSED_HIGHLIGHT_FG,
    COLOR_HC_BG, COLOR_HC_FG, COLOR_HC_BG_ACCENT, COLOR_HC_BTN_BG,
    COLOR_HC_BTN_FG, COLOR_HC_BTN_HOVER, COLOR_HC_HEADER, COLOR_HC_STATUS,
    COLOR_HC_FOLDER, COLOR_HC_FILE_SELECTED, COLOR_HC_FILE_UNLOADED,
    COLOR_HC_FILE_DEFAULT, COLOR_HC_FILE_NONTEXT, COLOR_HC_HIGHLIGHT_BG,
    COLOR_HC_HIGHLIGHT_FG, COLOR_HC_FOCUSED_HIGHLIGHT_BG,
    COLOR_HC_FOCUSED_HIGHLIGHT_FG
)

class ThemeManager:
    def __init__(self, gui):
        self.gui = gui

    def apply_theme(self):
        hc = self.gui.high_contrast_mode.get()
        self.gui.colors = {
            'bg': COLOR_HC_BG if hc else COLOR_BG,
            'fg': COLOR_HC_FG if hc else COLOR_FG,
            'bg_accent': COLOR_HC_BG_ACCENT if hc else COLOR_BG_ACCENT,
            'btn_bg': COLOR_HC_BTN_BG if hc else COLOR_BTN_BG,
            'btn_fg': COLOR_HC_BTN_FG if hc else COLOR_BTN_FG,
            'btn_hover': COLOR_HC_BTN_HOVER if hc else COLOR_BTN_HOVER,
            'header': COLOR_HC_HEADER if hc else COLOR_HEADER,
            'status': COLOR_HC_STATUS if hc else COLOR_STATUS,
            'folder': COLOR_HC_FOLDER if hc else COLOR_FOLDER,
            'file_selected': COLOR_HC_FILE_SELECTED if hc else COLOR_FILE_SELECTED,
            'file_unloaded': COLOR_HC_FILE_UNLOADED if hc else COLOR_FILE_UNLOADED,
            'file_default': COLOR_HC_FILE_DEFAULT if hc else COLOR_FILE_DEFAULT,
            'file_nontext': COLOR_HC_FILE_NONTEXT if hc else COLOR_FILE_NONTEXT,
            'highlight_bg': COLOR_HC_HIGHLIGHT_BG if hc else COLOR_HIGHLIGHT_BG,
            'highlight_fg': COLOR_HC_HIGHLIGHT_FG if hc else COLOR_HIGHLIGHT_FG,
            'focused_highlight_bg': COLOR_HC_FOCUSED_HIGHLIGHT_BG if hc else COLOR_FOCUSED_HIGHLIGHT_BG,
            'focused_highlight_fg': COLOR_HC_FOCUSED_HIGHLIGHT_FG if hc else COLOR_FOCUSED_HIGHLIGHT_FG,
        }

    def toggle_high_contrast(self):
        self.gui.settings.set('app', 'high_contrast', self.gui.high_contrast_mode.get())
        self.gui.settings.save()
        self.apply_theme()
        self.reconfigure_ui_colors()
        self.gui.show_status_message("Theme updated")

    def reconfigure_ui_colors(self):
        hc = self.gui.high_contrast_mode.get()
        self.gui.root.configure(bg=self.gui.colors['bg'])

        self.gui.header_frame.config(bg=self.gui.colors['bg'])
        self.gui.header_frame.title_label.config(bg=self.gui.colors['bg'], fg=self.gui.colors['fg'])
        self.gui.header_frame.version_label.config(bg=self.gui.colors['bg'], fg=self.gui.colors['header'])
        # *** FIX: Correctly access the repo_label on the header_frame ***
        self.gui.header_frame.repo_label.config(bg=self.gui.colors['bg'], fg=self.gui.colors['status'])
        self.gui.header_separator.config(bg=self.gui.colors['btn_bg'])

        self.gui.left_frame.config(bg=self.gui.colors['bg'])
        self.gui.left_separator.config(bg=self.gui.colors['btn_bg'])
        self.gui.info_label.config(bg=self.gui.colors['bg'], fg=self.gui.colors['fg'])
        self.gui.prepend_checkbox.config(bg=self.gui.colors['bg'], fg=self.gui.colors['fg'], selectcolor=self.gui.colors['bg_accent'])
        self.gui.clear_button_frame.config(bg=self.gui.colors['bg'])
        for btn in [self.gui.select_button, self.gui.refresh_button, self.gui.copy_button, self.gui.copy_all_button, self.gui.copy_structure_button, self.gui.clear_button, self.gui.clear_all_button]:
             btn.config(bg=self.gui.colors['btn_bg'], fg=self.gui.colors['btn_fg'])

        self.gui.right_frame.config(bg=self.gui.colors['bg'])
        self.gui.search_frame.config(bg=self.gui.colors['bg'])
        self.gui.search_entry.config(bg=self.gui.colors['bg_accent'], fg=self.gui.colors['fg'], insertbackground=self.gui.colors['fg'])
        for btn in [self.gui.search_button, self.gui.next_button, self.gui.prev_button, self.gui.find_all_button]:
             btn.config(bg=self.gui.colors['btn_bg'], fg=self.gui.colors['btn_fg'])
        self.gui.case_sensitive_checkbox.config(bg=self.gui.colors['bg'], fg=self.gui.colors['fg'], selectcolor=self.gui.colors['bg_accent'])
        self.gui.whole_word_checkbox.config(bg=self.gui.colors['bg'], fg=self.gui.colors['fg'], selectcolor=self.gui.colors['bg_accent'])

        style = ttk.Style()
        style.configure("Custom.TNotebook", background=self.gui.colors['bg'])
        style.configure("Custom.TNotebook.Tab", background=self.gui.colors['bg_accent'], foreground=self.gui.colors['fg'])
        style.map("Custom.TNotebook.Tab",
                  background=[('selected', self.gui.colors['header'])],
                  foreground=[('selected', COLOR_HC_FG if hc else COLOR_BG)])

        self.gui.content_tab.reconfigure_colors(self.gui.colors)
        self.gui.structure_tab.reconfigure_colors(self.gui.colors)
        self.gui.base_prompt_tab.reconfigure_colors(self.gui.colors)
        self.gui.settings_tab.reconfigure_colors(self.gui.colors)
        self.gui.file_list_tab.reconfigure_colors(self.gui.colors)

        self.gui.status_bar.config(bg=self.gui.colors['bg'], fg=self.gui.colors['status'])