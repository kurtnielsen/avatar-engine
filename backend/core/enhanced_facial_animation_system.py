"""
Enhanced Facial Animation System
Integrates all components for production-ready facial animation
"""

import asyncio
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time

from facial_animation_mapper_enhanced import FacialAnimationMapperEnhanced
from viseme_transition_engine import VisemeTransitionEngine
from facial_animation_performance_optimizer import FacialAnimationPerformanceOptimizer


@dataclass
class AnimationConfig:
    """Configuration for the animation system"""
    enable_emotions: bool = True
    enable_micro_expressions: bool = True
    enable_natural_movements: bool = True
    enable_performance_optimization: bool = True
    target_fps: int = 60
    smoothing_window: int = 5
    blend_speed: float = 0.15
    emotion_intensity: float = 0.5
    websocket_host: str = "localhost"
    websocket_port: int = 8765


class EnhancedFacialAnimationSystem:
    """Complete facial animation system with all enhancements"""
    
    def __init__(self, config: AnimationConfig = None):
        self.config = config or AnimationConfig()
        
        # Initialize components
        self.mapper = FacialAnimationMapperEnhanced(
            smoothing_window=self.config.smoothing_window,
            blend_speed=self.config.blend_speed
        )
        self.viseme_engine = VisemeTransitionEngine()
        self.optimizer = FacialAnimationPerformanceOptimizer(
            target_fps=self.config.target_fps
        )
        
        # State management
        self.current_emotion = "neutral"
        self.emotion_intensity = self.config.emotion_intensity
        self.is_speaking = False
        self.animation_queue = asyncio.Queue()
        self.websocket_clients = set()
        
        # Performance tracking
        self.frame_count = 0
        self.start_time = time.time()
    
    async def process_arkit_data(self, arkit_data: Dict[str, float]) -> Dict[str, float]:
        """Process ARKit data with all enhancements"""
        # Apply enhanced mapping
        morphs = self.mapper.map_arkit_to_cc4_enhanced(
            arkit_data,
            emotion=self.current_emotion,
            emotion_intensity=self.emotion_intensity,
            add_micro_expressions=self.config.enable_micro_expressions,
            add_natural_movements=self.config.enable_natural_movements
        )
        
        # Apply performance optimization
        if self.config.enable_performance_optimization:
            morphs = self.optimizer.process_frame(morphs)
            if morphs is None:  # Frame skipped
                return {}
        
        return morphs
    
    async def process_phoneme_sequence(self, phoneme_data: List[Dict]) -> List[Dict[str, float]]:
        """Process phoneme sequence for speech animation"""
        self.is_speaking = True
        
        # Add viseme information to phoneme data
        enhanced_phonemes = []
        for i, phoneme_info in enumerate(phoneme_data):
            phoneme = phoneme_info['phoneme']
            
            # Get viseme mapping
            viseme_morphs = self.mapper.map_phoneme_to_viseme_enhanced(
                phoneme,
                phoneme_info.get('intensity', 1.0),
                context=(
                    phoneme_data[i-1]['phoneme'] if i > 0 else None,
                    phoneme_data[i+1]['phoneme'] if i < len(phoneme_data)-1 else None
                )
            )
            
            # Find primary viseme
            primary_viseme = max(viseme_morphs.items(), key=lambda x: x[1])[0] if viseme_morphs else 'V_None'
            
            enhanced_phonemes.append({
                'phoneme': phoneme,
                'viseme': primary_viseme,
                'duration': phoneme_info.get('duration', 0.1),
                'timestamp': phoneme_info.get('timestamp', i * 0.1),
                'word_position': phoneme_info.get('word_position'),
                'morphs': viseme_morphs
            })
        
        # Process with transition engine
        smooth_frames = self.viseme_engine.process_phoneme_sequence(
            enhanced_phonemes,
            stress_pattern=phoneme_data[0].get('stress_pattern') if phoneme_data else None
        )
        
        # Add emotion overlay to speech
        if self.config.enable_emotions and self.current_emotion != 'neutral':
            emotion_frames = []
            for frame in smooth_frames:
                emotion_frame = self.mapper.apply_emotion_layer(
                    frame,
                    {self.current_emotion: self.emotion_intensity}
                )
                emotion_frames.append(emotion_frame)
            smooth_frames = emotion_frames
        
        # Optimize each frame
        if self.config.enable_performance_optimization:
            optimized_frames = []
            for frame in smooth_frames:
                opt_frame = self.optimizer.process_frame(frame)
                if opt_frame is not None:  # Skip None frames
                    optimized_frames.append(opt_frame)
            smooth_frames = optimized_frames
        
        self.is_speaking = False
        return smooth_frames
    
    async def set_emotion(self, emotion: str, intensity: float = None, 
                         transition_time: float = 1.0):
        """Set current emotion with optional transition"""
        if emotion not in self.mapper.emotion_presets:
            print(f"Warning: Unknown emotion '{emotion}', using 'neutral'")
            emotion = 'neutral'
        
        self.current_emotion = emotion
        if intensity is not None:
            self.emotion_intensity = max(0.0, min(1.0, intensity))
        
        # Trigger appropriate micro-expressions
        if self.config.enable_micro_expressions:
            if emotion == 'happy':
                self.mapper.trigger_micro_expression('subtle_smile')
            elif emotion == 'surprised':
                self.mapper.trigger_micro_expression('eye_flash')
            elif emotion == 'angry':
                self.mapper.trigger_micro_expression('lip_tighten')
    
    async def trigger_micro_expression(self, expression_type: str):
        """Manually trigger a micro-expression"""
        if self.config.enable_micro_expressions:
            self.mapper.trigger_micro_expression(expression_type)
    
    async def get_performance_metrics(self) -> Dict:
        """Get current performance metrics"""
        metrics = self.optimizer.get_performance_report()
        
        # Add system-wide metrics
        uptime = time.time() - self.start_time
        metrics['uptime_seconds'] = uptime
        metrics['total_frames'] = self.frame_count
        metrics['average_fps'] = self.frame_count / uptime if uptime > 0 else 0
        metrics['is_speaking'] = self.is_speaking
        metrics['current_emotion'] = self.current_emotion
        metrics['websocket_clients'] = len(self.websocket_clients)
        
        return metrics
    
    async def broadcast_morphs(self, morphs: Dict[str, float]):
        """Broadcast morph data to all connected clients"""
        if not self.websocket_clients or not morphs:
            return
        
        message = json.dumps({
            'type': 'blendshape_update',
            'data': morphs,
            'timestamp': time.time(),
            'frame': self.frame_count,
            'emotion': self.current_emotion,
            'is_speaking': self.is_speaking
        })
        
        # Send to all clients
        disconnected = set()
        for client in self.websocket_clients:
            try:
                await client.send(message)
            except Exception:
                disconnected.add(client)
        
        # Remove disconnected clients
        self.websocket_clients -= disconnected
        
        self.frame_count += 1
    
    async def process_udp_stream(self, udp_data: bytes) -> Dict[str, float]:
        """Process incoming UDP data (ARKit or viseme)"""
        try:
            data = json.loads(udp_data.decode('utf-8'))
            
            # Determine data type
            if 'blendShapes' in data:
                # ARKit data
                return await self.process_arkit_data(data['blendShapes'])
            elif 'viseme' in data or 'phoneme' in data:
                # Single viseme/phoneme
                viseme_morphs = self.mapper.map_viseme_stream(data)
                
                # Apply emotion and optimization
                if self.config.enable_emotions:
                    viseme_morphs = self.mapper.apply_emotion_layer(
                        viseme_morphs,
                        {self.current_emotion: self.emotion_intensity}
                    )
                
                if self.config.enable_performance_optimization:
                    viseme_morphs = self.optimizer.process_frame(viseme_morphs)
                
                return viseme_morphs or {}
            elif 'phoneme_sequence' in data:
                # Full phoneme sequence
                frames = await self.process_phoneme_sequence(data['phoneme_sequence'])
                # Queue frames for playback
                for frame in frames:
                    await self.animation_queue.put(frame)
                return frames[0] if frames else {}
            
        except Exception as e:
            print(f"Error processing UDP data: {e}")
            return {}
    
    async def animation_playback_loop(self):
        """Main animation playback loop"""
        while True:
            try:
                # Get next frame from queue or generate idle animation
                if not self.animation_queue.empty():
                    morphs = await self.animation_queue.get()
                else:
                    # Generate idle animation when not speaking
                    if not self.is_speaking:
                        # Just natural movements and current emotion
                        morphs = await self.process_arkit_data({})
                    else:
                        morphs = {}
                
                # Broadcast to clients
                if morphs:
                    await self.broadcast_morphs(morphs)
                
                # Control frame rate
                await asyncio.sleep(1.0 / self.config.target_fps)
                
            except Exception as e:
                print(f"Error in animation loop: {e}")
                await asyncio.sleep(0.1)
    
    def generate_test_animation(self) -> List[Dict[str, float]]:
        """Generate a test animation sequence"""
        # Test speech
        test_phonemes = [
            {'phoneme': 'HH', 'duration': 0.08, 'timestamp': 0.0},
            {'phoneme': 'EH', 'duration': 0.12, 'timestamp': 0.08},
            {'phoneme': 'L', 'duration': 0.10, 'timestamp': 0.20},
            {'phoneme': 'OW', 'duration': 0.15, 'timestamp': 0.30},
        ]
        
        # Process with happy emotion
        self.current_emotion = 'happy'
        frames = asyncio.run(self.process_phoneme_sequence(test_phonemes))
        
        return frames


