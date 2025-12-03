"""
Audio/Video Capture Stubs

Provides stub implementations for audio and video capture.
In production, this would interface with actual capture hardware
via libraries like PyAudio and OpenCV.
"""

import threading
import logging
from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CaptureState(Enum):
    """State of capture device."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class AudioConfig:
    """Audio capture configuration."""
    sample_rate: int = 48000
    channels: int = 1
    bits_per_sample: int = 16
    frame_duration_ms: int = 20  # 20ms frames for low latency
    device_index: Optional[int] = None


@dataclass
class VideoConfig:
    """Video capture configuration."""
    width: int = 640
    height: int = 480
    fps: int = 30
    device_index: int = 0


@dataclass
class AudioFrame:
    """Represents a captured audio frame."""
    data: bytes
    timestamp: float
    sample_rate: int
    channels: int


@dataclass
class VideoFrame:
    """Represents a captured video frame."""
    data: bytes
    width: int
    height: int
    timestamp: float
    format: str = "RGB24"


class AudioCapture:
    """
    Audio capture device (Stub Implementation).
    
    In production, this would use PyAudio or similar to capture
    from the microphone.
    """
    
    def __init__(self, config: AudioConfig):
        """
        Initialize audio capture.
        
        Args:
            config: Audio capture configuration.
        """
        self.config = config
        self._state = CaptureState.STOPPED
        self._capture_thread: Optional[threading.Thread] = None
        self._on_frame: Optional[Callable[[AudioFrame], None]] = None
        self._enabled = False
        
    def set_frame_callback(self, callback: Callable[[AudioFrame], None]):
        """
        Set callback for captured audio frames.
        
        Args:
            callback: Function receiving AudioFrame objects.
        """
        self._on_frame = callback
        
    def start(self) -> bool:
        """
        Start audio capture.
        
        Returns:
            True if successful, False otherwise.
        """
        if self._state == CaptureState.RUNNING:
            logger.warning("Audio capture already running")
            return True
            
        try:
            self._state = CaptureState.STARTING
            
            # Stub: In production, initialize audio device here
            logger.info(
                f"Audio capture stub started: {self.config.sample_rate}Hz, "
                f"{self.config.channels} channel(s)"
            )
            
            self._enabled = True
            self._state = CaptureState.RUNNING
            
            # Start capture thread
            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True
            )
            self._capture_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            self._state = CaptureState.ERROR
            return False
            
    def stop(self):
        """Stop audio capture."""
        self._enabled = False
        
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None
            
        self._state = CaptureState.STOPPED
        logger.info("Audio capture stopped")
        
    def _capture_loop(self):
        """
        Main capture loop (stub).
        
        In production, this would read from the audio device.
        """
        import time
        
        frame_duration = self.config.frame_duration_ms / 1000.0
        frame_size = int(
            self.config.sample_rate * frame_duration * 
            self.config.channels * (self.config.bits_per_sample // 8)
        )
        
        while self._enabled:
            try:
                # Stub: Generate silent frame
                frame_data = bytes(frame_size)
                timestamp = time.time()
                
                frame = AudioFrame(
                    data=frame_data,
                    timestamp=timestamp,
                    sample_rate=self.config.sample_rate,
                    channels=self.config.channels
                )
                
                if self._on_frame:
                    self._on_frame(frame)
                    
                time.sleep(frame_duration)
                
            except Exception as e:
                logger.error(f"Error in audio capture: {e}")
                break
                
    def set_muted(self, muted: bool):
        """
        Set mute state.
        
        Args:
            muted: Whether audio should be muted.
        """
        # Stub: In production, this would control the actual capture
        logger.info(f"Audio {'muted' if muted else 'unmuted'}")
        
    @property
    def state(self) -> CaptureState:
        """Get capture state."""
        return self._state
        
    @property
    def is_running(self) -> bool:
        """Check if capture is running."""
        return self._state == CaptureState.RUNNING


class VideoCapture:
    """
    Video capture device (Stub Implementation).
    
    In production, this would use OpenCV or v4l2 to capture
    from the camera.
    """
    
    def __init__(self, config: VideoConfig):
        """
        Initialize video capture.
        
        Args:
            config: Video capture configuration.
        """
        self.config = config
        self._state = CaptureState.STOPPED
        self._capture_thread: Optional[threading.Thread] = None
        self._on_frame: Optional[Callable[[VideoFrame], None]] = None
        self._enabled = False
        
    def set_frame_callback(self, callback: Callable[[VideoFrame], None]):
        """
        Set callback for captured video frames.
        
        Args:
            callback: Function receiving VideoFrame objects.
        """
        self._on_frame = callback
        
    def start(self) -> bool:
        """
        Start video capture.
        
        Returns:
            True if successful, False otherwise.
        """
        if self._state == CaptureState.RUNNING:
            logger.warning("Video capture already running")
            return True
            
        try:
            self._state = CaptureState.STARTING
            
            # Stub: In production, initialize camera device here
            logger.info(
                f"Video capture stub started: {self.config.width}x{self.config.height} "
                f"@ {self.config.fps}fps"
            )
            
            self._enabled = True
            self._state = CaptureState.RUNNING
            
            # Start capture thread
            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True
            )
            self._capture_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start video capture: {e}")
            self._state = CaptureState.ERROR
            return False
            
    def stop(self):
        """Stop video capture."""
        self._enabled = False
        
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None
            
        self._state = CaptureState.STOPPED
        logger.info("Video capture stopped")
        
    def _capture_loop(self):
        """
        Main capture loop (stub).
        
        In production, this would read from the camera device.
        """
        import time
        
        frame_interval = 1.0 / self.config.fps
        frame_size = self.config.width * self.config.height * 3  # RGB24
        
        while self._enabled:
            try:
                # Stub: Generate black frame
                frame_data = bytes(frame_size)
                timestamp = time.time()
                
                frame = VideoFrame(
                    data=frame_data,
                    width=self.config.width,
                    height=self.config.height,
                    timestamp=timestamp
                )
                
                if self._on_frame:
                    self._on_frame(frame)
                    
                time.sleep(frame_interval)
                
            except Exception as e:
                logger.error(f"Error in video capture: {e}")
                break
                
    def set_enabled(self, enabled: bool):
        """
        Enable or disable video.
        
        Args:
            enabled: Whether video should be enabled.
        """
        # Stub: In production, this would control the actual capture
        logger.info(f"Video {'enabled' if enabled else 'disabled'}")
        
    @property
    def state(self) -> CaptureState:
        """Get capture state."""
        return self._state
        
    @property
    def is_running(self) -> bool:
        """Check if capture is running."""
        return self._state == CaptureState.RUNNING


def list_audio_devices() -> list:
    """
    List available audio input devices (stub).
    
    Returns:
        List of device dictionaries.
    """
    # Stub: In production, enumerate actual devices
    return [
        {"index": 0, "name": "Default Audio Input", "channels": 1},
    ]


def list_video_devices() -> list:
    """
    List available video input devices (stub).
    
    Returns:
        List of device dictionaries.
    """
    # Stub: In production, enumerate actual devices
    return [
        {"index": 0, "name": "Default Camera"},
    ]
