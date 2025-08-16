"""
Avatar Engine Backend Server
Real-time facial animation engine with AI-driven optimization
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.enhanced_facial_animation_system import EnhancedFacialAnimationSystem
from core.facial_animation_performance_optimizer import FacialAnimationOptimizer
from core.viseme_transition_engine import VisemeTransitionEngine
from compression.delta_compressor import DeltaCompressor
from compression.performance_monitor import PerformanceMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
animation_system = None
optimizer = None
performance_monitor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global animation_system, optimizer, performance_monitor
    
    logger.info("Initializing Avatar Engine...")
    
    # Initialize systems
    animation_system = EnhancedFacialAnimationSystem()
    optimizer = FacialAnimationOptimizer()
    performance_monitor = PerformanceMonitor()
    
    # Start performance monitoring
    asyncio.create_task(performance_monitor.start_monitoring())
    
    logger.info("Avatar Engine initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Avatar Engine...")
    if performance_monitor:
        await performance_monitor.stop_monitoring()


# Create FastAPI app
app = FastAPI(
    title="Avatar Engine API",
    description="Real-time facial animation engine with AI-driven optimization",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Avatar Engine",
        "version": "1.0.0"
    }


@app.get("/api/v1/status")
async def get_status():
    """Get system status and metrics"""
    if not performance_monitor:
        return JSONResponse(
            status_code=503,
            content={"error": "System not initialized"}
        )
    
    metrics = await performance_monitor.get_current_metrics()
    return {
        "status": "operational",
        "metrics": metrics,
        "capabilities": {
            "max_avatars": 10,
            "protocols": ["websocket", "webrtc"],
            "compression": ["delta", "keyframe"],
            "target_fps": 60
        }
    }


@app.websocket("/ws/avatar/{avatar_id}")
async def avatar_websocket(websocket: WebSocket, avatar_id: str):
    """WebSocket endpoint for real-time avatar animation"""
    await websocket.accept()
    logger.info(f"Avatar {avatar_id} connected")
    
    # Initialize connection-specific components
    compressor = DeltaCompressor()
    viseme_engine = VisemeTransitionEngine()
    
    try:
        while True:
            # Receive animation data
            data = await websocket.receive_json()
            
            # Process based on message type
            if data["type"] == "animation":
                # Apply optimizations
                optimized_data = await optimizer.optimize_animation_data(
                    data["data"],
                    avatar_id
                )
                
                # Compress data
                compressed = compressor.compress_frame(optimized_data)
                
                # Send back
                await websocket.send_bytes(compressed)
                
            elif data["type"] == "audio":
                # Process audio to visemes
                visemes = await viseme_engine.audio_to_visemes(
                    data["audio"],
                    data.get("sampleRate", 48000)
                )
                
                await websocket.send_json({
                    "type": "visemes",
                    "data": visemes
                })
                
            elif data["type"] == "control":
                # Handle control messages
                if data["action"] == "reset":
                    compressor.reset()
                    await websocket.send_json({
                        "type": "ack",
                        "action": "reset"
                    })
                    
    except WebSocketDisconnect:
        logger.info(f"Avatar {avatar_id} disconnected")
    except Exception as e:
        logger.error(f"Error in avatar {avatar_id}: {e}")
        await websocket.close(code=1000)


@app.post("/api/v1/avatar/{avatar_id}/benchmark")
async def run_benchmark(avatar_id: str, config: Dict[str, Any] = None):
    """Run performance benchmark for specific configuration"""
    if not animation_system:
        return JSONResponse(
            status_code=503,
            content={"error": "System not initialized"}
        )
    
    results = await animation_system.run_benchmark(
        avatar_id,
        config or {}
    )
    
    return {
        "avatar_id": avatar_id,
        "results": results,
        "recommendations": optimizer.get_recommendations(results)
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
        access_log=True
    )