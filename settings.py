import os
import json
import appdirs
import tkinter as tk

class SettingsManager:
    def __init__(self):
        self.user_data_dir = appdirs.user_data_dir("CodeBase")
        self.settings_file = os.path.join(self.user_data_dir, "settings.json")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.settings = self.load_settings()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f:
                return json.load(f)
        return {"app": {}, "repo": {"extensions": {}, "exclude": {}}}

    def save(self):
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def get(self, section, key, default=None):
        return self.settings.get(section, {}).get(key, default)

    def set(self, section, key, value):
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value

    def load_repo_settings(self, text_extensions_enabled, exclude_files):
        repo_settings = self.settings.get("repo", {})
        for ext in text_extensions_enabled:
            text_extensions_enabled[ext].set(repo_settings.get("extensions", {}).get(ext, 1))
        for file in exclude_files:
            exclude_files[file].set(repo_settings.get("exclude", {}).get(file, 0))

    def save_repo_settings(self, text_extensions_enabled, exclude_files):
        self.settings["repo"] = {
            "extensions": {ext: text_extensions_enabled[ext].get() for ext in text_extensions_enabled},
            "exclude": {file: exclude_files[file].get() for file in exclude_files}
        }
        self.save()