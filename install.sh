#!/bin/bash
# Install script for CodeBase v2.0

EXEC_NAME="CodeBase"
ICON_NAME="icon.png"
DESKTOP_FILE="codebase.desktop"
SOURCE_DIR=$(dirname "$(realpath "$0")")
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/pixmaps"

EXEC_DEST="$BIN_DIR/$EXEC_NAME"
ICON_DEST="$ICON_DIR/$ICON_NAME"
DESKTOP_DEST="$APPS_DIR/$DESKTOP_FILE"

# Check dependencies
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Python 3 is not installed. Please install it (e.g., 'sudo dnf install python3' on Fedora)."
    exit 1
fi
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "Error: Tkinter is not installed. Please install it (e.g., 'sudo dnf install python3-tkinter' on Fedora)."
    exit 1
fi

# Check files
for file in "$SOURCE_DIR/main.py" "$SOURCE_DIR/$ICON_NAME" "$SOURCE_DIR/$DESKTOP_FILE"; do
    if [ ! -f "$file" ]; then
        echo "Error: $file not found"
        exit 1
    fi
done

# Create directories
mkdir -p "$BIN_DIR" || { echo "Error: Failed to create $BIN_DIR"; exit 1; }
mkdir -p "$APPS_DIR" || { echo "Error: Failed to create $APPS_DIR"; exit 1; }
mkdir -p "$ICON_DIR" || { echo "Error: Failed to create $ICON_DIR"; exit 1; }

# Copy files
cp "$SOURCE_DIR/"*.py "$BIN_DIR/" || { echo "Error: Failed to copy Python files to $BIN_DIR"; exit 1; }
cp "$SOURCE_DIR/$ICON_NAME" "$ICON_DEST" || { echo "Error: Failed to copy $ICON_NAME to $ICON_DEST"; exit 1; }
cp "$SOURCE_DIR/$DESKTOP_FILE" "$DESKTOP_DEST" || { echo "Error: Failed to copy $DESKTOP_FILE to $DESKTOP_DEST"; exit 1; }

# Create executable
echo "#!/usr/bin/env python3" > "$EXEC_DEST"
cat "$SOURCE_DIR/main.py" >> "$EXEC_DEST" || { echo "Error: Failed to create executable at $EXEC_DEST"; exit 1; }
chmod +x "$EXEC_DEST" || { echo "Error: Failed to make $EXEC_DEST executable"; exit 1; }

# Update desktop file
sed -i "s|@EXEC_PATH@|$EXEC_DEST|" "$DESKTOP_DEST" || { echo "Error: Failed to update desktop file exec path"; exit 1; }
sed -i "s|@ICON_PATH@|$ICON_DEST|" "$DESKTOP_DEST" || { echo "Error: Failed to update desktop file icon path"; exit 1; }

update-desktop-database "$APPS_DIR" || echo "Warning: Desktop database update failed"
echo "CodeBase v2.0 installed successfully!"