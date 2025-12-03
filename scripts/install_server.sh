#!/bin/bash
# PQC Chat Server Installation Script
# Run this script on your Raspberry Pi to install the PQC Chat server

set -e

echo "=== PQC Chat Server Installation ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Configuration
INSTALL_DIR="/opt/pqc-chat"
CONFIG_DIR="/etc/pqc-chat"
LOG_DIR="/var/log/pqc-chat"
SERVICE_USER="pqc-chat"

# Install dependencies
echo "Installing dependencies..."
apt-get update
apt-get install -y python3 python3-pip openssl

# Create service user
echo "Creating service user..."
if ! id -u "$SERVICE_USER" > /dev/null 2>&1; then
    useradd --system --no-create-home --shell /bin/false "$SERVICE_USER"
fi

# Create directories
echo "Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$LOG_DIR"

# Copy application files
echo "Installing application files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cp -r "$PROJECT_DIR/server" "$INSTALL_DIR/"
cp -r "$PROJECT_DIR/client" "$INSTALL_DIR/"
cp "$PROJECT_DIR/run_server.py" "$INSTALL_DIR/" 2>/dev/null || echo "Note: run_server.py not found, will need to create"

# Install configuration
echo "Installing configuration..."
if [ ! -f "$CONFIG_DIR/server.conf" ]; then
    cp "$PROJECT_DIR/config/server.conf" "$CONFIG_DIR/"
fi

# Generate TLS certificates if not present
if [ ! -f "$CONFIG_DIR/server.crt" ] || [ ! -f "$CONFIG_DIR/server.key" ]; then
    echo "Generating TLS certificates..."
    openssl req -x509 -newkey rsa:4096 \
        -keyout "$CONFIG_DIR/server.key" \
        -out "$CONFIG_DIR/server.crt" \
        -days 365 -nodes \
        -subj "/CN=pqc-chat-server/O=PQC Chat/C=US"
fi

# Set permissions
echo "Setting permissions..."
chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
chown -R root:root "$INSTALL_DIR"
chown -R root:"$SERVICE_USER" "$CONFIG_DIR"
chmod 750 "$CONFIG_DIR"
chmod 640 "$CONFIG_DIR"/*

# Install systemd service
echo "Installing systemd service..."
cp "$PROJECT_DIR/systemd/pqc-chat-server.service" /etc/systemd/system/
systemctl daemon-reload

echo ""
echo "=== Installation Complete ==="
echo ""
echo "To start the server:"
echo "  sudo systemctl start pqc-chat-server"
echo ""
echo "To enable on boot:"
echo "  sudo systemctl enable pqc-chat-server"
echo ""
echo "To check status:"
echo "  sudo systemctl status pqc-chat-server"
echo ""
echo "Configuration file: $CONFIG_DIR/server.conf"
echo "Log file: $LOG_DIR/server.log"
