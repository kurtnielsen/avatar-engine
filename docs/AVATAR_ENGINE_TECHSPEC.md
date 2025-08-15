# Avatar Engine - Technical Specification

## 1. Tech Stack Summary

### 1.1 Backend Technologies
- **Language**: Python 3.8+
- **Framework**: FastAPI (async REST/WebSocket server) - `backend/app/api/v1/facial_animation_dashboard.py`
- **Real-time**: aiortc (WebRTC implementation) - `facial_animation_unified_system.py:14-16`
- **Async**: asyncio, aiofiles
- **Serialization**: JSON, MessagePack (binary) - `backend/compression/delta_compressor.py:428`
- **Compression**: zlib, custom delta compression - `backend/compression/delta_compressor.py:DeltaCompressor`

### 1.2 Frontend Technologies
- **Language**: JavaScript ES6+
- **3D Engine**: Three.js r140+
- **WebRTC**: Native browser APIs
- **Module System**: ES6 modules with importmap
- **Build**: No build step (native modules)

### 1.3 Communication Protocols
- **Primary**: WebRTC DataChannel (unreliable, unordered)
- **Fallback**: WebSocket (reliable, ordered)
- **REST**: HTTP/HTTPS for configuration
- **Binary**: MessagePack for efficiency

### 1.4 Development Tools
- **Testing**: pytest, headless simulation
- **Benchmarking**: Custom performance framework
- **Monitoring**: Built-in metrics collection
- **Documentation**: Markdown, inline code docs

## 2. Data Flow Architecture

### 2.1 Input Processing Pipeline

**Implementation Files:**
- ARKit Mapper: `facial_animation_mapper_enhanced.py:EnhancedFacialAnimationMapper:100-350`
- Viseme Engine: `viseme_transition_engine.py:VisemeTransitionEngine:15-180`
- Emotion Blender: `enhanced_facial_animation_system.py:blend_emotion_with_speech:200-280`
- Micro-expression: `facial_animation_mapper_enhanced.py:apply_micro_expressions:400-450`
- Temporal Smoother: `facial_animation_performance_optimizer.py:SmoothingFilter:50-120`
- Performance Optimizer: `facial_animation_performance_optimizer.py:FacialAnimationPerformanceOptimizer`

```
ARKit Device          Viseme Generator
     |                      |
     v                      v
[UDP Socket]          [REST API]
     |                      |
     v                      v
Input Validator      Phoneme Processor
     |                      |
     v                      v
    ARKit Mapper      Viseme Engine
          |                |
          v                v
      Emotion Blender <----+
              |
              v
       Micro-expression Generator
              |
              v
       Temporal Smoother
              |
              v
       Performance Optimizer
```

### 2.2 Network Pipeline

**Implementation Files:**
- Delta Compressor: `backend/compression/delta_compressor.py:DeltaCompressor:compress`
- WebRTC Handler: `facial_animation_unified_system.py:create_peer_connection:75-110`
- WebSocket Server: `facial_animation_department_dashboard_webrtc.py:WebSocketHandler:50-150`

```
Optimized Morphs
       |
       v
Delta Compressor
       |
   +---+---+
   |       |
   v       v
WebRTC  WebSocket
   |       |
   v       v
Client  Client
```

### 2.3 Client Rendering Pipeline

**Implementation Files:**
- Client Decompressor: `facial_animation_webrtc_client.js:decompressData`
- Frame Buffer: `facial_animation_client_optimized.js:FrameBuffer`
- Interpolator: `facial_animation_client_optimized.js:interpolateMorphs`
- LOD Filter: `facial_animation_client_optimized.js:LODManager:200-300`
- Morph Updater: `facial_animation_webrtc_client.js:updateMorphTargets:150-250`
- Three.js Renderer: `facial_animation_client_optimized.js:AvatarRenderer`

```
Network Data
     |
     v
Decompressor
     |
     v
Frame Buffer
     |
     v
Interpolator
     |
     v
LOD Filter
     |
     v
Morph Updater
     |
     v
Three.js Renderer
```

## 3. APIs & Interfaces

### 3.1 WebSocket API

#### Connection
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8766/ws');

