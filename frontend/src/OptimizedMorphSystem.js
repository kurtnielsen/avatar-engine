/**
 * OptimizedMorphSystem.js
 * High-performance morph target animation system for Three.js
 * Implements LOD, selective updates, and GPU optimizations
 */

import * as THREE from 'three';

export class OptimizedMorphSystem {
    constructor(options = {}) {
        // Default configuration
        this.config = {
            lodEnabled: true,
            selectiveUpdates: true,
            frustumCulling: true,
            gpuMorphing: true,
            quality: 'medium',
            updateThreshold: 0.01,
            maxActiveMorphs: 100,
            priorityMorphs: new Set([
                'V_Open', 'V_AA', 'V_EE', 'V_OH', 'V_U',
                'Eye_Blink_L', 'Eye_Blink_R',
                'Mouth_Smile_L', 'Mouth_Smile_R'
            ]),
            ...options
        };

        // Quality presets
        this.qualityPresets = {
            low: {
                shadowMapSize: 512,
                morphUpdateThreshold: 0.05,
                maxActiveMorphs: 50,
                lodDistances: [2, 5, 10],
                updateFrequency: 3,
                morphNormals: false,
                pixelRatio: 1
            },
            medium: {
                shadowMapSize: 1024,
                morphUpdateThreshold: 0.01,
                maxActiveMorphs: 100,
                lodDistances: [3, 8, 15],
                updateFrequency: 2,
                morphNormals: true,
                pixelRatio: Math.min(window.devicePixelRatio, 2)
            },
            high: {
                shadowMapSize: 2048,
                morphUpdateThreshold: 0.001,
                maxActiveMorphs: 266,
                lodDistances: [5, 12, 20],
                updateFrequency: 1,
                morphNormals: true,
                pixelRatio: window.devicePixelRatio
            },
            ultra: {
                shadowMapSize: 4096,
                morphUpdateThreshold: 0.0001,
                maxActiveMorphs: 500,
                lodDistances: [10, 20, 30],
                updateFrequency: 1,
                morphNormals: true,
                pixelRatio: window.devicePixelRatio
            }
        };

        // Internal state
        this.meshes = [];
        this.morphMap = new Map();
        this.morphStates = new Map();
        this.previousStates = new Map();
        this.dirtyMorphs = new Set();
        this.activeMorphs = new Set();
        this.lodLevel = 0;
        this.frameCounter = 0;
        this.lastUpdateTime = 0;
        
        // Performance tracking
        this.stats = {
            morphUpdatesPerFrame: 0,
            skippedUpdates: 0,
            totalMorphs: 0,
            activeMorphCount: 0
        };

        // GPU morph texture (for advanced GPU morphing)
        this.morphTexture = null;
        this.morphTextureSize = 256;
    }

    /**
     * Initialize the system with meshes containing morph targets
     */
    initialize(meshes) {
        this.meshes = Array.isArray(meshes) ? meshes : [meshes];
        this.buildMorphMap();
        this.initializeMorphStates();
        
        if (this.config.gpuMorphing) {
            this.setupGPUMorphing();
        }

        // Apply initial optimizations
        this.optimizeMeshes();
        
        console.log(`OptimizedMorphSystem initialized with ${this.morphMap.size} morphs across ${this.meshes.length} meshes`);
    }

    /**
     * Build a unified map of all morph targets
     */
    buildMorphMap() {
        this.morphMap.clear();
        
        this.meshes.forEach((mesh, meshIndex) => {
            if (!mesh.morphTargetDictionary || !mesh.morphTargetInfluences) return;
            
            Object.entries(mesh.morphTargetDictionary).forEach(([morphName, morphIndex]) => {
                if (!this.morphMap.has(morphName)) {
                    this.morphMap.set(morphName, []);
                }
                
                this.morphMap.get(morphName).push({
                    mesh,
                    meshIndex,
                    morphIndex,
                    influence: mesh.morphTargetInfluences
                });
            });
        });
        
        this.stats.totalMorphs = this.morphMap.size;
    }

    /**
     * Initialize morph states tracking
     */
    initializeMorphStates() {
        this.morphMap.forEach((targets, morphName) => {
            this.morphStates.set(morphName, 0);
            this.previousStates.set(morphName, 0);
        });
    }

