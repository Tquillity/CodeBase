# tests/test_settings.py
import os
import json
import tempfile
import pytest
from settings import SettingsManager

@pytest.fixture
def temp_settings_file():
    with tempfile.TemporaryDirectory() as temp_dir:
        settings_file = os.path.join(temp_dir, "settings.json")
        yield settings_file

def test_load_settings_defaults(temp_settings_file):
    manager = SettingsManager()
    manager.settings_file = temp_settings_file  # Override for test
    settings = manager.load_settings()
    assert settings['app']['prepend_prompt'] == 1
    assert settings['app']['exclude_files']['package-lock.json'] == 1

def test_load_settings_from_file(temp_settings_file):
    with open(temp_settings_file, 'w') as f:
        json.dump({'app': {'prepend_prompt': 0, 'exclude_files': {'custom.lock': 1}}}, f)
    manager = SettingsManager()
    manager.settings_file = temp_settings_file
    settings = manager.load_settings()
    assert settings['app']['prepend_prompt'] == 0
    assert settings['app']['exclude_files']['package-lock.json'] == 1  # Default merged
    assert settings['app']['exclude_files']['custom.lock'] == 1  # Loaded value

def test_load_settings_corrupt_file(caplog, temp_settings_file):
    with open(temp_settings_file, 'w') as f:
        f.write("invalid json")
    manager = SettingsManager()
    manager.settings_file = temp_settings_file
    settings = manager.load_settings()
    assert settings['app']['prepend_prompt'] == 1  # Defaults used
    assert "Error loading settings file" in caplog.text

def test_save_settings(temp_settings_file):
    manager = SettingsManager()
    manager.settings_file = temp_settings_file
    manager.set('app', 'prepend_prompt', 0)
    manager.save()
    with open(temp_settings_file, 'r') as f:
        data = json.load(f)
    assert data['app']['prepend_prompt'] == 0

def test_get_set(temp_settings_file):
    manager = SettingsManager()
    manager.settings_file = temp_settings_file
    assert manager.get('app', 'nonexistent', 42) == 42
    manager.set('app', 'test_key', "value")
    assert manager.get('app', 'test_key') == "value"