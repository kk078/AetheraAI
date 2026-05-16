"""
Aethera AI - Monitoring System

Health checks, metrics, and alerting.
"""
import asyncio
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class HealthStatus:
    """Service health status."""
    service: str
    healthy: bool
    latency_ms: float
    message: str
    timestamp: str


class MonitoringSystem:
    """
    System monitoring and alerting.

    Monitors:
    - Service health (orchestrator, Ollama, ChromaDB, etc.)
    - Resource usage (memory, CPU, disk)
    - Request rates and latencies
    - Error rates
    """

    def __init__(self):
        self._metrics: Dict[str, List[float]] = {}
        self._alerts: List[Dict] = []
        self._last_check: Optional[datetime] = None

    async def check_all_services(self) -> Dict[str, HealthStatus]:
        """Check health of all services."""
        services = [
            ("orchestrator", "http://localhost:8000/api/health"),
            ("ollama", "http://localhost:11434/api/tags"),
            ("chromadb", "http://localhost:8001/api/v1/heartbeat"),
            ("redis", "redis://localhost:6379"),
            ("litellm", "http://localhost:4000/health"),
            ("searxng", "http://localhost:8888/healthz"),
        ]

        results = {}

        for service, url in services:
            status = await self._check_service(service, url)
            results[service] = status

            if not status.healthy:
                self._create_alert(service, status)

        self._last_check = datetime.now()
        return results

    async def _check_service(self, name: str, url: Optional[str]) -> HealthStatus:
        """Check a single service."""
        start = time.time()

        if not url:
            return HealthStatus(
                service=name,
                healthy=True,
                latency_ms=0,
                message="OK (not checked)",
                timestamp=datetime.now().isoformat()
            )

        # Handle Redis URL (redis://host:port)
        if url and url.startswith("redis://"):
            try:
                import redis.asyncio as redis_lib
                r = redis_lib.from_url(url)
                start = time.time()
                await r.ping()
                latency = (time.time() - start) * 1000
                await r.aclose()
                return HealthStatus(
                    service=name,
                    healthy=True,
                    latency_ms=latency,
                    message="OK",
                    timestamp=datetime.now().isoformat()
                )
            except Exception as e:
                return HealthStatus(
                    service=name,
                    healthy=False,
                    latency_ms=(time.time() - start) * 1000,
                    message=str(e),
                    timestamp=datetime.now().isoformat()
                )

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    latency = (time.time() - start) * 1000

                    if resp.status == 200:
                        return HealthStatus(
                            service=name,
                            healthy=True,
                            latency_ms=latency,
                            message="OK",
                            timestamp=datetime.now().isoformat()
                        )
                    else:
                        return HealthStatus(
                            service=name,
                            healthy=False,
                            latency_ms=latency,
                            message=f"HTTP {resp.status}",
                            timestamp=datetime.now().isoformat()
                        )
        except Exception as e:
            return HealthStatus(
                service=name,
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                message=str(e),
                timestamp=datetime.now().isoformat()
            )

    def _create_alert(self, service: str, status: HealthStatus):
        """Create alert for unhealthy service."""
        alert = {
            "service": service,
            "message": f"Service {service} is unhealthy: {status.message}",
            "severity": "critical" if not status.healthy else "info",
            "timestamp": status.timestamp
        }
        self._alerts.append(alert)

        # Keep only last 100 alerts
        if len(self._alerts) > 100:
            self._alerts = self._alerts[-100:]

    def record_metric(self, name: str, value: float):
        """Record a metric value."""
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(value)

        # Keep only last 1000 values
        if len(self._metrics[name]) > 1000:
            self._metrics[name] = self._metrics[name][-1000:]

    def get_metrics(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics statistics."""
        if name:
            values = self._metrics.get(name, [])
            if not values:
                return {"name": name, "count": 0}
            return {
                "name": name,
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1] if values else None
            }

        return {
            name: self.get_metrics(name)
            for name in self._metrics
        }

    def get_alerts(self, limit: int = 20) -> List[Dict]:
        """Get recent alerts."""
        return self._alerts[-limit:]

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system resource statistics."""
        import psutil

        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_gb": psutil.virtual_memory().used / (1024 ** 3),
            "disk_percent": psutil.disk_usage("/").percent if psutil.disk_usage else 0,
            "timestamp": datetime.now().isoformat()
        }


# Singleton
_system: Optional[MonitoringSystem] = None


def get_monitoring_system() -> MonitoringSystem:
    """Get monitoring system instance."""
    global _system
    if _system is None:
        _system = MonitoringSystem()
    return _system
