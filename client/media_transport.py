"""
DTLS-SRTP Media Sender/Receiver Stubs

Provides stub implementations for DTLS-SRTP media transport.
Handles secure transmission and reception of audio/video streams.
"""

import socket
import threading
import logging
from typing import Callable, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TransportState(Enum):
    """State of media transport."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MediaTransportConfig:
    """Configuration for media transport."""
    server_host: str
    audio_port: int = 10000
    video_port: int = 10001
    local_audio_port: int = 0  # 0 = auto-assign
    local_video_port: int = 0
    certfile: Optional[str] = None
    keyfile: Optional[str] = None


@dataclass
class MediaPacket:
    """Represents a media packet."""
    data: bytes
    timestamp: float
    sequence: int
    ssrc: int
    payload_type: int


class DTLSSRTPSender:
    """
    DTLS-SRTP Media Sender (Stub Implementation).
    
    Handles sending encrypted media packets to the server.
    In production, this would implement actual DTLS handshake
    and SRTP encryption.
    """
    
    def __init__(self, config: MediaTransportConfig):
        """
        Initialize the media sender.
        
        Args:
            config: Media transport configuration.
        """
        self.config = config
        self._state = TransportState.DISCONNECTED
        self._audio_socket: Optional[socket.socket] = None
        self._video_socket: Optional[socket.socket] = None
        self._audio_sequence = 0
        self._video_sequence = 0
        self._audio_ssrc = 0
        self._video_ssrc = 0
        
    def connect(self) -> bool:
        """
        Connect to the media server.
        
        Returns:
            True if successful, False otherwise.
        """
        if self._state == TransportState.CONNECTED:
            logger.warning("Media sender already connected")
            return True
            
        try:
            self._state = TransportState.CONNECTING
            
            # Create UDP sockets
            self._audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._audio_socket.bind(('0.0.0.0', self.config.local_audio_port))
            
            self._video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._video_socket.bind(('0.0.0.0', self.config.local_video_port))
            
            # Generate random SSRCs
            import random
            self._audio_ssrc = random.randint(1, 0xFFFFFFFF)
            self._video_ssrc = random.randint(1, 0xFFFFFFFF)
            
            # Stub: In production, perform DTLS handshake here
            logger.info("Media sender connected (stub - no DTLS)")
            
            self._state = TransportState.CONNECTED
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect media sender: {e}")
            self._state = TransportState.ERROR
            return False
            
    def disconnect(self):
        """Disconnect from the media server."""
        if self._audio_socket:
            try:
                self._audio_socket.close()
            except Exception:
                pass
            self._audio_socket = None
            
        if self._video_socket:
            try:
                self._video_socket.close()
            except Exception:
                pass
            self._video_socket = None
            
        self._state = TransportState.DISCONNECTED
        logger.info("Media sender disconnected")
        
    def send_audio(self, data: bytes, timestamp: float) -> bool:
        """
        Send audio data.
        
        Args:
            data: Audio frame data.
            timestamp: Frame timestamp.
            
        Returns:
            True if successful, False otherwise.
        """
        if self._state != TransportState.CONNECTED:
            return False
            
        try:
            # Stub: In production, encrypt with SRTP
            packet = self._create_rtp_packet(
                data, timestamp, self._audio_sequence, self._audio_ssrc, 
                payload_type=111  # Opus
            )
            self._audio_sequence = (self._audio_sequence + 1) % 65536
            
            self._audio_socket.sendto(
                packet,
                (self.config.server_host, self.config.audio_port)
            )
            return True
            
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
            return False
            
    def send_video(self, data: bytes, timestamp: float) -> bool:
        """
        Send video data.
        
        Args:
            data: Video frame data.
            timestamp: Frame timestamp.
            
        Returns:
            True if successful, False otherwise.
        """
        if self._state != TransportState.CONNECTED:
            return False
            
        try:
            # Stub: In production, encrypt with SRTP
            packet = self._create_rtp_packet(
                data, timestamp, self._video_sequence, self._video_ssrc,
                payload_type=96  # VP8
            )
            self._video_sequence = (self._video_sequence + 1) % 65536
            
            self._video_socket.sendto(
                packet,
                (self.config.server_host, self.config.video_port)
            )
            return True
            
        except Exception as e:
            logger.error(f"Error sending video: {e}")
            return False
            
    def _create_rtp_packet(self, data: bytes, timestamp: float, 
                           sequence: int, ssrc: int, 
                           payload_type: int) -> bytes:
        """
        Create an RTP packet (simplified stub).
        
        In production, this would be a proper RTP implementation.
        """
        # Simple RTP header (12 bytes)
        header = bytearray(12)
        header[0] = 0x80  # Version 2
        header[1] = payload_type
        header[2:4] = sequence.to_bytes(2, 'big')
        header[4:8] = int(timestamp * 1000).to_bytes(4, 'big')
        header[8:12] = ssrc.to_bytes(4, 'big')
        
        return bytes(header) + data
        
    @property
    def state(self) -> TransportState:
        """Get transport state."""
        return self._state
        
    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._state == TransportState.CONNECTED


class DTLSSRTPReceiver:
    """
    DTLS-SRTP Media Receiver (Stub Implementation).
    
    Handles receiving encrypted media packets from the server.
    In production, this would implement actual DTLS handshake
    and SRTP decryption.
    """
    
    def __init__(self, config: MediaTransportConfig):
        """
        Initialize the media receiver.
        
        Args:
            config: Media transport configuration.
        """
        self.config = config
        self._state = TransportState.DISCONNECTED
        self._audio_socket: Optional[socket.socket] = None
        self._video_socket: Optional[socket.socket] = None
        self._running = False
        self._audio_thread: Optional[threading.Thread] = None
        self._video_thread: Optional[threading.Thread] = None
        self._on_audio: Optional[Callable[[MediaPacket], None]] = None
        self._on_video: Optional[Callable[[MediaPacket], None]] = None
        
    def set_audio_callback(self, callback: Callable[[MediaPacket], None]):
        """
        Set callback for received audio packets.
        
        Args:
            callback: Function receiving MediaPacket objects.
        """
        self._on_audio = callback
        
    def set_video_callback(self, callback: Callable[[MediaPacket], None]):
        """
        Set callback for received video packets.
        
        Args:
            callback: Function receiving MediaPacket objects.
        """
        self._on_video = callback
        
    def start(self, audio_port: int, video_port: int) -> bool:
        """
        Start receiving media.
        
        Args:
            audio_port: Local port for audio.
            video_port: Local port for video.
            
        Returns:
            True if successful, False otherwise.
        """
        if self._state == TransportState.CONNECTED:
            logger.warning("Media receiver already running")
            return True
            
        try:
            self._state = TransportState.CONNECTING
            
            # Create UDP sockets
            self._audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._audio_socket.bind(('0.0.0.0', audio_port))
            self._audio_socket.settimeout(1.0)
            
            self._video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._video_socket.bind(('0.0.0.0', video_port))
            self._video_socket.settimeout(1.0)
            
            # Stub: In production, perform DTLS handshake here
            
            self._running = True
            
            # Start receive threads
            self._audio_thread = threading.Thread(
                target=self._receive_loop,
                args=(self._audio_socket, self._on_audio),
                daemon=True
            )
            self._audio_thread.start()
            
            self._video_thread = threading.Thread(
                target=self._receive_loop,
                args=(self._video_socket, self._on_video),
                daemon=True
            )
            self._video_thread.start()
            
            self._state = TransportState.CONNECTED
            logger.info(
                f"Media receiver started on ports {audio_port} (audio), "
                f"{video_port} (video)"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to start media receiver: {e}")
            self._state = TransportState.ERROR
            return False
            
    def stop(self):
        """Stop receiving media."""
        self._running = False
        
        if self._audio_socket:
            try:
                self._audio_socket.close()
            except Exception:
                pass
            self._audio_socket = None
            
        if self._video_socket:
            try:
                self._video_socket.close()
            except Exception:
                pass
            self._video_socket = None
            
        if self._audio_thread:
            self._audio_thread.join(timeout=2.0)
            self._audio_thread = None
            
        if self._video_thread:
            self._video_thread.join(timeout=2.0)
            self._video_thread = None
            
        self._state = TransportState.DISCONNECTED
        logger.info("Media receiver stopped")
        
    def _receive_loop(self, sock: socket.socket, 
                      callback: Optional[Callable[[MediaPacket], None]]):
        """
        Main receive loop.
        
        Args:
            sock: Socket to receive from.
            callback: Callback for received packets.
        """
        while self._running:
            try:
                data, addr = sock.recvfrom(65535)
                
                if data and callback:
                    # Stub: In production, decrypt with SRTP
                    packet = self._parse_rtp_packet(data)
                    if packet:
                        callback(packet)
                        
            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    logger.error("Socket error in receive loop")
                break
            except Exception as e:
                if self._running:
                    logger.error(f"Error receiving packet: {e}")
                    
    def _parse_rtp_packet(self, data: bytes) -> Optional[MediaPacket]:
        """
        Parse an RTP packet (simplified stub).
        
        In production, this would be a proper RTP implementation.
        """
        if len(data) < 12:
            return None
            
        # Parse simple RTP header
        payload_type = data[1] & 0x7F
        sequence = int.from_bytes(data[2:4], 'big')
        timestamp = int.from_bytes(data[4:8], 'big') / 1000.0
        ssrc = int.from_bytes(data[8:12], 'big')
        
        return MediaPacket(
            data=data[12:],
            timestamp=timestamp,
            sequence=sequence,
            ssrc=ssrc,
            payload_type=payload_type
        )
        
    @property
    def state(self) -> TransportState:
        """Get transport state."""
        return self._state
        
    @property
    def is_running(self) -> bool:
        """Check if running."""
        return self._state == TransportState.CONNECTED
