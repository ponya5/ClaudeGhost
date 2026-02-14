#!/usr/bin/env bash
# ClaudeGhost Launcher (macOS / Linux)
# Usage: ./launch_claudeghost.sh
#        ./launch_claudeghost.sh "your task" [level] [budget]
# Example: ./launch_claudeghost.sh "Create a Python app" 3 10.00

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -z "$1" ]; then
    echo "Starting ClaudeGhost in interactive mode..."
    python3 "$SCRIPT_DIR/claudeghost.py"
else
    TASK="$1"
    LEVEL="${2:-3}"
    BUDGET="${3:-10.00}"

    echo "Starting ClaudeGhost..."
    echo "Task: $TASK"
    echo "Level: $LEVEL"
    echo "Budget: \$$BUDGET"
    echo
    python3 "$SCRIPT_DIR/claudeghost.py" "$TASK" --level "$LEVEL" --budget "$BUDGET"
fi
