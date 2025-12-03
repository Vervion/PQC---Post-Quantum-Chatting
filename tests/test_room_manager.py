"""
Tests for Room Manager
"""

import unittest
import threading
from server.room_manager import RoomManager, Room, Participant


class MockSocket:
    """Mock socket for testing."""
    def __init__(self):
        self.data_sent = []
        
    def sendall(self, data):
        self.data_sent.append(data)


class TestRoom(unittest.TestCase):
    """Tests for the Room class."""
    
    def test_create_room(self):
        """Test room creation."""
        room = Room(id="test-123", name="Test Room")
        self.assertEqual(room.id, "test-123")
        self.assertEqual(room.name, "Test Room")
        self.assertEqual(room.max_participants, 10)
        self.assertFalse(room.is_locked)
        
    def test_add_participant(self):
        """Test adding a participant to a room."""
        room = Room(id="test-123", name="Test Room")
        participant = Participant(
            id="p1",
            username="User1",
            socket=MockSocket(),
            address=("127.0.0.1", 12345)
        )
        
        result = room.add_participant(participant)
        self.assertTrue(result)
        self.assertEqual(room.get_participant_count(), 1)
        self.assertIn("p1", room.get_participant_ids())
        
    def test_room_capacity(self):
        """Test room capacity limit."""
        room = Room(id="test-123", name="Test Room", max_participants=2)
        
        p1 = Participant(id="p1", username="User1", socket=MockSocket(), address=("127.0.0.1", 1))
        p2 = Participant(id="p2", username="User2", socket=MockSocket(), address=("127.0.0.1", 2))
        p3 = Participant(id="p3", username="User3", socket=MockSocket(), address=("127.0.0.1", 3))
        
        self.assertTrue(room.add_participant(p1))
        self.assertTrue(room.add_participant(p2))
        self.assertFalse(room.add_participant(p3))  # Should fail - room full
        
    def test_locked_room(self):
        """Test that locked rooms reject new participants."""
        room = Room(id="test-123", name="Test Room", is_locked=True)
        participant = Participant(
            id="p1",
            username="User1",
            socket=MockSocket(),
            address=("127.0.0.1", 12345)
        )
        
        result = room.add_participant(participant)
        self.assertFalse(result)
        
    def test_remove_participant(self):
        """Test removing a participant from a room."""
        room = Room(id="test-123", name="Test Room")
        participant = Participant(
            id="p1",
            username="User1",
            socket=MockSocket(),
            address=("127.0.0.1", 12345)
        )
        
        room.add_participant(participant)
        self.assertEqual(room.get_participant_count(), 1)
        
        result = room.remove_participant("p1")
        self.assertTrue(result)
        self.assertEqual(room.get_participant_count(), 0)
        
        # Try removing non-existent participant
        result = room.remove_participant("p1")
        self.assertFalse(result)


class TestRoomManager(unittest.TestCase):
    """Tests for the RoomManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = RoomManager()
        
    def test_create_room(self):
        """Test room creation through manager."""
        room = self.manager.create_room("Test Room")
        self.assertIsNotNone(room)
        self.assertEqual(room.name, "Test Room")
        
    def test_get_room(self):
        """Test getting a room by ID."""
        room = self.manager.create_room("Test Room")
        retrieved = self.manager.get_room(room.id)
        self.assertEqual(retrieved.id, room.id)
        
    def test_get_room_by_name(self):
        """Test getting a room by name."""
        room = self.manager.create_room("Test Room")
        retrieved = self.manager.get_room_by_name("Test Room")
        self.assertEqual(retrieved.id, room.id)
        
    def test_list_rooms(self):
        """Test listing all rooms."""
        self.manager.create_room("Room 1")
        self.manager.create_room("Room 2")
        
        rooms = self.manager.list_rooms()
        self.assertEqual(len(rooms), 2)
        
    def test_join_and_leave_room(self):
        """Test joining and leaving a room."""
        room = self.manager.create_room("Test Room")
        participant = Participant(
            id="p1",
            username="User1",
            socket=MockSocket(),
            address=("127.0.0.1", 12345)
        )
        
        # Join room
        result = self.manager.join_room(room.id, participant)
        self.assertTrue(result)
        
        # Check participant is in room
        participant_room = self.manager.get_participant_room("p1")
        self.assertEqual(participant_room.id, room.id)
        
        # Leave room
        result = self.manager.leave_room("p1")
        self.assertTrue(result)
        
        # Check participant is no longer in room
        participant_room = self.manager.get_participant_room("p1")
        self.assertIsNone(participant_room)
        
    def test_delete_room(self):
        """Test deleting a room."""
        room = self.manager.create_room("Test Room")
        room_id = room.id
        
        result = self.manager.delete_room(room_id)
        self.assertTrue(result)
        
        retrieved = self.manager.get_room(room_id)
        self.assertIsNone(retrieved)
        
    def test_thread_safety(self):
        """Test thread safety of room operations."""
        room = self.manager.create_room("Test Room", max_participants=100)
        
        results = []
        
        def join_room(participant_id):
            participant = Participant(
                id=participant_id,
                username=f"User-{participant_id}",
                socket=MockSocket(),
                address=("127.0.0.1", 12345)
            )
            result = self.manager.join_room(room.id, participant)
            results.append(result)
            
        # Create multiple threads trying to join
        threads = []
        for i in range(50):
            t = threading.Thread(target=join_room, args=(f"p{i}",))
            threads.append(t)
            
        for t in threads:
            t.start()
            
        for t in threads:
            t.join()
            
        # All should have succeeded
        self.assertEqual(sum(results), 50)
        self.assertEqual(room.get_participant_count(), 50)


if __name__ == '__main__':
    unittest.main()
