/**
 * Optimized Facial Animation Client
 * Handles delta decompression, frame interpolation, and performance monitoring
 */

class OptimizedFacialAnimationClient {
    constructor(url = 'ws://localhost:8765', options = {}) {
        this.url = url;
        this.ws = null;
        this.connected = false;
        
        // Configuration
        this.config = {
            enableCompression: true,
            enableInterpolation: true,
            quality: 'high', // 'low', 'medium', 'high'
            reconnectInterval: 5000,
            performanceLogging: true,
            ...options
        };
        
        // State management
        this.currentBlendshapes = {};
        this.targetBlendshapes = {};
        this.keyframeBlendshapes = {};
        
        // Performance monitoring
        this.performanceMonitor = {
            frameCount: 0,
            lastFrameTime: Date.now(),
            fps: 0,
            latency: 0,
            compressionRatio: 0,
            bandwidthUsed: 0
        };
        
        // Frame interpolation
        this.interpolationActive = false;
        this.interpolationStartTime = 0;
        this.interpolationDuration = 33; // ms for 30 FPS
        
        // Callbacks
        this.onBlendshapeUpdate = null;
        this.onMetricsUpdate = null;
        this.onPerformanceUpdate = null;
        this.onConnectionChange = null;
        
        // Statistics
        this.stats = {
            messagesReceived: 0,
            bytesReceived: 0,
            deltasApplied: 0,
            keyframesReceived: 0,
            decompressionTime: 0
        };
        
        // Animation frame loop
        this.animationFrameId = null;
        this.startAnimationLoop();
    }
    
    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('Already connected');
            return;
        }
        
        try {
            this.ws = new WebSocket(this.url);
            this.ws.binaryType = 'arraybuffer';
            
            this.ws.onopen = () => {
                console.log('Connected to optimized facial animation server');
                this.connected = true;
                
                // Send initial configuration
                this.sendMessage({
                    type: 'set_performance_config',
                    config: {
                        enable_compression: this.config.enableCompression,
                        enable_interpolation: this.config.enableInterpolation,
                        quality: this.config.quality
                    }
                });
                
                if (this.onConnectionChange) {
                    this.onConnectionChange(true);
                }
            };
            
            this.ws.onmessage = async (event) => {
                await this.handleMessage(event);
            };
            
            this.ws.onclose = () => {
                console.log('Disconnected from server');
                this.connected = false;
                
                if (this.onConnectionChange) {
                    this.onConnectionChange(false);
                }
                
                // Auto-reconnect
                setTimeout(() => this.connect(), this.config.reconnectInterval);
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
        } catch (error) {
            console.error('Failed to connect:', error);
        }
    }
    
    async handleMessage(event) {
        const startTime = performance.now();
        
        let data;
        let messageSize = 0;
        
        // Handle binary (compressed) or text messages
        if (event.data instanceof ArrayBuffer) {
            // Decompress gzip data
            try {
                const compressed = new Uint8Array(event.data);
                messageSize = compressed.length;
                const decompressed = await this.decompressGzip(compressed);
                data = JSON.parse(decompressed);
                this.stats.decompressionTime += performance.now() - startTime;
            } catch (error) {
                console.error('Failed to decompress message:', error);
                return;
            }
        } else {
            // Plain text message
            messageSize = event.data.length;
            data = JSON.parse(event.data);
        }
        
        this.stats.messagesReceived++;
        this.stats.bytesReceived += messageSize;
        
        // Handle different message types
        switch (data.type) {
            case 'initial_state':
                this.handleInitialState(data);
                break;
                
            case 'blendshape_update':
                this.handleBlendshapeUpdate(data);
                break;
                
            case 'metrics_update':
                this.handleMetricsUpdate(data);
                break;
                
            case 'performance_stats':
                this.handlePerformanceStats(data);
                break;
                
            case 'recommendations':
                this.handleRecommendations(data);
                break;
        }
        
        // Update performance metrics
        this.updatePerformanceMetrics();
    }
    
    handleBlendshapeUpdate(data) {
        const { compression, animation_mode, timestamp, server_fps } = data;
        
        if (!compression) return;
        
        // Apply compression data
        if (compression.type === 'keyframe') {
            // Full keyframe update
            this.keyframeBlendshapes = { ...compression.data };
            this.targetBlendshapes = { ...compression.data };
            this.stats.keyframesReceived++;
            
        } else if (compression.type === 'delta') {
            // Apply delta changes
            this.targetBlendshapes = { ...this.keyframeBlendshapes };
            
            for (const [morph, value] of Object.entries(compression.data)) {
                this.targetBlendshapes[morph] = value;
            }
            
            this.stats.deltasApplied++;
        }
        
        // Start interpolation if enabled
        if (this.config.enableInterpolation) {
            this.startInterpolation();
        } else {
            // Direct update without interpolation
            this.currentBlendshapes = { ...this.targetBlendshapes };
            
            if (this.onBlendshapeUpdate) {
                this.onBlendshapeUpdate(this.currentBlendshapes, {
                    mode: animation_mode,
                    timestamp: timestamp,
                    serverFps: server_fps
                });
            }
        }
    }
    
    startInterpolation() {
        this.interpolationActive = true;
        this.interpolationStartTime = performance.now();
        
        // Store start values
        this.interpolationStartValues = { ...this.currentBlendshapes };
    }
    
    updateInterpolation() {
        if (!this.interpolationActive) return;
        
        const now = performance.now();
        const elapsed = now - this.interpolationStartTime;
        const t = Math.min(elapsed / this.interpolationDuration, 1.0);
        
        // Interpolate each morph
        const interpolated = {};
        const allMorphs = new Set([
            ...Object.keys(this.interpolationStartValues),
            ...Object.keys(this.targetBlendshapes)
        ]);
        
        for (const morph of allMorphs) {
            const startValue = this.interpolationStartValues[morph] || 0;
            const targetValue = this.targetBlendshapes[morph] || 0;
            
            // Cubic ease-in-out interpolation
            let eased;
            if (t < 0.5) {
                eased = 4 * t * t * t;
            } else {
                const p = 2 * t - 2;
                eased = 1 + p * p * p / 2;
            }
            
            interpolated[morph] = startValue + (targetValue - startValue) * eased;
        }
        
        this.currentBlendshapes = interpolated;
        
        // Check if interpolation is complete
        if (t >= 1.0) {
            this.interpolationActive = false;
            this.currentBlendshapes = { ...this.targetBlendshapes };
        }
        
        // Trigger update callback
        if (this.onBlendshapeUpdate) {
            this.onBlendshapeUpdate(this.currentBlendshapes, {
                interpolating: this.interpolationActive,
                progress: t
            });
        }
    }
    
    startAnimationLoop() {
        const animate = () => {
            // Update interpolation
            this.updateInterpolation();
            
            // Calculate FPS
            const now = Date.now();
            const delta = now - this.performanceMonitor.lastFrameTime;
            if (delta > 0) {
                this.performanceMonitor.fps = 1000 / delta;
            }
            this.performanceMonitor.lastFrameTime = now;
            this.performanceMonitor.frameCount++;
            
            // Continue loop
            this.animationFrameId = requestAnimationFrame(animate);
        };
        
        animate();
    }
    
    stopAnimationLoop() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
    }
    
    handleInitialState(data) {
        console.log('Received initial state:', data);
        
        if (data.config) {
            // Update local config based on server settings
            this.serverConfig = data.config;
        }
        
        if (this.onMetricsUpdate) {
            this.onMetricsUpdate(data.data);
        }
    }
    
    handleMetricsUpdate(data) {
        if (this.onMetricsUpdate) {
            this.onMetricsUpdate(data.data);
        }
    }
    
    handlePerformanceStats(data) {
        if (this.onPerformanceUpdate) {
            this.onPerformanceUpdate(data.data);
        }
    }
    
    handleRecommendations(data) {
        console.log('Recommendations:', data.data);
        // Could trigger UI updates or automatic adjustments
    }
    
    updatePerformanceMetrics() {
        // Calculate compression ratio
        if (this.stats.bytesReceived > 0) {
            const estimatedUncompressed = this.stats.messagesReceived * 5000; // Estimate
            this.performanceMonitor.compressionRatio = 
                this.stats.bytesReceived / estimatedUncompressed;
        }
        
        // Calculate bandwidth
        this.performanceMonitor.bandwidthUsed = 
            this.stats.bytesReceived / 1024; // KB
        
        // Log performance if enabled
        if (this.config.performanceLogging && this.performanceMonitor.frameCount % 300 === 0) {
            console.log('Performance Stats:', {
                fps: this.performanceMonitor.fps.toFixed(1),
                latency: this.performanceMonitor.latency.toFixed(1) + 'ms',
                compressionRatio: (this.performanceMonitor.compressionRatio * 100).toFixed(1) + '%',
                bandwidth: this.performanceMonitor.bandwidthUsed.toFixed(1) + 'KB',
                deltasApplied: this.stats.deltasApplied,
                keyframesReceived: this.stats.keyframesReceived
            });
        }
    }
    
    async decompressGzip(compressed) {
        // Use native DecompressionStream if available
        if ('DecompressionStream' in window) {
            const stream = new Response(compressed).body
                .pipeThrough(new DecompressionStream('gzip'));
            const decompressed = await new Response(stream).arrayBuffer();
            return new TextDecoder().decode(decompressed);
        } else {
            // Fallback to pako library (needs to be included)
            if (typeof pako !== 'undefined') {
                const decompressed = pako.inflate(compressed, { to: 'string' });
                return decompressed;
            } else {
                throw new Error('No gzip decompression available');
            }
        }
    }
    
    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }
    
    // Public API methods
    
    setAnimationMode(mode, blendFactor = 0.5) {
        this.sendMessage({
            type: 'set_animation_mode',
            mode: mode,
            blend_factor: blendFactor
        });
    }
    
    setQuality(quality) {
        this.config.quality = quality;
        this.sendMessage({
            type: 'set_performance_config',
            config: { quality: quality }
        });
    }
    
    setCompressionEnabled(enabled) {
        this.config.enableCompression = enabled;
        this.sendMessage({
            type: 'set_performance_config',
            config: { enable_compression: enabled }
        });
    }
    
    setInterpolationEnabled(enabled) {
        this.config.enableInterpolation = enabled;
    }
    
    requestPerformanceStats() {
        this.sendMessage({ type: 'get_performance_stats' });
    }
    
    requestRecommendations() {
        this.sendMessage({ type: 'get_recommendations' });
    }
    
    getLocalStats() {
        return {
            fps: this.performanceMonitor.fps,
            messagesReceived: this.stats.messagesReceived,
            bytesReceived: this.stats.bytesReceived,
            deltasApplied: this.stats.deltasApplied,
            keyframesReceived: this.stats.keyframesReceived,
            compressionRatio: this.performanceMonitor.compressionRatio,
            averageDecompressionTime: this.stats.messagesReceived > 0 ? 
                this.stats.decompressionTime / this.stats.messagesReceived : 0
        };
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.stopAnimationLoop();
        this.connected = false;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = OptimizedFacialAnimationClient;
}