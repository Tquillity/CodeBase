from __future__ import annotations

import os
import shutil
import subprocess
import sys

# Import version from constants.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from constants import VERSION

# --- CONFIGURATION ---
APP_NAME = "CodeBase"
DESCRIPTION = "CodeBase Repository Manager"

# Paths
ASSETS_DIR = "assets"
DIST_DIR = "dist"
ICON_ICO = os.path.join(ASSETS_DIR, "icon.ico")


def run_command(command: list[str]) -> None:
    print(f"Running: {' '.join(command)}")
    try:
        subprocess.check_call(command)
    except subprocess.CalledProcessError as e:
        print(f"Error command failed: {e}")
        sys.exit(1)


def clean() -> None:
    print("Cleaning previous builds...")
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists(f"{APP_NAME}.spec"):
        os.remove(f"{APP_NAME}.spec")


def ensure_pyinstaller() -> None:
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "show", "pyinstaller"],
            stdout=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        print("Warning: PyInstaller not found. Attempting to install...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0.0,<7"])


def ensure_icon() -> None:
    """Make sure a multi-size .ico exists; regenerate from icon.png if missing."""
    if os.path.exists(ICON_ICO):
        return
    png = os.path.join(ASSETS_DIR, "icon.png")
    if not os.path.exists(png):
        print(f"Warning: neither {ICON_ICO} nor {png} found; building without an icon.")
        return
    try:
        from PIL import Image  # Pillow is already a runtime dependency
        print(f"Generating {ICON_ICO} from {png}...")
        Image.open(png).save(
            ICON_ICO, sizes=[(16, 16), (32, 32), (48, 48), (256, 256)]
        )
    except Exception as e:
        print(f"Warning: could not generate .ico ({e}); building without an icon.")


def build_binary() -> None:
    print(f"Compiling {APP_NAME} v{VERSION} to a Windows executable with PyInstaller...")
    ensure_pyinstaller()
    ensure_icon()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", APP_NAME,
    ]

    if os.path.exists(ICON_ICO):
        # Windows embeds the .exe icon from a real .ico (not a .png).
        cmd += ["--icon", ICON_ICO]

    # Bundle data files. os.pathsep is ';' on Windows, the separator PyInstaller
    # expects for --add-data "SRC<sep>DEST".
    cmd += [
        "--add-data", f"codebase-icon.svg{os.pathsep}.",
        # Bundle the assets folder so the runtime window icon (assets/icon.ico,
        # resolved via sys._MEIPASS in main.set_window_icon) is found.
        "--add-data", f"{ASSETS_DIR}{os.pathsep}{ASSETS_DIR}",

        # Collect packages that load data/native libs at runtime. tkinterdnd2
        # ships the native tkdnd Tcl extension as DATA (pkgIndex.tcl + .dll),
        # which PyInstaller misses without an explicit --collect-data, silently
        # disabling drag-and-drop in the frozen exe.
        "--collect-all", "tkinterdnd2",
        "--collect-data", "tkinterdnd2",
        "--collect-all", "ttkbootstrap",
        "--collect-all", "PIL",
        "--collect-all", "tiktoken",

        "main.py",
    ]
    run_command(cmd)


def main() -> None:
    clean()
    build_binary()
    exe = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
    if os.path.exists(exe):
        print(f"\nSUCCESS! Windows executable is located at: {exe}")
        print("Optionally run install.ps1 to create Start Menu / Desktop shortcuts.")
    else:
        print("\nBuild finished but the expected executable was not found.")
        sys.exit(1)


if __name__ == "__main__":
    main()
