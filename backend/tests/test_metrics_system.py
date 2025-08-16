#!/usr/bin/env python3
"""
Simple test for the metrics system without requiring Unreal Engine
Simulates metrics data via WebSocket
"""

import asyncio
import websockets
import json
import numpy as np
import time

async def simulate_metrics():
    """Simulate metrics data as if coming from Unreal Engine"""
    
    uri = "ws://localhost:8765"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to dashboard!")
            
            # Simulate metrics updates
            for i in range(100):
                # Create simulated metrics
                metrics_data = {
                    "type": "metrics_update",
                    "data": {
                        "fps": float(60 + np.random.normal(0, 5)),
                        "system_load": float(0.3 + np.random.random() * 0.4),
                        "blendshapes": {
                            # Viseme-related (simulate speech)
                            "jawOpen": float(np.random.random() * 0.5 if np.random.random() > 0.3 else 0),
                            "mouthSmileLeft": float(np.random.random() * 0.3),
                            "mouthSmileRight": float(np.random.random() * 0.3),
                            "mouthFunnel": float(np.random.random() * 0.4 if np.random.random() > 0.5 else 0),
                            
                            # Blink
                            "eyeBlinkLeft": float(1.0 if (i % 30) < 3 else 0.0),
                            "eyeBlinkRight": float(1.0 if (i % 30) < 3 else 0.0),
                            
                            # Microexpressions
                            "browInnerUp": float(np.random.random() * 0.2 if np.random.random() > 0.8 else 0),
                            "browDownLeft": float(np.random.random() * 0.1 if np.random.random() > 0.9 else 0),
                            "browDownRight": float(np.random.random() * 0.1 if np.random.random() > 0.9 else 0),
                            "cheekPuff": float(np.random.random() * 0.2 if np.random.random() > 0.95 else 0),
                            
                            # Head movement would affect position/rotation, not blendshapes
                        },
                        "departments": {
                            "Viseme": {
                                "active": float(np.random.random() > 0.3),
                                "intensity": float(np.random.random() * 0.8),
                                "conflict": float(np.random.random() * 0.1),
                                "latency": float(np.random.random() * 20),
                                "success": True
                            },
                            "Blink": {
                                "active": float((i % 30) < 3),  # Blink every ~0.5 seconds
                                "intensity": 0.9 if (i % 30) < 3 else 0.0,
                                "conflict": 0.0,
                                "latency": 5.0,
                                "success": True
                            },
                            "Microexpression": {
                                "active": float(np.random.random() > 0.8),
                                "intensity": float(np.random.random() * 0.4),
                                "conflict": float(np.random.random() * 0.05),
                                "latency": float(np.random.random() * 15),
                                "success": True
                            },
                            "HeadMovement": {
                                "active": float(np.sin(i * 0.1) > 0),
                                "intensity": float(abs(np.sin(i * 0.1)) * 0.5),
                                "conflict": 0.0,
                                "latency": 10.0,
                                "success": True
                            },
                            "MasterController": {
                                "active": 1.0,
                                "intensity": 0.5,
                                "conflict": np.random.random() * 0.1,
                                "latency": 2,
                                "success": True
                            }
                        }
                    }
                }
                
                # Send metrics
                await websocket.send(json.dumps(metrics_data))
                
                # Print status
                if i % 10 == 0:
                    print(f"Sent metrics update {i}/100")
                
                # Wait 100ms (10Hz update rate)
                await asyncio.sleep(0.1)
            
            # Request recommendations
            print("\nRequesting recommendations...")
            request = {
                "type": "get_recommendations",
                "data": {}
            }
            await websocket.send(json.dumps(request))
            
            # Wait for response
            response = await websocket.recv()
            recommendations = json.loads(response)
            
            if recommendations.get("type") == "recommendations":
                print("\nReceived Recommendations:")
                for dept, recs in recommendations.get("data", {}).items():
                    print(f"\n{dept}:")
                    for rec in recs:
                        print(f"  [{rec['priority']}] {rec['message']}")
            
            print("\nTest complete! Check the dashboard for results.")
            
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure the dashboard server is running:")
        print("  python facial_animation_department_dashboard.py")

if __name__ == "__main__":
    print("=== Facial Animation Metrics Test ===")
    print("This simulates metrics data without requiring Unreal Engine")
    print()
    
    asyncio.run(simulate_metrics())