// Connection events
ws.onopen = () => console.log('Connected');
ws.onclose = () => console.log('Disconnected');
ws.onerror = (error) => console.error('Error:', error);
```

#### Message Format
```typescript
// Server -> Client
interface BlendshapeUpdate {
    type: 'blendshape_update';
    data: Record<string, number>;  // morph_name -> value (0-1)
    timestamp: number;              // Unix timestamp
    frame: number;                  // Frame counter
    emotion?: string;               // Current emotion
    is_speaking: boolean;          // Speech state
}

interface PerformanceMetrics {
    type: 'performance_metrics';
    fps: number;
    latency_ms: number;
    active_morphs: number;
    compression_ratio: number;
}

// Client -> Server
interface SetEmotion {
    type: 'set_emotion';
    emotion: 'happy' | 'sad' | 'angry' | 'surprised' | 'fear' | 'disgust' | 'contempt';
    intensity: number;  // 0-1
}

interface ARKitData {
    type: 'arkit_data';
    blendshapes: Record<string, number>;
    timestamp?: string;
}

interface VisemeData {
    type: 'viseme_data';
    viseme: string;
    weight: number;
    duration_ms: number;
}
```

### 3.2 REST API

#### Endpoints
```yaml
# WebRTC Offer/Answer
POST /api/v1/rtc/offer
Request:
  {
    "sdp": "string",
    "type": "offer",
    "session_id": "string"
  }
Response:
  {
    "sdp": "string",
    "type": "answer",
    "session_id": "string"
  }

# Emotion Control
POST /api/v1/emotion
Request:
  {
    "emotion": "string",
    "intensity": 0.0-1.0
  }
Response:
  {
    "status": "ok",
    "emotion": "string",
    "intensity": number
  }

# Performance Stats
GET /api/v1/stats
Response:
  {
    "fps": number,
    "avg_frame_time_ms": number,
    "avg_morph_time_ms": number,
    "avg_active_morphs": number,
    "cache_hit_rate": number,
    "active_connections": number,
    "current_lod_level": "string"
  }

# Health Check
GET /api/v1/health
Response:
  {
    "status": "healthy",
    "version": "1.0.0",
    "uptime_seconds": number
  }
```

### 3.3 WebRTC DataChannel Protocol

#### Binary Format (MessagePack)
```python
# Compressed morph update
{
    't': 1,  # Type: 1=morph_update
    'd': {   # Delta morphs
        'V_Open': 0.5,
        'Mouth_Smile_L': 0.8
    },
    'f': 12345,  # Frame number
    'e': 1,      # Emotion: 1=happy
}

# Full state update
{
    't': 2,  # Type: 2=full_update
    'd': {   # All morphs
        # ... complete morph dictionary
    },
    'f': 12346
}
```

## 4. Model Orchestration & AI Logic

### 4.1 ARKit to CC4 Mapping

**Source File**: `facial_animation_mapper_enhanced.py:EnhancedFacialAnimationMapper:map_arkit_to_cc4:100-200`

#### Mapping Algorithm
```python
class EnhancedFacialAnimationMapper:
    def map_arkit_to_cc4(self, arkit_data: Dict[str, float]) -> Dict[str, float]:
        cc4_morphs = {}
        
        # Direct mappings with weights
        mappings = {
            'jawOpen': [('V_Open', 0.7), ('V_AA', 0.3)],
            'mouthSmileLeft': [('Mouth_Smile_L', 0.8), ('Cheek_Squint_L', 0.2)],
            'eyeBlinkLeft': [('Eye_Blink_L', 1.0), ('Eye_Squint_L', 0.1)]
        }
        
        # Apply weighted mappings
        for arkit_shape, targets in mappings.items():
            if arkit_shape in arkit_data:
                value = arkit_data[arkit_shape]
                for cc4_shape, weight in targets:
                    cc4_morphs[cc4_shape] = cc4_morphs.get(cc4_shape, 0) + value * weight
        
        # Apply limits and smoothing
        return self.apply_constraints(cc4_morphs)
