"""
Viseme Transition Engine for Natural Speech Animation
Handles smooth transitions between visemes with co-articulation and timing
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math


@dataclass
class VisemeFrame:
    """Represents a single frame of viseme animation"""
    viseme: str
    morphs: Dict[str, float]
    duration: float
    timestamp: float
    phoneme: Optional[str] = None
    word_position: Optional[str] = None  # 'start', 'middle', 'end'


class VisemeTransitionEngine:
    def __init__(self):
        # Define viseme categories for transition rules
        self.viseme_categories = {
            'bilabial': ['V_Explosive', 'V_M'],  # B, P, M
            'labiodental': ['V_FF', 'V_V'],       # F, V
            'dental': ['V_TH', 'V_Dental_Lip'],   # TH
            'alveolar': ['V_DD', 'V_NN', 'V_L', 'V_SS'],  # D, T, N, L, S, Z
            'postalveolar': ['V_CH', 'V_SH'],     # CH, SH, ZH
            'velar': ['V_KK', 'V_G'],             # K, G
            'glottal': ['V_H'],                   # H
            'rounded': ['V_U', 'V_OH', 'V_Narrow'],  # U, O, W
            'spread': ['V_EE', 'V_Wide'],         # EE, I
            'open': ['V_AA', 'V_Open'],           # AA, A
            'mid': ['V_EH', 'V_ER', 'V_IH'],     # E, ER
            'closed': ['V_None', 'V_Tight']       # Closed mouth
        }
        
        # Inverse mapping for quick lookup
        self.viseme_to_category = {}
        for category, visemes in self.viseme_categories.items():
            for viseme in visemes:
                self.viseme_to_category[viseme] = category
        
        # Transition timing modifiers based on viseme pairs
        self.transition_timing = {
            # Same category transitions are faster
            ('bilabial', 'bilabial'): 0.7,
            ('alveolar', 'alveolar'): 0.8,
            ('rounded', 'rounded'): 0.85,
            
            # Opposing transitions are slower
            ('spread', 'rounded'): 1.3,
            ('rounded', 'spread'): 1.3,
            ('open', 'closed'): 1.2,
            ('closed', 'open'): 1.1,
            
            # Special cases
            ('bilabial', 'open'): 0.9,      # B→A common transition
            ('alveolar', 'rounded'): 1.1,   # T→U needs time
            ('dental', 'any'): 1.2,         # TH transitions are slower
        }
        
        # Coarticulation influence weights
        self.coarticulation_weights = {
            'anticipatory': 0.25,  # Influence of next phoneme
            'carryover': 0.35,     # Influence of previous phoneme
            'target': 0.40         # Weight of current phoneme
        }
        
        # Mouth opening curves for different viseme types
        self.opening_curves = {
            'explosive': lambda t: 1.0 - math.exp(-5 * t),  # Quick opening
            'fricative': lambda t: t ** 0.7,                # Gradual opening
            'vowel': lambda t: math.sin(t * math.pi / 2),   # Smooth arc
            'closing': lambda t: 1.0 - t ** 2               # Quick close
        }
        
        # Additional shape modifiers for realism
        self.secondary_shapes = {
            'V_Explosive': {
                'Cheek_Puff': 0.15,      # Slight cheek puff for plosives
                'Mouth_Press_L': 0.1,
                'Mouth_Press_R': 0.1
            },
            'V_FF': {
                'Mouth_Lower_Down_L': 0.2,  # Lower lip tuck for F/V
                'Mouth_Lower_Down_R': 0.2
            },
            'V_EE': {
                'Mouth_Stretch_L': 0.3,     # Mouth corners stretch for EE
                'Mouth_Stretch_R': 0.3,
                'V_Wide': 0.2
            },
            'V_U': {
                'Mouth_Pucker_L': 0.2,      # Extra pucker for U sounds
                'Mouth_Pucker_R': 0.2,
                'V_Narrow': 0.3
            },
            'V_OH': {
                'Jaw_Forward': 0.1,         # Slight jaw forward for O
                'V_Round': 0.2
            }
        }
        
        # Stress and emphasis modifiers
        self.stress_modifiers = {
            'primary_stress': 1.2,    # 20% stronger articulation
            'secondary_stress': 1.1,  # 10% stronger
            'unstressed': 0.85,       # 15% weaker
            'reduced': 0.6           # 40% reduction (schwa-like)
        }
    
    def get_transition_curve(self, from_viseme: str, to_viseme: str, 
                           duration: float) -> List[float]:
        """Generate transition curve between two visemes"""
        from_cat = self.viseme_to_category.get(from_viseme, 'any')
        to_cat = self.viseme_to_category.get(to_viseme, 'any')
        
        # Get timing modifier
        timing_key = (from_cat, to_cat)
        if timing_key not in self.transition_timing:
            timing_key = (to_cat, from_cat)  # Try reverse
        
        timing_mod = self.transition_timing.get(timing_key, 1.0)
        
        # Generate curve points
        num_points = max(int(duration * 60), 10)  # 60 fps or minimum 10 points
        curve = []
        
        for i in range(num_points):
            t = i / (num_points - 1)
            
            # Apply different curves based on transition type
            if from_cat == 'closed' and to_cat in ['open', 'rounded']:
                # Opening movement
                value = self.opening_curves['vowel'](t)
            elif from_cat in ['open', 'rounded'] and to_cat == 'closed':
                # Closing movement
                value = self.opening_curves['closing'](t)
            elif from_cat == 'bilabial' or to_cat == 'bilabial':
                # Explosive movements
                value = self.opening_curves['explosive'](t)
            else:
                # Default S-curve
                value = 0.5 * (1 + math.tanh(6 * (t - 0.5)))
            
            # Apply timing modifier
            adjusted_t = min(1.0, t * timing_mod)
            curve.append(value if t == adjusted_t else value * (adjusted_t / t))
        
        return curve
    
    def apply_coarticulation(self, prev_frame: Optional[VisemeFrame],
                           current_frame: VisemeFrame,
                           next_frame: Optional[VisemeFrame]) -> Dict[str, float]:
        """Apply coarticulation effects based on surrounding phonemes"""
        result_morphs = current_frame.morphs.copy()
        
        weights = self.coarticulation_weights
        
        # Carryover from previous phoneme
        if prev_frame and prev_frame.morphs:
            for morph, value in prev_frame.morphs.items():
                if morph in result_morphs:
                    result_morphs[morph] = (
                        result_morphs[morph] * (1 - weights['carryover']) +
                        value * weights['carryover']
                    )
                else:
                    result_morphs[morph] = value * weights['carryover'] * 0.5
        
        # Anticipatory coarticulation from next phoneme
        if next_frame and next_frame.morphs:
            for morph, value in next_frame.morphs.items():
                if morph in result_morphs:
                    result_morphs[morph] = (
                        result_morphs[morph] * (1 - weights['anticipatory']) +
                        value * weights['anticipatory']
                    )
                else:
                    result_morphs[morph] = value * weights['anticipatory'] * 0.3
        
        return result_morphs
    
    def add_secondary_shapes(self, viseme: str, morphs: Dict[str, float]) -> Dict[str, float]:
        """Add secondary shape animations for more realistic movement"""
        if viseme in self.secondary_shapes:
            for shape, value in self.secondary_shapes[viseme].items():
                morphs[shape] = morphs.get(shape, 0) + value
        
        return morphs
    
    def apply_word_position_effects(self, frame: VisemeFrame) -> Dict[str, float]:
        """Modify viseme based on position in word"""
        morphs = frame.morphs.copy()
        
        if frame.word_position == 'start':
            # Stronger articulation at word start
            for morph in morphs:
                morphs[morph] *= 1.15
        elif frame.word_position == 'end':
            # Potential reduction at word end
            for morph in morphs:
                morphs[morph] *= 0.9
            # Add slight closing tendency
            morphs['V_None'] = morphs.get('V_None', 0) + 0.1
        
        return morphs
    
    def interpolate_frames(self, frames: List[VisemeFrame], 
                         target_fps: int = 60) -> List[Dict[str, float]]:
        """Interpolate between viseme frames to create smooth animation"""
        if not frames:
            return []
        
        interpolated = []
        
        for i in range(len(frames) - 1):
            current = frames[i]
            next_frame = frames[i + 1]
            
            # Calculate number of interpolation steps
            duration = next_frame.timestamp - current.timestamp
            num_steps = max(int(duration * target_fps), 1)
            
            # Get transition curve
            curve = self.get_transition_curve(
                current.viseme, 
                next_frame.viseme, 
                duration
            )
            
            # Resample curve to match steps
            if len(curve) != num_steps:
                curve = np.interp(
                    np.linspace(0, len(curve) - 1, num_steps),
                    range(len(curve)),
                    curve
                ).tolist()
            
            # Interpolate morphs
            for step in range(num_steps):
                t = curve[step]
                interpolated_morphs = {}
                
                # Get all morph names
                all_morphs = set(current.morphs.keys()) | set(next_frame.morphs.keys())
                
                for morph in all_morphs:
                    current_val = current.morphs.get(morph, 0)
                    next_val = next_frame.morphs.get(morph, 0)
                    
                    # Apply curve-based interpolation
                    interpolated_morphs[morph] = current_val + (next_val - current_val) * t
                
                interpolated.append(interpolated_morphs)
        
        # Add final frame
        if frames:
            interpolated.append(frames[-1].morphs)
        
        return interpolated
    
    def process_phoneme_sequence(self, phoneme_data: List[Dict],
                               stress_pattern: Optional[List[str]] = None) -> List[Dict[str, float]]:
        """
        Process a complete phoneme sequence with all enhancements
        
        Args:
            phoneme_data: List of dicts with 'phoneme', 'viseme', 'duration', 'timestamp'
            stress_pattern: Optional list of stress levels for each phoneme
            
        Returns:
            List of morph dictionaries for smooth animation
        """
        # Convert to VisemeFrame objects
        frames = []
        for i, data in enumerate(phoneme_data):
            frame = VisemeFrame(
                viseme=data['viseme'],
                morphs={data['viseme']: 1.0},  # Base morph
                duration=data['duration'],
                timestamp=data['timestamp'],
                phoneme=data.get('phoneme'),
                word_position=data.get('word_position')
            )
            
            # Apply stress if provided
            if stress_pattern and i < len(stress_pattern):
                stress_level = stress_pattern[i]
                if stress_level in self.stress_modifiers:
                    modifier = self.stress_modifiers[stress_level]
                    frame.morphs = {k: v * modifier for k, v in frame.morphs.items()}
            
            frames.append(frame)
        
        # Apply coarticulation
        for i, frame in enumerate(frames):
            prev_frame = frames[i - 1] if i > 0 else None
            next_frame = frames[i + 1] if i < len(frames) - 1 else None
            
            # Get coarticulated morphs
            coarticulated = self.apply_coarticulation(prev_frame, frame, next_frame)
            
            # Add secondary shapes
            enhanced = self.add_secondary_shapes(frame.viseme, coarticulated)
            
            # Apply word position effects
            if frame.word_position:
                enhanced = self.apply_word_position_effects(frame)
            
            frame.morphs = enhanced
        
        # Interpolate to target framerate
        smooth_animation = self.interpolate_frames(frames)
        
        # Final cleanup - clamp values and remove tiny movements
        for frame_morphs in smooth_animation:
            for morph in list(frame_morphs.keys()):
                value = frame_morphs[morph]
                if value < 0.01:
                    del frame_morphs[morph]
                else:
                    frame_morphs[morph] = min(1.0, max(0.0, value))
        
        return smooth_animation
    
    def generate_test_sequence(self) -> List[Dict[str, float]]:
        """Generate a test sequence saying 'Hello World' with natural timing"""
        # Phoneme sequence for "Hello World"
        test_phonemes = [
            {'phoneme': 'HH', 'viseme': 'V_H', 'duration': 0.08, 'timestamp': 0.0, 'word_position': 'start'},
            {'phoneme': 'EH', 'viseme': 'V_EH', 'duration': 0.12, 'timestamp': 0.08, 'word_position': 'middle'},
            {'phoneme': 'L', 'viseme': 'V_L', 'duration': 0.10, 'timestamp': 0.20, 'word_position': 'middle'},
            {'phoneme': 'OW', 'viseme': 'V_OH', 'duration': 0.15, 'timestamp': 0.30, 'word_position': 'end'},
            {'phoneme': 'SIL', 'viseme': 'V_None', 'duration': 0.20, 'timestamp': 0.45},
            {'phoneme': 'W', 'viseme': 'V_U', 'duration': 0.08, 'timestamp': 0.65, 'word_position': 'start'},
            {'phoneme': 'ER', 'viseme': 'V_ER', 'duration': 0.12, 'timestamp': 0.73, 'word_position': 'middle'},
            {'phoneme': 'L', 'viseme': 'V_L', 'duration': 0.08, 'timestamp': 0.85, 'word_position': 'middle'},
            {'phoneme': 'D', 'viseme': 'V_DD', 'duration': 0.10, 'timestamp': 0.93, 'word_position': 'end'},
        ]
        
        # Stress pattern: HEL-lo WORLD
        stress_pattern = [
            'primary_stress', 'unstressed', 'unstressed', 'unstressed',
            'unstressed',
            'primary_stress', 'primary_stress', 'unstressed', 'unstressed'
        ]
        
        return self.process_phoneme_sequence(test_phonemes, stress_pattern)


# Example usage
if __name__ == "__main__":
    engine = VisemeTransitionEngine()
    
    # Generate test animation
    print("Generating 'Hello World' animation...")
    animation_frames = engine.generate_test_sequence()
    
    print(f"Generated {len(animation_frames)} frames")
    
    # Show first few frames
    for i, frame in enumerate(animation_frames[:5]):
        print(f"\nFrame {i}:")
        for morph, value in sorted(frame.items(), key=lambda x: x[1], reverse=True)[:3]:
            print(f"  {morph}: {value:.3f}")
    
    # Test transition curve
    print("\n\nTransition curve from V_Explosive to V_AA:")
    curve = engine.get_transition_curve('V_Explosive', 'V_AA', 0.15)
    print(f"Curve points (sampled): {[f'{v:.2f}' for v in curve[::3]]}")