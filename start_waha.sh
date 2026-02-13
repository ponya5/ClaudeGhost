#!/bin/bash
# WAHA Server Launcher for macOS/Linux
# ClaudeGhost - WhatsApp HTTP API Server Manager

echo ""
echo "  ===================================="
echo "   WAHA Server Launcher (Unix)"
echo "  ===================================="
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "[ERROR] Python not found!"
        echo "Install Python from: https://python.org"
        exit 1
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

# Run the Python script with all arguments
$PYTHON_CMD "$SCRIPT_DIR/start_waha.py" "$@"

exit $?
