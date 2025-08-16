"""
Unit tests for compression module
"""

import pytest
import json
from backend.compression.delta_compressor import DeltaCompressor


class TestDeltaCompressor:
    """Test delta compression functionality"""
    
    def test_initialization(self):
        """Test compressor initialization"""
        compressor = DeltaCompressor()
        assert compressor.change_threshold == 0.01
        assert compressor.force_keyframe_interval == 30
        assert compressor.batch_size == 5
        assert compressor.frame_count == 0
        assert compressor.last_keyframe is None
        assert compressor.last_frame is None
    
    def test_first_frame_is_keyframe(self, delta_compressor):
        """Test that first frame is always a keyframe"""
        frame = {"morph1": 0.5, "morph2": 0.3}
        compressed = delta_compressor.compress_frame(frame)
        
        assert compressed["type"] == "keyframe"
        assert compressed["data"] == frame
        assert compressed["frame_number"] == 0
    
    def test_delta_compression(self, delta_compressor):
        """Test delta compression between frames"""
        # First frame (keyframe)
        frame1 = {"morph1": 0.5, "morph2": 0.3, "morph3": 0.1}
        compressed1 = delta_compressor.compress_frame(frame1)
        
        # Second frame (delta)
        frame2 = {"morph1": 0.6, "morph2": 0.3, "morph3": 0.15}
        compressed2 = delta_compressor.compress_frame(frame2)
        
        assert compressed2["type"] == "delta"
        assert "morph1" in compressed2["data"]  # Changed
        assert "morph2" not in compressed2["data"]  # Unchanged
        assert "morph3" in compressed2["data"]  # Changed
        assert compressed2["frame_number"] == 1
    
    def test_change_threshold(self, delta_compressor):
        """Test that small changes below threshold are ignored"""
        frame1 = {"morph1": 0.5, "morph2": 0.3}
        delta_compressor.compress_frame(frame1)
        
        # Small change below threshold (0.01)
        frame2 = {"morph1": 0.505, "morph2": 0.3}
        compressed2 = delta_compressor.compress_frame(frame2)
        
        assert compressed2["type"] == "delta"
        assert len(compressed2["data"]) == 0  # No changes above threshold
    
    def test_force_keyframe(self, delta_compressor):
        """Test forced keyframe insertion"""
        frame1 = {"morph1": 0.5, "morph2": 0.3}
        delta_compressor.compress_frame(frame1)
        
        # Force keyframe
        delta_compressor.force_keyframe()
        
        frame2 = {"morph1": 0.6, "morph2": 0.4}
        compressed2 = delta_compressor.compress_frame(frame2)
        
        assert compressed2["type"] == "keyframe"
        assert compressed2["data"] == frame2
    
    def test_automatic_keyframe_interval(self):
        """Test automatic keyframe insertion at intervals"""
        compressor = DeltaCompressor(force_keyframe_interval=5)
        
        frames_compressed = []
        frame = {"morph1": 0.5, "morph2": 0.3}
        
        # Compress 10 frames
        for i in range(10):
            frame["morph1"] += 0.1  # Change to ensure delta
            compressed = compressor.compress_frame(frame.copy())
            frames_compressed.append(compressed)
        
        # Check keyframes at correct intervals
        assert frames_compressed[0]["type"] == "keyframe"  # First frame
        assert frames_compressed[5]["type"] == "keyframe"  # Interval reached
        
        # Check deltas
        for i in [1, 2, 3, 4, 6, 7, 8, 9]:
            assert frames_compressed[i]["type"] == "delta"
    
    def test_reset(self, delta_compressor):
        """Test compressor reset"""
        frame1 = {"morph1": 0.5, "morph2": 0.3}
        delta_compressor.compress_frame(frame1)
        
        assert delta_compressor.frame_count == 1
        assert delta_compressor.last_frame is not None
        
        delta_compressor.reset()
        
        assert delta_compressor.frame_count == 0
        assert delta_compressor.last_frame is None
        assert delta_compressor.last_keyframe is None
    
    def test_compression_ratio(self, delta_compressor):
        """Test compression ratio calculation"""
        # Initial ratio should be 1.0
        assert delta_compressor.get_compression_ratio() == 1.0
        
        # Compress frames
        frame1 = {"morph1": 0.5, "morph2": 0.3, "morph3": 0.1}
        delta_compressor.compress_frame(frame1)
        
        frame2 = {"morph1": 0.6, "morph2": 0.3, "morph3": 0.1}
        delta_compressor.compress_frame(frame2)
        
        ratio = delta_compressor.get_compression_ratio()
        assert ratio > 1.0  # Should show compression benefit
    
    def test_batch_compression(self, delta_compressor):
        """Test batch frame compression"""
        frames = [
            {"morph1": 0.1, "morph2": 0.2},
            {"morph1": 0.2, "morph2": 0.2},
            {"morph1": 0.3, "morph2": 0.2},
            {"morph1": 0.4, "morph2": 0.2},
            {"morph1": 0.5, "morph2": 0.2}
        ]
        
        compressed_batch = delta_compressor.compress_batch(frames)
        
        assert len(compressed_batch) == len(frames)
        assert compressed_batch[0]["type"] == "keyframe"
        
        # Rest should be deltas
        for i in range(1, len(compressed_batch)):
            assert compressed_batch[i]["type"] == "delta"
            assert "morph1" in compressed_batch[i]["data"]
            assert "morph2" not in compressed_batch[i]["data"]  # Unchanged
    
    def test_decompress_frame(self, delta_compressor):
        """Test frame decompression"""
        # Compress some frames
        frame1 = {"morph1": 0.5, "morph2": 0.3}
        compressed1 = delta_compressor.compress_frame(frame1)
        
        frame2 = {"morph1": 0.6, "morph2": 0.4}
        compressed2 = delta_compressor.compress_frame(frame2)
        
        # Decompress
        decompressed1 = delta_compressor.decompress_frame(compressed1)
        assert decompressed1 == frame1
        
        decompressed2 = delta_compressor.decompress_frame(compressed2)
        assert decompressed2 == frame2
    
    def test_handle_missing_morphs(self, delta_compressor):
        """Test handling of morphs that appear/disappear between frames"""
        frame1 = {"morph1": 0.5, "morph2": 0.3}
        delta_compressor.compress_frame(frame1)
        
        # Frame with new morph and missing old one
        frame2 = {"morph1": 0.6, "morph3": 0.2}
        compressed2 = delta_compressor.compress_frame(frame2)
        
        assert compressed2["type"] == "delta"
        assert "morph1" in compressed2["data"]
        assert "morph3" in compressed2["data"]
        # morph2 is not included as it's not in the new frame
    
    def test_edge_cases(self, delta_compressor):
        """Test edge cases"""
        # Empty frame
        empty_frame = {}
        compressed_empty = delta_compressor.compress_frame(empty_frame)
        assert compressed_empty["type"] == "keyframe"
        assert compressed_empty["data"] == {}
        
        # Single morph
        single_morph = {"morph1": 1.0}
        compressed_single = delta_compressor.compress_frame(single_morph)
        assert compressed_single["type"] == "delta"
        
        # Very small values
        small_values = {"morph1": 0.0001, "morph2": 0.0}
        compressed_small = delta_compressor.compress_frame(small_values)
        assert compressed_small["type"] == "delta"