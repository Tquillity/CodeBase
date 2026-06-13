# tests/test_live_reload.py
from live_reload import RestartHandler


def test_should_ignore_file_basenames():
    handler = RestartHandler(None, "main.py")
    assert handler.should_ignore_file("/proj/__pycache__/mod.pyc") is True
    assert handler.should_ignore_file("/proj/main.py") is False
    assert handler.should_ignore_file("/proj/codebase_debug.log") is True
