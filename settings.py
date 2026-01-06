import os
import json
import appdirs
import logging
from typing import Dict, Any, Optional

class SettingsManager:
    def __init__(self) -> None:
        self.user_data_dir: str = appdirs.user_data_dir("CodeBase")
        self.settings_file: str = os.path.join(self.user_data_dir, "settings.json")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.settings: Dict[str, Any] = self.load_settings()

    def load_settings(self) -> Dict[str, Any]:
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
                "exclude_coverage": 1,
                "exclude_test_files": 0,
                "exclude_files": {
                    'package-lock.json': 1, 'yarn.lock': 1, 'composer.lock': 1,
                    'Gemfile.lock': 1, 'poetry.lock': 1, 'get-pip.py': 1
                },
                "include_icons": 1,
                "high_contrast": 0,
                "search_case_sensitive": 0,
                "search_whole_word": 0,
                "default_base_prompt": "",
                "copy_format": "Markdown (Grok)",
                "log_level": "INFO",
                "log_to_file": 1,
                "log_to_console": 1,
                # Performance settings
                "cache_max_size": 1000,
                "cache_max_memory_mb": 100,
                "tree_max_items": 10000,
                "tree_ui_update_interval": 100,
                "tree_safety_limit": 10000,
                # Security settings
                "security_enabled": 1,
                "max_file_size_mb": 10,
                "max_template_size_mb": 1,
                "max_content_length_mb": 50,
                "security_strict_mode": 1,
                # Error handling settings
                "error_handling_enabled": 1,
                "error_ui_feedback": 1,
                "error_logging_level": "ERROR",
                "error_recovery_attempts": 3,
                # Path normalization settings
                "path_normalization_enabled": 1,
                "cross_platform_paths": 1,
                # URL sanitization settings
                "sanitize_urls": 0,
                # Folder selection settings
                "default_start_folder": os.path.expanduser("~")
            },
            "repo": {}
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


    def save(self) -> None:
        """Saves the current settings to the JSON file."""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, sort_keys=True)
        except IOError as e:
            logging.error(f"Error saving settings to {self.settings_file}: {e}")
        except TypeError as e:
             logging.error(f"Error serializing settings (possible non-serializable data): {e}")


    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Gets a setting value, returning default if not found."""
        # Use the loaded self.settings which includes defaults
        return self.settings.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        """Sets a setting value."""
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value
        # Optional: Save immediately after setting? Or require explicit save call?
        # self.save() # Uncomment for immediate save on set