#!/bin/bash
# RAPP CLI Helper Script
# Usage: ./rapp-cli.sh [arguments]
# Example: ./rapp-cli.sh --message "Hello"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate virtual environment and run CLI
source "$SCRIPT_DIR/.venv/bin/activate"
python "$SCRIPT_DIR/cli.py" "$@"
