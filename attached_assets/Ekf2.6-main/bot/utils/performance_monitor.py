"""
Performance Monitoring System
Tracks bot performance metrics and optimization
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import asyncio

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitors bot performance and resource usage"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.start_time = time.time()
        
    def track_operation(self, operation_name: str):
        """Decorator to track operation performance"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.perf_counter() - start_time
                    self.record_metric(operation_name, duration)
            return wrapper
        return decorator
        
    def record_metric(self, metric_name: str, value: float):
        """Record a performance metric"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
            
        self.metrics[metric_name].append(value)
        
        # Keep only last 100 measurements
        if len(self.metrics[metric_name]) > 100:
            self.metrics[metric_name] = self.metrics[metric_name][-100:]
            
    def get_average_metric(self, metric_name: str) -> Optional[float]:
        """Get average value for a metric"""
        if metric_name in self.metrics and self.metrics[metric_name]:
            return sum(self.metrics[metric_name]) / len(self.metrics[metric_name])
        return None
        
    def get_performance_report(self) -> Dict[str, Dict]:
        """Generate comprehensive performance report"""
        report = {
            'uptime_seconds': time.time() - self.start_time,
            'metrics': {}
        }
        
        for metric_name, values in self.metrics.items():
            if values:
                report['metrics'][metric_name] = {
                    'average': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }
                
        return report