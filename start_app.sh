#!/bin/bash

# Configuration
PROJECT_DIR="/home/$USER/Documents/backend-df" # Adjust this path as needed
VENV_PATH="$PROJECT_DIR/venv"
PYTHON_BIN="$VENV_PATH/bin/python"
APP_MAIN="$PROJECT_DIR/run.py"

echo "Starting DF-Backpack Application..."
cd "$PROJECT_DIR"

if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Run the application
"$PYTHON_BIN" "$APP_MAIN"
