"""
Performance benchmark tests for Avatar Engine
"""

import pytest
import asyncio
import time
import statistics
from backend.core.facial_animation_unified_system import UnifiedFacialAnimationSystem
from backend.core.websocket_protocol import AnimationData, QualityLevel
from backend.compression.delta_compressor import DeltaCompressor


class TestPerformanceBenchmarks:
    """Performance benchmark tests"""
    
    @pytest.mark.asyncio
    async def test_frame_processing_latency(self, unified_system, mock_websocket):
        """Benchmark frame processing latency"""
        avatar_id = "perf_test_1"
        await unified_system.connect_avatar(avatar_id, mock_websocket)
        
        # Prepare test data
        animation_data = AnimationData(
            blendshapes={f"morph_{i}": 0.5 for i in range(52)}  # Full ARKit set
        )
        
        latencies = []
        
        # Warm up
        for _ in range(10):
            await unified_system.process_frame(avatar_id, animation_data)
        
        # Measure
        for _ in range(100):
            start = time.perf_counter()
            await unified_system.process_frame(avatar_id, animation_data)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms
        
        # Analysis
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        p99_latency = statistics.quantiles(latencies, n=100)[98]  # 99th percentile
        
        print(f"\nFrame Processing Latency:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  P99: {p99_latency:.2f}ms")
        
        # Assert performance requirements
        assert avg_latency < 10  # Average under 10ms
        assert p95_latency < 30  # P95 under 30ms (requirement)
        assert p99_latency < 50  # P99 under 50ms
    
    @pytest.mark.asyncio
    async def test_compression_performance(self):
        """Benchmark compression performance"""
        compressor = DeltaCompressor()
        
        # Generate test frames
        frames = []
        for i in range(100):
            frame = {f"morph_{j}": (i * 0.01 + j * 0.02) % 1.0 for j in range(52)}
            frames.append(frame)
        
        # Measure compression time
        compression_times = []
        compressed_sizes = []
        
        for frame in frames:
            start = time.perf_counter()
            compressed = compressor.compress_frame(frame)
            end = time.perf_counter()
            
            compression_times.append((end - start) * 1000)
            compressed_sizes.append(len(str(compressed)))
        
        # Calculate metrics
        avg_time = statistics.mean(compression_times)
        avg_size = statistics.mean(compressed_sizes)
        compression_ratio = compressor.get_compression_ratio()
        
        print(f"\nCompression Performance:")
        print(f"  Average time: {avg_time:.3f}ms")
        print(f"  Average compressed size: {avg_size:.0f} bytes")
        print(f"  Compression ratio: {compression_ratio:.2f}x")
        
        # Performance assertions
        assert avg_time < 1.0  # Under 1ms average
        assert compression_ratio > 2.0  # At least 2x compression
    
    @pytest.mark.asyncio
    async def test_concurrent_avatar_scaling(self, unified_system):
        """Test performance with multiple concurrent avatars"""
        avatar_counts = [1, 5, 10]
        results = {}
        
        animation_data = AnimationData(
            blendshapes={f"morph_{i}": 0.5 for i in range(52)}
        )
        
        for count in avatar_counts:
            # Create avatars
            avatars = []
            for i in range(count):
                avatar_id = f"scale_test_{i}"
                mock_ws = MockWebSocket()
                await unified_system.connect_avatar(avatar_id, mock_ws)
                avatars.append((avatar_id, mock_ws))
            
            # Measure concurrent processing
            start = time.perf_counter()
            
            tasks = [
                unified_system.process_frame(avatar_id, animation_data)
                for avatar_id, _ in avatars
                for _ in range(10)  # 10 frames each
            ]
            
            await asyncio.gather(*tasks)
            
            end = time.perf_counter()
            total_time = (end - start) * 1000
            avg_time_per_frame = total_time / (count * 10)
            
            results[count] = avg_time_per_frame
            
            # Cleanup
            for avatar_id, _ in avatars:
                await unified_system.disconnect_avatar(avatar_id)
            
        print(f"\nConcurrent Avatar Scaling:")
        for count, avg_time in results.items():
            print(f"  {count} avatars: {avg_time:.2f}ms per frame")
        
        # Check scaling efficiency
        scaling_factor = results[10] / results[1]
        assert scaling_factor < 3.0  # Should not be more than 3x slower with 10x avatars
    
    @pytest.mark.asyncio
    async def test_quality_level_performance(self, unified_system, mock_websocket):
        """Test performance impact of different quality levels"""
        avatar_id = "quality_test"
        await unified_system.connect_avatar(avatar_id, mock_websocket)
        
        animation_data = AnimationData(
            blendshapes={f"morph_{i}": 0.5 for i in range(52)}
        )
        
        results = {}
        
        for quality in [QualityLevel.LOW, QualityLevel.MEDIUM, QualityLevel.HIGH, QualityLevel.ULTRA]:
            # Set quality
            await unified_system.handle_control(
                avatar_id,
                "quality",
                {"level": quality}
            )
            
            # Measure performance
            latencies = []
            
            for _ in range(50):
                start = time.perf_counter()
                result = await unified_system.process_frame(avatar_id, animation_data)
                end = time.perf_counter()
                
                if not result.get("skipped"):
                    latencies.append((end - start) * 1000)
            
            if latencies:
                avg_latency = statistics.mean(latencies)
                results[quality] = avg_latency
            else:
                results[quality] = 0  # All frames skipped
        
        print(f"\nQuality Level Performance:")
        for quality, latency in results.items():
            print(f"  {quality}: {latency:.2f}ms")
        
        # Lower quality should be faster
        if results[QualityLevel.LOW] > 0 and results[QualityLevel.HIGH] > 0:
            assert results[QualityLevel.LOW] < results[QualityLevel.HIGH]
    
    @pytest.mark.asyncio
    async def test_memory_usage(self, unified_system):
        """Test memory usage with extended operation"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create multiple avatars and process many frames
        avatars = []
        for i in range(5):
            avatar_id = f"memory_test_{i}"
            mock_ws = MockWebSocket()
            await unified_system.connect_avatar(avatar_id, mock_ws)
            avatars.append(avatar_id)
        
        animation_data = AnimationData(
            blendshapes={f"morph_{i}": 0.5 for i in range(52)}
        )
        
        # Process many frames
        for _ in range(100):
            for avatar_id in avatars:
                await unified_system.process_frame(avatar_id, animation_data)
        
        # Check memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"\nMemory Usage:")
        print(f"  Initial: {initial_memory:.1f}MB")
        print(f"  Final: {final_memory:.1f}MB")
        print(f"  Increase: {memory_increase:.1f}MB")
        
        # Cleanup
        for avatar_id in avatars:
            await unified_system.disconnect_avatar(avatar_id)
        
        # Memory increase should be reasonable
        assert memory_increase < 150  # Less than 150MB increase
    
    @pytest.mark.asyncio
    async def test_fps_stability(self, unified_system, mock_websocket):
        """Test FPS stability over time"""
        avatar_id = "fps_test"
        session = await unified_system.connect_avatar(avatar_id, mock_websocket)
        
        animation_data = AnimationData(
            blendshapes={f"morph_{i}": 0.5 for i in range(52)}
        )
        
        # Target 60 FPS
        target_frame_time = 1.0 / 60.0
        frame_times = []
        
        # Process frames at target rate
        for i in range(120):  # 2 seconds at 60 FPS
            start = time.perf_counter()
            
            await unified_system.process_frame(avatar_id, animation_data)
            
            # Sleep to maintain frame rate
            elapsed = time.perf_counter() - start
            if elapsed < target_frame_time:
                await asyncio.sleep(target_frame_time - elapsed)
            
            frame_times.append(time.perf_counter() - start)
        
        # Calculate FPS metrics
        actual_fps = [1.0 / ft for ft in frame_times if ft > 0]
        avg_fps = statistics.mean(actual_fps)
        fps_std_dev = statistics.stdev(actual_fps)
        
        print(f"\nFPS Stability:")
        print(f"  Average FPS: {avg_fps:.1f}")
        print(f"  Std Dev: {fps_std_dev:.1f}")
        print(f"  Session reported FPS: {session.metrics.fps:.1f}")
        
        # FPS should be stable
        assert 55 <= avg_fps <= 65  # Within 10% of target
        assert fps_std_dev < 5  # Low variance


class MockWebSocket:
    """Mock WebSocket for performance testing"""
    def __init__(self):
        self.sent_messages = []
        
    async def send_json(self, data):
        self.sent_messages.append(("json", data))
        
    async def send_bytes(self, data):
        self.sent_messages.append(("bytes", data))
        
    async def close(self, code=1000):
        pass