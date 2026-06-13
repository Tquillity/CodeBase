# tests/test_git_handler.py
from unittest.mock import MagicMock, patch

from handlers.git_handler import GitHandler, _parse_git_branch_header, _parse_porcelain_path


def test_parse_git_branch_header():
    assert _parse_git_branch_header("## main...origin/main") == "main"
    assert _parse_git_branch_header("## feature/foo") == "feature/foo"


def test_parse_porcelain_path_quoted():
    assert _parse_porcelain_path('XY "path with spaces.txt"') == "path with spaces.txt"


def test_parse_porcelain_path_rename():
    assert _parse_porcelain_path("XY old -> new.txt") == "new.txt"


def test_get_git_status_parses_staged():
    gui = MagicMock()
    gui.current_repo_path = "/repo"
    handler = GitHandler(gui)
    porcelain = "## main...origin/main\nM  staged.py\n"
    with patch("handlers.git_handler.os.path.exists", return_value=True), \
         patch("handlers.git_handler.subprocess.run") as mock_run:
        mock_run.return_value.stdout = porcelain
        mock_run.return_value.strip = lambda: porcelain.strip()
        status = handler.get_git_status("/repo")
    assert status["branch"] == "main"
    assert any("staged.py" in p for p in status["staged"])
