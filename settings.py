import os
import json
import appdirs
import logging

class SettingsManager:
    def __init__(self):
        self.user_data_dir = appdirs.user_data_dir("CodeBase")
        self.settings_file = os.path.join(self.user_data_dir, "settings.json")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.settings = self.load_settings()

    def load_settings(self):
        """Loads settings from JSON file, applying defaults for missing keys."""
        default_settings = {
            "app": {
                "window_geometry": "1200x800",
                "default_tab": "Content Preview",
                "prepend_prompt": 1,
                "show_unloaded": 0,
                "expansion": "Collapsed",
                "levels": 1,
                "exclude_node_modules": 1,
                "exclude_dist": 1,
                "exclude_files": {
                    'package-lock.json': 1, 'yarn.lock': 1, 'composer.lock': 1,
                    'Gemfile.lock': 1, 'poetry.lock': 1
                },
                "include_icons": 1,
                "high_contrast": 0,
                "search_case_sensitive": 0,
                "search_whole_word": 0,
                "default_base_prompt": "",
                "log_level": "INFO",
                "log_to_file": 1,
                "log_to_console": 1
                # Add default for text_extensions if needed, though FileHandler provides it
            },
            "repo": {} # For future repo-specific settings if needed
        }

        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                # Merge loaded settings with defaults to ensure all keys exist
                # Deep merge for 'app' section
                app_settings = default_settings['app'].copy()
                app_settings.update(loaded_settings.get('app', {}))
                # Ensure nested dicts like exclude_files are also merged/defaulted
                default_exclude = default_settings['app']['exclude_files']
                loaded_exclude = app_settings.get('exclude_files', {})
                final_exclude = default_exclude.copy()
                final_exclude.update(loaded_exclude) # Overwrite defaults with loaded values
                app_settings['exclude_files'] = final_exclude

                settings = default_settings # Start with defaults
                settings['app'] = app_settings # Update app section
                settings['repo'] = loaded_settings.get('repo', {}) # Update repo section

            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Error loading settings file {self.settings_file}: {e}. Using default settings.")
                settings = default_settings
        else:
            logging.info(f"Settings file not found at {self.settings_file}. Using default settings.")
            settings = default_settings

        # ** THE FIX IS HERE **
        # Ensure that any new default text extensions are merged into the loaded settings,
        # preserving the user's choices for existing extensions.
        from constants import TEXT_EXTENSIONS_DEFAULT
        # Get the full default list with every extension enabled by default.
        default_extensions = {ext: 1 for ext in TEXT_EXTENSIONS_DEFAULT}
        # Get the user's currently loaded extensions (or an empty dict if none exist).
        loaded_extensions = settings['app'].get('text_extensions', {})
        # Update the defaults with the user's settings. This means if a user has
        # turned an extension OFF, their choice is preserved. Any NEW extensions
        # from the default list that are not in the loaded list will be added.
        default_extensions.update(loaded_extensions)
        # Assign the fully merged dictionary back to the settings.
        settings['app']['text_extensions'] = default_extensions

        return settings


    def save(self):
        """Saves the current settings to the JSON file."""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, sort_keys=True)
        except IOError as e:
            logging.error(f"Error saving settings to {self.settings_file}: {e}")
        except TypeError as e:
             logging.error(f"Error serializing settings (possible non-serializable data): {e}")


    def get(self, section, key, default=None):
        """Gets a setting value, returning default if not found."""
        # Use the loaded self.settings which includes defaults
        return self.settings.get(section, {}).get(key, default)

    def set(self, section, key, value):
        """Sets a setting value."""
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value
        # Optional: Save immediately after setting? Or require explicit save call?
        # self.save() # Uncomment for immediate save on set