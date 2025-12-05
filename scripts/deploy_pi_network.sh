#!/bin/bash
# PQC Chat Raspberry Pi Network Deployment Guide
# This script helps deploy the PQC Chat application across 3 Raspberry Pi 5s

set -e

echo "=== PQC Chat Raspberry Pi Network Deployment ==="
echo ""

# Function to detect which Pi this is based on IP
detect_pi_role() {
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    case $LOCAL_IP in
        "192.168.10.101")
            echo "server"
            ;;
        "192.168.10.102")
            echo "client1"
            ;;
        "192.168.10.103")
            echo "client2"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# Function to setup server
setup_server() {
    echo "Setting up this Pi as PQC Chat Server (192.168.10.101)"
    
    # Copy server configuration
    sudo cp config/server_pi.toml /etc/pqc-chat/server.toml
    
    # Generate certificates if they don't exist
    if [ ! -f "/etc/pqc-chat/server.crt" ] || [ ! -f "/etc/pqc-chat/server.key" ]; then
        echo "Generating TLS certificates..."
        sudo ./scripts/generate_certs.sh
    fi
    
    # Install and enable server service
    sudo ./scripts/install_server.sh
    sudo systemctl enable pqc-chat-server
    sudo systemctl start pqc-chat-server
    
    echo "Server setup complete!"
    echo "Server is now running on:"
    echo "  - Signaling: https://192.168.10.101:8443"
    echo "  - Audio: udp://192.168.10.101:10000"
    echo "  - Video: udp://192.168.10.101:10001"
}

# Function to setup client
setup_client() {
    CLIENT_NUM=$1
    echo "Setting up this Pi as PQC Chat Client $CLIENT_NUM"
    
    # Copy appropriate client configuration
    sudo cp config/client${CLIENT_NUM}_pi.toml /etc/pqc-chat/client.toml
    
    # Install client
    sudo ./scripts/install_client.sh
    
    echo "Client $CLIENT_NUM setup complete!"
    echo "To start the GUI client, run: /opt/pqc-chat/bin/pqc-gui"
    echo "Or to start with systemd: systemctl --user enable pqc-chat-client@default"
}

# Main deployment logic
main() {
    # Check if we're in the right directory
    if [ ! -f "Cargo.toml" ] || [ ! -d "src" ]; then
        echo "Error: Please run this script from the PQC Chat project root directory"
        exit 1
    fi
    
    # Build the project first
    echo "Building PQC Chat..."
    cargo build --release
    
    # Detect Pi role
    ROLE=$(detect_pi_role)
    
    case $ROLE in
        "server")
            setup_server
            ;;
        "client1")
            setup_client 1
            ;;
        "client2")
            setup_client 2
            ;;
        "unknown")
            echo "Warning: Could not auto-detect Pi role based on IP address."
            echo "Current IP: $(hostname -I | awk '{print $1}')"
            echo ""
            echo "Please run setup manually:"
            echo "  For server (192.168.10.101): sudo ./scripts/setup_pi.sh server"
            echo "  For client 1 (192.168.10.102): sudo ./scripts/setup_pi.sh client1"
            echo "  For client 2 (192.168.10.103): sudo ./scripts/setup_pi.sh client2"
            exit 1
            ;;
    esac
    
    echo ""
    echo "=== Deployment Complete ==="
    echo "Network status:"
    echo "  Server Pi (192.168.10.101): $(ping -c1 192.168.10.101 &>/dev/null && echo "Online" || echo "Offline")"
    echo "  Client Pi 1 (192.168.10.102): $(ping -c1 192.168.10.102 &>/dev/null && echo "Online" || echo "Offline")"
    echo "  Client Pi 2 (192.168.10.103): $(ping -c1 192.168.10.103 &>/dev/null && echo "Online" || echo "Offline")"
    echo ""
    echo "Current network configuration:"
    echo "  Ethernet (eth0): $(ip addr show eth0 2>/dev/null | grep 'inet ' | awk '{print $2}' || echo "Not configured")"
    echo "  WLAN (wlan0): $(ip addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' || echo "Not connected")"
    echo "  Internet access: $(ping -c1 google.com &>/dev/null && echo "Available" || echo "Not available")"
}

# Handle manual role specification
if [ $# -eq 1 ]; then
    case $1 in
        "server")
            setup_server
            ;;
        "client1")
            setup_client 1
            ;;
        "client2")
            setup_client 2
            ;;
        *)
            echo "Usage: $0 [server|client1|client2]"
            echo "If no argument is provided, role will be auto-detected based on IP address."
            exit 1
            ;;
    esac
else
    main
fi