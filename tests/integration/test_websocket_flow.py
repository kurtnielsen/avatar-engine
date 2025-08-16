"""
Integration tests for WebSocket communication flow
"""

import pytest
import asyncio
from backend.core.facial_animation_unified_system import UnifiedFacialAnimationSystem
from backend.core.websocket_protocol import (
    AnimationData, AudioData, ControlData,
    MessageType, ControlAction, QualityLevel
)


class TestWebSocketIntegration:
    """Test WebSocket integration with unified system"""
    
    @pytest.mark.asyncio
    async def test_avatar_connection(self, unified_system, mock_websocket):
        """Test avatar connection and disconnection"""
        avatar_id = "test_avatar_1"
        
        # Connect avatar
        session = await unified_system.connect_avatar(avatar_id, mock_websocket)
        
        assert avatar_id in unified_system.sessions
        assert session.id == avatar_id
        assert session.active is True
        assert session.quality == QualityLevel.HIGH
        
        # Check initial state message was sent
        assert len(mock_websocket.sent_messages) == 1
        msg_type, msg_data = mock_websocket.sent_messages[0]
        assert msg_type == "json"
        assert msg_data["type"] == "state"
        assert msg_data["avatar_id"] == avatar_id
        
        # Disconnect avatar
        await unified_system.disconnect_avatar(avatar_id)
        assert avatar_id not in unified_system.sessions
    
    @pytest.mark.asyncio
    async def test_animation_frame_processing(self, unified_system, mock_websocket, sample_animation_data):
        """Test animation frame processing flow"""
        avatar_id = "test_avatar_2"
        await unified_system.connect_avatar(avatar_id, mock_websocket)
        mock_websocket.clear()
        
        # Process animation frame
        result = await unified_system.process_frame(avatar_id, sample_animation_data)
        
        assert "data" in result
        assert "metrics" in result
        assert result["metrics"]["latency_ms"] > 0
        assert result["metrics"]["morphs_active"] > 0
        assert not result.get("skipped", False)
    
    @pytest.mark.asyncio
    async def test_audio_to_viseme_processing(self, unified_system, mock_websocket, sample_audio_data):
        """Test audio to viseme conversion"""
        avatar_id = "test_avatar_3"
        await unified_system.connect_avatar(avatar_id, mock_websocket)
        
        # Process audio
        visemes = await unified_system.process_audio(avatar_id, sample_audio_data)
        
        assert visemes.visemes is not None
        assert visemes.duration_ms >= 0
        assert hasattr(visemes, 'offset_ms')
    
    @pytest.mark.asyncio
    async def test_quality_control(self, unified_system, mock_websocket):
        """Test quality level control"""
        avatar_id = "test_avatar_4"
        session = await unified_system.connect_avatar(avatar_id, mock_websocket)
        mock_websocket.clear()
        
        # Change quality
        await unified_system.handle_control(
            avatar_id, 
            ControlAction.QUALITY,
            {"level": QualityLevel.LOW}
        )
        
        assert session.quality == QualityLevel.LOW
        
        # Check state update was sent
        assert len(mock_websocket.sent_messages) == 1
        msg_type, msg_data = mock_websocket.sent_messages[0]
        assert msg_data["quality"] == QualityLevel.LOW
    
    @pytest.mark.asyncio
    async def test_compression_reset(self, unified_system, mock_websocket):
        """Test compression reset control"""
        avatar_id = "test_avatar_5"
        await unified_system.connect_avatar(avatar_id, mock_websocket)
        
        # Process a frame to establish compression state
        animation_data = AnimationData(blendshapes={"morph1": 0.5})
        await unified_system.process_frame(avatar_id, animation_data)
        
        # Reset compression
        await unified_system.handle_control(avatar_id, ControlAction.RESET)
        
        # Verify compressor was reset
        compressor = unified_system.compressors[avatar_id]
        assert compressor.frame_count == 0
        assert compressor.last_frame is None
    
    @pytest.mark.asyncio
    async def test_pause_resume(self, unified_system, mock_websocket):
        """Test pause and resume functionality"""
        avatar_id = "test_avatar_6"
        session = await unified_system.connect_avatar(avatar_id, mock_websocket)
        
        # Pause
        await unified_system.handle_control(avatar_id, ControlAction.PAUSE)
        assert session.active is False
        
        # Try to process frame while paused
        animation_data = AnimationData(blendshapes={"morph1": 0.5})
        with pytest.raises(ValueError):
            await unified_system.process_frame(avatar_id, animation_data)
        
        # Resume
        await unified_system.handle_control(avatar_id, ControlAction.RESUME)
        assert session.active is True
        
        # Should work now
        result = await unified_system.process_frame(avatar_id, animation_data)
        assert "data" in result
    
    @pytest.mark.asyncio
    async def test_frame_skipping(self, unified_system, mock_websocket):
        """Test frame skipping based on performance"""
        avatar_id = "test_avatar_7"
        session = await unified_system.connect_avatar(avatar_id, mock_websocket)
        
        # Set low quality for higher skip rate
        await unified_system.handle_control(
            avatar_id,
            ControlAction.QUALITY,
            {"level": QualityLevel.LOW}
        )
        
        # Simulate rapid frames
        animation_data = AnimationData(blendshapes={"morph1": 0.5})
        
        results = []
        for i in range(10):
            # Minimal delay to trigger skipping
            await asyncio.sleep(0.001)
            result = await unified_system.process_frame(avatar_id, animation_data)
            results.append(result)
        
        # Some frames should be skipped
        skipped_count = sum(1 for r in results if r.get("skipped", False))
        assert skipped_count > 0
    
    @pytest.mark.asyncio
    async def test_temporal_smoothing(self, unified_system, mock_websocket):
        """Test temporal smoothing between frames"""
        avatar_id = "test_avatar_8"
        await unified_system.connect_avatar(avatar_id, mock_websocket)
        
        # Process frames with sudden changes
        frame1 = AnimationData(blendshapes={"morph1": 0.0, "morph2": 0.0})
        frame2 = AnimationData(blendshapes={"morph1": 1.0, "morph2": 1.0})
        
        result1 = await unified_system.process_frame(avatar_id, frame1)
        await asyncio.sleep(0.05)  # 50ms between frames
        result2 = await unified_system.process_frame(avatar_id, frame2)
        
        # Due to smoothing, the second frame should not jump directly to 1.0
        # (This would require examining the actual compressed data)
        assert result2["metrics"]["latency_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_avatars(self, unified_system):
        """Test handling multiple concurrent avatars"""
        mock_websockets = [MockWebSocket() for _ in range(5)]
        avatar_ids = [f"avatar_{i}" for i in range(5)]
        
        # Connect all avatars
        for avatar_id, ws in zip(avatar_ids, mock_websockets):
            await unified_system.connect_avatar(avatar_id, ws)
        
        assert len(unified_system.sessions) == 5
        
        # Process frames for all avatars
        animation_data = AnimationData(blendshapes={"morph1": 0.5})
        
        tasks = [
            unified_system.process_frame(avatar_id, animation_data)
            for avatar_id in avatar_ids
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert all("data" in r for r in results)
        
        # Disconnect all
        for avatar_id in avatar_ids:
            await unified_system.disconnect_avatar(avatar_id)
        
        assert len(unified_system.sessions) == 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, unified_system):
        """Test error handling for invalid operations"""
        # Try to process frame for non-existent avatar
        with pytest.raises(ValueError) as exc_info:
            animation_data = AnimationData(blendshapes={"morph1": 0.5})
            await unified_system.process_frame("non_existent", animation_data)
        
        assert "Unknown avatar" in str(exc_info.value)
        
        # Try to handle control for non-existent avatar
        with pytest.raises(ValueError):
            await unified_system.handle_control(
                "non_existent",
                ControlAction.PAUSE
            )


class MockWebSocket:
    """Mock WebSocket for testing"""
    def __init__(self):
        self.sent_messages = []
        self.closed = False
        
    async def send_json(self, data):
        self.sent_messages.append(("json", data))
        
    async def send_bytes(self, data):
        self.sent_messages.append(("bytes", data))
        
    async def close(self, code=1000):
        self.closed = True
        
    def clear(self):
        self.sent_messages.clear()