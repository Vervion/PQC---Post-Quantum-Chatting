# PQC - Post-Quantum Chatting

A LAN-based, post-quantum secure audio/video chat system designed to run on Raspberry Pis.

## Overview

This project implements a secure audio/video chat system with the following features:
- TLS 1.3 encrypted signaling channel
- DTLS-SRTP encrypted media transport (stub implementation)
- Room-based chat system
- Python tkinter GUI client
- Designed for Raspberry Pi deployment

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    PQC Chat Server                       │
│  ┌─────────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  TLS Listener   │  │    Room     │  │   Media     │  │
│  │  (Signaling)    │  │   Manager   │  │  Forwarder  │  │
│  └────────┬────────┘  └──────┬──────┘  └──────┬──────┘  │
│           │                  │                │          │
│           └──────────────────┴────────────────┘          │
└─────────────────────────────────────────────────────────┘
                           │
                    TLS/DTLS-SRTP
                           │
┌─────────────────────────────────────────────────────────┐
│                    PQC Chat Client                       │
│  ┌─────────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │   Signaling     │  │  AV Capture │  │   Media     │  │
│  │    Client       │  │   (Stubs)   │  │  Transport  │  │
│  └────────┬────────┘  └──────┬──────┘  └──────┬──────┘  │
│           │                  │                │          │
│           └──────────────────┴────────────────┘          │
│                          │                               │
│                   ┌──────┴──────┐                        │
│                   │  Python GUI │                        │
│                   └─────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

## Components

### Server (`server/`)
- **tls_listener.py**: TCP TLS listener for signaling connections
- **room_manager.py**: Room creation, joining, and participant management
- **media_forwarder.py**: DTLS-SRTP media forwarding (stub implementation)
- **server.py**: Main server coordinating all components

### Client (`client/`)
- **signaling_client.py**: TLS signaling connection to server
- **av_capture.py**: Audio/video capture stubs
- **media_transport.py**: DTLS-SRTP media sender/receiver stubs
- **client_engine.py**: Main client engine

### GUI (`gui/`)
- **main_window.py**: tkinter-based GUI with controls for:
  - Server connection
  - Room browsing and creation
  - Joining/leaving rooms
  - Audio/video toggle

### Configuration (`config/`)
- **server.conf**: Server configuration template
- **client.conf**: Client configuration template

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

- Python 3.8+
- OpenSSL (for certificate generation)
- tkinter (for GUI)

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/pqc-chat.git
   cd pqc-chat
   ```

2. Generate TLS certificates:
   ```bash
   ./scripts/generate_certs.sh
   ```

3. Run the server:
   ```bash
   python3 run_server.py
   ```

4. Run the client (in another terminal):
   ```bash
   python3 -m gui.main_window
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
# Edit /etc/pqc-chat/client.conf with server address
python3 /opt/pqc-chat/gui/main_window.py
```

## Running Tests

```bash
python3 -m pytest tests/
# Or run individual test files:
python3 -m unittest tests/test_room_manager.py
python3 -m unittest tests/test_media_forwarder.py
python3 -m unittest tests/test_av_capture.py
python3 -m unittest tests/test_media_transport.py
```

## Configuration

### Server Configuration (`config/server.conf`)

```ini
[server]
signaling_host = 0.0.0.0
signaling_port = 8443
audio_port = 10000
video_port = 10001

[tls]
certfile = /etc/pqc-chat/server.crt
keyfile = /etc/pqc-chat/server.key
```

### Client Configuration (`config/client.conf`)

```ini
[server]
host = 192.168.1.100
signaling_port = 8443

[user]
username = MyRaspberryPi

[video]
width = 640
height = 480
fps = 30
```

## Protocol

### Signaling Messages

The client and server communicate via JSON messages over TLS:

| Message Type | Direction | Description |
|--------------|-----------|-------------|
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

- ✅ Server skeleton with TLS listener
- ✅ Basic room manager
- ✅ DTLS-SRTP media forwarder stubs
- ✅ Signaling client
- ✅ Audio/video capture stubs
- ✅ DTLS-SRTP media transport stubs
- ✅ Python tkinter GUI
- ✅ Configuration templates
- ✅ Systemd service files
- ✅ Installation scripts

## Future Enhancements

- [ ] Implement actual post-quantum key exchange (Kyber)
- [ ] Real DTLS-SRTP implementation
- [ ] Actual audio/video capture with PyAudio and OpenCV
- [ ] Audio/video encoding (Opus, VP8/VP9)
- [ ] ICE/STUN/TURN support for NAT traversal
- [ ] End-to-end encryption for media
- [ ] Screen sharing
- [ ] Text chat

## License

MIT License - see [LICENSE](LICENSE) for details.