```

### 4.2 Emotion System

**Source File**: `enhanced_facial_animation_system.py:EmotionSystem:45-120`

#### Emotion Blending
```python
# Emotion presets (additive on top of base expression)
EMOTION_PRESETS = {
    'happy': {
        'Mouth_Smile_L': 0.6,
        'Mouth_Smile_R': 0.6,
        'Cheek_Squint_L': 0.3,
        'Cheek_Squint_R': 0.3,
        'Eye_Squint_L': 0.1,
        'Eye_Squint_R': 0.1
    },
    'sad': {
        'Mouth_Frown_L': 0.5,
        'Mouth_Frown_R': 0.5,
        'Brow_Drop_L': 0.4,
        'Brow_Drop_R': 0.4,
        'Eye_Look_Down_L': 0.2,
        'Eye_Look_Down_R': 0.2
    }
}

def blend_emotion(base_morphs: Dict, emotion: str, intensity: float) -> Dict:
    """Blend emotion on top of base expression"""
    result = base_morphs.copy()
    if emotion in EMOTION_PRESETS:
        for morph, value in EMOTION_PRESETS[emotion].items():
            current = result.get(morph, 0.0)
            # Additive blending with saturation
            result[morph] = min(1.0, current + value * intensity)
    return result
```

### 4.3 Micro-Expression Engine

**Source File**: `facial_animation_mapper_enhanced.py:apply_micro_expressions:400-450`

#### Generation Algorithm
```python
class MicroExpressionGenerator:
    def generate(self, expression_type: str, progress: float) -> Dict[str, float]:
        """Generate micro-expression with bell curve intensity"""
        # Bell curve: 0->1->0 over duration
        intensity = math.sin(progress * math.pi)
        
        expressions = {
            'subtle_smile': {
                'Mouth_Smile_L': 0.2 * intensity,
                'Mouth_Smile_R': 0.2 * intensity
            },
            'eye_flash': {
                'Eye_Wide_L': 0.3 * intensity,
                'Eye_Wide_R': 0.3 * intensity,
                'Brow_Raise_L': 0.2 * intensity,
                'Brow_Raise_R': 0.2 * intensity
            }
        }
        
        return expressions.get(expression_type, {})
```

### 4.4 Viseme Processing

**Source File**: `viseme_transition_engine.py:VisemeTransitionEngine:calculate_transition:220-300`

#### Co-articulation Model
```python
class VisemeTransitionEngine:
    def calculate_transition(self, from_viseme: str, to_viseme: str, 
                           progress: float) -> Dict[str, float]:
        """Calculate smooth transition between visemes"""
        # Get base shapes
        from_shapes = VISEME_SHAPES[from_viseme]
        to_shapes = VISEME_SHAPES[to_viseme]
        
        # Apply co-articulation rules
        if self.is_bilabial(from_viseme) and self.is_vowel(to_viseme):
            # Slower release for bilabial->vowel
            progress = self.ease_out_cubic(progress)
        
        # Interpolate with easing
        result = {}
        all_morphs = set(from_shapes.keys()) | set(to_shapes.keys())
        for morph in all_morphs:
            from_val = from_shapes.get(morph, 0.0)
            to_val = to_shapes.get(morph, 0.0)
            result[morph] = from_val + (to_val - from_val) * progress
        
        return result
```

## 5. Communication Protocols

### 5.1 WebRTC Configuration

#### ICE Servers
```javascript
const configuration = {
    iceServers: [
        {
            urls: 'stun:stun.l.google.com:19302'
        },
        {
            urls: 'turn:turnserver.com:3478',
            username: 'user',
            credential: 'pass'
        }
    ],
    iceCandidatePoolSize: 10
};
```

#### DataChannel Options
```javascript
const dataChannelOptions = {
    ordered: false,              // No ordering required
    maxPacketLifeTime: null,     // No time-based retransmit
    maxRetransmits: 0,          // No retransmissions
    protocol: 'animation-data',  // Custom protocol identifier
    negotiated: false,          // Not pre-negotiated
    id: null                    // Auto-assign ID
};
```

### 5.2 Message Prioritization

```python
class MessagePriority(Enum):
    CRITICAL = 1   # Connection control
    HIGH = 2       # Morph updates
    MEDIUM = 3     # Emotion changes
    LOW = 4        # Metrics/stats

class MessageQueue:
    def __init__(self):
        self.queues = {p: asyncio.Queue() for p in MessagePriority}
    
    async def get_next(self) -> Message:
        """Get highest priority message"""
        for priority in MessagePriority:
            if not self.queues[priority].empty():
                return await self.queues[priority].get()
        # Wait for any message
        return await self._wait_any()
