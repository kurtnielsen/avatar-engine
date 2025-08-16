/**
 * PerformanceMonitor.js
 * Real-time performance monitoring for Three.js applications
 * Tracks FPS, frame time, draw calls, and morph performance
 */

export class PerformanceMonitor {
    constructor(renderer, options = {}) {
        this.renderer = renderer;
        this.config = {
            updateInterval: 1000, // Update stats every second
            showPanel: true,
            panelPosition: 'top-right',
            trackHistory: true,
            historySize: 60, // Keep 60 seconds of history
            ...options
        };

        // Performance metrics
        this.metrics = {
            fps: 0,
            frameTime: 0,
            frameTimeMin: Infinity,
            frameTimeMax: 0,
            drawCalls: 0,
            triangles: 0,
            points: 0,
            lines: 0,
            morphUpdates: 0,
            activeMorphs: 0,
            textureMemory: 0,
            geometryMemory: 0,
            programCount: 0
        };

        // Timing
        this.frameCount = 0;
        this.lastTime = performance.now();
        this.lastUpdateTime = performance.now();
        this.frameTimes = [];

        // History tracking
        this.history = {
            fps: [],
            frameTime: [],
            drawCalls: [],
            morphUpdates: []
        };

        // Create UI panel if requested
        if (this.config.showPanel) {
            this.createPanel();
        }

        // GPU timer queries (if supported)
        this.gpuTimer = null;
        this.initGPUTimer();
    }

    /**
     * Initialize GPU timer for accurate GPU timing
     */
    initGPUTimer() {
        const gl = this.renderer.getContext();
        const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2');
        
        if (ext) {
            this.gpuTimer = {
                ext: ext,
                query: null,
                isRunning: false
            };
        }
    }

    /**
     * Create performance monitoring panel
     */
    createPanel() {
        const panel = document.createElement('div');
        panel.id = 'performance-monitor';
        panel.style.cssText = `
            position: fixed;
            ${this.config.panelPosition.includes('top') ? 'top: 10px' : 'bottom: 10px'};
            ${this.config.panelPosition.includes('right') ? 'right: 10px' : 'left: 10px'};
            background: rgba(0, 0, 0, 0.9);
            color: #fff;
            padding: 15px;
            font-family: monospace;
            font-size: 12px;
            border-radius: 5px;
            min-width: 250px;
            z-index: 10000;
            pointer-events: none;
            user-select: none;
        `;

        document.body.appendChild(panel);
        this.panel = panel;
        this.updatePanel();
    }

