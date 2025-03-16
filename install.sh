#!/bin/bash
# Install script for CodeBase

EXEC_NAME="CodeBase"
ICON_NAME="icon.png"
DESKTOP_FILE="codebase.desktop"
SOURCE_DIR=$(dirname "$(realpath "$0")")
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/pixmaps"

EXEC_SRC="$SOURCE_DIR/main.py"  # Updated for v2.0 structure
ICON_SRC="$SOURCE_DIR/$ICON_NAME"
DESKTOP_SRC="$SOURCE_DIR/$DESKTOP_FILE"

EXEC_DEST="$BIN_DIR/$EXEC_NAME"
ICON_DEST="$ICON_DIR/$ICON_NAME"
DESKTOP_DEST="$APPS_DIR/$DESKTOP_FILE"

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

mkdir -p "$BIN_DIR" || { echo "Error: Cannot create bin directory"; exit 1; }
mkdir -p "$APPS_DIR" || { echo "Error: Cannot create applications directory"; exit 1; }
mkdir -p "$ICON_DIR" || { echo "Error: Cannot create icons directory"; exit 1; }

cp "$EXEC_SRC" "$EXEC_DEST" || { echo "Error: Failed to copy executable"; exit 1; }
cp "$ICON_SRC" "$ICON_DEST" || { echo "Error: Failed to copy icon"; exit 1; }
cp "$DESKTOP_SRC" "$DESKTOP_DEST" || { echo "Error: Failed to copy .desktop file"; exit 1; }

sed -i "s|@EXEC_PATH@|$EXEC_DEST|" "$DESKTOP_DEST"
sed -i "s|@ICON_PATH@|$ICON_DEST|" "$DESKTOP_DEST"

update-desktop-database "$APPS_DIR" || echo "Warning: Failed to update desktop database."

echo "CodeBase installed successfully!"