# WebSocket handler
async def websocket_handler(websocket, path, animation_system):
    """Handle WebSocket connections"""
    animation_system.websocket_clients.add(websocket)
    try:
        async for message in websocket:
            # Handle incoming messages (commands, etc.)
            try:
                data = json.loads(message)
                
                if data['type'] == 'set_emotion':
                    await animation_system.set_emotion(
                        data['emotion'],
                        data.get('intensity', 0.5)
                    )
                elif data['type'] == 'trigger_micro':
                    await animation_system.trigger_micro_expression(
                        data['expression']
                    )
                elif data['type'] == 'get_metrics':
                    metrics = await animation_system.get_performance_metrics()
                    await websocket.send(json.dumps({
                        'type': 'metrics',
                        'data': metrics
                    }))
                
            except json.JSONDecodeError:
                pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        animation_system.websocket_clients.remove(websocket)


# Example usage
if __name__ == "__main__":
    import websockets
    
    # Create animation system
    config = AnimationConfig(
        enable_emotions=True,
        enable_micro_expressions=True,
        enable_natural_movements=True,
        enable_performance_optimization=True,
        target_fps=60
    )
    
    animation_system = EnhancedFacialAnimationSystem(config)
    
    print("Enhanced Facial Animation System")
    print("================================")
    
    # Test basic functionality
    print("\n1. Testing ARKit mapping with emotion:")
    test_arkit = {
        'jawOpen': 0.3,
        'mouthSmileLeft': 0.5,
        'mouthSmileRight': 0.5,
    }
    
    async def test():
        await animation_system.set_emotion('happy', 0.6)
        result = await animation_system.process_arkit_data(test_arkit)
        print(f"Active morphs: {len(result)}")
        for morph, value in sorted(result.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {morph}: {value:.3f}")
        
        print("\n2. Testing speech animation:")
        frames = animation_system.generate_test_animation()
        print(f"Generated {len(frames)} frames")
        
        print("\n3. Performance metrics:")
        metrics = await animation_system.get_performance_metrics()
        print(f"  Target FPS: {config.target_fps}")
        print(f"  Current FPS: {metrics['fps']:.1f}")
        print(f"  Cache hit rate: {metrics['cache_hit_rate']:.2%}")
    
    # Run test
    asyncio.run(test())
    
    print("\n4. Starting WebSocket server...")
    print("Connect Three.js client to ws://localhost:8765")
    
    # Start WebSocket server
    async def main():
        # Start animation playback loop
        asyncio.create_task(animation_system.animation_playback_loop())
        
        # Start WebSocket server
        async with websockets.serve(
            lambda ws, path: websocket_handler(ws, path, animation_system),
            config.websocket_host,
            config.websocket_port
        ):
            print(f"WebSocket server running on {config.websocket_host}:{config.websocket_port}")
            await asyncio.Future()  # Run forever
    
    # Uncomment to run server
    # asyncio.run(main())