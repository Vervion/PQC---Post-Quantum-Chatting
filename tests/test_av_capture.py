"""
Tests for AV Capture
"""

import unittest
import time
from client.av_capture import (
    AudioCapture, VideoCapture, AudioConfig, VideoConfig,
    CaptureState, list_audio_devices, list_video_devices
)


class TestAudioCapture(unittest.TestCase):
    """Tests for the AudioCapture class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = AudioConfig(
            sample_rate=48000,
            channels=1,
            bits_per_sample=16,
            frame_duration_ms=20
        )
        self.capture = AudioCapture(self.config)
        
    def tearDown(self):
        """Clean up after tests."""
        self.capture.stop()
        
    def test_initial_state(self):
        """Test initial capture state."""
        self.assertEqual(self.capture.state, CaptureState.STOPPED)
        self.assertFalse(self.capture.is_running)
        
    def test_start_capture(self):
        """Test starting audio capture."""
        result = self.capture.start()
        self.assertTrue(result)
        self.assertEqual(self.capture.state, CaptureState.RUNNING)
        self.assertTrue(self.capture.is_running)
        
    def test_stop_capture(self):
        """Test stopping audio capture."""
        self.capture.start()
        self.capture.stop()
        self.assertEqual(self.capture.state, CaptureState.STOPPED)
        
    def test_frame_callback(self):
        """Test audio frame callback."""
        frames_received = []
        
        def on_frame(frame):
            frames_received.append(frame)
            
        self.capture.set_frame_callback(on_frame)
        self.capture.start()
        
        # Wait for some frames
        time.sleep(0.1)
        
        self.capture.stop()
        
        # Should have received at least one frame
        self.assertGreater(len(frames_received), 0)
        
        # Check frame properties
        frame = frames_received[0]
        self.assertEqual(frame.sample_rate, 48000)
        self.assertEqual(frame.channels, 1)


class TestVideoCapture(unittest.TestCase):
    """Tests for the VideoCapture class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = VideoConfig(
            width=640,
            height=480,
            fps=30,
            device_index=0
        )
        self.capture = VideoCapture(self.config)
        
    def tearDown(self):
        """Clean up after tests."""
        self.capture.stop()
        
    def test_initial_state(self):
        """Test initial capture state."""
        self.assertEqual(self.capture.state, CaptureState.STOPPED)
        self.assertFalse(self.capture.is_running)
        
    def test_start_capture(self):
        """Test starting video capture."""
        result = self.capture.start()
        self.assertTrue(result)
        self.assertEqual(self.capture.state, CaptureState.RUNNING)
        self.assertTrue(self.capture.is_running)
        
    def test_stop_capture(self):
        """Test stopping video capture."""
        self.capture.start()
        self.capture.stop()
        self.assertEqual(self.capture.state, CaptureState.STOPPED)
        
    def test_frame_callback(self):
        """Test video frame callback."""
        frames_received = []
        
        def on_frame(frame):
            frames_received.append(frame)
            
        self.capture.set_frame_callback(on_frame)
        self.capture.start()
        
        # Wait for some frames
        time.sleep(0.2)
        
        self.capture.stop()
        
        # Should have received at least one frame
        self.assertGreater(len(frames_received), 0)
        
        # Check frame properties
        frame = frames_received[0]
        self.assertEqual(frame.width, 640)
        self.assertEqual(frame.height, 480)


class TestDeviceListing(unittest.TestCase):
    """Tests for device listing functions."""
    
    def test_list_audio_devices(self):
        """Test listing audio devices."""
        devices = list_audio_devices()
        self.assertIsInstance(devices, list)
        # Stub should return at least one device
        self.assertGreater(len(devices), 0)
        
    def test_list_video_devices(self):
        """Test listing video devices."""
        devices = list_video_devices()
        self.assertIsInstance(devices, list)
        # Stub should return at least one device
        self.assertGreater(len(devices), 0)


if __name__ == '__main__':
    unittest.main()