    /**
     * Apply optimizations to meshes
     */
    optimizeMeshes() {
        const preset = this.qualityPresets[this.config.quality];
        
        this.meshes.forEach(mesh => {
            if (!mesh.material) return;
            
            // Clone material to avoid affecting other instances
            mesh.material = mesh.material.clone();
            
            // Basic optimizations
            mesh.material.morphTargets = true;
            mesh.material.morphNormals = preset.morphNormals;
            
            // Frustum culling
            mesh.frustumCulled = this.config.frustumCulling;
            
            // Quality-based optimizations
            if (this.config.quality === 'low') {
                mesh.material.flatShading = true;
                mesh.material.vertexColors = false;
            }
            
            // Shadow optimizations
            mesh.castShadow = this.config.quality !== 'low';
            mesh.receiveShadow = this.config.quality !== 'low';
            
            mesh.material.needsUpdate = true;
        });
    }

    /**
     * Setup GPU morphing using texture-based morph data
     */
    setupGPUMorphing() {
        // Create texture to store morph weights
        const size = this.morphTextureSize;
        const data = new Float32Array(size * size * 4); // RGBA
        
        this.morphTexture = new THREE.DataTexture(
            data,
            size,
            size,
            THREE.RGBAFormat,
            THREE.FloatType
        );
        
        this.morphTexture.needsUpdate = true;
        
        // Create custom shader material for GPU morphing (optional advanced feature)
        // This would require custom vertex shaders that read from the texture
    }

    /**
     * Set a morph target value with optimizations
     */
    setMorph(morphName, value, force = false) {
        if (!this.morphMap.has(morphName)) return false;
        
        const preset = this.qualityPresets[this.config.quality];
        const currentValue = this.morphStates.get(morphName) || 0;
        const delta = Math.abs(value - currentValue);
        
        // Early exit for negligible changes
        if (!force && this.config.selectiveUpdates && delta < preset.morphUpdateThreshold) {
            this.stats.skippedUpdates++;
            return false;
        }
        
        // Check active morph limit
        if (!force && 
            value > 0 && 
            !this.activeMorphs.has(morphName) && 
            this.activeMorphs.size >= preset.maxActiveMorphs && 
            !this.config.priorityMorphs.has(morphName)) {
            this.stats.skippedUpdates++;
            return false;
        }
        
        // Update state
        this.morphStates.set(morphName, value);
        this.dirtyMorphs.add(morphName);
        
        // Track active morphs
        if (value > 0.001) {
            this.activeMorphs.add(morphName);
        } else {
            this.activeMorphs.delete(morphName);
        }
        
        return true;
    }

    /**
     * Batch update multiple morphs
     */
    updateMorphs(morphData) {
        const updates = [];
        
        // Sort by priority
        const sortedEntries = Object.entries(morphData).sort(([a], [b]) => {
            const aPriority = this.config.priorityMorphs.has(a);
            const bPriority = this.config.priorityMorphs.has(b);
            return bPriority - aPriority;
        });
        
        sortedEntries.forEach(([morphName, value]) => {
            if (this.setMorph(morphName, value)) {
                updates.push(morphName);
            }
        });
        
        this.stats.activeMorphCount = this.activeMorphs.size;
        return updates.length;
    }

    /**
     * Apply morph changes based on LOD and frame rate
     */
    applyMorph(morphName, value) {
        const targets = this.morphMap.get(morphName);
        if (!targets) return;
        
        targets.forEach(target => {
            // Apply GPU optimizations
            if (this.config.gpuMorphing && target.mesh.material) {
                target.mesh.material.morphNormals = value > 0.1;
            }
            
            target.influence[target.morphIndex] = value;
        });
        
        this.stats.morphUpdatesPerFrame++;
    }

    /**
     * Process dirty morphs based on current settings
     */
    processDirtyMorphs() {
        const preset = this.qualityPresets[this.config.quality];
        
        this.dirtyMorphs.forEach(morphName => {
            const value = this.morphStates.get(morphName);
            
            // Check if should update based on LOD and priority
            if (this.shouldUpdateMorph(morphName, preset)) {
                this.applyMorph(morphName, value);
            }
        });
        
        this.dirtyMorphs.clear();
    }

    /**
     * Determine if a morph should be updated this frame
     */
    shouldUpdateMorph(morphName, preset) {
        // Always update priority morphs
        if (this.config.priorityMorphs.has(morphName)) return true;
        
        // Frame-based updates
        if (this.frameCounter % preset.updateFrequency !== 0) return false;
        
        // LOD-based filtering
        if (this.config.lodEnabled && this.lodLevel > 1) {
            return this.config.priorityMorphs.has(morphName);
        }
        
        return true;
    }