```

### 5.3 Compression Protocol

**Source File**: `backend/compression/delta_compressor.py:DeltaCompressor:compress`

#### Delta Compression
```python
class DeltaCompressor:
    def compress(self, current: Dict, previous: Dict) -> bytes:
        """Compress using delta encoding"""
        delta = {}
        
        # Find changes
        for key, value in current.items():
            if key not in previous or abs(value - previous[key]) > 0.001:
                delta[key] = value
        
        # Remove zeros
        for key, value in previous.items():
            if key not in current and value > 0.001:
                delta[key] = 0.0
        
        # Pack with MessagePack
        return msgpack.packb(delta, use_bin_type=True)
```

## 6. Database Schemas

### 6.1 Performance Metrics Storage
```sql
-- Real-time metrics (in-memory)
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fps FLOAT,
    latency_ms FLOAT,
    cpu_percent FLOAT,
    memory_mb FLOAT,
    active_morphs INTEGER,
    compression_ratio FLOAT
);

-- Session metadata
CREATE TABLE animation_sessions (
    id VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    client_ip VARCHAR(45),
    connection_type VARCHAR(20), -- 'webrtc' or 'websocket'
    user_agent TEXT,
    quality_preset VARCHAR(20),
    ended_at TIMESTAMP
);

-- Aggregated stats (hourly)
CREATE TABLE performance_stats_hourly (
    hour TIMESTAMP PRIMARY KEY,
    avg_fps FLOAT,
    p95_latency_ms FLOAT,
    total_sessions INTEGER,
    total_frames BIGINT,
    avg_session_duration_seconds FLOAT
);
```

### 6.2 Configuration Storage
```sql
-- Avatar configurations
CREATE TABLE avatar_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE,
    morph_mappings JSONB,
    emotion_presets JSONB,
    quality_settings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User preferences
CREATE TABLE user_preferences (
    user_id VARCHAR(255) PRIMARY KEY,
    default_quality VARCHAR(20),
    enable_emotions BOOLEAN DEFAULT true,
    enable_micro_expressions BOOLEAN DEFAULT true,
    custom_mappings JSONB
);
```

## 7. Error Handling & Recovery

### 7.1 Error Categories

```python
class AnimationError(Exception):
    """Base animation error"""
    pass

class NetworkError(AnimationError):
    """Network-related errors"""
    error_code: str
    retry_after: Optional[float]

class ProcessingError(AnimationError):
    """Processing pipeline errors"""
    stage: str
    recoverable: bool

class PerformanceError(AnimationError):
    """Performance degradation"""
    current_fps: float
    target_fps: float
```

### 7.2 Recovery Strategies

#### Network Recovery
```python
async def handle_network_error(error: NetworkError):
    if error.error_code == 'CONNECTION_LOST':
        # Attempt reconnection with exponential backoff
        for attempt in range(MAX_RETRIES):
            wait_time = min(2 ** attempt, MAX_WAIT)
            await asyncio.sleep(wait_time)
            try:
                await reconnect()
                break
            except:
                continue
    
    elif error.error_code == 'CHANNEL_FULL':
        # Switch to fallback mode
        await switch_to_websocket()
```

#### Performance Recovery
```python
async def handle_performance_degradation(metrics: PerformanceMetrics):
    if metrics.fps < CRITICAL_FPS:
        # Emergency mode - minimal morphs only
        optimizer.set_mode('emergency')
    elif metrics.fps < WARNING_FPS:
        # Reduce quality progressively
        optimizer.reduce_quality_level()
    
    # Log for analysis
    await log_performance_event(metrics)
```

### 7.3 State Recovery

```python
class StateManager:
    def __init__(self):
        self.checkpoint_interval = 60  # seconds
        self.state_buffer = deque(maxlen=10)
    
    async def checkpoint(self, state: AnimationState):
        """Save state checkpoint"""
        self.state_buffer.append({
            'timestamp': time.time(),
            'morphs': state.current_morphs.copy(),
            'emotion': state.emotion,
            'frame': state.frame_count
        })
    
    async def recover(self, target_time: float) -> AnimationState:
        """Recover to nearest checkpoint"""
        for checkpoint in reversed(self.state_buffer):
            if checkpoint['timestamp'] <= target_time:
                return AnimationState.from_checkpoint(checkpoint)
        return AnimationState.default()
