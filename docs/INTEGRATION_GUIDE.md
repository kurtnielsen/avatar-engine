# Avatar Engine Integration Guide

## Quick Start

### 1. Install Dependencies

#### NPM Package
```bash
npm install @neureval/avatar-engine
```

#### CDN
```html
<script src="https://unpkg.com/@neureval/avatar-engine@latest/dist/avatar-engine.min.js"></script>
```

### 2. Basic Integration

```javascript
import { AvatarEngine } from '@neureval/avatar-engine';

// Initialize
const engine = new AvatarEngine({
  container: document.getElementById('avatar-container'),
  modelUrl: '/models/avatar.glb',
  apiUrl: 'ws://localhost:8080/avatar'
});

// Start rendering
await engine.initialize();
engine.start();

// Send animation data
engine.animate({
  blendshapes: {
    jawOpen: 0.5,
    mouthSmile: 0.3
  }
});
```

## Dashboard Widget Integration

### React Component

```jsx
import { AvatarWidget } from '@neureval/avatar-engine/react';

function Dashboard() {
  return (
    <AvatarWidget
      avatarId="user_123"
      width={400}
      height={300}
      quality="high"
      onReady={(engine) => console.log('Avatar ready', engine)}
      onError={(error) => console.error('Avatar error', error)}
    />
  );
}
```

### Vanilla JavaScript

```html
<div id="avatar-widget"></div>

<script>
  const widget = new AvatarEngine.Widget({
    container: 'avatar-widget',
    config: {
      width: 400,
      height: 300,
      autoConnect: true
    }
  });
  
  widget.on('ready', () => {
    console.log('Widget ready');
  });
</script>
```

## Advanced Configuration

### Performance Optimization

```javascript
const engine = new AvatarEngine({
  performance: {
    targetFPS: 30,           // Lower for mobile
    adaptiveQuality: true,   // Auto-adjust quality
    maxVertices: 50000,      // Limit mesh complexity
    textureSize: 1024        // Smaller textures
  },
  compression: {
    enabled: true,
    algorithm: 'delta',      // Use delta compression
    keyframeInterval: 60     // Keyframe every 60 frames
  }
});
```

### Multi-Avatar Support

```javascript
const manager = new AvatarEngine.Manager({
  maxAvatars: 10,
  pooling: true,
  loadBalancing: 'round-robin'
});

// Add avatars
const avatar1 = await manager.createAvatar({ id: 'avatar1' });
const avatar2 = await manager.createAvatar({ id: 'avatar2' });

// Animate specific avatar
manager.animate('avatar1', { jawOpen: 0.5 });
```

### WebRTC Integration

```javascript
const engine = new AvatarEngine({
  protocol: 'webrtc',
  rtc: {
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' }
    ],
    videoCodec: 'vp9',
    audioCodec: 'opus'
  }
});

// Handle WebRTC events
engine.on('peer:connected', (peer) => {
  console.log('Peer connected', peer.id);
});
```

## Event Handling

```javascript
engine.on('frame', (metrics) => {
  console.log(`FPS: ${metrics.fps}, Latency: ${metrics.latency}ms`);
});

engine.on('error', (error) => {
  console.error('Avatar error:', error);
  // Implement fallback
});

engine.on('quality:changed', (quality) => {
  console.log('Quality adjusted to:', quality);
});
```

## Troubleshooting

### Common Issues

1. **Black screen / Avatar not visible**
   ```javascript
   // Check WebGL support
   if (!engine.isWebGLSupported()) {
     console.error('WebGL not supported');
   }
   
   // Enable debug mode
   engine.debug = true;
   ```

2. **Poor performance**
   ```javascript
   // Reduce quality settings
   engine.setQuality('low');
   
   // Check metrics
   const metrics = engine.getMetrics();
   console.log('Draw calls:', metrics.drawCalls);
   ```

3. **Connection issues**
   ```javascript
   // Implement reconnection
   engine.on('disconnect', () => {
     setTimeout(() => engine.reconnect(), 1000);
   });
   ```

### Debug Mode

```javascript
const engine = new AvatarEngine({
  debug: {
    showStats: true,
    showWireframe: false,
    logLevel: 'verbose'
  }
});
```

## Best Practices

1. **Preload Models**
   ```javascript
   await AvatarEngine.preloadModel('/models/avatar.glb');
   ```

2. **Cleanup Resources**
   ```javascript
   // Always dispose when done
   engine.dispose();
   ```

3. **Handle Network Changes**
   ```javascript
   window.addEventListener('online', () => engine.reconnect());
   window.addEventListener('offline', () => engine.pause());
   ```

4. **Mobile Optimization**
   ```javascript
   if (AvatarEngine.isMobile()) {
     engine.setQuality('low');
     engine.setMaxFPS(30);
   }
   ```