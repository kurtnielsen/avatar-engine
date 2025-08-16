"""
Pytest configuration and fixtures for Avatar Engine tests
"""

import pytest
import asyncio
from typing import AsyncGenerator, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.core.facial_animation_unified_system import UnifiedFacialAnimationSystem
from backend.core.websocket_protocol import AnimationData, AudioData, ControlData
from backend.compression.delta_compressor import DeltaCompressor
from backend.compression.performance_monitor import PerformanceMonitor


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def unified_system():
    """Create a unified facial animation system for testing"""
    system = UnifiedFacialAnimationSystem()
    await system.start()
    yield system
    await system.stop()


@pytest.fixture
def delta_compressor():
    """Create a delta compressor instance"""
    return DeltaCompressor()


@pytest.fixture
async def performance_monitor():
    """Create a performance monitor instance"""
    monitor = PerformanceMonitor()
    await monitor.start_monitoring()
    yield monitor
    await monitor.stop_monitoring()


@pytest.fixture
def sample_animation_data():
    """Sample animation data for testing"""
    return AnimationData(
        blendshapes={
            "jawOpen": 0.5,
            "eyeBlinkLeft": 0.2,
            "eyeBlinkRight": 0.2,
            "mouthSmile": 0.3,
            "browInnerUp": 0.1
        },
        frame_number=1,
        delta=True
    )


@pytest.fixture
def sample_audio_data():
    """Sample audio data for testing"""
    # Base64 encoded silent audio (very small)
    return AudioData(
        chunk="AAAAAAAAAAAAAAAA",  # Silent audio
        sample_rate=48000,
        channels=1,
        format="pcm_f32le"
    )


@pytest.fixture
def sample_control_data():
    """Sample control data for testing"""
    return ControlData(
        action="quality",
        params={"level": "high"}
    )


@pytest.fixture
def mock_websocket():
    """Mock WebSocket for testing"""
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []
            self.closed = False
            
        async def send_json(self, data: Dict[str, Any]):
            self.sent_messages.append(("json", data))
            
        async def send_bytes(self, data: bytes):
            self.sent_messages.append(("bytes", data))
            
        async def close(self, code: int = 1000):
            self.closed = True
            
        def clear(self):
            self.sent_messages.clear()
            
    return MockWebSocket()


@pytest.fixture
def arkit_blendshapes():
    """Complete ARKit blendshape data"""
    return {
        "eyeBlinkLeft": 0.0,
        "eyeLookDownLeft": 0.0,
        "eyeLookInLeft": 0.0,
        "eyeLookOutLeft": 0.0,
        "eyeLookUpLeft": 0.0,
        "eyeSquintLeft": 0.0,
        "eyeWideLeft": 0.0,
        "eyeBlinkRight": 0.0,
        "eyeLookDownRight": 0.0,
        "eyeLookInRight": 0.0,
        "eyeLookOutRight": 0.0,
        "eyeLookUpRight": 0.0,
        "eyeSquintRight": 0.0,
        "eyeWideRight": 0.0,
        "jawForward": 0.0,
        "jawLeft": 0.0,
        "jawRight": 0.0,
        "jawOpen": 0.5,
        "mouthClose": 0.0,
        "mouthFunnel": 0.0,
        "mouthPucker": 0.0,
        "mouthLeft": 0.0,
        "mouthRight": 0.0,
        "mouthSmileLeft": 0.3,
        "mouthSmileRight": 0.3,
        "mouthFrownLeft": 0.0,
        "mouthFrownRight": 0.0,
        "mouthDimpleLeft": 0.0,
        "mouthDimpleRight": 0.0,
        "mouthStretchLeft": 0.0,
        "mouthStretchRight": 0.0,
        "mouthRollLower": 0.0,
        "mouthRollUpper": 0.0,
        "mouthShrugLower": 0.0,
        "mouthShrugUpper": 0.0,
        "mouthPressLeft": 0.0,
        "mouthPressRight": 0.0,
        "mouthLowerDownLeft": 0.0,
        "mouthLowerDownRight": 0.0,
        "mouthUpperUpLeft": 0.0,
        "mouthUpperUpRight": 0.0,
        "browDownLeft": 0.0,
        "browDownRight": 0.0,
        "browInnerUp": 0.1,
        "browOuterUpLeft": 0.0,
        "browOuterUpRight": 0.0,
        "cheekPuff": 0.0,
        "cheekSquintLeft": 0.0,
        "cheekSquintRight": 0.0,
        "noseSneerLeft": 0.0,
        "noseSneerRight": 0.0,
        "tongueOut": 0.0
    }