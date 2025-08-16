"""
Unified Facial Animation System
Coordinates all animation components into a cohesive pipeline
"""

import asyncio
import logging
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, field
import time
import json
from collections import deque

from .enhanced_facial_animation_system import EnhancedFacialAnimationSystem
from .facial_animation_performance_optimizer import FacialAnimationOptimizer
from .viseme_transition_engine import VisemeTransitionEngine
from .websocket_protocol import (
    AnimationData, AudioData, VisemeData, MetricsData,
    QualityLevel, parse_message, create_error_message
)
from ..compression.delta_compressor import DeltaCompressor
from ..compression.performance_monitor import PerformanceMonitor


logger = logging.getLogger(__name__)


@dataclass
class AvatarSession:
    """Tracks individual avatar session state"""
    id: str
    websocket: Any
    quality: QualityLevel = QualityLevel.HIGH
    compression_enabled: bool = True
    active: bool = True
    created_at: float = field(default_factory=time.time)
    last_frame_time: float = field(default_factory=time.time)
    frame_count: int = 0
    metrics: MetricsData = field(default_factory=lambda: MetricsData(
        fps=0.0, latency_ms=0.0, bandwidth_kbps=0.0,
        draw_calls=0, triangles=0, compression_ratio=1.0
    ))
    frame_history: deque = field(default_factory=lambda: deque(maxlen=60))


