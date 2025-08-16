"""
WebRTC Handler for Avatar Engine
Manages WebRTC connections and data channels for real-time communication
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
import time

try:
    from aiortc import RTCPeerConnection, RTCDataChannel, RTCSessionDescription
    from aiortc.contrib.media import MediaPlayer, MediaRelay
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("aiortc not installed. WebRTC features will be unavailable.")

from .websocket_protocol import (
    MessageType, AnimationMessage, AudioMessage, 
    ControlMessage, parse_message
)


@dataclass
class WebRTCSession:
    """WebRTC session information"""
    peer_id: str
    pc: 'RTCPeerConnection'
    data_channel: Optional['RTCDataChannel'] = None
    audio_track: Optional[Any] = None
    created_at: float = time.time()
    stats: Dict[str, Any] = None


class WebRTCHandler:
    """
    Handles WebRTC connections for ultra-low latency communication
    """
    
    def __init__(self, ice_servers: Optional[List[Dict[str, str]]] = None):
        if not WEBRTC_AVAILABLE:
            raise ImportError("WebRTC support requires 'aiortc' package")
            
        self.logger = logging.getLogger(__name__)
        
        # ICE configuration
        self.ice_servers = ice_servers or [
            {"urls": "stun:stun.l.google.com:19302"},
            {"urls": "stun:stun1.l.google.com:19302"}
        ]
        
        # Active sessions
        self.sessions: Dict[str, WebRTCSession] = {}
        
        # Callbacks
        self.on_animation_data: Optional[Callable] = None
        self.on_audio_data: Optional[Callable] = None
        self.on_control_message: Optional[Callable] = None
        
        # Media relay for audio
        self.relay = MediaRelay()
        
        # Performance settings
        self.data_channel_options = {
            "ordered": True,
            "maxRetransmits": 3,
            "maxPacketLifeTime": None,
            "protocol": "",
            "negotiated": False,
            "id": None
        }
        
    async def create_peer_connection(self, peer_id: str) -> RTCPeerConnection:
        """Create a new peer connection"""
        self.logger.info(f"Creating peer connection for {peer_id}")
        
        # Create RTCPeerConnection
        pc = RTCPeerConnection(
            configuration={
                "iceServers": self.ice_servers
            }
        )
        
        # Add event handlers
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            self.logger.info(f"Connection state for {peer_id}: {pc.connectionState}")
            
            if pc.connectionState == "connected":
                await self._on_peer_connected(peer_id)
            elif pc.connectionState == "failed":
                await self._on_peer_failed(peer_id)
            elif pc.connectionState == "closed":
                await self._on_peer_closed(peer_id)
        
        @pc.on("datachannel")
        async def on_datachannel(channel: RTCDataChannel):
            self.logger.info(f"Data channel created: {channel.label}")
            await self._setup_data_channel(peer_id, channel)
        
        @pc.on("track")
        async def on_track(track):
            self.logger.info(f"Track received: {track.kind}")
            if track.kind == "audio":
                await self._handle_audio_track(peer_id, track)
        
        # Create session
        session = WebRTCSession(peer_id=peer_id, pc=pc)
        self.sessions[peer_id] = session
        
        return pc
    
    async def create_offer(self, peer_id: str) -> Dict[str, Any]:
        """Create WebRTC offer"""
        if peer_id not in self.sessions:
            pc = await self.create_peer_connection(peer_id)
        else:
            pc = self.sessions[peer_id].pc
        
        # Create data channel for animation data
        channel = pc.createDataChannel(
            "avatar-data",
            **self.data_channel_options
        )
        await self._setup_data_channel(peer_id, channel)
        
        # Create offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        
        return {
            "type": offer.type,
            "sdp": offer.sdp
        }
    
    async def create_answer(self, peer_id: str, offer: Dict[str, Any]) -> Dict[str, Any]:
        """Create WebRTC answer"""
        if peer_id not in self.sessions:
            pc = await self.create_peer_connection(peer_id)
        else:
            pc = self.sessions[peer_id].pc
        
        # Set remote description
        remote_desc = RTCSessionDescription(
            sdp=offer["sdp"],
            type=offer["type"]
        )
        await pc.setRemoteDescription(remote_desc)
        
        # Create answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        return {
            "type": answer.type,
            "sdp": answer.sdp
        }
    
    async def add_ice_candidate(self, peer_id: str, candidate: Dict[str, Any]):
        """Add ICE candidate"""
        if peer_id not in self.sessions:
            self.logger.error(f"Unknown peer: {peer_id}")
            return
            
        pc = self.sessions[peer_id].pc
        
        if candidate and "candidate" in candidate:
            await pc.addIceCandidate(candidate)
        else:
            # Null candidate signals end of candidates
            self.logger.info(f"End of ICE candidates for {peer_id}")
    
    async def send_animation_data(self, peer_id: str, data: Dict[str, Any]):
        """Send animation data via data channel"""
        if peer_id not in self.sessions:
            raise ValueError(f"Unknown peer: {peer_id}")
            
        session = self.sessions[peer_id]
        if not session.data_channel or session.data_channel.readyState != "open":
            raise ValueError(f"Data channel not ready for {peer_id}")
        
        # Create animation message
        message = AnimationMessage(data=data)
        
        # Send as binary for efficiency
        binary_data = self._encode_binary_message(message.dict())
        session.data_channel.send(binary_data)
    
    async def close_connection(self, peer_id: str):
        """Close peer connection"""
        if peer_id not in self.sessions:
            return
            
        session = self.sessions[peer_id]
        
        # Close data channel
        if session.data_channel:
            session.data_channel.close()
        
        # Close peer connection
        await session.pc.close()
        
        # Remove session
        del self.sessions[peer_id]
        self.logger.info(f"Closed connection for {peer_id}")
    
    async def get_stats(self, peer_id: str) -> Dict[str, Any]:
        """Get connection statistics"""
        if peer_id not in self.sessions:
            raise ValueError(f"Unknown peer: {peer_id}")
            
        session = self.sessions[peer_id]
        stats = await session.pc.getStats()
        
        # Parse relevant stats
        result = {
            "timestamp": time.time(),
            "connection_state": session.pc.connectionState,
            "ice_connection_state": session.pc.iceConnectionState,
            "data_channel_state": session.data_channel.readyState if session.data_channel else None,
            "stats": {}
        }
        
        for stat in stats.values():
            if stat.type == "candidate-pair" and stat.get("state") == "succeeded":
                result["stats"]["rtt"] = stat.get("currentRoundTripTime", 0) * 1000  # ms
                result["stats"]["bytes_sent"] = stat.get("bytesSent", 0)
                result["stats"]["bytes_received"] = stat.get("bytesReceived", 0)
            elif stat.type == "data-channel":
                result["stats"]["messages_sent"] = stat.get("messagesSent", 0)
                result["stats"]["messages_received"] = stat.get("messagesReceived", 0)
        
        return result
    
    async def _setup_data_channel(self, peer_id: str, channel: RTCDataChannel):
        """Set up data channel event handlers"""
        session = self.sessions[peer_id]
        session.data_channel = channel
        
        @channel.on("open")
        async def on_open():
            self.logger.info(f"Data channel opened for {peer_id}")
        
        @channel.on("close")
        async def on_close():
            self.logger.info(f"Data channel closed for {peer_id}")
        
        @channel.on("message")
        async def on_message(message):
            try:
                # Decode message
                if isinstance(message, bytes):
                    data = self._decode_binary_message(message)
                else:
                    data = json.loads(message)
                
                # Parse message
                msg = parse_message(data)
                
                # Handle based on type
                if msg.type == MessageType.ANIMATION and self.on_animation_data:
                    await self.on_animation_data(peer_id, msg.data)
                elif msg.type == MessageType.CONTROL and self.on_control_message:
                    await self.on_control_message(peer_id, msg.data)
                    
            except Exception as e:
                self.logger.error(f"Error handling data channel message: {e}")
    
    async def _handle_audio_track(self, peer_id: str, track):
        """Handle incoming audio track"""
        session = self.sessions[peer_id]
        session.audio_track = track
        
        if self.on_audio_data:
            # Set up audio processing
            @track.on("ended")
            async def on_ended():
                self.logger.info(f"Audio track ended for {peer_id}")
            
            # Process audio frames
            while True:
                try:
                    frame = await track.recv()
                    if frame:
                        # Convert to format expected by audio handler
                        audio_data = {
                            "data": frame.to_bytes(),
                            "sample_rate": frame.sample_rate,
                            "channels": len(frame.layout.channels),
                            "samples": frame.samples
                        }
                        await self.on_audio_data(peer_id, audio_data)
                except Exception as e:
                    self.logger.error(f"Error processing audio: {e}")
                    break
    
    def _encode_binary_message(self, data: Dict[str, Any]) -> bytes:
        """Encode message to binary format"""
        # Simple JSON encoding for now
        # Could be replaced with MessagePack or Protocol Buffers
        return json.dumps(data).encode('utf-8')
    
    def _decode_binary_message(self, data: bytes) -> Dict[str, Any]:
        """Decode binary message"""
        return json.loads(data.decode('utf-8'))
    
    async def _on_peer_connected(self, peer_id: str):
        """Handle peer connection established"""
        self.logger.info(f"Peer {peer_id} connected")
        
        # Get initial stats
        stats = await self.get_stats(peer_id)
        session = self.sessions[peer_id]
        session.stats = stats
    
    async def _on_peer_failed(self, peer_id: str):
        """Handle peer connection failure"""
        self.logger.error(f"Peer {peer_id} connection failed")
        
        # Attempt to reconnect or clean up
        await self.close_connection(peer_id)
    
    async def _on_peer_closed(self, peer_id: str):
        """Handle peer connection closed"""
        self.logger.info(f"Peer {peer_id} connection closed")
        
        # Clean up
        if peer_id in self.sessions:
            del self.sessions[peer_id]


# Fallback for when WebRTC is not available
class WebRTCFallback:
    """Fallback implementation when WebRTC is not available"""
    
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.logger.warning("WebRTC not available - using fallback mode")
    
    async def create_peer_connection(self, peer_id: str):
        raise NotImplementedError("WebRTC support not available. Install 'aiortc' package.")
    
    async def create_offer(self, peer_id: str):
        raise NotImplementedError("WebRTC support not available. Install 'aiortc' package.")
    
    async def create_answer(self, peer_id: str, offer: Dict[str, Any]):
        raise NotImplementedError("WebRTC support not available. Install 'aiortc' package.")


# Export appropriate class based on availability
if WEBRTC_AVAILABLE:
    WebRTCHandlerClass = WebRTCHandler
else:
    WebRTCHandlerClass = WebRTCFallback