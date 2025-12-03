# PQC - Post-Quantum Chatting

A LAN-based, post-quantum secure audio/video chat system designed to run on Raspberry Pis.

**Built with Rust and Kyber post-quantum cryptography.**

## Overview

This project implements a secure audio/video chat system with the following features:
- **Kyber1024 post-quantum key exchange** for quantum-resistant encryption
- TLS 1.3 encrypted signaling channel
- DTLS-SRTP encrypted media transport (stub implementation)
- Room-based chat system
- Native egui GUI client
- Designed for Raspberry Pi deployment

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PQC Chat Server (Rust)                   │
│  ┌─────────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  TLS Listener   │  │    Room     │  │   Media         │  │
│  │  + Kyber KEM    │  │   Manager   │  │   Forwarder     │  │
│  └────────┬────────┘  └──────┬──────┘  └───────┬─────────┘  │
│           │                  │                 │            │
│           └──────────────────┴─────────────────┘            │
└─────────────────────────────────────────────────────────────┘
                           │
                    TLS + Kyber / DTLS-SRTP
                           │
┌─────────────────────────────────────────────────────────────┐
│                    PQC Chat Client (Rust)                   │
│  ┌─────────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   Signaling     │  │  AV Capture │  │   Media         │  │
│  │   + Kyber KEM   │  │   (Stubs)   │  │   Transport     │  │
│  └────────┬────────┘  └──────┬──────┘  └───────┬─────────┘  │
│           │                  │                 │            │
│           └──────────────────┴─────────────────┘            │
│                          │                                  │
│                   ┌──────┴──────┐                           │
│                   │  egui GUI   │                           │
│                   └─────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

## Components

### Server (`src/server/`)
- **main.rs**: TCP TLS listener with Kyber key exchange for signaling connections
- Async Tokio runtime for high performance
- Post-quantum key exchange using Kyber1024

### Client (`src/client/`)
- **main.rs**: TLS signaling client with Kyber key exchange
- Command-line interface for testing

### GUI (`src/gui/`)
- **main.rs**: egui-based native GUI with controls for:
  - Server connection
  - Room browsing and creation
  - Joining/leaving rooms
  - Audio/video toggle

### Library (`src/`)
- **crypto/kyber.rs**: Kyber1024 key encapsulation mechanism
- **protocol.rs**: JSON signaling message definitions
- **room.rs**: Room and participant management
- **media.rs**: DTLS-SRTP media handling stubs
- **config.rs**: Configuration structures

### Configuration (`config/`)
- **server.toml**: Server configuration (TOML format)
- **client.toml**: Client configuration (TOML format)

### Scripts (`scripts/`)
- **install_server.sh**: Server installation for Raspberry Pi
- **install_client.sh**: Client installation for Raspberry Pi
- **generate_certs.sh**: TLS certificate generation
- **run_server.sh**: Development server launcher
- **run_client.sh**: Development client launcher

### Systemd (`systemd/`)
- **pqc-chat-server.service**: Server systemd service
- **pqc-chat-client@.service**: Client systemd service template

## Quick Start

### Prerequisites

- Rust 1.70+ (install via https://rustup.rs/)
- OpenSSL development libraries
- For GUI: X11/Wayland development libraries

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Vervion/PQC---Post-Quantum-Chatting.git
   cd PQC---Post-Quantum-Chatting
   ```

2. Build the project:
   ```bash
   cargo build --release
   ```

3. Generate TLS certificates:
   ```bash
   ./scripts/generate_certs.sh
   ```

4. Run the server:
   ```bash
   ./target/release/pqc-server
   # Or use the script:
   ./scripts/run_server.sh
   ```

5. Run the client (in another terminal):
   ```bash
   ./target/release/pqc-client --host 127.0.0.1
   # Or run the GUI:
   ./target/release/pqc-gui
   ```

### Raspberry Pi Installation

#### Server Installation
```bash
sudo ./scripts/install_server.sh
sudo systemctl enable pqc-chat-server
sudo systemctl start pqc-chat-server
```

#### Client Installation
```bash
sudo ./scripts/install_client.sh
# Edit /etc/pqc-chat/client.toml with server address
/opt/pqc-chat/bin/pqc-gui
```

## Running Tests

```bash
# Run Rust unit tests
cargo test

# Run Python integration tests
python3 -m unittest discover tests/
```

## Configuration

### Server Configuration (`config/server.toml`)

```toml
signaling_host = "0.0.0.0"
signaling_port = 8443
audio_port = 10000
video_port = 10001
certfile = "server.crt"
keyfile = "server.key"
default_max_participants = 10
log_level = "info"
```

### Client Configuration (`config/client.toml`)

```toml
server_host = "192.168.1.100"
signaling_port = 8443
default_username = "RaspberryPi"
log_level = "info"

[video]
width = 640
height = 480
fps = 30

[audio]
sample_rate = 48000
channels = 1
```

## Protocol

### Kyber Key Exchange

Before signaling begins, a post-quantum key exchange is performed:

1. Client generates Kyber1024 key pair
2. Client sends public key to server (`KeyExchangeInit`)
3. Server encapsulates shared secret and returns ciphertext (`KeyExchangeResponse`)
4. Client decapsulates to derive same shared secret
5. Shared secret can be used for additional encryption layers

### Signaling Messages

The client and server communicate via JSON messages over TLS:

| Message Type | Direction | Description |
|--------------|-----------|-------------|
| key_exchange_init | C→S | Send Kyber public key |
| key_exchange_response | S→C | Return ciphertext |
| login | C→S | User authentication |
| list_rooms | C→S | Request room list |
| create_room | C→S | Create a new room |
| join_room | C→S | Join an existing room |
| leave_room | C→S | Leave current room |
| toggle_audio | C→S | Toggle audio state |
| toggle_video | C→S | Toggle video state |
| participant_joined | S→C | Notification of new participant |
| participant_left | S→C | Notification of participant leaving |

## Implementation Status

- ✅ Rust server with TLS listener
- ✅ Kyber1024 post-quantum key exchange
- ✅ Basic room manager
- ✅ DTLS-SRTP media forwarder stubs
- ✅ Rust signaling client
- ✅ Audio/video capture stubs
- ✅ DTLS-SRTP media transport stubs
- ✅ egui native GUI
- ✅ TOML configuration
- ✅ Systemd service files
- ✅ Installation scripts for Raspberry Pi

## Future Enhancements

- [ ] Use Kyber shared secret for additional media encryption
- [ ] Real DTLS-SRTP implementation
- [ ] Actual audio/video capture integration
- [ ] Audio/video encoding (Opus, VP8/VP9)
- [ ] ICE/STUN/TURN support for NAT traversal
- [ ] End-to-end encryption for media using Kyber-derived keys
- [ ] Screen sharing
- [ ] Text chat

## Security

This project uses **Kyber1024**, a NIST-selected post-quantum key encapsulation mechanism that is resistant to attacks from both classical and quantum computers.

## License

MIT License - see [LICENSE](LICENSE) for details.