class UnifiedFacialAnimationSystem:
    """
    Unified system that orchestrates all facial animation components
    """
    
    def __init__(self):
        # Core components
        self.animation_system = EnhancedFacialAnimationSystem()
        self.optimizer = FacialAnimationOptimizer()
        self.viseme_engine = VisemeTransitionEngine()
        self.performance_monitor = PerformanceMonitor()
        
        # Session management
        self.sessions: Dict[str, AvatarSession] = {}
        self.compressors: Dict[str, DeltaCompressor] = {}
        
        # Performance settings
        self.target_fps = 60
        self.max_latency_ms = 30
        self.frame_skip_threshold = 2  # Skip frames if behind by 2+ frames
        
        # Quality presets
        self.quality_settings = {
            QualityLevel.LOW: {
                "morph_limit": 10,
                "update_rate": 30,
                "compression": True,
                "lod": 2
            },
            QualityLevel.MEDIUM: {
                "morph_limit": 25,
                "update_rate": 45,
                "compression": True,
                "lod": 1
            },
            QualityLevel.HIGH: {
                "morph_limit": 52,
                "update_rate": 60,
                "compression": True,
                "lod": 0
            },
            QualityLevel.ULTRA: {
                "morph_limit": 52,
                "update_rate": 90,
                "compression": False,
                "lod": 0
            }
        }
        
        # Monitoring
        self.monitoring_task = None
        self.stats_interval = 1.0  # seconds
        
    async def start(self):
        """Start the unified system"""
        logger.info("Starting Unified Facial Animation System")
        
        # Initialize components
        await self.animation_system.initialize()
        await self.performance_monitor.start_monitoring()
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitor_performance())
        
    async def stop(self):
        """Stop the unified system"""
        logger.info("Stopping Unified Facial Animation System")
        
        # Stop monitoring
        if self.monitoring_task:
            self.monitoring_task.cancel()
            
        # Stop components
        await self.performance_monitor.stop_monitoring()
        
        # Clean up sessions
        for session_id in list(self.sessions.keys()):
            await self.disconnect_avatar(session_id)
    
    async def connect_avatar(self, avatar_id: str, websocket: Any) -> AvatarSession:
        """Connect a new avatar session"""
        logger.info(f"Connecting avatar: {avatar_id}")
        
        # Create session
        session = AvatarSession(id=avatar_id, websocket=websocket)
        self.sessions[avatar_id] = session
        
        # Create compressor for this session
        self.compressors[avatar_id] = DeltaCompressor()
        
        # Send initial state
        await self._send_state_update(session)
        
        return session
    
    async def disconnect_avatar(self, avatar_id: str):
        """Disconnect an avatar session"""
        logger.info(f"Disconnecting avatar: {avatar_id}")
        
        if avatar_id in self.sessions:
            session = self.sessions[avatar_id]
            session.active = False
            
            # Clean up
            del self.sessions[avatar_id]
            if avatar_id in self.compressors:
                del self.compressors[avatar_id]
    
    async def process_frame(self, avatar_id: str, animation_data: AnimationData) -> Dict[str, Any]:
        """Process an animation frame"""
        if avatar_id not in self.sessions:
            raise ValueError(f"Unknown avatar: {avatar_id}")
            
        session = self.sessions[avatar_id]
        if not session.active:
            raise ValueError(f"Avatar {avatar_id} is not active")
        
        start_time = time.time()
        
        try:
            # Frame timing
            current_time = time.time()
            frame_delta = current_time - session.last_frame_time
            session.last_frame_time = current_time
            
            # Check if we should skip frames
            if self._should_skip_frame(session, frame_delta):
                logger.debug(f"Skipping frame for avatar {avatar_id}")
                return {"skipped": True}
            
            # Get quality settings
            quality = self.quality_settings[session.quality]
            
            # Optimize animation data
            optimized_data = await self.optimizer.optimize_animation_data(
                animation_data.blendshapes,
                avatar_id,
                morph_limit=quality["morph_limit"]
            )
            
            # Apply temporal smoothing
            smoothed_data = self._apply_temporal_smoothing(
                session, optimized_data, frame_delta
            )
            
            # Compress if enabled
            if session.compression_enabled and session.quality != QualityLevel.ULTRA:
                compressor = self.compressors[avatar_id]
                compressed = compressor.compress_frame(smoothed_data)
                compression_ratio = compressor.get_compression_ratio()
            else:
                compressed = smoothed_data
                compression_ratio = 1.0
            
            # Update metrics
            latency = (time.time() - start_time) * 1000
            session.frame_count += 1
            session.frame_history.append({
                "timestamp": current_time,
                "latency": latency,
                "size": len(json.dumps(compressed))
            })
            
            # Update session metrics
            session.metrics.latency_ms = latency
            session.metrics.compression_ratio = compression_ratio
            session.metrics.fps = self._calculate_fps(session)
            
            return {
                "data": compressed,
                "metrics": {
                    "latency_ms": latency,
                    "compression_ratio": compression_ratio,
                    "morphs_active": len(smoothed_data),
                    "frame_number": session.frame_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing frame for {avatar_id}: {e}")
            raise
    
    async def process_audio(self, avatar_id: str, audio_data: AudioData) -> VisemeData:
        """Process audio to generate visemes"""
        if avatar_id not in self.sessions:
            raise ValueError(f"Unknown avatar: {avatar_id}")
        
        try:
            # Convert base64 audio to visemes
            visemes = await self.viseme_engine.audio_to_visemes(
                audio_data.chunk,
                audio_data.sample_rate
            )
            
            return VisemeData(
                visemes=visemes["visemes"],
                duration_ms=visemes["duration_ms"],
                offset_ms=0
            )
            
        except Exception as e:
            logger.error(f"Error processing audio for {avatar_id}: {e}")
            raise
    
    async def handle_control(self, avatar_id: str, action: str, params: Optional[Dict[str, Any]] = None):
        """Handle control commands"""
        if avatar_id not in self.sessions:
            raise ValueError(f"Unknown avatar: {avatar_id}")
            
        session = self.sessions[avatar_id]
        
        if action == "quality":
            # Change quality setting
            new_quality = params.get("level", QualityLevel.HIGH)
            if new_quality in QualityLevel:
                session.quality = new_quality
                logger.info(f"Avatar {avatar_id} quality changed to {new_quality}")
                await self._send_state_update(session)
                
        elif action == "reset":
            # Reset compression state
            if avatar_id in self.compressors:
                self.compressors[avatar_id].reset()
            session.frame_count = 0
            session.frame_history.clear()
            
        elif action == "pause":
            session.active = False
            
        elif action == "resume":
            session.active = True
            session.last_frame_time = time.time()
            
        elif action == "keyframe":
            # Force keyframe
            if avatar_id in self.compressors:
                self.compressors[avatar_id].force_keyframe()
    
    def _should_skip_frame(self, session: AvatarSession, frame_delta: float) -> bool:
        """Determine if frame should be skipped based on performance"""
        target_frame_time = 1.0 / self.target_fps
        
        # Skip if we're running too far behind
        if frame_delta > target_frame_time * self.frame_skip_threshold:
            return True
            
        # Skip based on quality setting
        quality = self.quality_settings[session.quality]
        target_fps = quality["update_rate"]
        if session.frame_count % (self.target_fps // target_fps) != 0:
            return True
            
        return False
    
    def _apply_temporal_smoothing(self, session: AvatarSession, 
                                 data: Dict[str, float], 
                                 frame_delta: float) -> Dict[str, float]:
        """Apply temporal smoothing to reduce jitter"""
        # Simple exponential smoothing
        alpha = min(1.0, frame_delta * 10)  # Smoothing factor
        
        if hasattr(session, '_last_frame_data'):
            smoothed = {}
            for key, value in data.items():
                if key in session._last_frame_data:
                    # Smooth between frames
                    smoothed[key] = (alpha * value + 
                                   (1 - alpha) * session._last_frame_data[key])
                else:
                    smoothed[key] = value
            session._last_frame_data = smoothed
            return smoothed
        else:
            session._last_frame_data = data.copy()
            return data
    
    def _calculate_fps(self, session: AvatarSession) -> float:
        """Calculate current FPS from frame history"""
        if len(session.frame_history) < 2:
            return 0.0
            
        # Get timestamps from last second
        current_time = time.time()
        recent_frames = [f for f in session.frame_history 
                        if current_time - f["timestamp"] <= 1.0]
        
        if len(recent_frames) < 2:
            return 0.0
            
        time_span = recent_frames[-1]["timestamp"] - recent_frames[0]["timestamp"]
        if time_span > 0:
            return len(recent_frames) / time_span
        return 0.0
    
    async def _send_state_update(self, session: AvatarSession):
        """Send state update to client"""
        state_msg = {
            "type": "state",
            "avatar_id": session.id,
            "state": "active" if session.active else "paused",
            "quality": session.quality,
            "compression_enabled": session.compression_enabled,
            "metrics": session.metrics.dict() if session.metrics else None
        }
        
        if session.websocket:
            await session.websocket.send_json(state_msg)
    
    async def _monitor_performance(self):
        """Background task to monitor system performance"""
        while True:
            try:
                await asyncio.sleep(self.stats_interval)
                
                # Get system metrics
                system_metrics = await self.performance_monitor.get_current_metrics()
                
                # Update each session
                for session in self.sessions.values():
                    if session.active and session.metrics:
                        # Send metrics update
                        metrics_msg = {
                            "type": "metrics",
                            "data": {
                                **session.metrics.dict(),
                                "system": system_metrics
                            }
                        }
                        
                        if session.websocket:
                            try:
                                await session.websocket.send_json(metrics_msg)
                            except Exception as e:
                                logger.error(f"Failed to send metrics to {session.id}: {e}")
                                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
    
    def create_peer_connection(self, configuration: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create WebRTC peer connection configuration"""
        # Ice servers configuration
        ice_config = configuration or {
            "iceServers": [
                {"urls": "stun:stun.l.google.com:19302"},
                {"urls": "stun:stun1.l.google.com:19302"}
            ]
        }
        
        return {
            "configuration": ice_config,
            "video": False,  # No video for avatar data
            "audio": True,   # Audio for speech
            "data": True     # Data channel for animation
        }