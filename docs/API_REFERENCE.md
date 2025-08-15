# Avatar Engine API Reference

## Overview

The Avatar Engine provides WebSocket and HTTP APIs for real-time facial animation control.

## WebSocket API

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8080/avatar');
```

### Message Protocol

#### Animation Data
```json
{
  "type": "animation",
  "timestamp": 1234567890,
  "data": {
    "blendshapes": {
      "jawOpen": 0.5,
      "lipFunnel": 0.3,
      "mouthSmile": 0.2
    },
    "audio": {
      "chunk": "base64_encoded_audio",
      "sampleRate": 48000
    }
  }
}
```

#### Control Messages
```json
{
  "type": "control",
  "action": "start|stop|pause|resume",
  "avatarId": "avatar_123"
}
```

## HTTP API

### POST /api/v1/avatar/create
Creates a new avatar instance.

**Request:**
```json
{
  "modelUrl": "https://example.com/model.glb",
  "config": {
    "quality": "high",
    "fps": 60,
    "protocol": "webrtc"
  }
}
```

**Response:**
```json
{
  "avatarId": "avatar_123",
  "websocketUrl": "ws://localhost:8080/avatar/avatar_123",
  "status": "ready"
}
```

### GET /api/v1/avatar/{avatarId}/status
Get avatar status and metrics.

**Response:**
```json
{
  "avatarId": "avatar_123",
  "status": "active",
  "metrics": {
    "fps": 58.2,
    "latency": 28,
    "bandwidth": 15240
  }
}
```

### POST /api/v1/avatar/{avatarId}/animation
Send animation data via HTTP (for testing).

**Request:**
```json
{
  "blendshapes": {
    "jawOpen": 0.5,
    "lipFunnel": 0.3
  }
}
```

## Blend Shape Reference

### Core Animation Targets
- `eyeBlinkLeft` (0-1): Left eye blink
- `eyeBlinkRight` (0-1): Right eye blink
- `eyeLookUpLeft` (0-1): Left eye look up
- `eyeLookDownLeft` (0-1): Left eye look down
- `browInnerUp` (0-1): Inner brow raise
- `browOuterUpLeft` (0-1): Left outer brow raise

### Speech Visemes
- `viseme_AA` (0-1): "ah" sound
- `viseme_EE` (0-1): "ee" sound
- `viseme_II` (0-1): "ih" sound
- `viseme_OH` (0-1): "oh" sound
- `viseme_UU` (0-1): "oo" sound

### Mouth Shapes
- `jawOpen` (0-1): Jaw opening
- `mouthFunnel` (0-1): Lips funnel shape
- `mouthPucker` (0-1): Lips pucker
- `mouthLeft` (0-1): Mouth shift left
- `mouthRight` (0-1): Mouth shift right
- `mouthSmileLeft` (0-1): Left smile
- `mouthSmileRight` (0-1): Right smile

## Error Codes

| Code | Description |
|------|-------------|
| 1001 | Invalid avatar ID |
| 1002 | WebSocket connection failed |
| 1003 | Invalid animation data |
| 1004 | Rate limit exceeded |
| 2001 | Model loading failed |
| 2002 | Renderer initialization failed |
| 3001 | Protocol negotiation failed |