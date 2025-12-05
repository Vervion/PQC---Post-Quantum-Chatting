# PQC Chat - Raspberry Pi 5 Network Setup

This guide provides complete instructions for setting up PQC Chat across 3 Raspberry Pi 5s connected via ethernet switch with static IP addresses.

## Quick Start

1. **Configure static network on all Pis** (see [NETWORK_SETUP.md](NETWORK_SETUP.md))
2. **Deploy the application on each Pi**:
   ```bash
   # On each Pi, clone and build the project
   git clone https://github.com/Vervion/PQC---Post-Quantum-Chatting.git
   cd PQC---Post-Quantum-Chatting
   
   # Run the deployment script (auto-detects role based on IP)
   sudo ./scripts/deploy_pi_network.sh
   ```

## Network Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Pi 1 (Server)   │    │ Pi 2 (Client)   │    │ Pi 3 (Client)   │
│ 192.168.10.101  │◄──►│ 192.168.10.102  │    │ 192.168.10.103  │
│ pqc-server      │    │ pqc-client1     │◄──►│ pqc-client2     │
│                 │    │                 │    │                 │
│ Runs:           │    │ Runs:           │    │ Runs:           │
│ - pqc-server    │    │ - pqc-gui       │    │ - pqc-gui       │
│ - Signaling     │    │ - Audio/Video   │    │ - Audio/Video   │
│ - Certificate   │    │   capture       │    │   capture       │
│   management    │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Step-by-Step Setup

### 1. Network Configuration

Follow the detailed instructions in [NETWORK_SETUP.md](NETWORK_SETUP.md) to configure static IP addresses:
- **Pi 1 (Server)**: 192.168.10.101
- **Pi 2 (Client 1)**: 192.168.10.102  
- **Pi 3 (Client 2)**: 192.168.10.103

### 2. Install Dependencies

On **all three Pis**, install required dependencies:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Install system dependencies
sudo apt install -y \
    build-essential \
    pkg-config \
    libssl-dev \
    libasound2-dev \
    libv4l-dev \
    libxkbcommon-dev \
    libwayland-dev \
    libxrandr-dev \
    libxcursor-dev \
    libxi-dev \
    libxinerama-dev \
    libgl1-mesa-dev
```

### 3. Clone and Build

On **all three Pis**:

```bash
# Clone the repository
git clone https://github.com/Vervion/PQC---Post-Quantum-Chatting.git
cd PQC---Post-Quantum-Chatting

# Build the project
cargo build --release
```

### 4. Deploy Application

#### Option A: Automatic Deployment (Recommended)

Run the deployment script on each Pi. It will auto-detect the role based on IP address:

```bash
sudo ./scripts/deploy_pi_network.sh
```

#### Option B: Manual Deployment

**On Pi 1 (Server - 192.168.10.101):**
```bash
sudo ./scripts/deploy_pi_network.sh server
```

**On Pi 2 (Client 1 - 192.168.10.102):**
```bash
sudo ./scripts/deploy_pi_network.sh client1
```

**On Pi 3 (Client 2 - 192.168.10.103):**
```bash
sudo ./scripts/deploy_pi_network.sh client2
```

## Starting the Chat System

### 1. Start the Server (Pi 1)

The server should start automatically after deployment. If needed:

```bash
# Check server status
sudo systemctl status pqc-chat-server

# Start server manually
sudo systemctl start pqc-chat-server

# View server logs
sudo journalctl -u pqc-chat-server -f
```

### 2. Start Clients (Pi 2 & Pi 3)

On each client Pi:

```bash
# Start the GUI application
/opt/pqc-chat/bin/pqc-gui

# Or run from the project directory
./target/release/pqc-gui
```

## Configuration Files

The deployment creates these configuration files:

- **Server (Pi 1)**: `/etc/pqc-chat/server.toml`
- **Client 1 (Pi 2)**: `/etc/pqc-chat/client.toml` (points to Pi-Client-1)
- **Client 2 (Pi 3)**: `/etc/pqc-chat/client.toml` (points to Pi-Client-2)

## Port Configuration

The system uses these ports:
- **8443**: HTTPS signaling (encrypted control messages)
- **10000**: UDP audio stream
- **10001**: UDP video stream

Make sure these ports are not blocked by any firewall.

## Troubleshooting

### Network Issues

```bash
# Test network connectivity from any Pi
ping 192.168.10.101  # Server
ping 192.168.10.102  # Client 1  
ping 192.168.10.103  # Client 2

# Test specific ports (from client Pis)
nc -zv 192.168.10.101 8443  # Test signaling port
```

### Server Issues

```bash
# Check server logs
sudo journalctl -u pqc-chat-server -n 50

# Restart server
sudo systemctl restart pqc-chat-server

# Check if ports are listening
sudo netstat -tlnp | grep -E ":(8443|10000|10001)"
```

### Client Issues

```bash
# Run client with debug output
RUST_LOG=debug /opt/pqc-chat/bin/pqc-gui

# Check client configuration
cat /etc/pqc-chat/client.toml
```

### Certificate Issues

If TLS certificates are causing problems:

```bash
# Regenerate certificates on server
cd /path/to/PQC---Post-Quantum-Chatting
sudo ./scripts/generate_certs.sh

# Restart server after certificate regeneration
sudo systemctl restart pqc-chat-server
```

### Audio/Video Issues

```bash
# List available cameras
v4l2-ctl --list-devices

# List audio devices  
arecord -l

# Test camera
ffplay /dev/video0

# Test audio recording
arecord -f cd -t wav -d 5 test.wav && aplay test.wav
```

## Performance Optimization

For optimal performance on Raspberry Pi 5:

1. **GPU Memory Split**: Increase GPU memory to at least 128MB:
   ```bash
   sudo raspi-config
   # Advanced Options → Memory Split → 128
   ```

2. **Disable unnecessary services**:
   ```bash
   sudo systemctl disable bluetooth
   sudo systemctl disable wifi
   # (if using ethernet only)
   ```

3. **Monitor CPU/Memory usage**:
   ```bash
   htop
   # Watch for CPU usage during video chat
   ```

## Security Notes

- The system uses TLS certificates for signaling encryption
- Consider changing default ports if deploying on a network with other services
- The static IP configuration assumes a private network segment
- Kyber post-quantum cryptography is used for key exchange

## Hardware Requirements

- **Raspberry Pi 5** (4GB+ RAM recommended)
- **USB Camera** or **Raspberry Pi Camera Module**
- **USB Microphone** or **Audio HAT**
- **Ethernet cables** (Cat 5e or better)
- **Ethernet switch** (unmanaged is sufficient)

## Next Steps

After successful deployment:
1. Test basic connectivity between all Pis
2. Start a video chat session from both clients
3. Verify audio and video quality
4. Monitor performance and adjust settings if needed

For advanced configuration and troubleshooting, see the individual configuration files in the `config/` directory.