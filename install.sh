#!/bin/bash
# Install script for CodeBase

# Define file names and directories
EXEC_NAME="CodeBase"
ICON_NAME="icon.png"
DESKTOP_FILE="codebase.desktop"

# Source directory (where the script is run from)
SOURCE_DIR=$(dirname "$(realpath "$0")")

# Destination directories
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/pixmaps"

# Paths to source files (all in the same directory as the script)
EXEC_SRC="$SOURCE_DIR/$EXEC_NAME"
ICON_SRC="$SOURCE_DIR/$ICON_NAME"
DESKTOP_SRC="$SOURCE_DIR/$DESKTOP_FILE"

# Paths to destination files
EXEC_DEST="$BIN_DIR/$EXEC_NAME"
ICON_DEST="$ICON_DIR/$ICON_NAME"
DESKTOP_DEST="$APPS_DIR/$DESKTOP_FILE"

# Check if required files exist
if [ ! -f "$EXEC_SRC" ]; then
    echo "Error: Executable not found at $EXEC_SRC"
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

# Ensure destination directories exist
mkdir -p "$BIN_DIR" || { echo "Error: Cannot create bin directory"; exit 1; }
mkdir -p "$APPS_DIR" || { echo "Error: Cannot create applications directory"; exit 1; }
mkdir -p "$ICON_DIR" || { echo "Error: Cannot create icons directory"; exit 1; }

# Copy files to destination
cp "$EXEC_SRC" "$EXEC_DEST" || { echo "Error: Failed to copy executable to $EXEC_DEST"; exit 1; }
cp "$ICON_SRC" "$ICON_DEST" || { echo "Error: Failed to copy icon to $ICON_DEST"; exit 1; }
cp "$DESKTOP_SRC" "$DESKTOP_DEST" || { echo "Error: Failed to copy .desktop file to $DESKTOP_DEST"; exit 1; }

# Replace placeholders in .desktop file
sed -i "s|@EXEC_PATH@|$EXEC_DEST|" "$DESKTOP_DEST"
sed -i "s|@ICON_PATH@|$ICON_DEST|" "$DESKTOP_DEST"

# Update desktop database (optional, depending on the desktop environment)
update-desktop-database "$APPS_DIR" || echo "Warning: Failed to update desktop database. You may need to log out and log in."

echo "CodeBase installed successfully! Check your Applications menu or log out and log in to see the changes."