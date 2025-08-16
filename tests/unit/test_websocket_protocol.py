"""
Unit tests for WebSocket protocol
"""

import pytest
from backend.core.websocket_protocol import (
    MessageType, ControlAction, QualityLevel,
    AnimationData, AudioData, ControlData, VisemeData, MetricsData, ErrorData,
    AnimationMessage, AudioMessage, ControlMessage, VisemeMessage, 
    MetricsMessage, ErrorMessage, AckMessage, StateMessage,
    parse_message, create_error_message
)


class TestMessageTypes:
    """Test message type enums"""
    
    def test_message_types(self):
        """Test all message types are defined"""
        assert MessageType.ANIMATION == "animation"
        assert MessageType.AUDIO == "audio"
        assert MessageType.CONTROL == "control"
        assert MessageType.VISEMES == "visemes"
        assert MessageType.ERROR == "error"
        assert MessageType.ACK == "ack"
        assert MessageType.PING == "ping"
        assert MessageType.PONG == "pong"
    
    def test_control_actions(self):
        """Test control action types"""
        assert ControlAction.START == "start"
        assert ControlAction.STOP == "stop"
        assert ControlAction.PAUSE == "pause"
        assert ControlAction.RESUME == "resume"
        assert ControlAction.RESET == "reset"
        assert ControlAction.QUALITY == "quality"
    
    def test_quality_levels(self):
        """Test quality level presets"""
        assert QualityLevel.LOW == "low"
        assert QualityLevel.MEDIUM == "medium"
        assert QualityLevel.HIGH == "high"
        assert QualityLevel.ULTRA == "ultra"


class TestDataModels:
    """Test data model validation"""
    
    def test_animation_data_validation(self):
        """Test animation data validation"""
        # Valid data
        data = AnimationData(
            blendshapes={"morph1": 0.5, "morph2": -0.3},
            frame_number=1,
            delta=True
        )
        assert data.blendshapes["morph1"] == 0.5
        assert data.delta is True
        
        # Invalid range should raise error
        with pytest.raises(ValueError):
            AnimationData(
                blendshapes={"morph1": 1.5}  # Out of range
            )
    
    def test_audio_data(self):
        """Test audio data model"""
        data = AudioData(
            chunk="base64audiodata",
            sample_rate=48000,
            channels=2,
            format="pcm_f32le"
        )
        assert data.sample_rate == 48000
        assert data.channels == 2
    
    def test_control_data(self):
        """Test control data model"""
        data = ControlData(
            action=ControlAction.QUALITY,
            avatar_id="avatar_123",
            params={"level": "high"}
        )
        assert data.action == ControlAction.QUALITY
        assert data.params["level"] == "high"
    
    def test_viseme_data(self):
        """Test viseme data model"""
        data = VisemeData(
            visemes=[
                {"viseme": "AA", "weight": 0.8, "duration": 100},
                {"viseme": "EE", "weight": 0.5, "duration": 150}
            ],
            duration_ms=250,
            offset_ms=50
        )
        assert len(data.visemes) == 2
        assert data.duration_ms == 250
    
    def test_metrics_data(self):
        """Test metrics data model"""
        data = MetricsData(
            fps=59.8,
            latency_ms=28.5,
            bandwidth_kbps=256.0,
            draw_calls=150,
            triangles=50000,
            compression_ratio=3.5,
            dropped_frames=2,
            cpu_usage=35.2,
            memory_mb=128.5
        )
        assert data.fps == 59.8
        assert data.compression_ratio == 3.5
    
    def test_error_data(self):
        """Test error data model"""
        data = ErrorData(
            code="INVALID_FRAME",
            message="Frame data is invalid",
            details={"frame_number": 42},
            recoverable=True
        )
        assert data.code == "INVALID_FRAME"
        assert data.recoverable is True


