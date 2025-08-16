"""
Facial Animation Mapper for ARKit to CC4 conversion
Maps between different facial animation systems
"""

class FacialAnimationMapper:
    def __init__(self):
        # ARKit to CC4 blendshape mapping
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
        
        # Phoneme to CC4 viseme mapping
        self.phoneme_to_viseme = {
            # Vowels
            'AA': 'V_AA',      # father
            'AE': 'V_AA',      # cat
            'AH': 'V_AA',      # cut
            'AO': 'V_OH',      # thought
            'AW': 'V_OH',      # house
            'AY': 'V_AA',      # bite
            'EH': 'V_EH',      # bed
            'ER': 'V_ER',      # bird
            'EY': 'V_EH',      # bait
            'IH': 'V_IH',      # sit
            'IY': 'V_EE',      # see
            'OW': 'V_OH',      # go
            'OY': 'V_OH',      # boy
            'UH': 'V_U',       # book
            'UW': 'V_U',       # too
            
            # Consonants
            'B': 'V_Explosive',  # boy
            'CH': 'V_CH',        # cheese
            'D': 'V_DD',         # dog
            'DH': 'V_TH',        # this
            'F': 'V_FF',         # fox
            'G': 'V_KK',         # go
            'HH': 'V_AA',        # hat
            'JH': 'V_CH',        # jump
            'K': 'V_KK',         # cat
            'L': 'V_L',          # let
            'M': 'V_Explosive',  # mom
            'N': 'V_NN',         # net
            'NG': 'V_NN',        # sing
            'P': 'V_Explosive',  # put
            'R': 'V_RR',         # red
            'S': 'V_SS',         # see
            'SH': 'V_CH',        # she
            'T': 'V_DD',         # top
            'TH': 'V_TH',        # think
            'V': 'V_FF',         # voice
            'W': 'V_U',          # we
            'Y': 'V_EE',         # yes
            'Z': 'V_SS',         # zoo
            'ZH': 'V_CH',        # measure
            'SIL': 'V_None'      # silence
        }
        
        # Simple viseme codes (A, B, C, etc.) to CC4
        self.simple_viseme_map = {
            'A': 'V_AA',
            'B': 'V_Explosive',
            'C': 'V_IH',
            'D': 'V_AA',
            'E': 'V_EH',
            'F': 'V_FF',
            'G': 'V_FF',
            'H': 'V_L',
            'X': 'V_None'
        }
    
    def map_arkit_to_cc4(self, arkit_data):
        """
        Convert ARKit blendshape values to CC4 morph targets
        
        Args:
            arkit_data: Dict of ARKit blendshape names to values (0-1)
            
        Returns:
            Dict of CC4 morph names to values (0-1)
        """
        cc4_morphs = {}
        
        for arkit_name, value in arkit_data.items():
            if arkit_name in self.arkit_to_cc4:
                cc4_name = self.arkit_to_cc4[arkit_name]
                cc4_morphs[cc4_name] = float(value)
            # else:
            #     print(f"Warning: Unknown ARKit blendshape: {arkit_name}")
        
        return cc4_morphs
    
    def map_phoneme_to_viseme(self, phoneme, intensity=1.0):
        """
        Convert phoneme to CC4 viseme
        
        Args:
            phoneme: Phoneme code (e.g., 'AA', 'P', 'S')
            intensity: Strength of the viseme (0-1)
            
        Returns:
            Dict with single viseme and intensity
        """
        phoneme_upper = phoneme.upper()
        
        if phoneme_upper in self.phoneme_to_viseme:
            viseme = self.phoneme_to_viseme[phoneme_upper]
            return {viseme: float(intensity)}
        elif phoneme_upper in self.simple_viseme_map:
            viseme = self.simple_viseme_map[phoneme_upper]
            return {viseme: float(intensity)}
        else:
            # Default to neutral
            return {'V_None': 0.0}
    
    def map_viseme_stream(self, viseme_data):
        """
        Map a stream of viseme data (from speech recognition or TTS)
        
        Args:
            viseme_data: Dict with 'viseme' and 'weight' or similar structure
            
        Returns:
            Dict of CC4 morph names to values
        """
        if isinstance(viseme_data, dict):
            if 'viseme' in viseme_data:
                return self.map_phoneme_to_viseme(
                    viseme_data['viseme'], 
                    viseme_data.get('weight', 1.0)
                )
            elif 'phoneme' in viseme_data:
                return self.map_phoneme_to_viseme(
                    viseme_data['phoneme'],
                    viseme_data.get('intensity', 1.0)
                )
        
        return {'V_None': 0.0}
    
    def combine_morphs(self, *morph_dicts):
        """
        Combine multiple morph dictionaries, taking the maximum value for each morph
        
        Args:
            *morph_dicts: Variable number of morph dictionaries
            
        Returns:
            Combined dictionary with max values
        """
        combined = {}
        
        for morph_dict in morph_dicts:
            for morph_name, value in morph_dict.items():
                if morph_name in combined:
                    combined[morph_name] = max(combined[morph_name], value)
                else:
                    combined[morph_name] = value
        
        return combined


# Example usage
if __name__ == "__main__":
    mapper = FacialAnimationMapper()
    
    # Test ARKit mapping
    arkit_test = {
        'jawOpen': 0.5,
        'mouthSmileLeft': 0.8,
        'mouthSmileRight': 0.8,
        'eyeBlinkLeft': 1.0,
        'eyeBlinkRight': 1.0
    }
    
    cc4_result = mapper.map_arkit_to_cc4(arkit_test)
    print("ARKit to CC4:", cc4_result)
    
    # Test phoneme mapping
    phoneme_result = mapper.map_phoneme_to_viseme('AA', 0.7)
    print("Phoneme to viseme:", phoneme_result)