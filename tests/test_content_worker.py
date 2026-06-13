# tests/test_content_worker.py
import threading
from unittest.mock import MagicMock, patch

import pytest

from content_generation_context import build_content_context_from_gui
from handlers.content_worker import start_content_generation


@pytest.fixture
def mock_gui():
    gui = MagicMock()
    gui.settings = MagicMock()
    gui.settings.security_enabled.return_value = True
    gui.settings.max_file_size_bytes.return_value = 5 * 1024 * 1024
    gui.settings.sanitize_urls_enabled.return_value = True
    gui._shutdown_requested = False
    gui._scan_cancel_requested = False
    gui.register_background_thread = MagicMock()
    return gui


def test_build_content_context_from_gui_uses_settings_helpers(mock_gui):
    ctx = build_content_context_from_gui(mock_gui)
    assert ctx.security_enabled is True
    assert ctx.max_file_size == 5 * 1024 * 1024
    assert ctx.sanitize_urls is True
    assert ctx.gui is mock_gui
    mock_gui.settings.security_enabled.assert_called_once()
    mock_gui.settings.max_file_size_bytes.assert_called_once()
    mock_gui.settings.sanitize_urls_enabled.assert_called_once()


def test_start_content_generation_happy_path(mock_gui):
    done = threading.Event()
    results: list[tuple] = []

    def on_complete(content, token_count, errors, deleted_files=None):
        results.append((content, token_count, errors, deleted_files))
        done.set()

    def fake_generate(*args, **kwargs):
        on_complete = args[3]
        on_complete("body", 42, [], [])

    with patch("handlers.content_worker.generate_content", side_effect=fake_generate) as mock_gen:
        start_content_generation(
            mock_gui,
            files={"/repo/a.py"},
            repo_path="/repo",
            lock=threading.Lock(),
            content_cache=MagicMock(),
            template_format="Markdown (Grok)",
            on_complete=on_complete,
            thread_name="TestGen",
        )
        assert done.wait(timeout=2)
        mock_gen.assert_called_once()
        assert results[0][0] == "body"
        assert results[0][1] == 42

    mock_gui.register_background_thread.assert_called_once()


def test_start_content_generation_exception_invokes_on_complete(mock_gui):
    done = threading.Event()
    errors_captured: list[str] = []

    def on_complete(content, token_count, errors, deleted_files=None):
        errors_captured.extend(errors)
        done.set()

    with patch("handlers.content_worker.generate_content", side_effect=RuntimeError("boom")):
        start_content_generation(
            mock_gui,
            files=set(),
            repo_path="/repo",
            lock=threading.Lock(),
            content_cache=MagicMock(),
            template_format="Markdown (Grok)",
            on_complete=on_complete,
            error_prefix="Copy failed",
        )
        assert done.wait(timeout=2)
        assert any("Copy failed" in err for err in errors_captured)


def test_context_abort_reads_live_gui_flags(mock_gui):
    ctx = build_content_context_from_gui(mock_gui)
    assert not ctx.should_abort_shutdown()
    mock_gui._shutdown_requested = True
    assert ctx.should_abort_shutdown()
