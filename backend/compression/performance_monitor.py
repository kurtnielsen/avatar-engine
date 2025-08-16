#!/usr/bin/env python3
"""
Performance Monitor for Facial Animation Pipeline
Tracks motion-to-photon latency and system performance
"""

import time
import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Deque
import numpy as np
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class LatencyMetrics:
    """Detailed latency breakdown"""
    udp_receive: float = 0.0          # Time to receive UDP packet
    decompression: float = 0.0        # Time to decompress data
    processing: float = 0.0           # Time to process morphs
    compression: float = 0.0          # Time to compress for WebSocket
    websocket_send: float = 0.0      # Time to send via WebSocket
    client_render: float = 0.0       # Time to render on client (if reported)
    total: float = 0.0               # Total motion-to-photon latency


@dataclass
class PerformanceMetrics:
    """Overall performance metrics"""
    frame_rate: float = 0.0
    dropped_frames: int = 0
    compression_ratio: float = 0.0
    bandwidth_usage: float = 0.0      # KB/s
    cpu_usage: float = 0.0            # Percentage
    memory_usage: float = 0.0         # MB
    active_connections: int = 0


@dataclass
class Alert:
    """Performance alert"""
    level: str  # 'warning', 'critical'
    metric: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    value: float = 0.0
    threshold: float = 0.0


