#!/bin/bash
# Run PQC Chat Client GUI
# Simple script to start the client for development/testing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Starting PQC Chat Client..."
python3 -m gui.main_window "$@"
