"""
Basic Room Manager

Manages chat rooms for the PQC chat system.
Handles room creation, joining, leaving, and participant management.
"""

import threading
import logging
import uuid
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Participant:
    """Represents a participant in a room."""
    id: str
    username: str
    socket: object  # ssl.SSLSocket
    address: tuple
    joined_at: datetime = field(default_factory=datetime.now)
    audio_enabled: bool = True
    video_enabled: bool = True


@dataclass
class Room:
    """Represents a chat room."""
    id: str
    name: str
    created_at: datetime = field(default_factory=datetime.now)
    participants: Dict[str, Participant] = field(default_factory=dict)
    max_participants: int = 10
    is_locked: bool = False
    
    def add_participant(self, participant: Participant) -> bool:
        """
        Add a participant to the room.
        
        Args:
            participant: The participant to add.
            
        Returns:
            True if successful, False if room is full or locked.
        """
        if self.is_locked:
            logger.warning(f"Cannot join locked room {self.id}")
            return False
            
        if len(self.participants) >= self.max_participants:
            logger.warning(f"Room {self.id} is full")
            return False
            
        self.participants[participant.id] = participant
        logger.info(f"Participant {participant.username} joined room {self.name}")
        return True
        
    def remove_participant(self, participant_id: str) -> bool:
        """
        Remove a participant from the room.
        
        Args:
            participant_id: ID of the participant to remove.
            
        Returns:
            True if successful, False if participant not found.
        """
        if participant_id in self.participants:
            participant = self.participants.pop(participant_id)
            logger.info(f"Participant {participant.username} left room {self.name}")
            return True
        return False
        
    def get_participant_ids(self) -> List[str]:
        """Get list of participant IDs in the room."""
        return list(self.participants.keys())
        
    def get_participant_count(self) -> int:
        """Get the number of participants in the room."""
        return len(self.participants)


class RoomManager:
    """
    Manages all chat rooms in the system.
    
    Provides thread-safe operations for creating, joining, and leaving rooms.
    """
    
    def __init__(self):
        """Initialize the room manager."""
        self._rooms: Dict[str, Room] = {}
        self._participant_rooms: Dict[str, str] = {}  # participant_id -> room_id
        self._lock = threading.RLock()
        
    def create_room(self, name: str, max_participants: int = 10) -> Room:
        """
        Create a new room.
        
        Args:
            name: Display name for the room.
            max_participants: Maximum number of participants allowed.
            
        Returns:
            The newly created Room object.
        """
        with self._lock:
            room_id = str(uuid.uuid4())
            room = Room(
                id=room_id,
                name=name,
                max_participants=max_participants
            )
            self._rooms[room_id] = room
            logger.info(f"Created room: {name} ({room_id})")
            return room
            
    def get_room(self, room_id: str) -> Optional[Room]:
        """
        Get a room by ID.
        
        Args:
            room_id: The room's unique identifier.
            
        Returns:
            The Room object or None if not found.
        """
        with self._lock:
            return self._rooms.get(room_id)
            
    def get_room_by_name(self, name: str) -> Optional[Room]:
        """
        Get a room by name.
        
        Args:
            name: The room's display name.
            
        Returns:
            The Room object or None if not found.
        """
        with self._lock:
            for room in self._rooms.values():
                if room.name == name:
                    return room
            return None
            
    def list_rooms(self) -> List[Dict]:
        """
        List all available rooms.
        
        Returns:
            List of room information dictionaries.
        """
        with self._lock:
            return [
                {
                    "id": room.id,
                    "name": room.name,
                    "participants": room.get_participant_count(),
                    "max_participants": room.max_participants,
                    "is_locked": room.is_locked
                }
                for room in self._rooms.values()
            ]
            
    def join_room(self, room_id: str, participant: Participant) -> bool:
        """
        Add a participant to a room.
        
        Args:
            room_id: The room to join.
            participant: The participant joining.
            
        Returns:
            True if successful, False otherwise.
        """
        with self._lock:
            room = self._rooms.get(room_id)
            if not room:
                logger.warning(f"Room {room_id} not found")
                return False
                
            # Leave current room if in one
            if participant.id in self._participant_rooms:
                self.leave_room(participant.id)
                
            if room.add_participant(participant):
                self._participant_rooms[participant.id] = room_id
                return True
            return False
            
    def leave_room(self, participant_id: str) -> bool:
        """
        Remove a participant from their current room.
        
        Args:
            participant_id: ID of the participant leaving.
            
        Returns:
            True if successful, False if not in a room.
        """
        with self._lock:
            room_id = self._participant_rooms.get(participant_id)
            if not room_id:
                return False
                
            room = self._rooms.get(room_id)
            if room:
                room.remove_participant(participant_id)
                
            del self._participant_rooms[participant_id]
            return True
            
    def delete_room(self, room_id: str) -> bool:
        """
        Delete a room.
        
        Args:
            room_id: The room to delete.
            
        Returns:
            True if successful, False if not found.
        """
        with self._lock:
            room = self._rooms.get(room_id)
            if not room:
                return False
                
            # Remove all participants from room mapping
            for participant_id in room.get_participant_ids():
                if participant_id in self._participant_rooms:
                    del self._participant_rooms[participant_id]
                    
            del self._rooms[room_id]
            logger.info(f"Deleted room: {room.name} ({room_id})")
            return True
            
    def get_participant_room(self, participant_id: str) -> Optional[Room]:
        """
        Get the room a participant is currently in.
        
        Args:
            participant_id: The participant's ID.
            
        Returns:
            The Room object or None if not in a room.
        """
        with self._lock:
            room_id = self._participant_rooms.get(participant_id)
            if room_id:
                return self._rooms.get(room_id)
            return None
            
    def broadcast_to_room(self, room_id: str, message: bytes, 
                          exclude_id: Optional[str] = None):
        """
        Broadcast a message to all participants in a room.
        
        Args:
            room_id: The room to broadcast to.
            message: The message bytes to send.
            exclude_id: Optional participant ID to exclude from broadcast.
        """
        with self._lock:
            room = self._rooms.get(room_id)
            if not room:
                return
                
            for participant_id, participant in room.participants.items():
                if participant_id == exclude_id:
                    continue
                    
                try:
                    participant.socket.sendall(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {participant.username}: {e}")
