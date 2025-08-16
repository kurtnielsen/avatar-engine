"""
WebSocket Protocol Definition for Avatar Engine
Defines message types and structures for real-time communication
"""

from enum import Enum
from typing import Dict, Any, Optional, Union, List
from pydantic import BaseModel, Field, validator
import time


class MessageType(str, Enum):
    """WebSocket message types"""
    # Client -> Server
    ANIMATION = "animation"
    AUDIO = "audio"
    CONTROL = "control"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    
    # Server -> Client
    VISEMES = "visemes"
    STATE = "state"
    ERROR = "error"
    ACK = "ack"
    METRICS = "metrics"
    
    # Bidirectional
    PING = "ping"
    PONG = "pong"


class ControlAction(str, Enum):
    """Control message actions"""
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    RESET = "reset"
    QUALITY = "quality"
    KEYFRAME = "keyframe"


class QualityLevel(str, Enum):
    """Quality presets"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    CUSTOM = "custom"


class BaseMessage(BaseModel):
    """Base message structure"""
    type: MessageType
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    id: Optional[str] = None
    
    class Config:
        use_enum_values = True


class AnimationData(BaseModel):
    """Animation frame data"""
    blendshapes: Dict[str, float] = Field(..., description="Morph target values")
    frame_number: Optional[int] = None
    delta: bool = Field(default=True, description="Whether this is a delta frame")
    priority_morphs: Optional[List[str]] = None
    
    @validator('blendshapes')
    def validate_blendshapes(cls, v):
        """Ensure blendshape values are in valid range"""
        for key, value in v.items():
            if not -1.0 <= value <= 1.0:
                raise ValueError(f"Blendshape {key} value {value} out of range [-1, 1]")
        return v


class AudioData(BaseModel):
    """Audio chunk data"""
    chunk: str = Field(..., description="Base64 encoded audio data")
    sample_rate: int = Field(default=48000)
    channels: int = Field(default=1)
    format: str = Field(default="pcm_f32le")
    duration_ms: Optional[int] = None


class ControlData(BaseModel):
    """Control command data"""
    action: ControlAction
    avatar_id: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class VisemeData(BaseModel):
    """Viseme sequence data"""
    visemes: List[Dict[str, Union[str, float, int]]]
    duration_ms: int
    offset_ms: int = 0
    blend_mode: str = Field(default="override")


class MetricsData(BaseModel):
    """Performance metrics"""
    fps: float
    latency_ms: float
    bandwidth_kbps: float
    draw_calls: int
    triangles: int
    compression_ratio: float
    dropped_frames: int = 0
    cpu_usage: Optional[float] = None
    memory_mb: Optional[float] = None


class ErrorData(BaseModel):
    """Error information"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    recoverable: bool = True


# Message Models
class AnimationMessage(BaseMessage):
    """Animation data message"""
    type: MessageType = MessageType.ANIMATION
    data: AnimationData


class AudioMessage(BaseMessage):
    """Audio data message"""
    type: MessageType = MessageType.AUDIO
    data: AudioData


class ControlMessage(BaseMessage):
    """Control command message"""
    type: MessageType = MessageType.CONTROL
    data: ControlData


class VisemeMessage(BaseMessage):
    """Viseme data message"""
    type: MessageType = MessageType.VISEMES
    data: VisemeData


class MetricsMessage(BaseMessage):
    """Metrics update message"""
    type: MessageType = MessageType.METRICS
    data: MetricsData


class ErrorMessage(BaseMessage):
    """Error message"""
    type: MessageType = MessageType.ERROR
    data: ErrorData


class AckMessage(BaseMessage):
    """Acknowledgment message"""
    type: MessageType = MessageType.ACK
    ack_id: str
    status: str = "ok"
    data: Optional[Dict[str, Any]] = None


class StateMessage(BaseMessage):
    """Avatar state update"""
    type: MessageType = MessageType.STATE
    avatar_id: str
    state: str  # "connected", "active", "paused", "error"
    quality: QualityLevel
    compression_enabled: bool
    metrics: Optional[MetricsData] = None


# Message type mapping
MESSAGE_TYPE_MAP = {
    MessageType.ANIMATION: AnimationMessage,
    MessageType.AUDIO: AudioMessage,
    MessageType.CONTROL: ControlMessage,
    MessageType.VISEMES: VisemeMessage,
    MessageType.METRICS: MetricsMessage,
    MessageType.ERROR: ErrorMessage,
    MessageType.ACK: AckMessage,
    MessageType.STATE: StateMessage,
}


def parse_message(data: Dict[str, Any]) -> BaseMessage:
    """Parse incoming message to appropriate type"""
    msg_type = data.get("type")
    if not msg_type:
        raise ValueError("Message missing 'type' field")
    
    message_class = MESSAGE_TYPE_MAP.get(msg_type)
    if not message_class:
        raise ValueError(f"Unknown message type: {msg_type}")
    
    return message_class(**data)


def create_error_message(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> ErrorMessage:
    """Helper to create error messages"""
    return ErrorMessage(
        data=ErrorData(
            code=code,
            message=message,
            details=details or {}
        )
    )