class PerformanceMonitor:
    """
    Monitors facial animation pipeline performance.
    Tracks latency, frame rates, and system resources.
    """
    
    def __init__(self,
                 target_latency_ms: float = 80.0,
                 target_fps: float = 30.0,
                 history_size: int = 300):  # 5 minutes at 60 FPS
        """
        Initialize performance monitor.
        
        Args:
            target_latency_ms: Target motion-to-photon latency in milliseconds
            target_fps: Target frame rate
            history_size: Number of samples to keep in history
        """
        self.target_latency_ms = target_latency_ms
        self.target_fps = target_fps
        self.history_size = history_size
        
        # Latency tracking
        self.latency_history: Deque[LatencyMetrics] = deque(maxlen=history_size)
        self.latency_percentiles = {}
        
        # Frame tracking
        self.frame_timestamps: Deque[float] = deque(maxlen=100)
        self.dropped_frame_count = 0
        self.last_frame_time = time.time()
        
        # Performance metrics
        self.metrics_history: Deque[PerformanceMetrics] = deque(maxlen=history_size)
        self.current_metrics = PerformanceMetrics()
        
        # Alerts
        self.active_alerts: List[Alert] = []
        self.alert_history: Deque[Alert] = deque(maxlen=100)
        
        # Thresholds
        self.thresholds = {
            'latency_warning': target_latency_ms * 1.5,      # 120ms
            'latency_critical': target_latency_ms * 2.0,     # 160ms
            'fps_warning': target_fps * 0.8,                 # 24 FPS
            'fps_critical': target_fps * 0.6,                # 18 FPS
            'compression_warning': 0.5,                       # 50% compression
            'bandwidth_warning': 100.0,                       # 100 KB/s
            'cpu_warning': 80.0,                              # 80% CPU
            'memory_warning': 500.0                           # 500 MB
        }
        
        # Timing helpers
        self.timers: Dict[str, float] = {}
    
    def start_timer(self, name: str):
        """Start a named timer"""
        self.timers[name] = time.perf_counter()
    
    def end_timer(self, name: str) -> float:
        """End a named timer and return duration in milliseconds"""
        if name not in self.timers:
            return 0.0
        
        duration = (time.perf_counter() - self.timers[name]) * 1000
        del self.timers[name]
        return duration
    
    def record_frame(self, latency: LatencyMetrics, metrics: Optional[PerformanceMetrics] = None):
        """
        Record a frame with its latency breakdown.
        
        Args:
            latency: Latency metrics for this frame
            metrics: Optional performance metrics update
        """
        # Calculate total latency
        latency.total = (latency.udp_receive + latency.decompression + 
                        latency.processing + latency.compression + 
                        latency.websocket_send + latency.client_render)
        
        # Add to history
        self.latency_history.append(latency)
        
        # Update frame tracking
        current_time = time.time()
        self.frame_timestamps.append(current_time)
        
        # Check for dropped frames
        expected_frame_interval = 1.0 / self.target_fps
        actual_interval = current_time - self.last_frame_time
        if actual_interval > expected_frame_interval * 1.5:
            self.dropped_frame_count += 1
        
        self.last_frame_time = current_time
        
        # Update metrics if provided
        if metrics:
            self.current_metrics = metrics
            self.metrics_history.append(metrics)
        
        # Check for alerts
        self._check_alerts(latency)
        
        # Update percentiles periodically
        if len(self.latency_history) % 10 == 0:
            self._update_percentiles()
    
    def _update_percentiles(self):
        """Update latency percentiles"""
        if not self.latency_history:
            return
        
        latencies = [l.total for l in self.latency_history]
        self.latency_percentiles = {
            'p50': np.percentile(latencies, 50),
            'p90': np.percentile(latencies, 90),
            'p95': np.percentile(latencies, 95),
            'p99': np.percentile(latencies, 99),
            'mean': np.mean(latencies),
            'std': np.std(latencies)
        }
    
    def _check_alerts(self, latency: LatencyMetrics):
        """Check for performance alerts"""
        # Clear old alerts
        self.active_alerts = [a for a in self.active_alerts 
                             if datetime.now() - a.timestamp < timedelta(minutes=5)]
        
        # Check latency
        if latency.total > self.thresholds['latency_critical']:
            self._add_alert('critical', 'latency', 
                           f'Critical latency: {latency.total:.1f}ms',
                           latency.total, self.thresholds['latency_critical'])
        elif latency.total > self.thresholds['latency_warning']:
            self._add_alert('warning', 'latency',
                           f'High latency: {latency.total:.1f}ms',
                           latency.total, self.thresholds['latency_warning'])
        
        # Check frame rate
        current_fps = self.get_current_fps()
        if current_fps < self.thresholds['fps_critical']:
            self._add_alert('critical', 'fps',
                           f'Critical FPS: {current_fps:.1f}',
                           current_fps, self.thresholds['fps_critical'])
        elif current_fps < self.thresholds['fps_warning']:
            self._add_alert('warning', 'fps',
                           f'Low FPS: {current_fps:.1f}',
                           current_fps, self.thresholds['fps_warning'])
        
        # Check other metrics
        if self.current_metrics.compression_ratio < self.thresholds['compression_warning']:
            self._add_alert('warning', 'compression',
                           f'Low compression: {self.current_metrics.compression_ratio:.1%}',
                           self.current_metrics.compression_ratio,
                           self.thresholds['compression_warning'])
        
        if self.current_metrics.bandwidth_usage > self.thresholds['bandwidth_warning']:
            self._add_alert('warning', 'bandwidth',
                           f'High bandwidth: {self.current_metrics.bandwidth_usage:.1f} KB/s',
                           self.current_metrics.bandwidth_usage,
                           self.thresholds['bandwidth_warning'])
    
    def _add_alert(self, level: str, metric: str, message: str, value: float, threshold: float):
        """Add a new alert if not already active"""
        # Check if similar alert already active
        for alert in self.active_alerts:
            if alert.metric == metric and alert.level == level:
                return
        
        alert = Alert(level=level, metric=metric, message=message,
                     value=value, threshold=threshold)
        self.active_alerts.append(alert)
        self.alert_history.append(alert)
        
        logger.warning(f"Performance alert: {message}")
    
    def get_current_fps(self) -> float:
        """Calculate current frame rate"""
        if len(self.frame_timestamps) < 2:
            return 0.0
        
        time_span = self.frame_timestamps[-1] - self.frame_timestamps[0]
        if time_span <= 0:
            return 0.0
        
        return (len(self.frame_timestamps) - 1) / time_span
    
    def get_latency_report(self) -> Dict:
        """Get detailed latency report"""
        if not self.latency_history:
            return {
                'current': None,
                'percentiles': {},
                'breakdown': {},
                'trend': 'stable'
            }
        
        # Current latency
        current = self.latency_history[-1]
        
        # Average breakdown
        breakdown = {
            'udp_receive': np.mean([l.udp_receive for l in self.latency_history]),
            'decompression': np.mean([l.decompression for l in self.latency_history]),
            'processing': np.mean([l.processing for l in self.latency_history]),
            'compression': np.mean([l.compression for l in self.latency_history]),
            'websocket_send': np.mean([l.websocket_send for l in self.latency_history]),
            'client_render': np.mean([l.client_render for l in self.latency_history if l.client_render > 0])
        }
        
        # Trend analysis
        if len(self.latency_history) > 10:
            recent = [l.total for l in list(self.latency_history)[-10:]]
            older = [l.total for l in list(self.latency_history)[-20:-10]]
            
            recent_avg = np.mean(recent)
            older_avg = np.mean(older) if older else recent_avg
            
            if recent_avg > older_avg * 1.1:
                trend = 'increasing'
            elif recent_avg < older_avg * 0.9:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            'current': {
                'total': current.total,
                'breakdown': {
                    'udp_receive': current.udp_receive,
                    'decompression': current.decompression,
                    'processing': current.processing,
                    'compression': current.compression,
                    'websocket_send': current.websocket_send,
                    'client_render': current.client_render
                }
            },
            'percentiles': self.latency_percentiles,
            'average_breakdown': breakdown,
            'trend': trend,
            'target_ms': self.target_latency_ms
        }
    
    def get_performance_summary(self) -> Dict:
        """Get overall performance summary"""
        return {
            'fps': {
                'current': self.get_current_fps(),
                'target': self.target_fps,
                'dropped_frames': self.dropped_frame_count
            },
            'latency': self.get_latency_report(),
            'metrics': {
                'compression_ratio': self.current_metrics.compression_ratio,
                'bandwidth_kb_s': self.current_metrics.bandwidth_usage,
                'cpu_percent': self.current_metrics.cpu_usage,
                'memory_mb': self.current_metrics.memory_usage,
                'active_connections': self.current_metrics.active_connections
            },
            'alerts': [
                {
                    'level': a.level,
                    'metric': a.metric,
                    'message': a.message,
                    'timestamp': a.timestamp.isoformat()
                }
                for a in self.active_alerts
            ],
            'health_score': self._calculate_health_score()
        }
    
    def _calculate_health_score(self) -> float:
        """Calculate overall health score (0.0 - 1.0)"""
        score = 1.0
        
        # Latency impact
        if self.latency_percentiles.get('mean', 0) > 0:
            latency_ratio = self.target_latency_ms / self.latency_percentiles['mean']
            score *= min(latency_ratio, 1.0)
        
        # FPS impact
        fps_ratio = self.get_current_fps() / self.target_fps
        score *= min(fps_ratio, 1.0)
        
        # Alert impact
        for alert in self.active_alerts:
            if alert.level == 'critical':
                score *= 0.7
            elif alert.level == 'warning':
                score *= 0.9
        
        return max(0.0, min(1.0, score))
    
    def export_metrics(self) -> Dict:
        """Export metrics for logging or analysis"""
        return {
            'timestamp': datetime.now().isoformat(),
            'summary': self.get_performance_summary(),
            'latency_history': [
                {
                    'total': l.total,
                    'udp': l.udp_receive,
                    'decompress': l.decompression,
                    'process': l.processing,
                    'compress': l.compression,
                    'websocket': l.websocket_send,
                    'render': l.client_render
                }
                for l in list(self.latency_history)[-100:]  # Last 100 frames
            ],
            'alerts': [
                {
                    'level': a.level,
                    'metric': a.metric,
                    'message': a.message,
                    'timestamp': a.timestamp.isoformat(),
                    'value': a.value,
                    'threshold': a.threshold
                }
                for a in list(self.alert_history)[-50:]  # Last 50 alerts
            ]
        }