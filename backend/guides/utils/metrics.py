"""
Metrics collection system for performance monitoring
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import time
import logging
from enum import Enum
import statistics
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """Individual metric data point"""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None


class MetricsCollector:
    """
    Central metrics collection system
    Collects and aggregates performance metrics
    """
    
    def __init__(self, namespace: str = "supervisor"):
        """
        Initialize metrics collector
        
        Args:
            namespace: Metrics namespace for grouping
        """
        self.namespace = namespace
        self.metrics: List[Metric] = []
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.start_time = datetime.now()
        
        logger.info(f"MetricsCollector initialized for namespace: {namespace}")
    
    def _make_metric_name(self, name: str) -> str:
        """Create fully qualified metric name"""
        return f"{self.namespace}.{name}"
    
    def increment_counter(
        self, 
        name: str, 
        value: float = 1, 
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Increment a counter metric
        
        Args:
            name: Metric name
            value: Value to increment by
            tags: Optional tags
        """
        full_name = self._make_metric_name(name)
        self.counters[full_name] += value
        
        self.metrics.append(Metric(
            name=full_name,
            type=MetricType.COUNTER,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        ))
        
        logger.debug(f"Counter {full_name} incremented by {value}")
    
    def set_gauge(
        self, 
        name: str, 
        value: float, 
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Set a gauge metric
        
        Args:
            name: Metric name
            value: Current value
            tags: Optional tags
        """
        full_name = self._make_metric_name(name)
        self.gauges[full_name] = value
        
        self.metrics.append(Metric(
            name=full_name,
            type=MetricType.GAUGE,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        ))
        
        logger.debug(f"Gauge {full_name} set to {value}")
    
    def record_latency(
        self, 
        operation: str, 
        duration: float, 
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Record operation latency
        
        Args:
            operation: Operation name
            duration: Duration in seconds
            tags: Optional tags
        """
        full_name = self._make_metric_name(f"{operation}.latency")
        self.timers[full_name].append(duration)
        
        self.metrics.append(Metric(
            name=full_name,
            type=MetricType.TIMER,
            value=duration,
            timestamp=datetime.now(),
            tags=tags or {},
            unit="seconds"
        ))
        
        logger.debug(f"Latency recorded for {operation}: {duration:.3f}s")
    
    def record_value(
        self, 
        name: str, 
        value: float, 
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Record a value in a histogram
        
        Args:
            name: Metric name
            value: Value to record
            tags: Optional tags
        """
        full_name = self._make_metric_name(name)
        self.histograms[full_name].append(value)
        
        self.metrics.append(Metric(
            name=full_name,
            type=MetricType.HISTOGRAM,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        ))
    
    def record_success(
        self, 
        operation: str, 
        success: bool, 
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Record operation success/failure
        
        Args:
            operation: Operation name
            success: Whether operation succeeded
            tags: Optional tags
        """
        status = "success" if success else "failure"
        counter_name = f"{operation}.{status}"
        self.increment_counter(counter_name, tags=tags)
    
    def record_error(
        self, 
        operation: str, 
        error: str, 
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Record an error
        
        Args:
            operation: Operation name
            error: Error message
            tags: Optional tags
        """
        error_tags = {**(tags or {}), "error": error[:100]}  # Limit error message length
        self.increment_counter(f"{operation}.errors", tags=error_tags)
    
    def record_event(
        self, 
        event_name: str, 
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Record a custom event
        
        Args:
            event_name: Event name
            data: Optional event data
        """
        self.increment_counter(f"events.{event_name}")
        
        if data:
            logger.debug(f"Event recorded: {event_name} with data: {data}")
    
    @asynccontextmanager
    async def measure(self, operation: str, tags: Optional[Dict[str, str]] = None):
        """
        Context manager to measure operation time
        
        Args:
            operation: Operation name
            tags: Optional tags
        
        Usage:
            async with metrics.measure("database_query"):
                result = await query_database()
        """
        start_time = time.perf_counter()
        success = True
        
        try:
            yield
        except Exception as e:
            success = False
            self.record_error(operation, str(e), tags)
            raise
        finally:
            duration = time.perf_counter() - start_time
            self.record_latency(operation, duration, tags)
            self.record_success(operation, success, tags)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics summary
        
        Returns:
            Dictionary with aggregated metrics
        """
        summary = {
            "namespace": self.namespace,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "total_metrics": len(self.metrics),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "timers": {},
            "histograms": {}
        }
        
        # Aggregate timer statistics
        for name, values in self.timers.items():
            if values:
                summary["timers"][name] = {
                    "count": len(values),
                    "sum": sum(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "stddev": statistics.stdev(values) if len(values) > 1 else 0,
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99)
                }
        
        # Aggregate histogram statistics
        for name, values in self.histograms.items():
            if values:
                summary["histograms"][name] = {
                    "count": len(values),
                    "sum": sum(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "stddev": statistics.stdev(values) if len(values) > 1 else 0
                }
        
        return summary
    
    def get_recent_metrics(
        self, 
        duration_seconds: int = 60
    ) -> List[Metric]:
        """
        Get metrics from the recent period
        
        Args:
            duration_seconds: How far back to look
        
        Returns:
            List of recent metrics
        """
        cutoff = datetime.now() - timedelta(seconds=duration_seconds)
        return [m for m in self.metrics if m.timestamp >= cutoff]
    
    def get_metrics_by_type(self, metric_type: MetricType) -> List[Metric]:
        """
        Get all metrics of a specific type
        
        Args:
            metric_type: Type of metrics to retrieve
        
        Returns:
            List of metrics of the specified type
        """
        return [m for m in self.metrics if m.type == metric_type]
    
    def reset(self):
        """Reset all metrics"""
        self.metrics.clear()
        self.counters.clear()
        self.gauges.clear()
        self.timers.clear()
        self.histograms.clear()
        self.start_time = datetime.now()
        logger.info(f"Metrics reset for namespace: {self.namespace}")
    
    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format
        
        Returns:
            Prometheus-formatted metrics string
        """
        lines = []
        
        # Export counters
        for name, value in self.counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        # Export gauges
        for name, value in self.gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        # Export timer summaries
        for name, values in self.timers.items():
            if values:
                lines.append(f"# TYPE {name} summary")
                lines.append(f"{name}_count {len(values)}")
                lines.append(f"{name}_sum {sum(values)}")
                
                if len(values) > 0:
                    for quantile in [0.5, 0.9, 0.95, 0.99]:
                        value = self._percentile(values, quantile * 100)
                        lines.append(f'{name}{{quantile="{quantile}"}} {value}')
        
        return "\n".join(lines)
    
    @staticmethod
    def _percentile(values: List[float], percentile: float) -> float:
        """
        Calculate percentile of values
        
        Args:
            values: List of values
            percentile: Percentile to calculate (0-100)
        
        Returns:
            Percentile value
        """
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = (len(sorted_values) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1
        
        if upper >= len(sorted_values):
            return sorted_values[lower]
        
        weight = index - lower
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


class AggregatedMetrics:
    """
    Aggregate metrics from multiple collectors
    """
    
    def __init__(self):
        """Initialize aggregated metrics"""
        self.collectors: Dict[str, MetricsCollector] = {}
    
    def register_collector(self, name: str, collector: MetricsCollector):
        """
        Register a metrics collector
        
        Args:
            name: Collector name
            collector: MetricsCollector instance
        """
        self.collectors[name] = collector
        logger.info(f"Registered metrics collector: {name}")
    
    def get_global_summary(self) -> Dict[str, Any]:
        """
        Get summary from all collectors
        
        Returns:
            Combined metrics summary
        """
        global_summary = {}
        
        for name, collector in self.collectors.items():
            global_summary[name] = collector.get_summary()
        
        # Add aggregate statistics
        total_metrics = sum(
            c.get_summary()["total_metrics"] 
            for c in self.collectors.values()
        )
        
        global_summary["_aggregate"] = {
            "total_collectors": len(self.collectors),
            "total_metrics": total_metrics
        }
        
        return global_summary
    
    def reset_all(self):
        """Reset all registered collectors"""
        for collector in self.collectors.values():
            collector.reset()
        logger.info("All metrics collectors reset")


# Global metrics instance for easy access
_global_metrics = AggregatedMetrics()


def get_global_metrics() -> AggregatedMetrics:
    """Get global metrics aggregator"""
    return _global_metrics


def create_metrics_collector(namespace: str) -> MetricsCollector:
    """
    Create and register a new metrics collector
    
    Args:
        namespace: Namespace for the collector
    
    Returns:
        New MetricsCollector instance
    """
    collector = MetricsCollector(namespace)
    _global_metrics.register_collector(namespace, collector)
    return collector
