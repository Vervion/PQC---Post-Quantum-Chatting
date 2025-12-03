"""
PQC Chat Server

Main server application that coordinates the TLS listener, room manager,
and media forwarder components.
"""

import json
import logging
import ssl
import threading
import uuid
from typing import Optional
from dataclasses import dataclass

from .tls_listener import TLSListener, TLSConfig
from .room_manager import RoomManager, Participant
from .media_forwarder import DTLSSRTPForwarder, DTLSConfig, MediaEndpoint

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Server configuration."""
    # TLS settings
    certfile: str
    keyfile: str
    ca_certfile: Optional[str] = None
    
    # Network settings
    signaling_host: str = "0.0.0.0"
    signaling_port: int = 8443
    media_host: str = "0.0.0.0"
    audio_port: int = 10000
    video_port: int = 10001


class PQCChatServer:
    """
    Main PQC Chat Server.
    
    Coordinates all server components and handles client signaling messages.
    """
    
    def __init__(self, config: ServerConfig):
        """
        Initialize the server.
        
        Args:
            config: Server configuration.
        """
        self.config = config
        
        # Initialize TLS listener
        tls_config = TLSConfig(
            certfile=config.certfile,
            keyfile=config.keyfile,
            ca_certfile=config.ca_certfile,
            host=config.signaling_host,
            port=config.signaling_port
        )
        self._tls_listener = TLSListener(tls_config)
        self._tls_listener.set_connection_handler(self._handle_connection)
        
        # Initialize room manager
        self._room_manager = RoomManager()
        
        # Initialize media forwarder
        dtls_config = DTLSConfig(
            certfile=config.certfile,
            keyfile=config.keyfile,
            host=config.media_host,
            audio_port=config.audio_port,
            video_port=config.video_port
        )
        self._media_forwarder = DTLSSRTPForwarder(dtls_config)
        
        self._running = False
        
    def start(self):
        """Start the server."""
        if self._running:
            logger.warning("Server already running")
            return
            
        logger.info("Starting PQC Chat Server...")
        
        self._running = True
        self._tls_listener.start()
        self._media_forwarder.start()
        
        logger.info("PQC Chat Server started successfully")
        
    def stop(self):
        """Stop the server."""
        logger.info("Stopping PQC Chat Server...")
        
        self._running = False
        self._tls_listener.stop()
        self._media_forwarder.stop()
        
        logger.info("PQC Chat Server stopped")
        
    def _handle_connection(self, ssl_socket: ssl.SSLSocket, address: tuple):
        """
        Handle a new client connection.
        
        Args:
            ssl_socket: The SSL socket for the client.
            address: The client's address.
        """
        participant_id = str(uuid.uuid4())
        participant: Optional[Participant] = None
        
        logger.info(f"New connection from {address}, assigned ID: {participant_id}")
        
        try:
            while self._running:
                # Receive message length (4 bytes)
                length_data = ssl_socket.recv(4)
                if not length_data:
                    break
                    
                msg_length = int.from_bytes(length_data, 'big')
                if msg_length > 1024 * 1024:  # 1MB max
                    logger.warning(f"Message too large from {address}")
                    break
                    
                # Receive message
                msg_data = b""
                while len(msg_data) < msg_length:
                    chunk = ssl_socket.recv(min(4096, msg_length - len(msg_data)))
                    if not chunk:
                        break
                    msg_data += chunk
                    
                if len(msg_data) < msg_length:
                    break
                    
                # Parse and handle message
                try:
                    message = json.loads(msg_data.decode('utf-8'))
                    response = self._handle_message(
                        message, ssl_socket, address, participant_id, participant
                    )
                    
                    # Update participant reference if login occurred
                    if message.get('type') == 'login' and response.get('success'):
                        room = self._room_manager.get_participant_room(participant_id)
                        if room:
                            participant = room.participants.get(participant_id)
                            
                    # Send response
                    self._send_message(ssl_socket, response)
                    
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from {address}")
                    self._send_message(ssl_socket, {"error": "Invalid JSON"})
                    
        except Exception as e:
            logger.error(f"Error handling client {address}: {e}")
        finally:
            # Clean up
            if participant:
                self._room_manager.leave_room(participant_id)
                
            try:
                ssl_socket.close()
            except Exception:
                pass
                
            logger.info(f"Connection closed: {address}")
            
    def _handle_message(self, message: dict, ssl_socket: ssl.SSLSocket,
                        address: tuple, participant_id: str,
                        participant: Optional[Participant]) -> dict:
        """
        Handle a signaling message from a client.
        
        Args:
            message: The parsed message.
            ssl_socket: The client's socket.
            address: The client's address.
            participant_id: The participant's ID.
            participant: The Participant object if logged in.
            
        Returns:
            Response message to send back.
        """
        msg_type = message.get('type')
        
        if msg_type == 'login':
            return self._handle_login(message, ssl_socket, address, participant_id)
        elif msg_type == 'list_rooms':
            return self._handle_list_rooms()
        elif msg_type == 'create_room':
            return self._handle_create_room(message)
        elif msg_type == 'join_room':
            return self._handle_join_room(message, ssl_socket, address, participant_id)
        elif msg_type == 'leave_room':
            return self._handle_leave_room(participant_id)
        elif msg_type == 'media_offer':
            return self._handle_media_offer(message, participant_id)
        elif msg_type == 'media_answer':
            return self._handle_media_answer(message, participant_id)
        elif msg_type == 'ice_candidate':
            return self._handle_ice_candidate(message, participant_id)
        elif msg_type == 'toggle_audio':
            return self._handle_toggle_audio(message, participant_id)
        elif msg_type == 'toggle_video':
            return self._handle_toggle_video(message, participant_id)
        else:
            return {"error": f"Unknown message type: {msg_type}"}
            
    def _handle_login(self, message: dict, ssl_socket: ssl.SSLSocket,
                      address: tuple, participant_id: str) -> dict:
        """Handle login message."""
        username = message.get('username')
        if not username:
            return {"error": "Username required", "success": False}
            
        # Create participant (not yet in a room)
        logger.info(f"User {username} logged in with ID {participant_id}")
        
        return {
            "type": "login_response",
            "success": True,
            "participant_id": participant_id,
            "username": username
        }
        
    def _handle_list_rooms(self) -> dict:
        """Handle list rooms request."""
        rooms = self._room_manager.list_rooms()
        return {
            "type": "room_list",
            "rooms": rooms
        }
        
    def _handle_create_room(self, message: dict) -> dict:
        """Handle create room request."""
        room_name = message.get('name')
        max_participants = message.get('max_participants', 10)
        
        if not room_name:
            return {"error": "Room name required", "success": False}
            
        room = self._room_manager.create_room(room_name, max_participants)
        
        # Create media session for the room
        self._media_forwarder.create_session(room.id, room.id)
        
        return {
            "type": "room_created",
            "success": True,
            "room_id": room.id,
            "room_name": room.name
        }
        
    def _handle_join_room(self, message: dict, ssl_socket: ssl.SSLSocket,
                          address: tuple, participant_id: str) -> dict:
        """Handle join room request."""
        room_id = message.get('room_id')
        username = message.get('username', f"User-{participant_id[:8]}")
        
        if not room_id:
            return {"error": "Room ID required", "success": False}
            
        participant = Participant(
            id=participant_id,
            username=username,
            socket=ssl_socket,
            address=address
        )
        
        if self._room_manager.join_room(room_id, participant):
            room = self._room_manager.get_room(room_id)
            participants = [
                {"id": p.id, "username": p.username}
                for p in room.participants.values()
            ]
            
            # Notify other participants
            self._broadcast_to_room(room_id, {
                "type": "participant_joined",
                "participant_id": participant_id,
                "username": username
            }, exclude_id=participant_id)
            
            return {
                "type": "room_joined",
                "success": True,
                "room_id": room_id,
                "room_name": room.name,
                "participants": participants
            }
        else:
            return {"error": "Failed to join room", "success": False}
            
    def _handle_leave_room(self, participant_id: str) -> dict:
        """Handle leave room request."""
        room = self._room_manager.get_participant_room(participant_id)
        
        if room:
            room_id = room.id
            self._room_manager.leave_room(participant_id)
            
            # Notify other participants
            self._broadcast_to_room(room_id, {
                "type": "participant_left",
                "participant_id": participant_id
            })
            
            return {"type": "room_left", "success": True}
        else:
            return {"error": "Not in a room", "success": False}
            
    def _handle_media_offer(self, message: dict, participant_id: str) -> dict:
        """Handle WebRTC-style media offer."""
        target_id = message.get('target_id')
        sdp = message.get('sdp')
        
        if not target_id or not sdp:
            return {"error": "target_id and sdp required", "success": False}
            
        room = self._room_manager.get_participant_room(participant_id)
        if not room:
            return {"error": "Not in a room", "success": False}
            
        target = room.participants.get(target_id)
        if not target:
            return {"error": "Target not found", "success": False}
            
        # Forward offer to target
        self._send_message(target.socket, {
            "type": "media_offer",
            "from_id": participant_id,
            "sdp": sdp
        })
        
        return {"type": "offer_sent", "success": True}
        
    def _handle_media_answer(self, message: dict, participant_id: str) -> dict:
        """Handle WebRTC-style media answer."""
        target_id = message.get('target_id')
        sdp = message.get('sdp')
        
        if not target_id or not sdp:
            return {"error": "target_id and sdp required", "success": False}
            
        room = self._room_manager.get_participant_room(participant_id)
        if not room:
            return {"error": "Not in a room", "success": False}
            
        target = room.participants.get(target_id)
        if not target:
            return {"error": "Target not found", "success": False}
            
        # Forward answer to target
        self._send_message(target.socket, {
            "type": "media_answer",
            "from_id": participant_id,
            "sdp": sdp
        })
        
        return {"type": "answer_sent", "success": True}
        
    def _handle_ice_candidate(self, message: dict, participant_id: str) -> dict:
        """Handle ICE candidate exchange."""
        target_id = message.get('target_id')
        candidate = message.get('candidate')
        
        if not target_id or not candidate:
            return {"error": "target_id and candidate required", "success": False}
            
        room = self._room_manager.get_participant_room(participant_id)
        if not room:
            return {"error": "Not in a room", "success": False}
            
        target = room.participants.get(target_id)
        if not target:
            return {"error": "Target not found", "success": False}
            
        # Forward candidate to target
        self._send_message(target.socket, {
            "type": "ice_candidate",
            "from_id": participant_id,
            "candidate": candidate
        })
        
        return {"type": "candidate_sent", "success": True}
        
    def _handle_toggle_audio(self, message: dict, participant_id: str) -> dict:
        """Handle audio toggle."""
        enabled = message.get('enabled', True)
        
        room = self._room_manager.get_participant_room(participant_id)
        if not room:
            return {"error": "Not in a room", "success": False}
            
        participant = room.participants.get(participant_id)
        if participant:
            participant.audio_enabled = enabled
            
            # Notify others
            self._broadcast_to_room(room.id, {
                "type": "audio_toggled",
                "participant_id": participant_id,
                "enabled": enabled
            }, exclude_id=participant_id)
            
        return {"type": "audio_toggled", "success": True, "enabled": enabled}
        
    def _handle_toggle_video(self, message: dict, participant_id: str) -> dict:
        """Handle video toggle."""
        enabled = message.get('enabled', True)
        
        room = self._room_manager.get_participant_room(participant_id)
        if not room:
            return {"error": "Not in a room", "success": False}
            
        participant = room.participants.get(participant_id)
        if participant:
            participant.video_enabled = enabled
            
            # Notify others
            self._broadcast_to_room(room.id, {
                "type": "video_toggled",
                "participant_id": participant_id,
                "enabled": enabled
            }, exclude_id=participant_id)
            
        return {"type": "video_toggled", "success": True, "enabled": enabled}
        
    def _send_message(self, ssl_socket: ssl.SSLSocket, message: dict):
        """Send a JSON message to a client."""
        try:
            data = json.dumps(message).encode('utf-8')
            length = len(data).to_bytes(4, 'big')
            ssl_socket.sendall(length + data)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            
    def _broadcast_to_room(self, room_id: str, message: dict,
                           exclude_id: Optional[str] = None):
        """Broadcast a message to all participants in a room."""
        data = json.dumps(message).encode('utf-8')
        length = len(data).to_bytes(4, 'big')
        self._room_manager.broadcast_to_room(room_id, length + data, exclude_id)
        
    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._running
        
    @property
    def room_manager(self) -> RoomManager:
        """Get the room manager."""
        return self._room_manager
        
    @property
    def media_forwarder(self) -> DTLSSRTPForwarder:
        """Get the media forwarder."""
        return self._media_forwarder
