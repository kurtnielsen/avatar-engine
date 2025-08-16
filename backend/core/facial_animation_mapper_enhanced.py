"""
Enhanced Facial Animation Mapper for ARKit to CC4 conversion
Includes expression blending, smoothing, micro-expressions, and emotion layers
"""

import numpy as np
from collections import deque
from typing import Dict, List, Tuple, Optional
import math
import time


class FacialAnimationMapperEnhanced:
    def __init__(self, smoothing_window: int = 5, blend_speed: float = 0.15):
        # Original ARKit to CC4 mapping
        self.arkit_to_cc4 = {
            # Mouth/Jaw movements
            'jawForward': 'Jaw_Forward',
            'jawLeft': 'Jaw_L',
            'jawRight': 'Jaw_R',
            'jawOpen': 'V_Open',
            'mouthClose': 'V_None',
            'mouthFunnel': 'V_OH',
            'mouthPucker': 'V_U',
            'mouthLeft': 'Mouth_L',
            'mouthRight': 'Mouth_R',
            'mouthSmileLeft': 'Mouth_Smile_L',
            'mouthSmileRight': 'Mouth_Smile_R',
            'mouthFrownLeft': 'Mouth_Frown_L',
            'mouthFrownRight': 'Mouth_Frown_R',
            'mouthDimpleLeft': 'Mouth_Dimple_L',
            'mouthDimpleRight': 'Mouth_Dimple_R',
            'mouthStretchLeft': 'Mouth_Stretch_L',
            'mouthStretchRight': 'Mouth_Stretch_R',
            'mouthRollLower': 'Mouth_Roll_Lower',
            'mouthRollUpper': 'Mouth_Roll_Upper',
            'mouthShrugLower': 'Mouth_Shrug_Lower',
            'mouthShrugUpper': 'Mouth_Shrug_Upper',
            'mouthPressLeft': 'Mouth_Press_L',
            'mouthPressRight': 'Mouth_Press_R',
            'mouthLowerDownLeft': 'Mouth_Lower_Down_L',
            'mouthLowerDownRight': 'Mouth_Lower_Down_R',
            'mouthUpperUpLeft': 'Mouth_Upper_Up_L',
            'mouthUpperUpRight': 'Mouth_Upper_Up_R',
            
            # Eye movements
            'eyeBlinkLeft': 'Eye_Blink_L',
            'eyeBlinkRight': 'Eye_Blink_R',
            'eyeLookUpLeft': 'Eye_Look_Up_L',
            'eyeLookUpRight': 'Eye_Look_Up_R',
            'eyeLookDownLeft': 'Eye_Look_Down_L',
            'eyeLookDownRight': 'Eye_Look_Down_R',
            'eyeLookInLeft': 'Eye_Look_In_L',
            'eyeLookInRight': 'Eye_Look_In_R',
            'eyeLookOutLeft': 'Eye_Look_Out_L',
            'eyeLookOutRight': 'Eye_Look_Out_R',
            'eyeWideLeft': 'Eye_Wide_L',
            'eyeWideRight': 'Eye_Wide_R',
            'eyeSquintLeft': 'Eye_Squint_L',
            'eyeSquintRight': 'Eye_Squint_R',
            
            # Brow movements
            'browDownLeft': 'Brow_Drop_L',
            'browDownRight': 'Brow_Drop_R',
            'browInnerUp': 'Brow_Raise_Inner',
            'browOuterUpLeft': 'Brow_Raise_L',
            'browOuterUpRight': 'Brow_Raise_R',
            
            # Nose movements
            'noseSneerLeft': 'Nose_Sneer_L',
            'noseSneerRight': 'Nose_Sneer_R',
            
            # Cheek movements
            'cheekPuff': 'Cheek_Puff',
            'cheekSquintLeft': 'Cheek_Squint_L',
            'cheekSquintRight': 'Cheek_Squint_R',
            
            # Tongue (if available)
            'tongueOut': 'Tongue_Out'
        }
        
        # Enhanced phoneme to CC4 viseme mapping with co-articulation
        self.phoneme_to_viseme = {
            # Vowels
            'AA': {'V_AA': 1.0, 'V_Open': 0.3},       # father
            'AE': {'V_AA': 0.8, 'V_EH': 0.2},         # cat
            'AH': {'V_AA': 0.7, 'V_Open': 0.2},       # cut
            'AO': {'V_OH': 1.0, 'V_U': 0.1},          # thought
            'AW': {'V_OH': 0.8, 'V_U': 0.3},          # house
            'AY': {'V_AA': 0.6, 'V_EE': 0.4},         # bite
            'EH': {'V_EH': 1.0},                      # bed
            'ER': {'V_ER': 1.0, 'V_RR': 0.3},         # bird
            'EY': {'V_EH': 0.7, 'V_EE': 0.3},         # bait
            'IH': {'V_IH': 1.0, 'V_EE': 0.2},         # sit
            'IY': {'V_EE': 1.0, 'V_Wide': 0.3},       # see
            'OW': {'V_OH': 0.9, 'V_U': 0.3},          # go
            'OY': {'V_OH': 0.7, 'V_EE': 0.3},         # boy
            'UH': {'V_U': 0.8, 'V_OH': 0.2},          # book
            'UW': {'V_U': 1.0, 'V_Narrow': 0.3},      # too
            
            # Consonants with co-articulation
            'B': {'V_Explosive': 1.0, 'V_Tight': 0.3},     # boy
            'CH': {'V_CH': 1.0, 'V_Dental_Lip': 0.2},      # cheese
            'D': {'V_DD': 1.0, 'V_Dental_Lip': 0.3},       # dog
            'DH': {'V_TH': 1.0, 'V_Dental_Lip': 0.5},      # this
            'F': {'V_FF': 1.0, 'V_Dental_Lip': 0.7},       # fox
            'G': {'V_KK': 1.0, 'V_Open': 0.1},             # go
            'HH': {'V_AA': 0.3, 'V_Open': 0.2},            # hat
            'JH': {'V_CH': 0.9, 'V_DD': 0.2},              # jump
            'K': {'V_KK': 1.0, 'V_Tight': 0.2},            # cat
            'L': {'V_L': 1.0, 'V_DD': 0.2},                # let
            'M': {'V_Explosive': 1.0, 'V_Tight': 0.5},     # mom
            'N': {'V_NN': 1.0, 'V_DD': 0.2},               # net
            'NG': {'V_NN': 0.8, 'V_KK': 0.3},              # sing
            'P': {'V_Explosive': 1.0, 'V_Tight': 0.4},     # put
            'R': {'V_RR': 1.0, 'V_ER': 0.2},               # red
            'S': {'V_SS': 1.0, 'V_Dental_Lip': 0.2},       # see
            'SH': {'V_CH': 0.8, 'V_SS': 0.3},              # she
            'T': {'V_DD': 1.0, 'V_Dental_Lip': 0.4},       # top
            'TH': {'V_TH': 1.0, 'V_Dental_Lip': 0.6},      # think
            'V': {'V_FF': 0.9, 'V_Dental_Lip': 0.6},       # voice
            'W': {'V_U': 0.8, 'V_OH': 0.3},                # we
            'Y': {'V_EE': 0.8, 'V_IH': 0.2},               # yes
            'Z': {'V_SS': 0.9, 'V_Dental_Lip': 0.2},       # zoo
            'ZH': {'V_CH': 0.7, 'V_SS': 0.3},              # measure
            'SIL': {'V_None': 0.0}                         # silence
        }
        
        # Emotion presets with blendshape combinations
        self.emotion_presets = {
            'happy': {
                'Mouth_Smile_L': 0.7,
                'Mouth_Smile_R': 0.7,
                'Mouth_Dimple_L': 0.3,
                'Mouth_Dimple_R': 0.3,
                'Eye_Squint_L': 0.2,
                'Eye_Squint_R': 0.2,
                'Cheek_Squint_L': 0.4,
                'Cheek_Squint_R': 0.4,
                'Brow_Raise_L': 0.1,
                'Brow_Raise_R': 0.1
            },
            'sad': {
                'Mouth_Frown_L': 0.6,
                'Mouth_Frown_R': 0.6,
                'Mouth_Press_L': 0.3,
                'Mouth_Press_R': 0.3,
                'Brow_Drop_L': 0.4,
                'Brow_Drop_R': 0.4,
                'Brow_Raise_Inner': 0.5,
                'Eye_Look_Down_L': 0.2,
                'Eye_Look_Down_R': 0.2
            },
            'angry': {
                'Brow_Drop_L': 0.8,
                'Brow_Drop_R': 0.8,
                'Eye_Squint_L': 0.4,
                'Eye_Squint_R': 0.4,
                'Nose_Sneer_L': 0.3,
                'Nose_Sneer_R': 0.3,
                'Mouth_Press_L': 0.4,
                'Mouth_Press_R': 0.4,
                'Jaw_Forward': 0.2
            },
            'surprised': {
                'Brow_Raise_L': 0.9,
                'Brow_Raise_R': 0.9,
                'Eye_Wide_L': 0.8,
                'Eye_Wide_R': 0.8,
                'V_Open': 0.4,
                'V_OH': 0.3
            },
            'fear': {
                'Brow_Raise_Inner': 0.7,
                'Brow_Raise_L': 0.4,
                'Brow_Raise_R': 0.4,
                'Eye_Wide_L': 0.6,
                'Eye_Wide_R': 0.6,
                'Mouth_Stretch_L': 0.5,
                'Mouth_Stretch_R': 0.5,
                'V_Open': 0.2
            },
            'disgust': {
                'Nose_Sneer_L': 0.7,
                'Nose_Sneer_R': 0.7,
                'Mouth_Upper_Up_L': 0.4,
                'Mouth_Upper_Up_R': 0.4,
                'Eye_Squint_L': 0.3,
                'Eye_Squint_R': 0.3,
                'Brow_Drop_L': 0.2,
                'Brow_Drop_R': 0.2
            },
            'contempt': {
                'Mouth_Smile_L': 0.0,
                'Mouth_Smile_R': 0.5,
                'Mouth_Press_L': 0.3,
                'Mouth_Press_R': 0.1,
                'Eye_Squint_L': 0.1,
                'Eye_Squint_R': 0.2,
                'Brow_Raise_L': 0.0,
                'Brow_Raise_R': 0.2
            },
            'neutral': {}
        }
        
        # Micro-expression patterns
        self.micro_expressions = {
            'subtle_smile': {
                'duration': 0.5,
                'peak': 0.3,
                'morphs': {
                    'Mouth_Smile_L': 0.2,
                    'Mouth_Smile_R': 0.2,
                    'Eye_Squint_L': 0.1,
                    'Eye_Squint_R': 0.1
                }
            },
            'eye_flash': {
                'duration': 0.2,
                'peak': 0.15,
                'morphs': {
                    'Eye_Wide_L': 0.3,
                    'Eye_Wide_R': 0.3,
                    'Brow_Raise_L': 0.2,
                    'Brow_Raise_R': 0.2
                }
            },
            'lip_tighten': {
                'duration': 0.3,
                'peak': 0.2,
                'morphs': {
                    'Mouth_Press_L': 0.4,
                    'Mouth_Press_R': 0.4
                }
            },
            'nose_wrinkle': {
                'duration': 0.25,
                'peak': 0.15,
                'morphs': {
                    'Nose_Sneer_L': 0.3,
                    'Nose_Sneer_R': 0.3
                }
            }
        }
        
        # Smoothing and blending parameters
        self.smoothing_window = smoothing_window
        self.blend_speed = blend_speed
        self.morph_history = {}
        self.current_values = {}
        self.target_values = {}
        self.emotion_weights = {'neutral': 1.0}
        self.active_micro_expressions = []
        
        # Viseme transition rules for smoother speech
        self.viseme_transitions = {
            ('V_Explosive', 'V_AA'): 0.8,    # Smooth transition from B/P to vowel
            ('V_AA', 'V_Explosive'): 0.6,    # Slightly faster closing
            ('V_OH', 'V_U'): 0.9,             # Similar mouth shapes
            ('V_EE', 'V_IH'): 0.9,            # Close vowel transitions
            ('V_FF', 'V_SS'): 0.7,            # Fricative transitions
            ('V_DD', 'V_NN'): 0.8,            # Alveolar transitions
        }
        
        # Eye movement patterns
        self.eye_patterns = {
            'natural_blink': {
                'interval': (2.0, 6.0),  # Random interval between blinks
                'duration': 0.15,        # Blink duration
                'pattern': [(0, 0), (0.05, 0.7), (0.1, 1.0), (0.15, 0)]
            },
            'thinking': {
                'pattern': [
                    {'Eye_Look_Up_L': 0.3, 'Eye_Look_Up_R': 0.3, 'duration': 1.0},
                    {'Eye_Look_In_L': 0.2, 'Eye_Look_Out_R': 0.2, 'duration': 0.5}
                ]
            }
        }
        
        self.last_blink_time = time.time()
        self.next_blink_interval = np.random.uniform(*self.eye_patterns['natural_blink']['interval'])
    
    def smooth_values(self, morph_name: str, value: float) -> float:
        """Apply exponential moving average smoothing"""
        if morph_name not in self.morph_history:
            self.morph_history[morph_name] = deque(maxlen=self.smoothing_window)
        
        self.morph_history[morph_name].append(value)
        
        # Weighted average with more weight on recent values
        if len(self.morph_history[morph_name]) > 0:
            weights = np.exp(np.linspace(-1, 0, len(self.morph_history[morph_name])))
            weights /= weights.sum()
            smoothed = np.average(list(self.morph_history[morph_name]), weights=weights)
            return float(smoothed)
        
        return value
    
    def blend_morphs(self, current: Dict[str, float], target: Dict[str, float], 
                     blend_factor: float = None) -> Dict[str, float]:
        """Smoothly blend between current and target morph values"""
        if blend_factor is None:
            blend_factor = self.blend_speed
        
        blended = {}
        all_morphs = set(current.keys()) | set(target.keys())
        
        for morph in all_morphs:
            current_val = current.get(morph, 0.0)
            target_val = target.get(morph, 0.0)
            
            # Check for specific transition rules
            transition_speed = blend_factor
            for (from_viseme, to_viseme), speed in self.viseme_transitions.items():
                if morph == to_viseme and any(from_viseme in m for m in current.keys()):
                    transition_speed *= speed
                    break
            
            # Exponential interpolation for smoother transitions
            if abs(target_val - current_val) > 0.001:
                blended[morph] = current_val + (target_val - current_val) * transition_speed
            else:
                blended[morph] = target_val
        
        return blended
    
    def apply_emotion_layer(self, base_morphs: Dict[str, float], 
                          emotion_weights: Dict[str, float]) -> Dict[str, float]:
        """Apply emotion overlays to base morphs"""
        result = base_morphs.copy()
        
        for emotion, weight in emotion_weights.items():
            if weight > 0 and emotion in self.emotion_presets:
                for morph, value in self.emotion_presets[emotion].items():
                    # Additive blending with saturation
                    current = result.get(morph, 0.0)
                    result[morph] = min(1.0, current + value * weight * 0.5)
        
        return result
    
    def process_micro_expression(self, expression_type: str, time_offset: float = 0):
        """Add a micro-expression to the animation queue"""
        if expression_type in self.micro_expressions:
            micro_exp = self.micro_expressions[expression_type].copy()
            micro_exp['start_time'] = time.time() + time_offset
            micro_exp['type'] = expression_type
            self.active_micro_expressions.append(micro_exp)
    
    def update_micro_expressions(self) -> Dict[str, float]:
        """Process active micro-expressions and return their contribution"""
        current_time = time.time()
        micro_morphs = {}
        
        # Process each active micro-expression
        self.active_micro_expressions = [
            exp for exp in self.active_micro_expressions
            if current_time - exp['start_time'] < exp['duration']
        ]
        
        for exp in self.active_micro_expressions:
            elapsed = current_time - exp['start_time']
            progress = elapsed / exp['duration']
            
            # Bell curve for micro-expression intensity
            intensity = math.exp(-((progress - 0.5) ** 2) / 0.1) * exp['peak']
            
            for morph, value in exp['morphs'].items():
                micro_morphs[morph] = micro_morphs.get(morph, 0) + value * intensity
        
        return micro_morphs
    
    def add_natural_blink(self) -> Dict[str, float]:
        """Add natural eye blinks based on time"""
        current_time = time.time()
        blink_morphs = {}
        
        if current_time - self.last_blink_time > self.next_blink_interval:
            # Calculate blink progress
            elapsed = current_time - self.last_blink_time - self.next_blink_interval
            blink_data = self.eye_patterns['natural_blink']
            
            if elapsed < blink_data['duration']:
                # Find current position in blink pattern
                for i in range(len(blink_data['pattern']) - 1):
                    t1, v1 = blink_data['pattern'][i]
                    t2, v2 = blink_data['pattern'][i + 1]
                    
                    if t1 <= elapsed <= t2:
                        # Linear interpolation
                        progress = (elapsed - t1) / (t2 - t1)
                        value = v1 + (v2 - v1) * progress
                        blink_morphs['Eye_Blink_L'] = value
                        blink_morphs['Eye_Blink_R'] = value
                        break
            else:
                # Reset blink timer
                self.last_blink_time = current_time
                self.next_blink_interval = np.random.uniform(
                    *self.eye_patterns['natural_blink']['interval']
                )
        
        return blink_morphs
    
    def map_phoneme_to_viseme_enhanced(self, phoneme: str, 
                                      intensity: float = 1.0,
                                      context: Optional[Tuple[str, str]] = None) -> Dict[str, float]:
        """Enhanced phoneme to viseme mapping with co-articulation"""
        phoneme_upper = phoneme.upper()
        
        if phoneme_upper in self.phoneme_to_viseme:
            viseme_data = self.phoneme_to_viseme[phoneme_upper]
            
            # Apply intensity scaling
            result = {k: v * intensity for k, v in viseme_data.items()}
            
            # Co-articulation adjustments based on context
            if context:
                prev_phoneme, next_phoneme = context
                
                # Adjust based on surrounding phonemes
                if prev_phoneme and prev_phoneme.upper() in self.phoneme_to_viseme:
                    prev_visemes = self.phoneme_to_viseme[prev_phoneme.upper()]
                    for viseme, value in prev_visemes.items():
                        if viseme in result:
                            # Blend with previous phoneme (25% influence)
                            result[viseme] = result[viseme] * 0.75 + value * 0.25
                
                if next_phoneme and next_phoneme.upper() in self.phoneme_to_viseme:
                    next_visemes = self.phoneme_to_viseme[next_phoneme.upper()]
                    for viseme, value in next_visemes.items():
                        if viseme in result:
                            # Pre-shape for next phoneme (15% influence)
                            result[viseme] = result[viseme] * 0.85 + value * 0.15
            
            return result
        
        return {'V_None': 0.0}
    
    def map_arkit_to_cc4_enhanced(self, arkit_data: Dict[str, float],
                                 emotion: Optional[str] = None,
                                 emotion_intensity: float = 0.5,
                                 add_micro_expressions: bool = True,
                                 add_natural_movements: bool = True) -> Dict[str, float]:
        """
        Enhanced ARKit to CC4 mapping with all features
        
        Args:
            arkit_data: Dict of ARKit blendshape names to values (0-1)
            emotion: Optional emotion preset to apply
            emotion_intensity: Strength of emotion overlay (0-1)
            add_micro_expressions: Whether to add micro-expressions
            add_natural_movements: Whether to add natural movements like blinking
            
        Returns:
            Dict of CC4 morph names to smoothed and blended values (0-1)
        """
        # Step 1: Basic ARKit to CC4 mapping
        cc4_morphs = {}
        for arkit_name, value in arkit_data.items():
            if arkit_name in self.arkit_to_cc4:
                cc4_name = self.arkit_to_cc4[arkit_name]
                # Apply smoothing to individual values
                smoothed_value = self.smooth_values(cc4_name, float(value))
                cc4_morphs[cc4_name] = smoothed_value
        
        # Step 2: Apply emotion layer if specified
        if emotion and emotion != 'neutral':
            emotion_weights = {emotion: emotion_intensity}
            cc4_morphs = self.apply_emotion_layer(cc4_morphs, emotion_weights)
        
        # Step 3: Add natural movements
        if add_natural_movements:
            blink_morphs = self.add_natural_blink()
            for morph, value in blink_morphs.items():
                cc4_morphs[morph] = max(cc4_morphs.get(morph, 0), value)
        
        # Step 4: Add micro-expressions
        if add_micro_expressions:
            micro_morphs = self.update_micro_expressions()
            for morph, value in micro_morphs.items():
                cc4_morphs[morph] = min(1.0, cc4_morphs.get(morph, 0) + value)
        
        # Step 5: Blend with previous frame for temporal smoothness
        self.target_values = cc4_morphs
        self.current_values = self.blend_morphs(self.current_values, self.target_values)
        
        # Step 6: Apply final constraints and cleanup
        final_morphs = {}
        for morph, value in self.current_values.items():
            # Clamp values
            clamped = max(0.0, min(1.0, value))
            # Remove very small values to reduce noise
            if clamped > 0.01:
                final_morphs[morph] = clamped
        
        return final_morphs
    
    def process_speech_with_emotion(self, phoneme_sequence: List[Dict],
                                  base_emotion: str = 'neutral',
                                  emotion_intensity: float = 0.3) -> List[Dict[str, float]]:
        """
        Process a sequence of phonemes with emotion overlay
        
        Args:
            phoneme_sequence: List of dicts with 'phoneme', 'duration', and optional 'intensity'
            base_emotion: Base emotion to apply
            emotion_intensity: Strength of emotion
            
        Returns:
            List of morph dictionaries for each frame
        """
        frames = []
        
        for i, phoneme_data in enumerate(phoneme_sequence):
            phoneme = phoneme_data['phoneme']
            intensity = phoneme_data.get('intensity', 1.0)
            
            # Get context for co-articulation
            prev_phoneme = phoneme_sequence[i-1]['phoneme'] if i > 0 else None
            next_phoneme = phoneme_sequence[i+1]['phoneme'] if i < len(phoneme_sequence)-1 else None
            
            # Get viseme morphs
            viseme_morphs = self.map_phoneme_to_viseme_enhanced(
                phoneme, intensity, (prev_phoneme, next_phoneme)
            )
            
            # Apply emotion
            if base_emotion != 'neutral':
                viseme_morphs = self.apply_emotion_layer(
                    viseme_morphs, {base_emotion: emotion_intensity}
                )
            
            # Add occasional micro-expressions during speech
            if np.random.random() < 0.05:  # 5% chance per phoneme
                self.process_micro_expression(
                    np.random.choice(['subtle_smile', 'lip_tighten'])
                )
            
            # Update micro-expressions
            micro_morphs = self.update_micro_expressions()
            for morph, value in micro_morphs.items():
                viseme_morphs[morph] = min(1.0, viseme_morphs.get(morph, 0) + value)
            
            # Smooth and blend
            self.target_values = viseme_morphs
            self.current_values = self.blend_morphs(self.current_values, self.target_values)
            
            frames.append(self.current_values.copy())
        
        return frames
    
    def set_emotion(self, emotion: str, intensity: float = 1.0, transition_time: float = 1.0):
        """Set the current emotion state with transition"""
        self.emotion_weights = {emotion: intensity}
    
    def trigger_micro_expression(self, expression_type: str):
        """Manually trigger a micro-expression"""
        self.process_micro_expression(expression_type)


