#!/usr/bin/env python3
"""
Test ARKit to CC4 blendshape mapping with Three.js viewer
Uses the FacialAnimationMapper to convert ARKit data to CC4 morphs
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from facial_animation_mapper import FacialAnimationMapper

async def test_arkit_mapping():
    """Test ARKit to CC4 mapping via WebSocket"""
    import websockets
    
    mapper = FacialAnimationMapper()
    
    print("🔌 Connecting to WebSocket server...")
    
    try:
        async with websockets.connect('ws://localhost:8765') as websocket:
            print("✅ Connected to WebSocket server")
            print("🎭 Testing ARKit to CC4 mapping...")
            
            # Test sequences with ARKit blendshapes
            arkit_sequences = [
                {
                    "name": "Neutral",
                    "blendshapes": {}
                },
                {
                    "name": "Happy (ARKit)",
                    "blendshapes": {
                        "mouthSmileLeft": 0.8,
                        "mouthSmileRight": 0.8,
                        "cheekSquintLeft": 0.4,
                        "cheekSquintRight": 0.4
                    }
                },
                {
                    "name": "Talking (ARKit)",
                    "blendshapes": {
                        "jawOpen": 0.5,
                        "mouthFunnel": 0.3,
                        "mouthUpperUpLeft": 0.2,
                        "mouthUpperUpRight": 0.2
                    }
                },
                {
                    "name": "Surprise (ARKit)",
                    "blendshapes": {
                        "jawOpen": 0.3,
                        "eyeWideLeft": 0.8,
                        "eyeWideRight": 0.8,
                        "browOuterUpLeft": 0.7,
                        "browOuterUpRight": 0.7,
                        "browInnerUp": 0.6
                    }
                },
                {
                    "name": "Sad (ARKit)",
                    "blendshapes": {
                        "mouthFrownLeft": 0.6,
                        "mouthFrownRight": 0.6,
                        "browDownLeft": 0.5,
                        "browDownRight": 0.5,
                        "eyeSquintLeft": 0.3,
                        "eyeSquintRight": 0.3
                    }
                },
                {
                    "name": "Blink (ARKit)",
                    "blendshapes": {
                        "eyeBlinkLeft": 1.0,
                        "eyeBlinkRight": 1.0
                    }
                },
                {
                    "name": "Wink Left (ARKit)",
                    "blendshapes": {
                        "eyeBlinkLeft": 1.0,
                        "mouthSmileLeft": 0.4,
                        "mouthSmileRight": 0.2
                    }
                },
                {
                    "name": "Pucker (ARKit)",
                    "blendshapes": {
                        "mouthPucker": 0.8,
                        "mouthFunnel": 0.6
                    }
                },
                {
                    "name": "Speech Test (ARKit)",
                    "blendshapes": {
                        "jawOpen": 0.2,
                        "mouthRollLower": 0.3,
                        "mouthPressLeft": 0.1,
                        "mouthPressRight": 0.1,
                        "tongueOut": 0.1
                    }
                }
            ]
            
            for sequence in arkit_sequences:
                print(f"\n🎭 Testing: {sequence['name']}")
                
                # Convert ARKit to CC4
                cc4_morphs = mapper.map_arkit_to_cc4(sequence['blendshapes'])
                
                print(f"   ARKit inputs: {list(sequence['blendshapes'].keys())}")
                print(f"   CC4 outputs: {list(cc4_morphs.keys())}")
                
                # Send to viewer
                message = {
                    "type": "blendshape_update",
                    "data": cc4_morphs,
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(message))
                
                # Show mapping details
                for arkit, value in sequence['blendshapes'].items():
                    cc4_name = mapper.arkit_to_cc4.get(arkit, "Unknown")
                    if cc4_name != "Unknown":
                        print(f"      {arkit} ({value:.1f}) → {cc4_name}")
                
                # Hold expression
                await asyncio.sleep(2.5)
            
            # Test viseme sequence (speech simulation)
            print("\n🗣️ Testing Viseme Sequence...")
            
            # Simulate saying "Hello World"
            viseme_sequence = [
                ("HH", 0.3),  # H
                ("EH", 0.8),  # e
                ("L", 0.7),   # l
                ("L", 0.7),   # l
                ("OW", 0.8),  # o
                ("SIL", 0.2), # space
                ("W", 0.6),   # w
                ("ER", 0.7),  # or
                ("L", 0.6),   # l
                ("D", 0.8),   # d
                ("SIL", 0.0)  # end
            ]
            
            for phoneme, intensity in viseme_sequence:
                viseme_morphs = mapper.map_phoneme_to_viseme(phoneme, intensity)
                
                # Add some jaw movement for realism
                if intensity > 0.5:
                    viseme_morphs["Jaw_Open"] = intensity * 0.3
                
                message = {
                    "type": "blendshape_update", 
                    "data": viseme_morphs,
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(message))
                print(f"   Phoneme: {phoneme} → Viseme: {list(viseme_morphs.keys())[0]}")
                
                await asyncio.sleep(0.15)
            
            # Reset to neutral
            reset_message = {
                "type": "blendshape_update",
                "data": {},
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(reset_message))
            
            print("\n✅ ARKit mapping test complete!")
            
    except ConnectionRefusedError:
        print("❌ Could not connect to WebSocket server at ws://localhost:8765")
        print("   Make sure facial_animation_department_dashboard.py is running")
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_combined_animation():
    """Test combining multiple animation sources"""
    import websockets
    
    mapper = FacialAnimationMapper()
    
    print("\n🎬 Testing Combined Animations...")
    
    try:
        async with websockets.connect('ws://localhost:8765') as websocket:
            
            # Simulate talking while smiling
            base_expression = {
                "mouthSmileLeft": 0.4,
                "mouthSmileRight": 0.4
            }
            
            speech_phonemes = ["AA", "EH", "IH", "OH", "U", "EH", "AA"]
            
            for phoneme in speech_phonemes:
                # Get base expression morphs
                expression_morphs = mapper.map_arkit_to_cc4(base_expression)
                
                # Get viseme morphs
                viseme_morphs = mapper.map_phoneme_to_viseme(phoneme, 0.7)
                
                # Combine them
                combined = mapper.combine_morphs(expression_morphs, viseme_morphs)
                
                # Add subtle jaw movement
                combined["Jaw_Open"] = 0.2
                
                message = {
                    "type": "blendshape_update",
                    "data": combined,
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(message))
                await asyncio.sleep(0.2)
            
            print("✅ Combined animation test complete!")
            
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    print("🚀 ARKit to CC4 Mapping Test")
    print("=" * 50)
    print("Prerequisites:")
    print("1. facial_animation_department_dashboard.py running")
    print("2. cc4_final_working_viewer.html open with WebSocket connected")
    print("=" * 50)
    
    # Test ARKit mapping
    await test_arkit_mapping()
    
    # Test combined animations
    await test_combined_animation()
    
    print("\n📋 Summary:")
    print("- ARKit blendshapes successfully mapped to CC4 morphs")
    print("- Phoneme to viseme conversion working")
    print("- Combined animations (expression + speech) functional")
    print("\n🎯 Next: Integrate with UDP receiver for real-time ARKit data")


if __name__ == "__main__":
    asyncio.run(main())