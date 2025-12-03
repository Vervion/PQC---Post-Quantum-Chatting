#!/bin/bash
# Run PQC Chat Server
# Simple script to start the server for development/testing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Check for certificates
if [ ! -f "server.crt" ] || [ ! -f "server.key" ]; then
    echo "Generating development certificates..."
    "$SCRIPT_DIR/generate_certs.sh" .
fi

echo "Starting PQC Chat Server..."
python3 run_server.py "$@"
