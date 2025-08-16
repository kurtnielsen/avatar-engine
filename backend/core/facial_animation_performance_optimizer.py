"""
Facial Animation Performance Optimizer
Ensures real-time performance with LOD system, frame skipping, and optimized calculations
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from collections import deque
import time
import threading
from dataclasses import dataclass, field


@dataclass
class PerformanceMetrics:
    """Track performance metrics for optimization decisions"""
    frame_times: deque = field(default_factory=lambda: deque(maxlen=60))
    morph_update_times: deque = field(default_factory=lambda: deque(maxlen=60))
    active_morph_count: deque = field(default_factory=lambda: deque(maxlen=30))
    fps: float = 60.0
    avg_frame_time: float = 0.0
    avg_morph_time: float = 0.0
    
    def update_fps(self):
        if len(self.frame_times) > 1:
            self.fps = len(self.frame_times) / sum(self.frame_times)
            self.avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        if self.morph_update_times:
            self.avg_morph_time = sum(self.morph_update_times) / len(self.morph_update_times)


class MorphLODSystem:
    """Level of Detail system for morph targets"""
    
    def __init__(self):
        # Define morph importance levels
        self.morph_priorities = {
            # Critical for speech (Priority 1)
            'V_AA': 1, 'V_EE': 1, 'V_OH': 1, 'V_U': 1,
            'V_Open': 1, 'V_Explosive': 1, 'V_FF': 1,
            'V_DD': 1, 'V_SS': 1, 'V_CH': 1,
            
            # Important expressions (Priority 2)
            'Mouth_Smile_L': 2, 'Mouth_Smile_R': 2,
            'Mouth_Frown_L': 2, 'Mouth_Frown_R': 2,
            'Eye_Blink_L': 2, 'Eye_Blink_R': 2,
            'Brow_Raise_L': 2, 'Brow_Raise_R': 2,
            'Brow_Drop_L': 2, 'Brow_Drop_R': 2,
            
            # Secondary movements (Priority 3)
            'Eye_Squint_L': 3, 'Eye_Squint_R': 3,
            'Cheek_Squint_L': 3, 'Cheek_Squint_R': 3,
            'Nose_Sneer_L': 3, 'Nose_Sneer_R': 3,
            'Mouth_Press_L': 3, 'Mouth_Press_R': 3,
            
            # Detail movements (Priority 4)
            'Mouth_Dimple_L': 4, 'Mouth_Dimple_R': 4,
            'Mouth_Upper_Up_L': 4, 'Mouth_Upper_Up_R': 4,
            'Mouth_Lower_Down_L': 4, 'Mouth_Lower_Down_R': 4,
            'Eye_Look_Up_L': 4, 'Eye_Look_Up_R': 4,
            'Eye_Look_Down_L': 4, 'Eye_Look_Down_R': 4,
        }
        
        # LOD thresholds based on FPS
        self.lod_thresholds = {
            'high': 60,      # All morphs
            'medium': 45,    # Priority 1-3
            'low': 30,       # Priority 1-2
            'minimal': 20    # Priority 1 only
        }
    
    def get_allowed_morphs(self, current_fps: float) -> Set[str]:
        """Get set of allowed morphs based on current performance"""
        if current_fps >= self.lod_thresholds['high']:
            max_priority = 4
        elif current_fps >= self.lod_thresholds['medium']:
            max_priority = 3
        elif current_fps >= self.lod_thresholds['low']:
            max_priority = 2
        else:
            max_priority = 1
        
        return {
            morph for morph, priority in self.morph_priorities.items()
            if priority <= max_priority
        }
    
    def filter_morphs(self, morphs: Dict[str, float], current_fps: float) -> Dict[str, float]:
        """Filter morphs based on LOD level"""
        allowed = self.get_allowed_morphs(current_fps)
        
        # Always include morphs not in our priority list (custom morphs)
        filtered = {}
        for morph, value in morphs.items():
            if morph in allowed or morph not in self.morph_priorities:
                filtered[morph] = value
        
        return filtered


class MorphDeltaCompression:
    """Compress morph updates by only sending deltas"""
    
    def __init__(self, threshold: float = 0.01):
        self.previous_state = {}
        self.threshold = threshold
        self.force_update_counter = 0
        self.force_update_interval = 60  # Force full update every 60 frames
    
    def get_delta(self, current_morphs: Dict[str, float], 
                  force_update: bool = False) -> Tuple[Dict[str, float], bool]:
        """
        Get delta between current and previous state
        
        Returns:
            Tuple of (delta_morphs, is_full_update)
        """
        self.force_update_counter += 1
        
        # Force periodic full updates to prevent drift
        if force_update or self.force_update_counter >= self.force_update_interval:
            self.force_update_counter = 0
            self.previous_state = current_morphs.copy()
            return current_morphs, True
        
        delta = {}
        
        # Find changed morphs
        all_morphs = set(current_morphs.keys()) | set(self.previous_state.keys())
        
        for morph in all_morphs:
            current_val = current_morphs.get(morph, 0.0)
            previous_val = self.previous_state.get(morph, 0.0)
            
            # Only include if change is significant
            if abs(current_val - previous_val) > self.threshold:
                delta[morph] = current_val
                self.previous_state[morph] = current_val
            elif current_val == 0.0 and previous_val != 0.0:
                # Always send zero values to clear morphs
                delta[morph] = 0.0
                self.previous_state[morph] = 0.0
        
        return delta, False


class FrameRateController:
    """Control animation frame rate based on performance"""
    
    def __init__(self, target_fps: float = 60.0):
        self.target_fps = target_fps
        self.target_frame_time = 1.0 / target_fps
        self.last_frame_time = time.time()
        self.frame_skip_threshold = 1.5  # Skip if behind by 1.5 frames
        self.adaptive_quality = True
    
    def should_update(self) -> Tuple[bool, float]:
        """
        Determine if we should update this frame
        
        Returns:
            Tuple of (should_update, time_delta)
        """
        current_time = time.time()
        time_delta = current_time - self.last_frame_time
        
        # Always update if enough time has passed
        if time_delta >= self.target_frame_time:
            self.last_frame_time = current_time
            return True, time_delta
        
        return False, time_delta
    
    def should_skip_frame(self, processing_time: float) -> bool:
        """Determine if we should skip the next frame to catch up"""
        return processing_time > self.target_frame_time * self.frame_skip_threshold


class OptimizedMorphCache:
    """Cache frequently used morph combinations"""
    
    def __init__(self, cache_size: int = 100):
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.max_size = cache_size
        self.access_count = {}
    
    def get_cache_key(self, morphs: Dict[str, float]) -> str:
        """Generate cache key from morph combination"""
        # Round values to reduce key variations
        rounded = {k: round(v, 2) for k, v in sorted(morphs.items())}
        return str(hash(tuple(rounded.items())))
    
    def get(self, key: str) -> Optional[Dict[str, float]]:
        """Get cached morph combination"""
        if key in self.cache:
            self.cache_hits += 1
            self.access_count[key] = self.access_count.get(key, 0) + 1
            return self.cache[key].copy()
        
        self.cache_misses += 1
        return None
    
    def put(self, key: str, morphs: Dict[str, float]):
        """Cache morph combination"""
        if len(self.cache) >= self.max_size:
            # Remove least accessed item
            if self.access_count:
                least_used = min(self.access_count.items(), key=lambda x: x[1])[0]
                if least_used in self.cache:
                    del self.cache[least_used]
                    del self.access_count[least_used]
        
        self.cache[key] = morphs.copy()
        self.access_count[key] = 1
    
    @property
    def hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


class FacialAnimationPerformanceOptimizer:
    """Main performance optimization controller"""
    
    def __init__(self, target_fps: float = 60.0):
        self.metrics = PerformanceMetrics()
        self.lod_system = MorphLODSystem()
        self.delta_compression = MorphDeltaCompression()
        self.frame_controller = FrameRateController(target_fps)
        self.morph_cache = OptimizedMorphCache()
        
        # Optimization settings
        self.enable_lod = True
        self.enable_compression = True
        self.enable_caching = True
        self.enable_frame_skipping = True
        
        # Performance thresholds
        self.critical_fps = 20.0
        self.warning_fps = 45.0
        
        # Morph batching
        self.morph_batch = []
        self.batch_size = 5
        self.batch_timeout = 0.016  # 16ms
        self.last_batch_time = time.time()
    
    def optimize_morphs(self, raw_morphs: Dict[str, float]) -> Dict[str, float]:
        """Apply all optimizations to morph data"""
        start_time = time.time()
        
        # Step 1: Check cache
        if self.enable_caching:
            cache_key = self.morph_cache.get_cache_key(raw_morphs)
            cached = self.morph_cache.get(cache_key)
            if cached is not None:
                return cached
        
        # Step 2: Apply LOD filtering
        if self.enable_lod:
            morphs = self.lod_system.filter_morphs(raw_morphs, self.metrics.fps)
        else:
            morphs = raw_morphs.copy()
        
        # Step 3: Remove very small values
        morphs = {k: v for k, v in morphs.items() if abs(v) > 0.005}
        
        # Step 4: Cache result
        if self.enable_caching and cache_key:
            self.morph_cache.put(cache_key, morphs)
        
        # Track performance
        self.metrics.morph_update_times.append(time.time() - start_time)
        self.metrics.active_morph_count.append(len(morphs))
        
        return morphs
    
    def process_frame(self, morphs: Dict[str, float]) -> Optional[Dict[str, float]]:
        """Process a single animation frame with all optimizations"""
        frame_start = time.time()
        
        # Check if we should update this frame
        should_update, time_delta = self.frame_controller.should_update()
        if not should_update and self.enable_frame_skipping:
            return None
        
        # Optimize morphs
        optimized = self.optimize_morphs(morphs)
        
        # Apply delta compression
        if self.enable_compression:
            delta, is_full_update = self.delta_compression.get_delta(optimized)
            result = delta
        else:
            result = optimized
        
        # Track frame time
        frame_time = time.time() - frame_start
        self.metrics.frame_times.append(frame_time)
        
        # Update metrics
        self.metrics.update_fps()
        
        # Check performance warnings
        if self.metrics.fps < self.critical_fps:
            self._handle_critical_performance()
        elif self.metrics.fps < self.warning_fps:
            self._handle_performance_warning()
        
        return result
    
    def batch_morphs(self, morphs: Dict[str, float]) -> Optional[List[Dict[str, float]]]:
        """Batch multiple morph updates for network efficiency"""
        self.morph_batch.append(morphs)
        
        current_time = time.time()
        time_since_last = current_time - self.last_batch_time
        
        # Send batch if size limit reached or timeout
        if len(self.morph_batch) >= self.batch_size or time_since_last > self.batch_timeout:
            batch = self.morph_batch
            self.morph_batch = []
            self.last_batch_time = current_time
            return batch
        
        return None
    
    def _handle_critical_performance(self):
        """Handle critical performance issues"""
        # Enable all optimizations
        self.enable_lod = True
        self.enable_compression = True
        self.enable_frame_skipping = True
        
        # Reduce quality further
        self.delta_compression.threshold = 0.02  # Increase threshold
        
        print(f"CRITICAL: FPS dropped to {self.metrics.fps:.1f}")
    
    def _handle_performance_warning(self):
        """Handle performance warnings"""
        # Enable medium optimizations
        self.enable_lod = True
        self.enable_compression = True
        
        print(f"WARNING: FPS at {self.metrics.fps:.1f}")
    
    def get_performance_report(self) -> Dict:
        """Get detailed performance report"""
        return {
            'fps': self.metrics.fps,
            'avg_frame_time_ms': self.metrics.avg_frame_time * 1000,
            'avg_morph_time_ms': self.metrics.avg_morph_time * 1000,
            'avg_active_morphs': np.mean(list(self.metrics.active_morph_count)) if self.metrics.active_morph_count else 0,
            'cache_hit_rate': self.morph_cache.hit_rate,
            'lod_enabled': self.enable_lod,
            'compression_enabled': self.enable_compression,
            'current_lod_level': self._get_current_lod_level()
        }
    
    def _get_current_lod_level(self) -> str:
        """Get current LOD level based on FPS"""
        fps = self.metrics.fps
        if fps >= 60:
            return 'high'
        elif fps >= 45:
            return 'medium'
        elif fps >= 30:
            return 'low'
        else:
            return 'minimal'


# Example usage
if __name__ == "__main__":
    import random
    
    # Create optimizer
    optimizer = FacialAnimationPerformanceOptimizer(target_fps=60.0)
    
    # Simulate animation loop
    print("Running performance test...")
    
    for frame in range(300):  # 5 seconds at 60 FPS
        # Generate random morph data
        morphs = {
            'V_AA': random.random() * 0.8,
            'V_Open': random.random() * 0.5,
            'Mouth_Smile_L': random.random() * 0.6,
            'Mouth_Smile_R': random.random() * 0.6,
            'Eye_Blink_L': random.random() * 0.1,
            'Eye_Blink_R': random.random() * 0.1,
            'Brow_Raise_L': random.random() * 0.3,
            'Brow_Raise_R': random.random() * 0.3,
            'Cheek_Squint_L': random.random() * 0.2,
            'Cheek_Squint_R': random.random() * 0.2,
        }
        
        # Add some expensive morphs occasionally
        if frame % 10 == 0:
            for i in range(20):
                morphs[f'Detail_Morph_{i}'] = random.random() * 0.1
        
        # Process frame
        result = optimizer.process_frame(morphs)
        
        # Simulate processing time
        time.sleep(0.01 + random.random() * 0.01)  # 10-20ms
        
        # Print performance every second
        if frame % 60 == 0 and frame > 0:
            report = optimizer.get_performance_report()
            print(f"\nFrame {frame}:")
            print(f"  FPS: {report['fps']:.1f}")
            print(f"  Frame time: {report['avg_frame_time_ms']:.2f}ms")
            print(f"  Active morphs: {report['avg_active_morphs']:.1f}")
            print(f"  Cache hit rate: {report['cache_hit_rate']:.2%}")
            print(f"  LOD level: {report['current_lod_level']}")
    
    # Final report
    print("\n=== Final Performance Report ===")
    final_report = optimizer.get_performance_report()
    for key, value in final_report.items():
        print(f"{key}: {value}")