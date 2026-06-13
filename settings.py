from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional, cast

import appdirs  # type: ignore[import-untyped]

from constants import (
    CACHE_MAX_MEMORY_MB,
    CACHE_MAX_SIZE,
    CROSS_PLATFORM_PATHS,
    DEFAULT_LOG_LEVEL,
    DEFAULT_WINDOW_SIZE,
    ERROR_HANDLING_ENABLED,
    ERROR_UI_FEEDBACK,
    get_default_allowed_repo_roots,
    LOG_TO_CONSOLE,
    LOG_TO_FILE,
    MAX_CONTENT_LENGTH,
    MAX_FILE_SIZE,
    MAX_TEMPLATE_SIZE,
    SECURITY_STRICT_MODE,
    TEMPLATE_MARKDOWN,
    TEXT_EXTENSIONS_DEFAULT,
    TREE_MAX_ITEMS,
    TREE_SAFETY_LIMIT,
    TREE_UI_UPDATE_INTERVAL,
)


class SettingsManager:
    def __init__(self) -> None:
        self.user_data_dir: str = appdirs.user_data_dir("CodeBase")
        self.settings_file: str = os.path.join(self.user_data_dir, "settings.json")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.settings: dict[str, Any] = self.load_settings()

    def load_settings(self) -> dict[str, Any]:
        """Loads settings from JSON file, applying defaults for missing keys."""
        default_settings = {
            "app": {
                "window_geometry": DEFAULT_WINDOW_SIZE,
                "default_tab": "Content Preview",
                "prepend_prompt": 1,
                "show_unloaded": 0,
                "expansion": "Collapsed",
                "levels": 1,
                "exclude_node_modules": 1,
                "exclude_venv": 1,
                "exclude_dist": 1,
                "exclude_coverage": 1,
                "exclude_test_files": 0,
                "exclude_lock_files": 1,
                "exclude_files": {
                    'package-lock.json': 1, 'yarn.lock': 1, 'composer.lock': 1,
                    'Gemfile.lock': 1, 'poetry.lock': 1, 'get-pip.py': 1
                },
                "include_icons": 1,
                "high_contrast": 0,
                "search_case_sensitive": 0,
                "search_whole_word": 0,
                "default_base_prompt": "",
                "copy_format": TEMPLATE_MARKDOWN,
                "log_level": DEFAULT_LOG_LEVEL,
                "log_to_file": 1 if LOG_TO_FILE else 0,
                "log_to_console": 1 if LOG_TO_CONSOLE else 0,
                # Performance settings
                "cache_max_size": CACHE_MAX_SIZE,
                "cache_max_memory_mb": CACHE_MAX_MEMORY_MB,
                "tree_max_items": TREE_MAX_ITEMS,
                "tree_ui_update_interval": TREE_UI_UPDATE_INTERVAL,
                "tree_safety_limit": TREE_SAFETY_LIMIT,
                # Security settings
                "security_enabled": 0,
                "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
                "max_template_size_mb": MAX_TEMPLATE_SIZE // (1024 * 1024),
                "max_content_length_mb": MAX_CONTENT_LENGTH // (1024 * 1024),
                "security_strict_mode": 1 if SECURITY_STRICT_MODE else 0,
                # Error handling settings
                "error_handling_enabled": 1 if ERROR_HANDLING_ENABLED else 0,
                "error_ui_feedback": 1 if ERROR_UI_FEEDBACK else 0,
                "error_logging_level": "ERROR",
                "error_recovery_attempts": 3,
                # Path normalization settings
                "cross_platform_paths": 1 if CROSS_PLATFORM_PATHS else 0,
                # URL sanitization settings
                "sanitize_urls": 0,
                # Folder selection settings
                "default_start_folder": os.path.expanduser("~"),
                "allowed_repo_roots": get_default_allowed_repo_roots(),
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
                default_exclude: dict[str, int] = cast(
                    dict[str, int], default_settings["app"]["exclude_files"]
                )
                loaded_exclude: Any = app_settings.get("exclude_files", {})
                final_exclude = default_exclude.copy()
                final_exclude.update(dict(loaded_exclude))
                app_settings["exclude_files"] = final_exclude

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
        default_extensions: dict[str, int] = {
            ext: 1 for ext in TEXT_EXTENSIONS_DEFAULT
        }
        loaded_extensions: Any = settings["app"].get("text_extensions", {})
        default_extensions.update(dict(loaded_extensions))
        settings["app"]["text_extensions"] = default_extensions

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

    def security_enabled(self) -> bool:
        """Whether stricter file-size and content validation is active."""
        return self.get('app', 'security_enabled', 0) == 1

    def max_file_size_bytes(self) -> int:
        """Configured max file size in bytes for security validation."""
        try:
            max_mb = int(self.get('app', 'max_file_size_mb', 10))
            return max_mb * 1024 * 1024
        except (TypeError, ValueError):
            return MAX_FILE_SIZE

    def sanitize_urls_enabled(self) -> bool:
        """Whether URL neutralization is applied during content generation."""
        return self.get('app', 'sanitize_urls', 0) == 1

    def set(self, section: str, key: str, value: Any) -> None:
        """Sets a setting value."""
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value
        # Optional: Save immediately after setting? Or require explicit save call?
        # self.save() # Uncomment for immediate save on set