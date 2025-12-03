"""
Tests for Media Forwarder
"""

import unittest
from server.media_forwarder import (
    DTLSSRTPForwarder, DTLSConfig, MediaSession, MediaEndpoint, MediaType
)


class TestMediaSession(unittest.TestCase):
    """Tests for the MediaSession class."""
    
    def test_create_session(self):
        """Test creating a media session."""
        session = MediaSession(
            session_id="session-123",
            room_id="room-456"
        )
        self.assertEqual(session.session_id, "session-123")
        self.assertEqual(session.room_id, "room-456")
        self.assertTrue(session.is_active)
        self.assertEqual(len(session.endpoints), 0)
        
    def test_add_endpoint(self):
        """Test adding an endpoint to a session."""
        session = MediaSession(session_id="s1", room_id="r1")
        endpoint = MediaEndpoint(
            participant_id="p1",
            address=("127.0.0.1", 12345),
            audio_port=10000,
            video_port=10001
        )
        
        session.endpoints[endpoint.participant_id] = endpoint
        self.assertEqual(len(session.endpoints), 1)
        self.assertIn("p1", session.endpoints)


class TestDTLSSRTPForwarder(unittest.TestCase):
    """Tests for the DTLSSRTPForwarder class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = DTLSConfig(
            certfile="test.crt",
            keyfile="test.key",
            host="127.0.0.1",
            audio_port=20000,
            video_port=20001
        )
        self.forwarder = DTLSSRTPForwarder(self.config)
        
    def test_create_session(self):
        """Test creating a media session."""
        session = self.forwarder.create_session("session-1", "room-1")
        self.assertIsNotNone(session)
        self.assertEqual(session.session_id, "session-1")
        
        # Verify session is retrievable
        retrieved = self.forwarder.get_session("session-1")
        self.assertEqual(retrieved.session_id, session.session_id)
        
    def test_destroy_session(self):
        """Test destroying a media session."""
        self.forwarder.create_session("session-1", "room-1")
        
        result = self.forwarder.destroy_session("session-1")
        self.assertTrue(result)
        
        # Verify session is gone
        retrieved = self.forwarder.get_session("session-1")
        self.assertIsNone(retrieved)
        
    def test_add_endpoint(self):
        """Test adding an endpoint to a session."""
        self.forwarder.create_session("session-1", "room-1")
        
        endpoint = MediaEndpoint(
            participant_id="p1",
            address=("127.0.0.1", 12345),
            audio_port=10000,
            video_port=10001
        )
        
        result = self.forwarder.add_endpoint("session-1", endpoint)
        self.assertTrue(result)
        
    def test_remove_endpoint(self):
        """Test removing an endpoint from a session."""
        self.forwarder.create_session("session-1", "room-1")
        
        endpoint = MediaEndpoint(
            participant_id="p1",
            address=("127.0.0.1", 12345),
            audio_port=10000,
            video_port=10001
        )
        self.forwarder.add_endpoint("session-1", endpoint)
        
        result = self.forwarder.remove_endpoint("session-1", "p1")
        self.assertTrue(result)
        
    def test_list_sessions(self):
        """Test listing all sessions."""
        self.forwarder.create_session("session-1", "room-1")
        self.forwarder.create_session("session-2", "room-2")
        
        sessions = self.forwarder.list_sessions()
        self.assertEqual(len(sessions), 2)
        
    def test_dtls_handshake_stub(self):
        """Test DTLS handshake stub returns empty bytes."""
        result = self.forwarder.perform_dtls_handshake("p1", b"client_hello")
        self.assertEqual(result, b"")
        
    def test_srtp_key_derivation_stub(self):
        """Test SRTP key derivation stub returns None."""
        self.forwarder.create_session("session-1", "room-1")
        result = self.forwarder.derive_srtp_keys("session-1", "p1")
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
