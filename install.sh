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

# Check files
for file in "$SOURCE_DIR/main.py" "$SOURCE_DIR/$ICON_NAME" "$SOURCE_DIR/$DESKTOP_FILE"; do
    if [ ! -f "$file" ]; then
        echo "Error: $file not found"
        exit 1
    fi
done

# Create directories
mkdir -p "$BIN_DIR" "$APPS_DIR" "$ICON_DIR" || exit 1

# Copy files
cp "$SOURCE_DIR/"*.py "$BIN_DIR/" || exit 1
cp "$SOURCE_DIR/$ICON_NAME" "$ICON_DEST" || exit 1
cp "$SOURCE_DIR/$DESKTOP_FILE" "$DESKTOP_DEST" || exit 1

# Create executable
echo "#!/usr/bin/env python3" > "$EXEC_DEST"
cat "$SOURCE_DIR/main.py" >> "$EXEC_DEST"
chmod +x "$EXEC_DEST"

# Update desktop file
sed -i "s|@EXEC_PATH@|$EXEC_DEST|" "$DESKTOP_DEST"
sed -i "s|@ICON_PATH@|$ICON_DEST|" "$DESKTOP_DEST"

update-desktop-database "$APPS_DIR" || echo "Warning: Desktop database update failed"
echo "CodeBase v2.0 installed successfully!"