# Example usage and testing
if __name__ == "__main__":
    # Initialize enhanced mapper
    mapper = FacialAnimationMapperEnhanced(smoothing_window=5, blend_speed=0.15)
    
    # Test 1: Basic ARKit mapping with emotion
    print("Test 1: ARKit with happy emotion")
    arkit_test = {
        'jawOpen': 0.3,
        'mouthSmileLeft': 0.5,
        'mouthSmileRight': 0.5,
        'eyeBlinkLeft': 0.0,
        'eyeBlinkRight': 0.0,
        'browInnerUp': 0.2
    }
    
    result = mapper.map_arkit_to_cc4_enhanced(
        arkit_test, 
        emotion='happy', 
        emotion_intensity=0.6
    )
    print(f"Morphs with emotion: {len(result)} active")
    for morph, value in sorted(result.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {morph}: {value:.3f}")
    
    # Test 2: Speech sequence with emotion
    print("\nTest 2: Speech with emotion")
    phoneme_sequence = [
        {'phoneme': 'HH', 'duration': 0.1, 'intensity': 0.8},
        {'phoneme': 'EH', 'duration': 0.15, 'intensity': 1.0},
        {'phoneme': 'L', 'duration': 0.1, 'intensity': 0.9},
        {'phoneme': 'OW', 'duration': 0.2, 'intensity': 1.0},
    ]
    
    speech_frames = mapper.process_speech_with_emotion(
        phoneme_sequence,
        base_emotion='happy',
        emotion_intensity=0.4
    )
    
    print(f"Generated {len(speech_frames)} frames for speech")
    print("First frame morphs:", list(speech_frames[0].keys())[:5])
    
    # Test 3: Micro-expression
    print("\nTest 3: Triggering micro-expression")
    mapper.trigger_micro_expression('subtle_smile')
    
    # Simulate a few frames to see the micro-expression
    for i in range(5):
        time.sleep(0.05)
        micro_result = mapper.update_micro_expressions()
        if micro_result:
            print(f"Frame {i}: Micro-expression active -", 
                  {k: f"{v:.3f}" for k, v in micro_result.items()})