    /**
     * Update the performance panel UI
     */
    updatePanel() {
        if (!this.panel) return;

        const getColorForFPS = (fps) => {
            if (fps >= 60) return '#4CAF50';
            if (fps >= 30) return '#FFC107';
            return '#F44336';
        };

        const getColorForFrameTime = (ms) => {
            if (ms <= 16.67) return '#4CAF50';
            if (ms <= 33.33) return '#FFC107';
            return '#F44336';
        };

        this.panel.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 10px;">Performance Monitor</div>
            <div style="display: grid; grid-template-columns: auto auto; gap: 5px 15px;">
                <div>FPS:</div>
                <div style="color: ${getColorForFPS(this.metrics.fps)}">${this.metrics.fps}</div>
                
                <div>Frame Time:</div>
                <div style="color: ${getColorForFrameTime(this.metrics.frameTime)}">${this.metrics.frameTime.toFixed(2)}ms</div>
                
                <div>Min/Max:</div>
                <div>${this.metrics.frameTimeMin.toFixed(1)}/${this.metrics.frameTimeMax.toFixed(1)}ms</div>
                
                <div>Draw Calls:</div>
                <div>${this.metrics.drawCalls}</div>
                
                <div>Triangles:</div>
                <div>${this.formatNumber(this.metrics.triangles)}</div>
                
                <div>Active Morphs:</div>
                <div>${this.metrics.activeMorphs}</div>
                
                <div>Morph Updates:</div>
                <div>${this.metrics.morphUpdates}/frame</div>
                
                <div>Programs:</div>
                <div>${this.metrics.programCount}</div>
                
                <div>Geometry Mem:</div>
                <div>${this.formatBytes(this.metrics.geometryMemory)}</div>
                
                <div>Texture Mem:</div>
                <div>${this.formatBytes(this.metrics.textureMemory)}</div>
            </div>
            ${this.renderHistoryGraph()}
        `;
    }

    /**
     * Render a simple ASCII history graph
     */
    renderHistoryGraph() {
        if (!this.config.trackHistory || this.history.fps.length < 2) return '';

        const width = 30;
        const height = 5;
        const maxFPS = 120;
        
        // Get last 'width' samples
        const samples = this.history.fps.slice(-width);
        const normalized = samples.map(fps => Math.min(fps / maxFPS, 1));
        
        let graph = '<div style="margin-top: 10px; font-size: 10px;">';
        graph += '<div>FPS History (60s):</div>';
        graph += '<div style="line-height: 1;">';
        
        // Create ASCII graph
        for (let y = height - 1; y >= 0; y--) {
            const threshold = y / height;
            let line = '';
            
            for (let x = 0; x < samples.length; x++) {
                if (normalized[x] >= threshold) {
                    line += '█';
                } else {
                    line += '·';
                }
            }
            
            graph += `<div>${line}</div>`;
        }
        
        graph += '</div></div>';
        return graph;
    }

    /**
     * Start GPU timing for current frame
     */
    beginGPUTimer() {
        if (!this.gpuTimer || this.gpuTimer.isRunning) return;

        const gl = this.renderer.getContext();
        const query = gl.createQuery();
        
        gl.beginQuery(this.gpuTimer.ext.TIME_ELAPSED_EXT, query);
        this.gpuTimer.query = query;
        this.gpuTimer.isRunning = true;
    }

    /**
     * End GPU timing for current frame
     */
    endGPUTimer() {
        if (!this.gpuTimer || !this.gpuTimer.isRunning) return;

        const gl = this.renderer.getContext();
        gl.endQuery(this.gpuTimer.ext.TIME_ELAPSED_EXT);
        this.gpuTimer.isRunning = false;

        // Check result asynchronously
        setTimeout(() => {
            if (this.gpuTimer.query) {
                const available = gl.getQueryParameter(
                    this.gpuTimer.query,
                    gl.QUERY_RESULT_AVAILABLE
                );
                
                if (available) {
                    const gpuTime = gl.getQueryParameter(
                        this.gpuTimer.query,
                        gl.QUERY_RESULT
                    );
                    
                    // Convert nanoseconds to milliseconds
                    this.metrics.gpuTime = gpuTime / 1000000;
                    gl.deleteQuery(this.gpuTimer.query);
                    this.gpuTimer.query = null;
                }
            }
        }, 0);
    }

    /**
     * Update performance metrics - call this before render
     */
    begin() {
        this.beginGPUTimer();
        this.frameStartTime = performance.now();
    }

    /**
     * Update performance metrics - call this after render
     */
    end(morphStats = null) {
        this.endGPUTimer();
        
        const now = performance.now();
        const frameTime = now - this.frameStartTime;
        
        // Track frame times
        this.frameTimes.push(frameTime);
        if (this.frameTimes.length > 10) {
            this.frameTimes.shift();
        }
        
        // Update min/max
        this.metrics.frameTimeMin = Math.min(this.metrics.frameTimeMin, frameTime);
        this.metrics.frameTimeMax = Math.max(this.metrics.frameTimeMax, frameTime);
        
        // Update render info
        if (this.renderer.info) {
            this.metrics.drawCalls = this.renderer.info.render.calls;
            this.metrics.triangles = this.renderer.info.render.triangles;
            this.metrics.points = this.renderer.info.render.points;
            this.metrics.lines = this.renderer.info.render.lines;
            this.metrics.programCount = this.renderer.info.programs?.length || 0;
            this.metrics.geometryMemory = this.renderer.info.memory.geometries || 0;
            this.metrics.textureMemory = this.renderer.info.memory.textures || 0;
        }
        
        // Update morph stats if provided
        if (morphStats) {
            this.metrics.morphUpdates = morphStats.morphUpdatesPerFrame || 0;
            this.metrics.activeMorphs = morphStats.activeMorphCount || 0;
        }
        
        this.frameCount++;
        
        // Update stats at interval
        if (now - this.lastUpdateTime >= this.config.updateInterval) {
            this.updateStats(now);
        }
    }

    /**
     * Update calculated statistics
     */
    updateStats(now) {
        const delta = now - this.lastUpdateTime;
        
        // Calculate FPS
        this.metrics.fps = Math.round((this.frameCount * 1000) / delta);
        
        // Calculate average frame time
        if (this.frameTimes.length > 0) {
            const avgFrameTime = this.frameTimes.reduce((a, b) => a + b) / this.frameTimes.length;
            this.metrics.frameTime = avgFrameTime;
        }
        
        // Update history
        if (this.config.trackHistory) {
            this.updateHistory();
        }
        
        // Reset counters
        this.frameCount = 0;
        this.lastUpdateTime = now;
        this.metrics.frameTimeMin = Infinity;
        this.metrics.frameTimeMax = 0;
        
        // Update UI
        this.updatePanel();
    }

    /**
     * Update performance history
     */
    updateHistory() {
        const historyKeys = ['fps', 'frameTime', 'drawCalls', 'morphUpdates'];
        
        historyKeys.forEach(key => {
            if (this.history[key]) {
                this.history[key].push(this.metrics[key]);
                
                // Trim history to size limit
                if (this.history[key].length > this.config.historySize) {
                    this.history[key].shift();
                }
            }
        });
    }

    /**
     * Get performance report
     */
    getReport() {
        const report = {
            current: { ...this.metrics },
            averages: {},
            recommendations: []
        };
        
        // Calculate averages from history
        if (this.config.trackHistory) {
            Object.keys(this.history).forEach(key => {
                const values = this.history[key];
                if (values.length > 0) {
                    report.averages[key] = values.reduce((a, b) => a + b) / values.length;
                }
            });
        }
        
        // Generate recommendations
        if (report.averages.fps < 30) {
            report.recommendations.push('Low FPS detected. Consider reducing quality settings.');
        }
        
        if (this.metrics.drawCalls > 100) {
            report.recommendations.push('High draw call count. Consider batching geometry.');
        }
        
        if (this.metrics.triangles > 1000000) {
            report.recommendations.push('High triangle count. Consider using LOD or reducing mesh complexity.');
        }
        
        if (this.metrics.activeMorphs > 100) {
            report.recommendations.push('Many active morphs. Consider using selective morph updates.');
        }
        
        return report;
    }

    /**
     * Format number with commas
     */
    formatNumber(num) {
        return num.toLocaleString();
    }

    /**
     * Format bytes to human readable
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    /**
     * Reset performance metrics
     */
    reset() {
        this.frameCount = 0;
        this.frameTimes = [];
        this.metrics.frameTimeMin = Infinity;
        this.metrics.frameTimeMax = 0;
        
        if (this.renderer.info) {
            this.renderer.info.reset();
        }
    }

    /**
     * Destroy the monitor
     */
    dispose() {
        if (this.panel && this.panel.parentNode) {
            this.panel.parentNode.removeChild(this.panel);
        }
        
        if (this.gpuTimer && this.gpuTimer.query) {
            const gl = this.renderer.getContext();
            gl.deleteQuery(this.gpuTimer.query);
        }
    }
}

// Export convenience function
export function createPerformanceMonitor(renderer, options) {
    return new PerformanceMonitor(renderer, options);
}