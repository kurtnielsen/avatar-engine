"""
Avatar Engine Backend Server
Real-time facial animation engine with AI-driven optimization
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.enhanced_facial_animation_system import EnhancedFacialAnimationSystem
from core.facial_animation_performance_optimizer import FacialAnimationOptimizer
from core.viseme_transition_engine import VisemeTransitionEngine
from core.facial_animation_unified_system import UnifiedFacialAnimationSystem
from core.websocket_protocol import (
    parse_message, create_error_message, MessageType,
    AnimationMessage, AudioMessage, ControlMessage, AckMessage, VisemeMessage
)
from core.webrtc_handler import WebRTCHandlerClass
from compression.delta_compressor import DeltaCompressor
from compression.performance_monitor import PerformanceMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
unified_system = None
webrtc_handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global unified_system, webrtc_handler
    
    try:
        logger.info("Initializing Avatar Engine...")
        
        # Initialize unified system
        unified_system = UnifiedFacialAnimationSystem()
        await unified_system.start()
        
        # Initialize WebRTC handler
        try:
            webrtc_handler = WebRTCHandlerClass()
            logger.info("WebRTC support enabled")
        except ImportError:
            logger.warning("WebRTC support disabled (aiortc not installed)")
            webrtc_handler = None
        
        logger.info("Avatar Engine initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize Avatar Engine: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down Avatar Engine...")
        if unified_system:
            await unified_system.stop()


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
    if not unified_system:
        return JSONResponse(
            status_code=503,
            content={"error": "System not initialized"}
        )
    
    # Get metrics from unified system
    metrics = {}
    if unified_system.performance_monitor:
        metrics = await unified_system.performance_monitor.get_current_metrics()
    
    return {
        "status": "operational",
        "metrics": metrics,
        "capabilities": {
            "max_avatars": 10,
            "protocols": ["websocket", "webrtc"] if webrtc_handler else ["websocket"],
            "compression": ["delta", "keyframe"],
            "target_fps": 60,
            "webrtc_available": webrtc_handler is not None
        },
        "active_sessions": len(unified_system.sessions) if unified_system else 0
    }


@app.websocket("/ws/avatar/{avatar_id}")
async def avatar_websocket(websocket: WebSocket, avatar_id: str):
    """WebSocket endpoint for real-time avatar animation"""
    await websocket.accept()
    logger.info(f"Avatar {avatar_id} connected via WebSocket")
    
    session = None
    
    try:
        # Connect avatar to unified system
        session = await unified_system.connect_avatar(avatar_id, websocket)
        
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            try:
                # Parse message using protocol
                message = parse_message(data)
                
                # Process based on message type
                if message.type == MessageType.ANIMATION:
                    # Process animation frame
                    result = await unified_system.process_frame(
                        avatar_id, 
                        message.data
                    )
                    
                    # Send compressed data back
                    if not result.get("skipped"):
                        await websocket.send_bytes(result["data"])
                
                elif message.type == MessageType.AUDIO:
                    # Process audio to visemes
                    visemes = await unified_system.process_audio(
                        avatar_id,
                        message.data
                    )
                    
                    # Send visemes
                    response = VisemeMessage(data=visemes)
                    await websocket.send_json(response.dict())
                
                elif message.type == MessageType.CONTROL:
                    # Handle control command
                    await unified_system.handle_control(
                        avatar_id,
                        message.data.action,
                        message.data.params
                    )
                    
                    # Send acknowledgment
                    ack = AckMessage(
                        ack_id=message.id or "control",
                        status="ok"
                    )
                    await websocket.send_json(ack.dict())
                
                elif message.type == MessageType.PING:
                    # Respond to ping
                    await websocket.send_json({"type": "pong"})
                    
            except ValueError as e:
                # Send error message
                error_msg = create_error_message(
                    code="INVALID_MESSAGE",
                    message=str(e)
                )
                await websocket.send_json(error_msg.dict())
                
    except WebSocketDisconnect:
        logger.info(f"Avatar {avatar_id} disconnected")
    except Exception as e:
        logger.error(f"Error in avatar {avatar_id}: {e}")
        
        # Try to send error before closing
        try:
            error_msg = create_error_message(
                code="INTERNAL_ERROR",
                message="An error occurred processing your request"
            )
            await websocket.send_json(error_msg.dict())
        except:
            pass
            
        await websocket.close(code=1000)
    finally:
        # Disconnect avatar from system
        if unified_system and session:
            await unified_system.disconnect_avatar(avatar_id)


@app.post("/api/v1/webrtc/offer")
async def create_webrtc_offer(request: Dict[str, Any]):
    """Create WebRTC offer for peer connection"""
    if not webrtc_handler:
        return JSONResponse(
            status_code=501,
            content={"error": "WebRTC not available. Install 'aiortc' package."}
        )
    
    peer_id = request.get("peer_id", f"peer_{int(time.time())}")
    
    try:
        offer = await webrtc_handler.create_offer(peer_id)
        return {
            "peer_id": peer_id,
            "offer": offer
        }
    except Exception as e:
        logger.error(f"Failed to create offer: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/v1/webrtc/answer")
async def create_webrtc_answer(request: Dict[str, Any]):
    """Create WebRTC answer for peer connection"""
    if not webrtc_handler:
        return JSONResponse(
            status_code=501,
            content={"error": "WebRTC not available. Install 'aiortc' package."}
        )
    
    peer_id = request.get("peer_id")
    offer = request.get("offer")
    
    if not peer_id or not offer:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing peer_id or offer"}
        )
    
    try:
        answer = await webrtc_handler.create_answer(peer_id, offer)
        return {
            "peer_id": peer_id,
            "answer": answer
        }
    except Exception as e:
        logger.error(f"Failed to create answer: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/v1/webrtc/ice")
async def add_ice_candidate(request: Dict[str, Any]):
    """Add ICE candidate for WebRTC connection"""
    if not webrtc_handler:
        return JSONResponse(
            status_code=501,
            content={"error": "WebRTC not available. Install 'aiortc' package."}
        )
    
    peer_id = request.get("peer_id")
    candidate = request.get("candidate")
    
    if not peer_id:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing peer_id"}
        )
    
    try:
        await webrtc_handler.add_ice_candidate(peer_id, candidate)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Failed to add ICE candidate: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/v1/webrtc/{peer_id}/stats")
async def get_webrtc_stats(peer_id: str):
    """Get WebRTC connection statistics"""
    if not webrtc_handler:
        return JSONResponse(
            status_code=501,
            content={"error": "WebRTC not available. Install 'aiortc' package."}
        )
    
    try:
        stats = await webrtc_handler.get_stats(peer_id)
        return stats
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/v1/avatar/{avatar_id}/benchmark")
async def run_benchmark(avatar_id: str, config: Dict[str, Any] = None):
    """Run performance benchmark for specific configuration"""
    if not unified_system:
        return JSONResponse(
            status_code=503,
            content={"error": "System not initialized"}
        )
    
    # Use the animation system from unified system
    if not unified_system.animation_system:
        return JSONResponse(
            status_code=503,
            content={"error": "Animation system not available"}
        )
    
    try:
        results = await unified_system.animation_system.run_benchmark(
            avatar_id,
            config or {}
        )
        
        recommendations = {}
        if unified_system.optimizer:
            recommendations = unified_system.optimizer.get_recommendations(results)
        
        return {
            "avatar_id": avatar_id,
            "results": results,
            "recommendations": recommendations
        }
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
        access_log=True
    )