```

## 8. Performance Benchmarks

### 8.1 Latency Breakdown
```
Component               | Time (ms) | Percentage
------------------------|-----------|------------
ARKit Capture          | 5-8       | 20%
Network Transmission   | 2-5       | 10%
Server Processing      | 8-12      | 35%
Client Decompression   | 1-2       | 5%
Render Update          | 6-10      | 30%
------------------------|-----------|------------
Total                  | 22-37     | 100%
```

### 8.2 Throughput Metrics
```
Metric                  | Value
------------------------|------------------
Messages per second     | 60-120
Morphs per message      | 15-25 (average)
Bytes per message       | 200-400 (compressed)
Bandwidth per avatar    | 15-20 KB/s
CPU per avatar          | 15-25%
Memory per avatar       | 80-150 MB
```

### 8.3 Scalability Limits
```
Avatars | FPS  | CPU  | Memory | Network
--------|------|------|--------|----------
1       | 120  | 15%  | 150MB  | 20KB/s
5       | 90   | 45%  | 600MB  | 90KB/s
10      | 60   | 75%  | 1.1GB  | 180KB/s
20      | 30   | 95%  | 2.0GB  | 350KB/s
```

## 9. Security Measures

### 9.1 Authentication
```python
# JWT token validation
async def validate_token(token: str) -> Optional[User]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return await get_user(payload['user_id'])
    except jwt.InvalidTokenError:
        return None

# WebSocket authentication
async def authenticate_websocket(websocket: WebSocket):
    token = await websocket.receive_text()
    user = await validate_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return None
    return user
```

### 9.2 Input Validation
```python
class MorphValidator:
    @staticmethod
    def validate_morphs(morphs: Dict[str, float]) -> Dict[str, float]:
        validated = {}
        for name, value in morphs.items():
            # Sanitize name
            if not re.match(r'^[A-Za-z0-9_]+$', name):
                continue
            # Clamp value
            validated[name] = max(0.0, min(1.0, float(value)))
        return validated
```

### 9.3 Rate Limiting
```python
class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(deque)
    
    async def check_limit(self, client_id: str) -> bool:
        now = time.time()
        requests = self.requests[client_id]
        
        # Remove old requests
        while requests and requests[0] < now - self.window:
            requests.popleft()
        
        # Check limit
        if len(requests) >= self.max_requests:
            return False
        
        requests.append(now)
        return True
```

## 10. Monitoring & Logging

### 10.1 Metrics Collection
```python
class MetricsCollector:
    def __init__(self):
        self.metrics = {
            'fps': deque(maxlen=300),
            'latency': deque(maxlen=300),
            'morphs': deque(maxlen=300),
            'errors': Counter()
        }
    
    async def collect(self):
        """Collect metrics every second"""
        while True:
            snapshot = {
                'timestamp': time.time(),
                'fps': self.calculate_fps(),
                'latency': self.get_avg_latency(),
                'active_connections': len(self.connections),
                'memory_usage': self.get_memory_usage()
            }
            await self.store_snapshot(snapshot)
            await asyncio.sleep(1.0)
```

### 10.2 Logging Configuration
```python
import logging
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Usage
logger = structlog.get_logger()
logger.info("animation_processed", 
    session_id=session_id,
    morphs_count=len(morphs),
    processing_time_ms=processing_time * 1000
)
```

### 10.3 Performance Profiling
```python
import cProfile
import pstats
from line_profiler import LineProfiler

