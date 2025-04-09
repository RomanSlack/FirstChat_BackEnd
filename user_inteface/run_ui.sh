#!/bin/bash
# Run the FirstChat UI interface

# Get the directory where this script is located
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# Change to the UI directory
cd "$SCRIPT_DIR"

# Check if Flask is installed
if ! python3 -c "import flask" &> /dev/null; then
    echo "Installing Flask..."
    pip install flask requests
fi

# Launch the UI
echo "Starting FirstChat UI on http://localhost:5001"
python3 firstchat_ui.py