    /**
     * Update LOD level based on distance
     */
    updateLOD(distance) {
        if (!this.config.lodEnabled) {
            this.lodLevel = 0;
            return;
        }
        
        const distances = this.qualityPresets[this.config.quality].lodDistances;
        
        if (distance < distances[0]) {
            this.lodLevel = 0; // Full detail
        } else if (distance < distances[1]) {
            this.lodLevel = 1; // Medium detail
        } else if (distance < distances[2]) {
            this.lodLevel = 2; // Low detail
        } else {
            this.lodLevel = 3; // Very low detail
        }
        
        return this.lodLevel;
    }

    /**
     * Main update tick - call this in your render loop
     */
    tick(deltaTime = 16) {
        this.frameCounter++;
        this.stats.morphUpdatesPerFrame = 0;
        
        // Update GPU morph texture if enabled
        if (this.config.gpuMorphing && this.morphTexture) {
            this.updateMorphTexture();
        }
        
        // Process dirty morphs
        this.processDirtyMorphs();
        
        // Store previous states for interpolation
        this.morphStates.forEach((value, name) => {
            this.previousStates.set(name, value);
        });
        
        this.lastUpdateTime += deltaTime;
    }

    /**
     * Update GPU morph texture with current values
     */
    updateMorphTexture() {
        if (!this.morphTexture) return;
        
        const data = this.morphTexture.image.data;
        let index = 0;
        
        this.morphStates.forEach((value, morphName) => {
            if (index < data.length) {
                data[index] = value;
                index += 4; // Skip to next pixel (RGBA)
            }
        });
        
        this.morphTexture.needsUpdate = true;
    }

    /**
     * Reset all morphs to zero
     */
    resetAll() {
        this.morphStates.forEach((_, morphName) => {
            this.morphStates.set(morphName, 0);
        });
        
        this.dirtyMorphs.clear();
        this.activeMorphs.clear();
        
        this.meshes.forEach(mesh => {
            if (mesh.morphTargetInfluences) {
                mesh.morphTargetInfluences.fill(0);
            }
        });
        
        this.stats.activeMorphCount = 0;
    }

    /**
     * Set quality preset
     */
    setQuality(quality) {
        if (!this.qualityPresets[quality]) {
            console.warn(`Unknown quality preset: ${quality}`);
            return;
        }
        
        this.config.quality = quality;
        this.optimizeMeshes();
    }

    /**
     * Get current performance statistics
     */
    getStats() {
        return {
            ...this.stats,
            lodLevel: this.lodLevel,
            quality: this.config.quality,
            frameCounter: this.frameCounter
        };
    }

    /**
     * Interpolate between morph states for smooth transitions
     */
    interpolateMorphs(alpha) {
        this.morphStates.forEach((targetValue, morphName) => {
            const previousValue = this.previousStates.get(morphName) || 0;
            const interpolatedValue = previousValue + (targetValue - previousValue) * alpha;
            
            const targets = this.morphMap.get(morphName);
            if (targets) {
                targets.forEach(target => {
                    target.influence[target.morphIndex] = interpolatedValue;
                });
            }
        });
    }

    /**
     * Dispose of resources
     */
    dispose() {
        if (this.morphTexture) {
            this.morphTexture.dispose();
        }
        
        this.morphMap.clear();
        this.morphStates.clear();
        this.previousStates.clear();
        this.dirtyMorphs.clear();
        this.activeMorphs.clear();
    }
}

// Export utility functions
export function createOptimizedRenderer(options = {}) {
    const renderer = new THREE.WebGLRenderer({
        antialias: options.antialias !== false,
        powerPreference: "high-performance",
        stencil: false,
        depth: true,
        ...options
    });
    
    // Optimize renderer settings
    renderer.shadowMap.enabled = options.shadows !== false;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.shadowMap.autoUpdate = false; // Manual updates for better control
    renderer.info.autoReset = false; // Manual reset for accurate stats
    
    return renderer;
}

export function optimizeScene(scene, quality = 'medium') {
    const presets = {
        low: { maxLights: 3, fog: false, shadows: false },
        medium: { maxLights: 5, fog: true, shadows: true },
        high: { maxLights: 10, fog: true, shadows: true }
    };
    
    const preset = presets[quality] || presets.medium;
    
    // Optimize lights
    let lightCount = 0;
    scene.traverse((obj) => {
        if (obj.isLight) {
            lightCount++;
            if (lightCount > preset.maxLights) {
                obj.visible = false;
            }
            
            // Optimize shadows
            if (obj.castShadow) {
                obj.castShadow = preset.shadows;
            }
        }
    });
    
    // Add fog for depth culling
    if (preset.fog && !scene.fog) {
        scene.fog = new THREE.Fog(scene.background || 0x000000, 10, 50);
    }
    
    return scene;
}