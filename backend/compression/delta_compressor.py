#!/usr/bin/env python3
"""
Delta Compression for Facial Animation Data
Optimizes network bandwidth by sending only changed morphs
"""

import msgpack
import numpy as np
from typing import Dict, Optional, Set, Tuple
from dataclasses import dataclass
from collections import deque
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class CompressionStats:
    """Statistics for compression performance"""
    total_frames: int = 0
    compressed_frames: int = 0
    total_morphs_sent: int = 0
    total_morphs_possible: int = 0
    compression_ratio: float = 0.0
    avg_frame_size: float = 0.0
    avg_morphs_per_frame: float = 0.0


class DeltaCompressor:
    """
    Delta compression for facial animation morphs.
    Only sends morphs that changed significantly since last frame.
    """
    
    def __init__(self, 
                 change_threshold: float = 0.001,
                 force_keyframe_interval: int = 30,
                 batch_size: int = 3,
                 enable_prediction: bool = True):
        """
        Initialize delta compressor.
        
        Args:
            change_threshold: Minimum change to send morph (0.001 = 0.1%)
            force_keyframe_interval: Send full frame every N frames
            batch_size: Number of frames to batch together
            enable_prediction: Use motion prediction for interpolation hints
        """
        self.change_threshold = change_threshold
        self.force_keyframe_interval = force_keyframe_interval
        self.batch_size = batch_size
        self.enable_prediction = enable_prediction
        
        # State tracking
        self.previous_frame: Dict[str, float] = {}
        self.frame_count = 0
        self.stats = CompressionStats()
        
        # Batching
        self.frame_batch = deque(maxlen=batch_size)
        
        # Motion prediction
        self.morph_velocities: Dict[str, float] = {}
        self.morph_accelerations: Dict[str, float] = {}
        
        # Priority morphs (always send if changed)
        self.priority_morphs = {
            'Jaw_Open', 'Mouth_Open', 'Eye_L_Blink', 'Eye_R_Blink',
            'Eye_L_Wide', 'Eye_R_Wide', 'Brow_Inner_Up', 'Brow_Down_L', 'Brow_Down_R'
        }
    
    def compress_frame(self, morphs: Dict[str, float], timestamp: Optional[float] = None) -> Optional[bytes]:
        """
        Compress a single frame of morph data.
        
        Args:
            morphs: Dictionary of morph names to values (0.0 - 1.0)
            timestamp: Optional timestamp for the frame
            
        Returns:
            Compressed binary data or None if batching
        """
        if timestamp is None:
            timestamp = time.time()
        
        self.frame_count += 1
        is_keyframe = (self.frame_count % self.force_keyframe_interval) == 0
        
        # Calculate deltas
        delta_frame = {}
        changed_morphs = set()
        
        if is_keyframe:
            # Send all non-zero morphs
            delta_frame = {k: v for k, v in morphs.items() if abs(v) > 0.001}
            changed_morphs = set(delta_frame.keys())
        else:
            # Calculate changes
            for morph, value in morphs.items():
                prev_value = self.previous_frame.get(morph, 0.0)
                change = abs(value - prev_value)
                
                # Check if morph should be included
                if (change > self.change_threshold or 
                    (morph in self.priority_morphs and change > 0.0001)):
                    delta_frame[morph] = value
                    changed_morphs.add(morph)
                    
                    # Update motion prediction
                    if self.enable_prediction:
                        self._update_motion_prediction(morph, value, prev_value, timestamp)
        
        # Update stats
        self._update_stats(len(morphs), len(delta_frame))
        
        # Store current frame
        self.previous_frame = morphs.copy()
        
        # Create frame data
        frame_data = {
            'type': 'keyframe' if is_keyframe else 'delta',
            'frame': self.frame_count,
            'timestamp': timestamp,
            'morphs': delta_frame
        }
        
        # Add prediction hints if enabled
        if self.enable_prediction and not is_keyframe:
            predictions = self._get_prediction_hints(changed_morphs, timestamp)
            if predictions:
                frame_data['predictions'] = predictions
        
        # Add to batch
        self.frame_batch.append(frame_data)
        
        # Return compressed batch if full
        if len(self.frame_batch) >= self.batch_size:
            return self._compress_batch()
        
        return None
    
    def _update_motion_prediction(self, morph: str, value: float, prev_value: float, timestamp: float):
        """Update motion prediction for a morph"""
        velocity = value - prev_value  # Simple velocity
        
        if morph in self.morph_velocities:
            prev_velocity = self.morph_velocities[morph]
            acceleration = velocity - prev_velocity
            self.morph_accelerations[morph] = acceleration
        
        self.morph_velocities[morph] = velocity
    
    def _get_prediction_hints(self, changed_morphs: Set[str], timestamp: float) -> Dict[str, Dict]:
        """Get motion prediction hints for interpolation"""
        predictions = {}
        
        for morph in changed_morphs:
            if morph in self.morph_velocities:
                velocity = self.morph_velocities[morph]
                acceleration = self.morph_accelerations.get(morph, 0.0)
                
                # Only send prediction if motion is significant
                if abs(velocity) > 0.01 or abs(acceleration) > 0.02:
                    predictions[morph] = {
                        'v': round(velocity, 4),  # velocity
                        'a': round(acceleration, 4)  # acceleration
                    }
        
        return predictions
    
    def _compress_batch(self) -> bytes:
        """Compress the current batch of frames"""
        if not self.frame_batch:
            return b''
        
        batch_data = {
            'batch_size': len(self.frame_batch),
            'frames': list(self.frame_batch)
        }
        
        # Clear batch
        self.frame_batch.clear()
        
        # Compress with msgpack
        return msgpack.packb(batch_data, use_bin_type=True)
    
    def flush(self) -> Optional[bytes]:
        """Flush any remaining frames in the batch"""
        if self.frame_batch:
            return self._compress_batch()
        return None
    
    def _update_stats(self, total_morphs: int, sent_morphs: int):
        """Update compression statistics"""
        self.stats.total_frames += 1
        self.stats.compressed_frames += 1 if sent_morphs < total_morphs else 0
        self.stats.total_morphs_sent += sent_morphs
        self.stats.total_morphs_possible += total_morphs
        
        if self.stats.total_morphs_possible > 0:
            self.stats.compression_ratio = 1 - (self.stats.total_morphs_sent / self.stats.total_morphs_possible)
        
        if self.stats.total_frames > 0:
            self.stats.avg_morphs_per_frame = self.stats.total_morphs_sent / self.stats.total_frames
            self.stats.avg_frame_size = self.stats.total_morphs_sent * 8 / self.stats.total_frames  # Approximate bytes
    
    def get_stats(self) -> CompressionStats:
        """Get current compression statistics"""
        return self.stats
    
    def reset(self):
        """Reset compressor state"""
        self.previous_frame.clear()
        self.frame_count = 0
        self.frame_batch.clear()
        self.morph_velocities.clear()
        self.morph_accelerations.clear()
        self.stats = CompressionStats()