class PerformanceProfiler:
    def __init__(self):
        self.profiler = cProfile.Profile()
        self.line_profiler = LineProfiler()
    
    def profile_function(self, func):
        """Decorator for function profiling"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            self.profiler.enable()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                self.profiler.disable()
                self.save_profile(func.__name__)
        return wrapper
    
    def save_profile(self, function_name: str):
        stats = pstats.Stats(self.profiler)
        stats.sort_stats('cumulative')
        stats.dump_stats(f'profiles/{function_name}_{time.time()}.prof')
```

## 11. Deployment Configuration

### 11.1 Docker Configuration
```dockerfile
FROM python:3.8-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose ports
EXPOSE 8766 8767

# Run application
CMD ["uvicorn", "facial_animation_unified_system:app", \
     "--host", "0.0.0.0", "--port", "8766", \
     "--workers", "4", "--loop", "uvloop"]
```

### 11.2 Environment Variables
```bash
# Network Configuration
AVATAR_HOST=0.0.0.0
AVATAR_PORT=8766
AVATAR_WEBSOCKET_PORT=8767

# WebRTC Configuration
STUN_SERVERS=stun:stun.l.google.com:19302
TURN_SERVER_URL=turn:turnserver.com:3478
TURN_USERNAME=user
TURN_PASSWORD=pass

# Performance Settings
TARGET_FPS=60
MAX_AVATARS=20
COMPRESSION_LEVEL=5
CACHE_SIZE_MB=500

# Monitoring
METRICS_ENABLED=true
METRICS_INTERVAL_SECONDS=60
LOG_LEVEL=INFO

# Security
JWT_SECRET_KEY=your-secret-key
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW=60
```

### 11.3 Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: avatar-engine
spec:
  replicas: 3
  selector:
    matchLabels:
      app: avatar-engine
  template:
    metadata:
      labels:
        app: avatar-engine
    spec:
      containers:
      - name: avatar-engine
        image: avatar-engine:latest
        ports:
        - containerPort: 8766
          name: http
        - containerPort: 8767
          name: websocket
        env:
        - name: TARGET_FPS
          value: "60"
        - name: MAX_AVATARS
          value: "20"
        resources:
          requests:
            memory: "1Gi"
            cpu: "1"
          limits:
            memory: "2Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8766
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8766
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: avatar-engine
spec:
  selector:
    app: avatar-engine
  ports:
    - name: http
      port: 80
      targetPort: 8766
    - name: websocket
      port: 8767
      targetPort: 8767
  type: LoadBalancer
```

## 12. Testing Strategy

### 12.1 Unit Tests
```python
# Test ARKit mapping
async def test_arkit_mapping():
    mapper = EnhancedFacialAnimationMapper()
    arkit_data = {
        'jawOpen': 0.5,
        'mouthSmileLeft': 0.8,
        'eyeBlinkLeft': 1.0
    }
    
    cc4_morphs = mapper.map_arkit_to_cc4(arkit_data)
    
    assert 'V_Open' in cc4_morphs
    assert 0.3 <= cc4_morphs['V_Open'] <= 0.4
    assert cc4_morphs['Eye_Blink_L'] == 1.0
```

### 12.2 Integration Tests
```python
# Test WebSocket connection
async def test_websocket_connection():
    async with websockets.connect('ws://localhost:8766/ws') as ws:
        # Send test data
        await ws.send(json.dumps({
            'type': 'arkit_data',
            'blendshapes': {'jawOpen': 0.5}
        }))
        
        # Receive response
        response = await ws.recv()
        data = json.loads(response)
        
        assert data['type'] == 'blendshape_update'
        assert 'V_Open' in data['data']
```

### 12.3 Performance Tests
```python
# Benchmark latency
async def test_end_to_end_latency():
    latencies = []
    
    for _ in range(100):
        start = time.time()
        
        # Send data
        await send_arkit_data(test_data)
        
        # Wait for response
        response = await receive_update()
        
        latency = (time.time() - start) * 1000
        latencies.append(latency)
    
    avg_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[95]
    
    assert avg_latency < 30  # Average under 30ms
    assert p95_latency < 50  # P95 under 50ms
```

## 13. Glossary of Technical Terms

- **Blendshape**: Mesh deformation defining facial expression
- **DataChannel**: WebRTC peer-to-peer data communication channel
- **Delta Compression**: Sending only changed values between frames
- **LOD (Level of Detail)**: Quality reduction based on distance/performance
- **MessagePack**: Efficient binary serialization format
- **Morph Target**: Alternative term for blendshape
- **P95/P99**: 95th/99th percentile metrics
- **STUN/TURN**: Protocols for NAT traversal in WebRTC
- **Temporal Smoothing**: Averaging values over time to reduce jitter
- **Viseme**: Visual representation of a phoneme