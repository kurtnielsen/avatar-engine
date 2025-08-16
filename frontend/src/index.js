/**
 * Avatar Engine Frontend
 * Main entry point for the avatar animation system
 */

import { OptimizedMorphSystem } from './OptimizedMorphSystem.js';
import { PerformanceMonitor } from './PerformanceMonitor.js';

// Re-export main components
export { OptimizedMorphSystem } from './OptimizedMorphSystem.js';
export { PerformanceMonitor } from './PerformanceMonitor.js';

// Main AvatarEngine class
export class AvatarEngine {
    constructor(config = {}) {
        this.config = {
            container: config.container || document.body,
            modelUrl: config.modelUrl,
            apiUrl: config.apiUrl || 'ws://localhost:8080/avatar',
            quality: config.quality || 'high',
            debug: config.debug || false,
            ...config
        };

        this.morphSystem = null;
        this.performanceMonitor = null;
        this.ws = null;
        this.avatarId = config.avatarId || this.generateAvatarId();
    }

    generateAvatarId() {
        return `avatar_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    async initialize() {
        try {
            // Initialize morph system
            this.morphSystem = new OptimizedMorphSystem(this.config);
            await this.morphSystem.initialize();

            // Initialize performance monitor
            if (this.config.debug) {
                this.performanceMonitor = new PerformanceMonitor();
                this.performanceMonitor.attach(this.config.container);
            }

            // Connect to WebSocket
            await this.connect();

            return true;
        } catch (error) {
            console.error('Failed to initialize Avatar Engine:', error);
            throw error;
        }
    }

    async connect() {
        return new Promise((resolve, reject) => {
            const wsUrl = `${this.config.apiUrl}/${this.avatarId}`;
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('Connected to Avatar Engine backend');
                resolve();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            };

            this.ws.onmessage = (event) => {
                this.handleMessage(event);
            };

            this.ws.onclose = () => {
                console.log('Disconnected from Avatar Engine backend');
                this.handleDisconnect();
            };
        });
    }

    handleMessage(event) {
        if (event.data instanceof Blob) {
            // Handle binary data (compressed animation)
            event.data.arrayBuffer().then(buffer => {
                const data = this.decompressData(buffer);
                this.morphSystem.applyAnimation(data);
            });
        } else {
            // Handle JSON messages
            try {
                const message = JSON.parse(event.data);
                this.handleJsonMessage(message);
            } catch (error) {
                console.error('Failed to parse message:', error);
            }
        }
    }

    handleJsonMessage(message) {
        switch (message.type) {
            case 'visemes':
                this.morphSystem.applyVisemes(message.data);
                break;
            case 'ack':
                console.log('Acknowledgment:', message.action);
                break;
            default:
                console.warn('Unknown message type:', message.type);
        }
    }

    decompressData(buffer) {
        // Simple decompression placeholder
        // In production, use proper decompression matching backend
        return new Float32Array(buffer);
    }

    animate(data) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('Not connected to backend');
            return;
        }

        this.ws.send(JSON.stringify({
            type: 'animation',
            timestamp: Date.now(),
            data: data
        }));
    }

    sendAudio(audioData, sampleRate = 48000) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('Not connected to backend');
            return;
        }

        this.ws.send(JSON.stringify({
            type: 'audio',
            audio: audioData,
            sampleRate: sampleRate
        }));
    }

    start() {
        if (this.morphSystem) {
            this.morphSystem.start();
        }
        if (this.performanceMonitor) {
            this.performanceMonitor.start();
        }
    }

    stop() {
        if (this.morphSystem) {
            this.morphSystem.stop();
        }
        if (this.performanceMonitor) {
            this.performanceMonitor.stop();
        }
    }

    dispose() {
        this.stop();
        
        if (this.ws) {
            this.ws.close();
        }
        
        if (this.morphSystem) {
            this.morphSystem.dispose();
        }
        
        if (this.performanceMonitor) {
            this.performanceMonitor.dispose();
        }
    }

    handleDisconnect() {
        // Implement reconnection logic
        setTimeout(() => {
            console.log('Attempting to reconnect...');
            this.connect().catch(error => {
                console.error('Reconnection failed:', error);
            });
        }, 5000);
    }

    getMetrics() {
        return {
            fps: this.morphSystem?.getCurrentFPS() || 0,
            latency: this.performanceMonitor?.getLatency() || 0,
            drawCalls: this.morphSystem?.getDrawCalls() || 0
        };
    }

    setQuality(quality) {
        this.config.quality = quality;
        if (this.morphSystem) {
            this.morphSystem.setQuality(quality);
        }
    }
}

// Widget for easy integration
export class AvatarWidget {
    constructor(config) {
        this.config = config;
        this.engine = null;
        this.container = null;
    }

    async mount(containerElement) {
        this.container = containerElement;
        
        // Create avatar container
        const avatarDiv = document.createElement('div');
        avatarDiv.style.width = `${this.config.width || 400}px`;
        avatarDiv.style.height = `${this.config.height || 300}px`;
        avatarDiv.style.position = 'relative';
        this.container.appendChild(avatarDiv);

        // Initialize engine
        this.engine = new AvatarEngine({
            ...this.config,
            container: avatarDiv
        });

        await this.engine.initialize();
        this.engine.start();

        return this.engine;
    }

    unmount() {
        if (this.engine) {
            this.engine.dispose();
        }
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Auto-initialize if data attribute present
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        const autoElements = document.querySelectorAll('[data-avatar-engine]');
        autoElements.forEach(element => {
            const config = JSON.parse(element.dataset.avatarEngine || '{}');
            const widget = new AvatarWidget(config);
            widget.mount(element);
        });
    });
}