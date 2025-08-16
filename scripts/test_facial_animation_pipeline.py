#!/usr/bin/env python3
"""
Test script for the complete facial animation pipeline
Tests: UDP → Backend → WebSocket → Three.js
"""

import asyncio
import json
import socket
import time
from datetime import datetime

async def test_websocket_broadcast():
    """Test sending morph data directly via WebSocket"""
    import websockets
    
    print("🔌 Connecting to WebSocket server...")
    
    try:
        async with websockets.connect('ws://localhost:8765') as websocket:
            print("✅ Connected to WebSocket server")
            
            # Test sequence of facial expressions
            test_sequences = [
                {
                    "name": "Neutral",
                    "morphs": {"V_None": 0.0}
                },
                {
                    "name": "Smile",
                    "morphs": {
                        "Mouth_Smile_L": 0.8,
                        "Mouth_Smile_R": 0.8,
                        "Cheek_Squint_L": 0.3,
                        "Cheek_Squint_R": 0.3
                    }
                },
                {
                    "name": "Talk - Open",
                    "morphs": {
                        "V_Open": 0.6,
                        "V_Wide": 0.3
                    }
                },
                {
                    "name": "Talk - OO",
                    "morphs": {
                        "V_U": 0.8,
                        "V_Tight_O": 0.6
                    }
                },
                {
                    "name": "Blink",
                    "morphs": {
                        "Eye_Blink_L": 1.0,
                        "Eye_Blink_R": 1.0
                    }
                },
                {
                    "name": "Surprise",
                    "morphs": {
                        "V_Open": 0.4,
                        "Eye_Wide_L": 0.8,
                        "Eye_Wide_R": 0.8,
                        "Brow_Raise_L": 0.7,
                        "Brow_Raise_R": 0.7
                    }
                }
            ]
            
            for sequence in test_sequences:
                print(f"\n🎭 Testing: {sequence['name']}")
                
                message = {
                    "type": "blendshape_update",
                    "data": sequence['morphs'],
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(message))
                print(f"   Sent morphs: {list(sequence['morphs'].keys())}")
                
                # Hold expression for 2 seconds
                await asyncio.sleep(2)
            
            # Reset to neutral
            reset_message = {
                "type": "blendshape_update",
                "data": {"V_None": 0.0},
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(reset_message))
            
            print("\n✅ Test sequence complete!")
            
    except ConnectionRefusedError:
        print("❌ Could not connect to WebSocket server at ws://localhost:8765")
        print("   Make sure facial_animation_department_dashboard.py is running")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_udp_viseme():
    """Test sending viseme data via UDP"""
    print("\n📡 Testing UDP viseme transmission...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Test viseme sequence (simulating speech)
    viseme_sequence = [
        {"viseme": "X", "weight": 0.0},    # Silence
        {"viseme": "A", "weight": 0.8},    # AA
        {"viseme": "B", "weight": 0.9},    # Explosive (P/B/M)
        {"viseme": "C", "weight": 0.7},    # IH
        {"viseme": "D", "weight": 0.8},    # AA
        {"viseme": "F", "weight": 0.9},    # FF
        {"viseme": "A", "weight": 0.6},    # AA
        {"viseme": "X", "weight": 0.0},    # Silence
    ]
    
    for viseme_data in viseme_sequence:
        data = json.dumps(viseme_data).encode()
        sock.sendto(data, ('localhost', 5005))
        print(f"   Sent viseme: {viseme_data['viseme']} (weight: {viseme_data['weight']})")
        time.sleep(0.3)
    
    sock.close()
    print("✅ UDP viseme test complete")


def test_udp_arkit():
    """Test sending ARKit blendshapes via UDP"""
    print("\n📡 Testing UDP ARKit blendshape transmission...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Simulate ARKit data
    arkit_data = {
        "blendshapes": {
            "jawOpen": 0.3,
            "mouthSmileLeft": 0.7,
            "mouthSmileRight": 0.7,
            "eyeBlinkLeft": 0.0,
            "eyeBlinkRight": 0.0,
            "browInnerUp": 0.2
        }
    }
    
    data = json.dumps(arkit_data).encode()
    sock.sendto(data, ('localhost', 5005))
    print(f"   Sent ARKit data with {len(arkit_data['blendshapes'])} blendshapes")
    
    sock.close()
    print("✅ UDP ARKit test complete")


async def main():
    print("🚀 Facial Animation Pipeline Test")
    print("=" * 50)
    
    # Test WebSocket directly
    await test_websocket_broadcast()
    
    # Test UDP inputs
    test_udp_viseme()
    test_udp_arkit()
    
    print("\n" + "=" * 50)
    print("📋 Next steps:")
    print("1. Ensure facial_animation_department_dashboard.py is running")
    print("2. Open cc4_camila_final_viewer.html in browser")
    print("3. Click 'Connect WebSocket' in the viewer")
    print("4. Run this test again to see morphs animate")


if __name__ == "__main__":
    asyncio.run(main())