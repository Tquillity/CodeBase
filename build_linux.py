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
MAINTAINER = "Mikael Sundh <mikael.sundh@gmail.com>"
URL = "https://www.mikaelsundh.com"
ARCH = "x86_64"

# Paths
ASSETS_DIR = "assets"
DIST_DIR = "dist"
BUILD_DIR = "build_staging"  # Assembly directory for RPM structure

def run_command(command):
    print(f"Running: {' '.join(command)}")
    try:
        subprocess.check_call(command)
    except subprocess.CalledProcessError as e:
        print(f"Error command failed: {e}")
        sys.exit(1)

def clean():
    print("Cleaning previous builds...")
    if os.path.exists(DIST_DIR): shutil.rmtree(DIST_DIR)
    if os.path.exists("build"): shutil.rmtree("build")
    if os.path.exists(BUILD_DIR): shutil.rmtree(BUILD_DIR)
    if os.path.exists(f"{APP_NAME}.spec"): os.remove(f"{APP_NAME}.spec")

def build_binary():
    print("Compiling Python to Binary with PyInstaller...")
    
    # Check if PyInstaller is installed first
    try:
        # Check silently if installed
        subprocess.check_call([sys.executable, "-m", "pip", "show", "pyinstaller"], stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("Warning: PyInstaller not found. Attempting to install...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Build command using python -m PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", APP_NAME,
        "--icon", os.path.join(ASSETS_DIR, "icon.png"),
        "--add-data", f"codebase-icon.svg{os.pathsep}.",
        
        # Collect necessary modules for standalone execution
        "--collect-all", "tkinterdnd2",
        "--collect-all", "ttkbootstrap",
        "--collect-all", "PIL",
        "--collect-all", "tiktoken",
        
        "main.py"
    ]
    run_command(cmd)

def create_linux_structure():
    print("Creating Linux directory structure...")
    
    # Define paths inside the package
    usr_bin = os.path.join(BUILD_DIR, "usr", "bin")
    usr_share_apps = os.path.join(BUILD_DIR, "usr", "share", "applications")
    usr_share_icons = os.path.join(BUILD_DIR, "usr", "share", "icons", "hicolor", "512x512", "apps")
    
    # Create directories
    os.makedirs(usr_bin, exist_ok=True)
    os.makedirs(usr_share_apps, exist_ok=True)
    os.makedirs(usr_share_icons, exist_ok=True)

    # 1. Copy Binary
    src_binary = os.path.join(DIST_DIR, APP_NAME)
    dst_binary = os.path.join(usr_bin, APP_NAME)
    shutil.copy2(src_binary, dst_binary)
    
    # Make executable
    os.chmod(dst_binary, 0o755)

    # 2. Copy Icon
    shutil.copy2(os.path.join(ASSETS_DIR, "icon.png"), os.path.join(usr_share_icons, f"{APP_NAME.lower()}.png"))

    # 3. Create .desktop file
    desktop_content = f"""[Desktop Entry]
Version={VERSION}
Name={APP_NAME}
Comment={DESCRIPTION}
Exec=/usr/bin/{APP_NAME}
Icon={APP_NAME.lower()}
Type=Application
Terminal=false
Categories=Development;Utility;
StartupWMClass={APP_NAME}
"""
    with open(os.path.join(usr_share_apps, f"{APP_NAME.lower()}.desktop"), "w") as f:
        f.write(desktop_content)

def build_rpm():
    print("Packaging RPM...")
    cmd = [
        "fpm",
        "-s", "dir",
        "-t", "rpm",
        "-n", APP_NAME.lower(),
        "-v", VERSION,
        "-a", ARCH,
        "--description", DESCRIPTION,
        "--maintainer", MAINTAINER,
        "--url", URL,
        "--license", "MIT",
        "--rpm-os", "linux",
        "-C", BUILD_DIR,
        "."
    ]
    run_command(cmd)
    
    # Move RPM to dist root for easy access
    rpm_name = f"{APP_NAME.lower()}-{VERSION}-1.{ARCH}.rpm"
    if os.path.exists(rpm_name):
        shutil.move(rpm_name, os.path.join(DIST_DIR, rpm_name))
        print(f"\nSUCCESS! RPM is located at: {os.path.join(DIST_DIR, rpm_name)}")

if __name__ == "__main__":
    clean()
    build_binary()
    create_linux_structure()
    build_rpm()

