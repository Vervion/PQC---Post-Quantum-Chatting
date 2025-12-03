"""
Signaling Client

Provides the signaling client for connecting to the PQC chat server.
Handles TLS connections and signaling message exchange.
"""

import json
import socket
import ssl
import threading
import logging
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from queue import Queue

logger = logging.getLogger(__name__)


@dataclass
class SignalingConfig:
    """Configuration for the signaling client."""
    server_host: str
    server_port: int = 8443
    ca_certfile: Optional[str] = None
    certfile: Optional[str] = None
    keyfile: Optional[str] = None


class SignalingClient:
    """
    Signaling client for PQC chat.
    
    Handles TLS connection to the server and message exchange for
    room management and media negotiation.
    """
    
    def __init__(self, config: SignalingConfig):
        """
        Initialize the signaling client.
        
        Args:
            config: Signaling configuration.
        """
        self.config = config
        self._socket: Optional[socket.socket] = None
        self._ssl_socket: Optional[ssl.SSLSocket] = None
        self._running = False
        self._receive_thread: Optional[threading.Thread] = None
        self._message_handlers: Dict[str, Callable[[dict], None]] = {}
        self._pending_responses: Queue = Queue()
        self._connected = False
        
        # Client state
        self.participant_id: Optional[str] = None
        self.username: Optional[str] = None
        self.current_room_id: Optional[str] = None
        self.current_room_name: Optional[str] = None
        
    def setup_ssl_context(self) -> ssl.SSLContext:
        """
        Create and configure the SSL context.
        
        Returns:
            Configured SSL context for client-side TLS.
        """
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        
        if self.config.ca_certfile:
            context.load_verify_locations(self.config.ca_certfile)
            context.verify_mode = ssl.CERT_REQUIRED
        else:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
        if self.config.certfile and self.config.keyfile:
            context.load_cert_chain(
                certfile=self.config.certfile,
                keyfile=self.config.keyfile
            )
            
        return context
        
    def register_handler(self, message_type: str, 
                         handler: Callable[[dict], None]):
        """
        Register a handler for a message type.
        
        Args:
            message_type: The message type to handle.
            handler: Callback function receiving the message dict.
        """
        self._message_handlers[message_type] = handler
        
    def connect(self) -> bool:
        """
        Connect to the signaling server.
        
        Returns:
            True if connection successful, False otherwise.
        """
        if self._connected:
            logger.warning("Already connected")
            return True
            
        try:
            ssl_context = self.setup_ssl_context()
            
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._ssl_socket = ssl_context.wrap_socket(
                self._socket,
                server_hostname=self.config.server_host
            )
            
            self._ssl_socket.connect((self.config.server_host, self.config.server_port))
            
            self._running = True
            self._connected = True
            
            # Start receive thread
            self._receive_thread = threading.Thread(
                target=self._receive_loop,
                daemon=True
            )
            self._receive_thread.start()
            
            logger.info(f"Connected to server at {self.config.server_host}:{self.config.server_port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self._cleanup()
            return False
            
    def disconnect(self):
        """Disconnect from the signaling server."""
        self._running = False
        self._connected = False
        
        if self._ssl_socket:
            try:
                self._ssl_socket.close()
            except Exception:
                pass
            self._ssl_socket = None
            
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
            
        if self._receive_thread:
            self._receive_thread.join(timeout=5.0)
            self._receive_thread = None
            
        self.participant_id = None
        self.current_room_id = None
        self.current_room_name = None
        
        logger.info("Disconnected from server")
        
    def _cleanup(self):
        """Clean up resources."""
        self._running = False
        self._connected = False
        
        if self._ssl_socket:
            try:
                self._ssl_socket.close()
            except Exception:
                pass
            self._ssl_socket = None
            
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
            
    def _receive_loop(self):
        """Main loop for receiving messages."""
        while self._running:
            try:
                # Receive message length
                length_data = self._ssl_socket.recv(4)
                if not length_data:
                    logger.info("Server closed connection")
                    break
                    
                msg_length = int.from_bytes(length_data, 'big')
                if msg_length > 1024 * 1024:
                    logger.error("Message too large")
                    break
                    
                # Receive message
                msg_data = b""
                while len(msg_data) < msg_length:
                    chunk = self._ssl_socket.recv(min(4096, msg_length - len(msg_data)))
                    if not chunk:
                        break
                    msg_data += chunk
                    
                if len(msg_data) < msg_length:
                    break
                    
                # Parse message
                message = json.loads(msg_data.decode('utf-8'))
                self._handle_message(message)
                
            except ssl.SSLError as e:
                if self._running:
                    logger.error(f"SSL error: {e}")
                break
            except Exception as e:
                if self._running:
                    logger.error(f"Error receiving message: {e}")
                break
                
        self._connected = False
        logger.info("Receive loop ended")
        
        # Notify disconnect handler if registered
        if 'disconnected' in self._message_handlers:
            self._message_handlers['disconnected']({})
            
    def _handle_message(self, message: dict):
        """
        Handle a received message.
        
        Args:
            message: The parsed message.
        """
        msg_type = message.get('type', '')
        
        # Put response in queue for synchronous calls
        self._pending_responses.put(message)
        
        # Call registered handler if any
        if msg_type in self._message_handlers:
            try:
                self._message_handlers[msg_type](message)
            except Exception as e:
                logger.error(f"Error in message handler for {msg_type}: {e}")
                
    def _send_message(self, message: dict) -> bool:
        """
        Send a message to the server.
        
        Args:
            message: The message to send.
            
        Returns:
            True if successful, False otherwise.
        """
        if not self._connected:
            logger.error("Not connected")
            return False
            
        try:
            data = json.dumps(message).encode('utf-8')
            length = len(data).to_bytes(4, 'big')
            self._ssl_socket.sendall(length + data)
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
            
    def _send_and_wait(self, message: dict, timeout: float = 10.0) -> Optional[dict]:
        """
        Send a message and wait for response.
        
        Args:
            message: The message to send.
            timeout: Timeout in seconds.
            
        Returns:
            Response message or None on timeout/error.
        """
        # Clear pending responses
        while not self._pending_responses.empty():
            try:
                self._pending_responses.get_nowait()
            except Exception:
                break
                
        if not self._send_message(message):
            return None
            
        try:
            return self._pending_responses.get(timeout=timeout)
        except Exception:
            return None
            
    def login(self, username: str) -> bool:
        """
        Log in to the server.
        
        Args:
            username: Display name for the user.
            
        Returns:
            True if login successful, False otherwise.
        """
        response = self._send_and_wait({
            "type": "login",
            "username": username
        })
        
        if response and response.get('success'):
            self.participant_id = response.get('participant_id')
            self.username = username
            logger.info(f"Logged in as {username}")
            return True
            
        return False
        
    def list_rooms(self) -> list:
        """
        Get list of available rooms.
        
        Returns:
            List of room dictionaries.
        """
        response = self._send_and_wait({"type": "list_rooms"})
        
        if response and response.get('type') == 'room_list':
            return response.get('rooms', [])
            
        return []
        
    def create_room(self, name: str, max_participants: int = 10) -> Optional[str]:
        """
        Create a new room.
        
        Args:
            name: Display name for the room.
            max_participants: Maximum number of participants.
            
        Returns:
            Room ID if successful, None otherwise.
        """
        response = self._send_and_wait({
            "type": "create_room",
            "name": name,
            "max_participants": max_participants
        })
        
        if response and response.get('success'):
            room_id = response.get('room_id')
            logger.info(f"Created room: {name} ({room_id})")
            return room_id
            
        return None
        
    def join_room(self, room_id: str) -> bool:
        """
        Join a room.
        
        Args:
            room_id: The room to join.
            
        Returns:
            True if successful, False otherwise.
        """
        response = self._send_and_wait({
            "type": "join_room",
            "room_id": room_id,
            "username": self.username
        })
        
        if response and response.get('success'):
            self.current_room_id = room_id
            self.current_room_name = response.get('room_name')
            logger.info(f"Joined room: {self.current_room_name}")
            return True
            
        return False
        
    def leave_room(self) -> bool:
        """
        Leave the current room.
        
        Returns:
            True if successful, False otherwise.
        """
        if not self.current_room_id:
            return False
            
        response = self._send_and_wait({"type": "leave_room"})
        
        if response and response.get('success'):
            self.current_room_id = None
            self.current_room_name = None
            logger.info("Left room")
            return True
            
        return False
        
    def send_media_offer(self, target_id: str, sdp: str) -> bool:
        """
        Send a media offer to a participant.
        
        Args:
            target_id: Target participant ID.
            sdp: SDP offer.
            
        Returns:
            True if successful, False otherwise.
        """
        response = self._send_and_wait({
            "type": "media_offer",
            "target_id": target_id,
            "sdp": sdp
        })
        
        return response and response.get('success', False)
        
    def send_media_answer(self, target_id: str, sdp: str) -> bool:
        """
        Send a media answer to a participant.
        
        Args:
            target_id: Target participant ID.
            sdp: SDP answer.
            
        Returns:
            True if successful, False otherwise.
        """
        response = self._send_and_wait({
            "type": "media_answer",
            "target_id": target_id,
            "sdp": sdp
        })
        
        return response and response.get('success', False)
        
    def send_ice_candidate(self, target_id: str, candidate: str) -> bool:
        """
        Send an ICE candidate to a participant.
        
        Args:
            target_id: Target participant ID.
            candidate: ICE candidate.
            
        Returns:
            True if successful, False otherwise.
        """
        response = self._send_and_wait({
            "type": "ice_candidate",
            "target_id": target_id,
            "candidate": candidate
        })
        
        return response and response.get('success', False)
        
    def toggle_audio(self, enabled: bool) -> bool:
        """
        Toggle audio state.
        
        Args:
            enabled: Whether audio should be enabled.
            
        Returns:
            True if successful, False otherwise.
        """
        response = self._send_and_wait({
            "type": "toggle_audio",
            "enabled": enabled
        })
        
        return response and response.get('success', False)
        
    def toggle_video(self, enabled: bool) -> bool:
        """
        Toggle video state.
        
        Args:
            enabled: Whether video should be enabled.
            
        Returns:
            True if successful, False otherwise.
        """
        response = self._send_and_wait({
            "type": "toggle_video",
            "enabled": enabled
        })
        
        return response and response.get('success', False)
        
    @property
    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self._connected
        
    @property
    def is_in_room(self) -> bool:
        """Check if currently in a room."""
        return self.current_room_id is not None
