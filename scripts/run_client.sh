#!/bin/bash
# Run PQC Chat Client GUI
# Simple script to start the client for development/testing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Build if needed
if [ ! -f "target/release/pqc-gui" ]; then
    echo "Building PQC Chat GUI..."
    cargo build --release --bin pqc-gui --features gui
fi

echo "Starting PQC Chat Client..."
./target/release/pqc-gui "$@"