class TestMessages:
    """Test message creation and serialization"""
    
    def test_animation_message(self):
        """Test animation message creation"""
        msg = AnimationMessage(
            data=AnimationData(
                blendshapes={"morph1": 0.5}
            )
        )
        assert msg.type == MessageType.ANIMATION
        assert msg.timestamp > 0
        
        # Test serialization
        data = msg.dict()
        assert data["type"] == "animation"
        assert "data" in data
        assert "blendshapes" in data["data"]
    
    def test_audio_message(self):
        """Test audio message creation"""
        msg = AudioMessage(
            data=AudioData(chunk="audiodata")
        )
        assert msg.type == MessageType.AUDIO
        
        data = msg.dict()
        assert data["type"] == "audio"
        assert data["data"]["chunk"] == "audiodata"
    
    def test_control_message(self):
        """Test control message creation"""
        msg = ControlMessage(
            data=ControlData(
                action=ControlAction.RESET
            )
        )
        assert msg.type == MessageType.CONTROL
        assert msg.data.action == ControlAction.RESET
    
    def test_ack_message(self):
        """Test acknowledgment message"""
        msg = AckMessage(
            ack_id="msg_123",
            status="ok",
            data={"processed": True}
        )
        assert msg.type == MessageType.ACK
        assert msg.ack_id == "msg_123"
    
    def test_state_message(self):
        """Test state message"""
        msg = StateMessage(
            avatar_id="avatar_123",
            state="active",
            quality=QualityLevel.HIGH,
            compression_enabled=True
        )
        assert msg.type == MessageType.STATE
        assert msg.state == "active"


class TestMessageParsing:
    """Test message parsing functionality"""
    
    def test_parse_animation_message(self):
        """Test parsing animation message"""
        data = {
            "type": "animation",
            "data": {
                "blendshapes": {"morph1": 0.5},
                "delta": True
            }
        }
        
        msg = parse_message(data)
        assert isinstance(msg, AnimationMessage)
        assert msg.data.blendshapes["morph1"] == 0.5
    
    def test_parse_audio_message(self):
        """Test parsing audio message"""
        data = {
            "type": "audio",
            "data": {
                "chunk": "audiodata",
                "sample_rate": 44100
            }
        }
        
        msg = parse_message(data)
        assert isinstance(msg, AudioMessage)
        assert msg.data.sample_rate == 44100
    
    def test_parse_control_message(self):
        """Test parsing control message"""
        data = {
            "type": "control",
            "data": {
                "action": "pause"
            }
        }
        
        msg = parse_message(data)
        assert isinstance(msg, ControlMessage)
        assert msg.data.action == "pause"
    
    def test_parse_missing_type(self):
        """Test parsing message without type"""
        data = {"data": {"something": "value"}}
        
        with pytest.raises(ValueError) as exc_info:
            parse_message(data)
        assert "missing 'type'" in str(exc_info.value).lower()
    
    def test_parse_unknown_type(self):
        """Test parsing message with unknown type"""
        data = {"type": "unknown", "data": {}}
        
        with pytest.raises(ValueError) as exc_info:
            parse_message(data)
        assert "unknown message type" in str(exc_info.value).lower()
    
    def test_parse_with_timestamp_and_id(self):
        """Test parsing preserves timestamp and ID"""
        data = {
            "type": "control",
            "timestamp": 1234567890,
            "id": "msg_123",
            "data": {"action": "start"}
        }
        
        msg = parse_message(data)
        assert msg.timestamp == 1234567890
        assert msg.id == "msg_123"


class TestErrorHandling:
    """Test error message creation"""
    
    def test_create_error_message(self):
        """Test error message helper"""
        error = create_error_message(
            code="TEST_ERROR",
            message="This is a test error",
            details={"field": "value"}
        )
        
        assert isinstance(error, ErrorMessage)
        assert error.type == MessageType.ERROR
        assert error.data.code == "TEST_ERROR"
        assert error.data.message == "This is a test error"
        assert error.data.details["field"] == "value"
    
    def test_error_message_serialization(self):
        """Test error message can be serialized"""
        error = create_error_message(
            code="SERIALIZATION_TEST",
            message="Testing serialization"
        )
        
        data = error.dict()
        assert data["type"] == "error"
        assert data["data"]["code"] == "SERIALIZATION_TEST"
        assert data["data"]["recoverable"] is True  # Default