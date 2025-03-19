import os
import json
import appdirs

class SettingsManager:
    def __init__(self):
        self.user_data_dir = appdirs.user_data_dir("CodeBase")
        self.settings_file = os.path.join(self.user_data_dir, "settings.json")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.settings = self.load_settings()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
        else:
            settings = {"app": {}, "repo": {}}
        if 'exclude_files' not in settings['app']:
            settings['app']['exclude_files'] = {
                'package-lock.json': 1,
                'yarn.lock': 1,
                'composer.lock': 1,
                'Gemfile.lock': 1,
                'poetry.lock': 1
            }
        if 'include_icons' not in settings['app']:
            settings['app']['include_icons'] = 1
        return settings

    def save(self):
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def get(self, section, key, default=None):
        return self.settings.get(section, {}).get(key, default)

    def set(self, section, key, value):
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value