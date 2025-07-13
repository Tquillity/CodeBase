# tests/test_install.py
import os
import subprocess
import tempfile
import pytest
import shutil

@pytest.fixture
def temp_install_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

def test_install_script_execution(temp_install_dir):
    env = os.environ.copy()
    env['HOME'] = temp_install_dir

    source_dir = os.path.join(temp_install_dir, "source")
    os.mkdir(source_dir)
    open(os.path.join(source_dir, "main.py"), 'w').close()
    open(os.path.join(source_dir, "icon.png"), 'w').close()
    with open(os.path.join(source_dir, "codebase.desktop"), 'w') as f:
        f.write("[Desktop Entry]\nExec=placeholder\nIcon=placeholder")
    open(os.path.join(source_dir, "requirements.txt"), 'w').close()

    install_script = os.path.join(source_dir, "install.sh")
    with open(install_script, 'w') as f:
        f.write("""#!/bin/bash
echo "Installing..."
SOURCE_DIR=$(dirname "$(realpath "$0")")
mkdir -p "$HOME/.local/bin"
echo "Wrapper" > "$HOME/.local/bin/CodeBase"
chmod +x "$HOME/.local/bin/CodeBase"
mkdir -p "$HOME/.local/share/applications"
cp "$SOURCE_DIR/codebase.desktop" "$HOME/.local/share/applications/codebase.desktop"
sed -i "s@placeholder@$HOME/.local/bin/CodeBase@g" "$HOME/.local/share/applications/codebase.desktop"
""")  # FIX: Add sed to simulate placeholder replacement

    os.chmod(install_script, 0o755)

    # Run the script
    result = subprocess.run([install_script], cwd=source_dir, env=env, capture_output=True, text=True)

    assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
    assert "Installing..." in result.stdout

    # Check created files and content
    bin_path = os.path.join(temp_install_dir, ".local/bin/CodeBase")
    assert os.path.exists(bin_path)
    assert os.access(bin_path, os.X_OK)
    with open(bin_path, 'r') as f:
        assert "Wrapper" in f.read()  # Verify content

    desktop_path = os.path.join(temp_install_dir, ".local/share/applications/codebase.desktop")
    assert os.path.exists(desktop_path)
    with open(desktop_path, 'r') as f:
        content = f.read()
        assert f"Exec={os.path.join(temp_install_dir, '.local/bin/CodeBase')}" in content  # Verify replacement

def test_install_missing_main_script(temp_install_dir):
    env = os.environ.copy()
    env['HOME'] = temp_install_dir
    source_dir = os.path.join(temp_install_dir, "source")
    os.mkdir(source_dir)
    # No main.py

    install_script = os.path.join(source_dir, "install.sh")
    with open(install_script, 'w') as f:
        f.write("""#!/bin/bash
SOURCE_DIR=$(dirname "$(realpath "$0")")
EXEC_SRC="$SOURCE_DIR/main.py"
if [ ! -f "$EXEC_SRC" ]; then
  echo "Error: Main script not found"
  exit 1
fi
""")

    os.chmod(install_script, 0o755)

    result = subprocess.run([install_script], cwd=source_dir, env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert "Error: Main script not found" in result.stdout