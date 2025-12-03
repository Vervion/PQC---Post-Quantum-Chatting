"""
Tests for Media Transport
"""

import unittest
from client.media_transport import (
    DTLSSRTPSender, DTLSSRTPReceiver, MediaTransportConfig, TransportState
)


class TestDTLSSRTPSender(unittest.TestCase):
    """Tests for the DTLSSRTPSender class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = MediaTransportConfig(
            server_host="127.0.0.1",
            audio_port=10000,
            video_port=10001
        )
        self.sender = DTLSSRTPSender(self.config)
        
    def tearDown(self):
        """Clean up after tests."""
        self.sender.disconnect()
        
    def test_initial_state(self):
        """Test initial transport state."""
        self.assertEqual(self.sender.state, TransportState.DISCONNECTED)
        self.assertFalse(self.sender.is_connected)
        
    def test_connect(self):
        """Test connecting the sender."""
        result = self.sender.connect()
        self.assertTrue(result)
        self.assertEqual(self.sender.state, TransportState.CONNECTED)
        self.assertTrue(self.sender.is_connected)
        
    def test_disconnect(self):
        """Test disconnecting the sender."""
        self.sender.connect()
        self.sender.disconnect()
        self.assertEqual(self.sender.state, TransportState.DISCONNECTED)
        
    def test_send_audio_not_connected(self):
        """Test sending audio when not connected fails."""
        result = self.sender.send_audio(b"test_data", 0.0)
        self.assertFalse(result)
        
    def test_send_video_not_connected(self):
        """Test sending video when not connected fails."""
        result = self.sender.send_video(b"test_data", 0.0)
        self.assertFalse(result)


class TestDTLSSRTPReceiver(unittest.TestCase):
    """Tests for the DTLSSRTPReceiver class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = MediaTransportConfig(
            server_host="127.0.0.1",
            audio_port=10000,
            video_port=10001
        )
        self.receiver = DTLSSRTPReceiver(self.config)
        
    def tearDown(self):
        """Clean up after tests."""
        self.receiver.stop()
        
    def test_initial_state(self):
        """Test initial transport state."""
        self.assertEqual(self.receiver.state, TransportState.DISCONNECTED)
        self.assertFalse(self.receiver.is_running)
        
    def test_start(self):
        """Test starting the receiver."""
        result = self.receiver.start(audio_port=30000, video_port=30001)
        self.assertTrue(result)
        self.assertEqual(self.receiver.state, TransportState.CONNECTED)
        self.assertTrue(self.receiver.is_running)
        
    def test_stop(self):
        """Test stopping the receiver."""
        self.receiver.start(audio_port=30002, video_port=30003)
        self.receiver.stop()
        self.assertEqual(self.receiver.state, TransportState.DISCONNECTED)


if __name__ == '__main__':
    unittest.main()
