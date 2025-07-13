#!/bin/bash

# Installation script for CodeBase

# --- Configuration ---
APP_NAME="CodeBase"
EXEC_NAME="CodeBase" # Command to run the app
MAIN_SCRIPT="main.py"
ICON_NAME="icon.png" # Make sure you have an icon.png file
DESKTOP_FILE_NAME="codebase.desktop" # Name of the .desktop file template

# --- Directories ---
# Get the directory where this script is located
SOURCE_DIR=$(dirname "$(realpath "$0")")

# Use standard Freedesktop locations within the user's home directory
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/128x128/apps" # Example size, adjust if needed
PIXMAPS_DIR="$HOME/.local/share/pixmaps" # Fallback/alternative icon location

# --- Source File Paths ---
EXEC_SRC="$SOURCE_DIR/$MAIN_SCRIPT" # The main Python script
WRAPPER_SCRIPT_DEST="$BIN_DIR/$EXEC_NAME" # A wrapper script to run the main python file
ICON_SRC="$SOURCE_DIR/$ICON_NAME"
DESKTOP_SRC="$SOURCE_DIR/$DESKTOP_FILE_NAME" # Template desktop file

# --- Destination File Paths ---
ICON_DEST="$ICON_DIR/$APP_NAME.png" # Use App Name for icon destination
PIXMAP_DEST="$PIXMAPS_DIR/$APP_NAME.png"
DESKTOP_DEST="$APPS_DIR/$DESKTOP_FILE_NAME"

# --- Pre-checks ---
echo "Starting CodeBase installation..."

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not found. Please install Python 3."
    exit 1
fi
# Check for pip
if ! python3 -m pip --version &> /dev/null; then
    echo "Warning: pip for Python 3 not found. Dependency installation might fail."
    # Optionally exit here: exit 1
fi

# Check source files exist
if [ ! -f "$EXEC_SRC" ]; then
    echo "Error: Main script not found at $EXEC_SRC"
    exit 1
fi
if [ ! -f "$ICON_SRC" ]; then
    echo "Warning: Icon file not found at $ICON_SRC. Installation will continue without icon."
    # Do not exit, just skip icon steps
else
    INSTALL_ICON=true
fi
if [ ! -f "$DESKTOP_SRC" ]; then
    echo "Warning: Desktop file template not found at $DESKTOP_SRC. Skipping desktop integration."
    # Do not exit, just skip desktop file steps
    INSTALL_DESKTOP=true
fi

# Check dependencies (requirements.txt)
if [ -f "$SOURCE_DIR/requirements.txt" ]; then
    echo "Please ensure dependencies are installed, for example using:"
    echo "python3 -m pip install --user -r $SOURCE_DIR/requirements.txt"
    echo "(Run this manually if needed)"
    # Optionally run pip install here, but often better for user to manage venvs etc.
    # python3 -m pip install --user -r "$SOURCE_DIR/requirements.txt" || echo "Warning: Failed to install dependencies."
else
    echo "Warning: requirements.txt not found. Cannot verify dependencies."
fi

# --- Create Directories ---
echo "Creating necessary directories..."
mkdir -p "$BIN_DIR" || { echo "Error: Cannot create bin directory $BIN_DIR"; exit 1; }
if [ "$INSTALL_DESKTOP" = true ]; then
    mkdir -p "$APPS_DIR" || { echo "Error: Cannot create applications directory $APPS_DIR"; exit 1; }
fi
if [ "$INSTALL_ICON" = true ]; then
    mkdir -p "$ICON_DIR" || { echo "Warning: Cannot create standard icon directory $ICON_DIR"; }
    mkdir -p "$PIXMAPS_DIR" || { echo "Warning: Cannot create pixmaps directory $PIXMAPS_DIR"; }
fi

# --- Create Wrapper Script ---
echo "Creating executable wrapper script..."
# This wrapper ensures it runs with python3 from the correct source directory context (if needed)
# Or simply runs the main script via the installed command. Here, simpler version:
cat << EOF > "$WRAPPER_SCRIPT_DEST"
#!/bin/bash
# Wrapper script to launch CodeBase Python application
# Get the directory where the main script *should* be relative to this wrapper,
# or assume it's globally runnable if installed via pip/setuptools.
# For this simple install, let's assume we run the python script directly.
# User should ensure python3 is in PATH and dependencies are installed.
python3 "$EXEC_SRC" "\$@"
EOF

# Make the wrapper executable
chmod +x "$WRAPPER_SCRIPT_DEST" || { echo "Error: Failed to make wrapper script executable"; exit 1; }
echo "Wrapper script created at $WRAPPER_SCRIPT_DEST"


# --- Install Icon ---
if [ "$INSTALL_ICON" = true ]; then
    echo "Installing icon..."
    cp "$ICON_SRC" "$ICON_DEST" 2>/dev/null || echo "Warning: Failed to copy icon to $ICON_DIR. Trying pixmaps..."
    cp "$ICON_SRC" "$PIXMAP_DEST" || echo "Warning: Failed to copy icon to $PIXMAPS_DIR."
fi

# --- Install Desktop File ---
if [ "$INSTALL_DESKTOP" = true ]; then
    echo "Installing desktop file..."
    cp "$DESKTOP_SRC" "$DESKTOP_DEST" || { echo "Error: Failed to copy .desktop file"; exit 1; }

    # Replace placeholders in the .desktop file
    # Use @ as delimiter for sed to avoid issues with slashes in paths
    EXEC_DEST_ESCAPED=$(printf '%s\n' "$WRAPPER_SCRIPT_DEST" | sed 's@[&/@\]@\\&@g')
    ICON_DEST_ESCAPED=$(printf '%s\n' "$APP_NAME" | sed 's@[&/@\]@\\&@g') # Use App Name, system finds icon
    # ICON_DEST_ESCAPED=$(printf '%s\n' "$ICON_DEST" | sed 's@[&/@\]@\\&@g') # Alternative: full path

    sed -i "s@^Exec=.*@Exec=$EXEC_DEST_ESCAPED@" "$DESKTOP_DEST"
    sed -i "s@^Icon=.*@Icon=$ICON_DEST_ESCAPED@" "$DESKTOP_DEST"
    # Add TryExec for robustness
    sed -i "/^Exec=/a TryExec=$EXEC_DEST_ESCAPED" "$DESKTOP_DEST"

    # Update desktop database
    echo "Updating desktop database..."
    update-desktop-database -q "$APPS_DIR" || echo "Warning: Failed to update desktop database. Menu item might be delayed."
fi

echo ""
echo "----------------------------------------"
echo "CodeBase installation/update finished!"
echo "----------------------------------------"
echo "You should now be able to run '$EXEC_NAME' from your terminal."
if [ "$INSTALL_DESKTOP" = true ]; then
    echo "A menu entry for '$APP_NAME' should appear shortly (may require logout/login)."
fi
echo "Ensure Python dependencies from requirements.txt are installed."

exit 0