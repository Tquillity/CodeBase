#!/bin/bash
# Install script for CodeBase

# Get the directory where the script is located
INSTALL_DIR=$(dirname "$(realpath "$0")")
EXEC_PATH="$INSTALL_DIR/CodeBase"
ICON_SRC="$INSTALL_DIR/icon.ico"
DESKTOP_SRC="$INSTALL_DIR/codebase.desktop"
ICON_DEST="$HOME/.local/share/icons/codebase.ico"
DESKTOP_DEST="$HOME/.local/share/applications/codebase.desktop"

# Check if required files exist
if [ ! -f "$EXEC_PATH" ]; then
    echo "Error: CodeBase executable not found at $EXEC_PATH"
    exit 1
fi
if [ ! -f "$ICON_SRC" ]; then
    echo "Error: Icon file not found at $ICON_SRC"
    exit 1
fi
if [ ! -f "$DESKTOP_SRC" ]; then
    echo "Error: Desktop file not found at $DESKTOP_SRC"
    exit 1
fi

# Ensure destination directories exist and are writable
mkdir -p "$HOME/.local/share/icons" || { echo "Error: Cannot create icons directory"; exit 1; }
mkdir -p "$HOME/.local/share/applications" || { echo "Error: Cannot create applications directory"; exit 1; }

# Copy icon to user's icons directory
cp "$ICON_SRC" "$ICON_DEST" || { echo "Error: Failed to copy icon to $ICON_DEST"; exit 1; }

# Create or update .desktop file
cat << EOF > "$DESKTOP_DEST"
[Desktop Entry]
Version=1.0
Name=CodeBase
Comment=A tool to scan repositories and copy contents
Exec=$EXEC_PATH
Icon=$ICON_DEST
Terminal=false
Type=Application
Categories=Utility;Development;
StartupWMClass=CodeBase
EOF

# Check if .desktop file was created successfully
if [ ! -f "$DESKTOP_DEST" ]; then
    echo "Error: Failed to create .desktop file at $DESKTOP_DEST"
    exit 1
fi

# Make the .desktop file executable
chmod +x "$DESKTOP_DEST" || { echo "Error: Failed to make .desktop file executable"; exit 1; }

# Update desktop database
update-desktop-database "$HOME/.local/share/applications" || echo "Warning: Failed to update desktop database"

echo "CodeBase installed successfully! Check your Applications menu."