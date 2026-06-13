# tests/test_install.py
import os
import shutil
import subprocess
import tempfile

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def temp_install_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def _setup_source_tree(source_dir: str, *, include_main: bool = True) -> str:
    os.makedirs(source_dir, exist_ok=True)
    if include_main:
        open(os.path.join(source_dir, "main.py"), "w").close()
    shutil.copy2(os.path.join(REPO_ROOT, "install.sh"), os.path.join(source_dir, "install.sh"))
    shutil.copy2(os.path.join(REPO_ROOT, "codebase.desktop"), os.path.join(source_dir, "codebase.desktop"))
    open(os.path.join(source_dir, "requirements.txt"), "w").close()
    icon_src = os.path.join(REPO_ROOT, "assets", "icon.png")
    if os.path.exists(icon_src):
        shutil.copy2(icon_src, os.path.join(source_dir, "icon.png"))
    else:
        open(os.path.join(source_dir, "icon.png"), "w").close()
    svg_src = os.path.join(REPO_ROOT, "codebase-icon.svg")
    if os.path.exists(svg_src):
        shutil.copy2(svg_src, os.path.join(source_dir, "codebase-icon.svg"))
    os.chmod(os.path.join(source_dir, "install.sh"), 0o755)
    return os.path.join(source_dir, "install.sh")


def test_install_script_execution(temp_install_dir):
    env = os.environ.copy()
    env["HOME"] = temp_install_dir
    fake_bin = os.path.join(temp_install_dir, "fakebin")
    os.makedirs(fake_bin, exist_ok=True)
    python_wrapper = os.path.join(fake_bin, "python3")
    with open(python_wrapper, "w") as f:
        f.write("#!/bin/sh\nexit 0\n")
    os.chmod(python_wrapper, 0o755)
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    source_dir = os.path.join(temp_install_dir, "source")
    install_script = _setup_source_tree(source_dir)

    result = subprocess.run(
        [install_script],
        cwd=source_dir,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
    assert "Starting CodeBase installation" in result.stdout

    bin_path = os.path.join(temp_install_dir, ".local/bin/CodeBase")
    assert os.path.exists(bin_path)
    assert os.access(bin_path, os.X_OK)

    desktop_path = os.path.join(temp_install_dir, ".local/share/applications/codebase.desktop")
    assert os.path.exists(desktop_path)


def test_install_missing_main_script(temp_install_dir):
    env = os.environ.copy()
    env["HOME"] = temp_install_dir
    fake_bin = os.path.join(temp_install_dir, "fakebin")
    os.makedirs(fake_bin, exist_ok=True)
    python_wrapper = os.path.join(fake_bin, "python3")
    with open(python_wrapper, "w") as f:
        f.write("#!/bin/sh\nexit 0\n")
    os.chmod(python_wrapper, 0o755)
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    source_dir = os.path.join(temp_install_dir, "source")
    install_script = _setup_source_tree(source_dir, include_main=False)

    result = subprocess.run(
        [install_script],
        cwd=source_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Main script" in result.stdout + result.stderr
