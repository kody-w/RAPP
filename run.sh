#!/bin/bash
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    source .venv/Scripts/activate
fi
echo "Starting Copilot Agent 365..."
echo "Local URL: http://localhost:7071/api/businessinsightbot_function"
echo "Press Ctrl+C to stop"
func start
