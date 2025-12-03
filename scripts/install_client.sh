#!/bin/bash
# PQC Chat Client Installation Script
# Run this script on your Raspberry Pi to install the PQC Chat client

set -e

echo "=== PQC Chat Client Installation ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Configuration
INSTALL_DIR="/opt/pqc-chat"
CONFIG_DIR="/etc/pqc-chat"
LOG_DIR="/var/log/pqc-chat"

# Install dependencies
echo "Installing dependencies..."
apt-get update
apt-get install -y python3 python3-pip python3-tk

# Optional: Install audio/video dependencies (uncomment if needed)
# apt-get install -y python3-opencv python3-pyaudio

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
cp -r "$PROJECT_DIR/gui" "$INSTALL_DIR/"

# Install configuration
echo "Installing configuration..."
if [ ! -f "$CONFIG_DIR/client.conf" ]; then
    cp "$PROJECT_DIR/config/client.conf" "$CONFIG_DIR/"
fi

# Set permissions
echo "Setting permissions..."
chown -R root:root "$INSTALL_DIR"
chmod -R 755 "$INSTALL_DIR"
mkdir -p "$LOG_DIR"
chmod 755 "$LOG_DIR"

# Install systemd service (template for per-user startup)
echo "Installing systemd service..."
cp "$PROJECT_DIR/systemd/pqc-chat-client@.service" /etc/systemd/system/
systemctl daemon-reload

# Create desktop entry
echo "Creating desktop entry..."
cat > /usr/share/applications/pqc-chat.desktop << 'EOF'
[Desktop Entry]
Name=PQC Chat
Comment=Post-Quantum Secure Video Chat
Exec=/usr/bin/python3 /opt/pqc-chat/gui/main_window.py
Icon=video-display
Terminal=false
Type=Application
Categories=Network;Chat;VideoConference;
EOF

echo ""
echo "=== Installation Complete ==="
echo ""
echo "To start the client GUI:"
echo "  python3 /opt/pqc-chat/gui/main_window.py"
echo ""
echo "Or use the desktop shortcut 'PQC Chat'"
echo ""
echo "To enable auto-start for user 'pi':"
echo "  sudo systemctl enable pqc-chat-client@pi"
echo ""
echo "Configuration file: $CONFIG_DIR/client.conf"
echo ""
echo "Note: Edit $CONFIG_DIR/client.conf to set the server address"