class DeltaDecompressor:
    """
    Decompressor for delta-compressed facial animation data.
    Maintains full frame state and handles interpolation.
    """
    
    def __init__(self, interpolation_enabled: bool = True):
        """
        Initialize delta decompressor.
        
        Args:
            interpolation_enabled: Enable frame interpolation
        """
        self.interpolation_enabled = interpolation_enabled
        self.current_frame: Dict[str, float] = {}
        self.target_frame: Dict[str, float] = {}
        self.morph_predictions: Dict[str, Dict] = {}
        self.last_timestamp = 0.0
        self.interpolation_alpha = 0.0
    
    def decompress_batch(self, data: bytes) -> List[Dict]:
        """
        Decompress a batch of frames.
        
        Args:
            data: Compressed binary data
            
        Returns:
            List of decompressed frame dictionaries
        """
        batch_data = msgpack.unpackb(data, raw=False)
        frames = []
        
        for frame_data in batch_data['frames']:
            frame = self.decompress_frame(frame_data)
            frames.append(frame)
        
        return frames
    
    def decompress_frame(self, frame_data: Dict) -> Dict:
        """
        Decompress a single frame.
        
        Args:
            frame_data: Compressed frame data
            
        Returns:
            Full frame with all morph values
        """
        is_keyframe = frame_data['type'] == 'keyframe'
        timestamp = frame_data['timestamp']
        morphs = frame_data['morphs']
        
        if is_keyframe:
            # Replace entire frame
            self.current_frame = morphs.copy()
            # Set missing morphs to 0
            for morph in list(self.current_frame.keys()):
                if morph not in morphs:
                    self.current_frame[morph] = 0.0
        else:
            # Apply deltas
            for morph, value in morphs.items():
                self.current_frame[morph] = value
        
        # Update predictions if available
        if 'predictions' in frame_data:
            self.morph_predictions = frame_data['predictions']
        
        # Set target for interpolation
        if self.interpolation_enabled:
            self.target_frame = self.current_frame.copy()
            self.interpolation_alpha = 0.0
        
        self.last_timestamp = timestamp
        
        return {
            'timestamp': timestamp,
            'frame': frame_data['frame'],
            'morphs': self.current_frame.copy(),
            'predictions': self.morph_predictions.copy() if self.morph_predictions else None
        }
    
    def interpolate_frame(self, current_time: float, target_fps: float = 30.0) -> Dict[str, float]:
        """
        Get interpolated frame for smooth animation.
        
        Args:
            current_time: Current time in seconds
            target_fps: Target frame rate for interpolation
            
        Returns:
            Interpolated morph values
        """
        if not self.interpolation_enabled:
            return self.current_frame.copy()
        
        # Calculate interpolation progress
        frame_duration = 1.0 / target_fps
        time_since_update = current_time - self.last_timestamp
        self.interpolation_alpha = min(time_since_update / frame_duration, 1.0)
        
        # Interpolate morphs
        interpolated = {}
        
        for morph, target_value in self.target_frame.items():
            current_value = self.current_frame.get(morph, 0.0)
            
            # Check for prediction data
            if morph in self.morph_predictions and self.interpolation_alpha < 1.0:
                # Use prediction for smoother motion
                prediction = self.morph_predictions[morph]
                velocity = prediction.get('v', 0.0)
                acceleration = prediction.get('a', 0.0)
                
                # Simple physics-based prediction
                predicted_value = current_value + velocity * self.interpolation_alpha
                predicted_value += 0.5 * acceleration * self.interpolation_alpha ** 2
                
                # Blend between linear and predicted
                interpolated[morph] = self._smooth_interpolate(
                    current_value, target_value, predicted_value, self.interpolation_alpha
                )
            else:
                # Linear interpolation
                interpolated[morph] = self._lerp(current_value, target_value, self.interpolation_alpha)
        
        return interpolated
    
    def _lerp(self, a: float, b: float, t: float) -> float:
        """Linear interpolation"""
        return a + (b - a) * t
    
    def _smooth_interpolate(self, current: float, target: float, predicted: float, t: float) -> float:
        """Smooth interpolation with prediction blending"""
        # Cubic ease-in-out
        t2 = t * t
        t3 = t2 * t
        smooth_t = 3 * t2 - 2 * t3
        
        # Blend linear and predicted based on confidence
        linear = self._lerp(current, target, smooth_t)
        
        # Weight prediction less as we approach target
        prediction_weight = (1.0 - t) * 0.5
        return linear * (1.0 - prediction_weight) + predicted * prediction_weight