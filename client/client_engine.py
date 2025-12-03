"""
PQC Chat Client Engine

Main client engine that coordinates signaling, capture, and media transport.
"""

import logging
import threading
from typing import Callable, Optional, Dict, List
from dataclasses import dataclass

from .signaling_client import SignalingClient, SignalingConfig
from .av_capture import AudioCapture, VideoCapture, AudioConfig, VideoConfig
from .media_transport import (
    DTLSSRTPSender, DTLSSRTPReceiver, MediaTransportConfig
)

logger = logging.getLogger(__name__)


@dataclass
class ClientConfig:
    """Client configuration."""
    # Server settings
    server_host: str
    signaling_port: int = 8443
    audio_port: int = 10000
    video_port: int = 10001
    
    # Certificate settings
    ca_certfile: Optional[str] = None
    certfile: Optional[str] = None
    keyfile: Optional[str] = None
    
    # Capture settings
    audio_device: Optional[int] = None
    video_device: int = 0
    video_width: int = 640
    video_height: int = 480
    video_fps: int = 30


class PQCChatClient:
    """
    Main PQC Chat Client Engine.
    
    Coordinates signaling, media capture, and transport for
    a complete audio/video chat experience.
    """
    
    def __init__(self, config: ClientConfig):
        """
        Initialize the chat client.
        
        Args:
            config: Client configuration.
        """
        self.config = config
        
        # Initialize signaling client
        signaling_config = SignalingConfig(
            server_host=config.server_host,
            server_port=config.signaling_port,
            ca_certfile=config.ca_certfile,
            certfile=config.certfile,
            keyfile=config.keyfile
        )
        self._signaling = SignalingClient(signaling_config)
        
        # Initialize audio/video capture
        audio_config = AudioConfig(device_index=config.audio_device)
        self._audio_capture = AudioCapture(audio_config)
        
        video_config = VideoConfig(
            width=config.video_width,
            height=config.video_height,
            fps=config.video_fps,
            device_index=config.video_device
        )
        self._video_capture = VideoCapture(video_config)
        
        # Initialize media transport
        transport_config = MediaTransportConfig(
            server_host=config.server_host,
            audio_port=config.audio_port,
            video_port=config.video_port,
            certfile=config.certfile,
            keyfile=config.keyfile
        )
        self._media_sender = DTLSSRTPSender(transport_config)
        self._media_receiver = DTLSSRTPReceiver(transport_config)
        
        # State
        self._audio_enabled = True
        self._video_enabled = True
        self._in_call = False
        
        # Callbacks
        self._on_participant_joined: Optional[Callable[[str, str], None]] = None
        self._on_participant_left: Optional[Callable[[str], None]] = None
        self._on_disconnected: Optional[Callable[[], None]] = None
        self._on_room_list: Optional[Callable[[List[Dict]], None]] = None
        
        # Set up signaling handlers
        self._setup_handlers()
        
        # Set up capture callbacks
        self._audio_capture.set_frame_callback(self._on_audio_frame)
        self._video_capture.set_frame_callback(self._on_video_frame)
        
    def _setup_handlers(self):
        """Set up signaling message handlers."""
        self._signaling.register_handler(
            'participant_joined',
            self._handle_participant_joined
        )
        self._signaling.register_handler(
            'participant_left',
            self._handle_participant_left
        )
        self._signaling.register_handler(
            'disconnected',
            self._handle_disconnected
        )
        self._signaling.register_handler(
            'media_offer',
            self._handle_media_offer
        )
        self._signaling.register_handler(
            'media_answer',
            self._handle_media_answer
        )
        self._signaling.register_handler(
            'ice_candidate',
            self._handle_ice_candidate
        )
        
    def set_participant_joined_callback(self, callback: Callable[[str, str], None]):
        """Set callback for when a participant joins."""
        self._on_participant_joined = callback
        
    def set_participant_left_callback(self, callback: Callable[[str], None]):
        """Set callback for when a participant leaves."""
        self._on_participant_left = callback
        
    def set_disconnected_callback(self, callback: Callable[[], None]):
        """Set callback for when disconnected from server."""
        self._on_disconnected = callback
        
    def connect(self, username: str) -> bool:
        """
        Connect to the chat server and log in.
        
        Args:
            username: Display name for the user.
            
        Returns:
            True if successful, False otherwise.
        """
        if not self._signaling.connect():
            return False
            
        if not self._signaling.login(username):
            self._signaling.disconnect()
            return False
            
        logger.info(f"Connected as {username}")
        return True
        
    def disconnect(self):
        """Disconnect from the server."""
        self.leave_room()
        self._signaling.disconnect()
        logger.info("Disconnected")
        
    def list_rooms(self) -> List[Dict]:
        """
        Get list of available rooms.
        
        Returns:
            List of room dictionaries.
        """
        return self._signaling.list_rooms()
        
    def create_room(self, name: str, max_participants: int = 10) -> Optional[str]:
        """
        Create a new room.
        
        Args:
            name: Room display name.
            max_participants: Maximum participants allowed.
            
        Returns:
            Room ID if successful, None otherwise.
        """
        return self._signaling.create_room(name, max_participants)
        
    def join_room(self, room_id: str) -> bool:
        """
        Join a room and start media.
        
        Args:
            room_id: The room to join.
            
        Returns:
            True if successful, False otherwise.
        """
        if not self._signaling.join_room(room_id):
            return False
            
        # Connect media transport
        if not self._media_sender.connect():
            logger.warning("Failed to connect media sender")
            
        # Start media receiver
        # Stub: Use dynamic port assignment
        self._media_receiver.start(
            audio_port=20000,
            video_port=20001
        )
        
        # Start capture
        self._audio_capture.start()
        self._video_capture.start()
        
        self._in_call = True
        logger.info(f"Joined room: {self._signaling.current_room_name}")
        return True
        
    def leave_room(self):
        """Leave the current room and stop media."""
        if not self._in_call:
            return
            
        # Stop capture
        self._audio_capture.stop()
        self._video_capture.stop()
        
        # Stop media transport
        self._media_sender.disconnect()
        self._media_receiver.stop()
        
        # Leave room
        self._signaling.leave_room()
        
        self._in_call = False
        logger.info("Left room")
        
    def toggle_audio(self, enabled: bool):
        """
        Toggle audio transmission.
        
        Args:
            enabled: Whether audio should be enabled.
        """
        self._audio_enabled = enabled
        self._audio_capture.set_muted(not enabled)
        self._signaling.toggle_audio(enabled)
        logger.info(f"Audio {'enabled' if enabled else 'disabled'}")
        
    def toggle_video(self, enabled: bool):
        """
        Toggle video transmission.
        
        Args:
            enabled: Whether video should be enabled.
        """
        self._video_enabled = enabled
        self._video_capture.set_enabled(enabled)
        self._signaling.toggle_video(enabled)
        logger.info(f"Video {'enabled' if enabled else 'disabled'}")
        
    def _on_audio_frame(self, frame):
        """Handle captured audio frame."""
        if self._in_call and self._audio_enabled:
            self._media_sender.send_audio(frame.data, frame.timestamp)
            
    def _on_video_frame(self, frame):
        """Handle captured video frame."""
        if self._in_call and self._video_enabled:
            self._media_sender.send_video(frame.data, frame.timestamp)
            
    def _handle_participant_joined(self, message: dict):
        """Handle participant joined notification."""
        participant_id = message.get('participant_id')
        username = message.get('username')
        
        if self._on_participant_joined:
            self._on_participant_joined(participant_id, username)
            
        logger.info(f"Participant joined: {username}")
        
    def _handle_participant_left(self, message: dict):
        """Handle participant left notification."""
        participant_id = message.get('participant_id')
        
        if self._on_participant_left:
            self._on_participant_left(participant_id)
            
        logger.info(f"Participant left: {participant_id}")
        
    def _handle_disconnected(self, message: dict):
        """Handle disconnection."""
        self._in_call = False
        
        if self._on_disconnected:
            self._on_disconnected()
            
        logger.info("Disconnected from server")
        
    def _handle_media_offer(self, message: dict):
        """Handle incoming media offer."""
        # Stub: In production, handle WebRTC-style negotiation
        from_id = message.get('from_id')
        logger.info(f"Received media offer from {from_id}")
        
    def _handle_media_answer(self, message: dict):
        """Handle media answer."""
        # Stub: In production, handle WebRTC-style negotiation
        from_id = message.get('from_id')
        logger.info(f"Received media answer from {from_id}")
        
    def _handle_ice_candidate(self, message: dict):
        """Handle ICE candidate."""
        # Stub: In production, handle ICE candidate
        from_id = message.get('from_id')
        logger.debug(f"Received ICE candidate from {from_id}")
        
    @property
    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self._signaling.is_connected
        
    @property
    def is_in_room(self) -> bool:
        """Check if in a room."""
        return self._signaling.is_in_room
        
    @property
    def is_in_call(self) -> bool:
        """Check if in an active call."""
        return self._in_call
        
    @property
    def username(self) -> Optional[str]:
        """Get current username."""
        return self._signaling.username
        
    @property
    def current_room_name(self) -> Optional[str]:
        """Get current room name."""
        return self._signaling.current_room_name
        
    @property
    def audio_enabled(self) -> bool:
        """Check if audio is enabled."""
        return self._audio_enabled
        
    @property
    def video_enabled(self) -> bool:
        """Check if video is enabled."""
        return self._video_enabled
