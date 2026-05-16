"""
Aethera AI - Container Health Monitoring

Monitors Docker container status, response times, and resource usage.
Provides HTTP API for health endpoints and alerts on failures.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger("aethera.health_check")

HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
ALERT_THRESHOLD_CONSECUTIVE = int(os.getenv("ALERT_THRESHOLD_CONSECUTIVE", "3"))
RESPONSE_TIME_WARN_MS = float(os.getenv("RESPONSE_TIME_WARN_MS", "5000"))
RESPONSE_TIME_CRIT_MS = float(os.getenv("RESPONSE_TIME_CRIT_MS", "15000"))
RESOURCE_CPU_WARN = float(os.getenv("RESOURCE_CPU_WARN", "80"))
RESOURCE_MEM_WARN = float(os.getenv("RESOURCE_MEM_WARN", "85"))

app = FastAPI(title="Aethera Health Check Service", version="1.0.0")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ContainerHealth(BaseModel):
    name: str
    status: HealthStatus
    running: bool
    response_time_ms: Optional[float] = None
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    memory_percent: Optional[float] = None
    restart_count: int = 0
    uptime_seconds: Optional[float] = None
    last_check: str
    message: str = ""
    consecutive_failures: int = 0


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert(BaseModel):
    id: str
    container: str
    severity: AlertSeverity
    message: str
    timestamp: str
    resolved: bool = False


class HealthReport(BaseModel):
    timestamp: str
    overall_status: HealthStatus
    containers: List[ContainerHealth]
    alerts: List[Alert] = []
    healthy_count: int
    unhealthy_count: int


# ---------------------------------------------------------------------------
# Container configuration
# ---------------------------------------------------------------------------

CONTAINER_CONFIGS = {
    "aethera-orchestrator": {
        "health_url": "http://localhost:8000/api/health",
        "essential": True,
    },
    "aethera-litellm": {
        "health_url": "http://localhost:4000/health",
        "essential": True,
    },
    "aethera-ollama": {
        "health_url": "http://localhost:11434/api/tags",
        "essential": True,
    },
    "aethera-chromadb": {
        "health_url": "http://localhost:8001/api/v1/heartbeat",
        "essential": True,
    },
    "aethera-searxng": {
        "health_url": "http://localhost:8888/healthz",
        "essential": False,
    },
    "aethera-redis": {
        "health_url": None,
        "essential": True,
        "custom_check": "redis_ping",
    },
    "aethera-ui": {
        "health_url": "http://localhost:3000",
        "essential": False,
    },
    "aethera-voice": {
        "health_url": "http://localhost:8500/health",
        "essential": False,
    },
}


# ---------------------------------------------------------------------------
# Health checker
# ---------------------------------------------------------------------------

class ContainerHealthChecker:
    """
    Checks health of Docker containers via HTTP endpoints
    and Docker stats for resource usage.
    """

    def __init__(self):
        self._container_states: Dict[str, ContainerHealth] = {}
        self._alerts: List[Alert] = []
        self._alert_counter = 0
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._running = False

    async def _get_http_session(self) -> aiohttp.ClientSession:
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        return self._http_session

    async def check_all(self) -> HealthReport:
        """
        Run health checks on all configured containers.
        Returns a comprehensive health report.
        """
        results = []

        for name, config in CONTAINER_CONFIGS.items():
            health = await self._check_container(name, config)
            results.append(health)
            self._container_states[name] = health

        # Determine overall status
        essential_unhealthy = any(
            h.status == HealthStatus.UNHEALTHY
            for h in results
            if CONTAINER_CONFIGS.get(h.name, {}).get("essential", False)
        )
        any_degraded = any(h.status == HealthStatus.DEGRADED for h in results)

        if essential_unhealthy:
            overall = HealthStatus.UNHEALTHY
        elif any_degraded:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        # Generate alerts
        for health in results:
            if health.status == HealthStatus.UNHEALTHY and health.consecutive_failures >= ALERT_THRESHOLD_CONSECUTIVE:
                self._create_alert(health.name, AlertSeverity.CRITICAL, f"{health.name} has been unhealthy for {health.consecutive_failures} consecutive checks")
            elif health.status == HealthStatus.DEGRADED:
                self._create_alert(health.name, AlertSeverity.WARNING, f"{health.name} is degraded: {health.message}")

        healthy_count = sum(1 for h in results if h.status == HealthStatus.HEALTHY)
        unhealthy_count = sum(1 for h in results if h.status == HealthStatus.UNHEALTHY)

        return HealthReport(
            timestamp=datetime.now().isoformat(),
            overall_status=overall,
            containers=results,
            alerts=self._get_active_alerts(),
            healthy_count=healthy_count,
            unhealthy_count=unhealthy_count,
        )

    async def _check_container(self, name: str, config: Dict) -> ContainerHealth:
        """Check a single container's health."""
        now = datetime.now().isoformat()

        # Get Docker container info
        running, restart_count, uptime = await self._get_docker_status(name)

        if not running:
            prev = self._container_states.get(name)
            consecutive = (prev.consecutive_failures + 1) if prev else 1
            return ContainerHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                running=False,
                restart_count=restart_count,
                uptime_seconds=uptime,
                last_check=now,
                message="Container not running",
                consecutive_failures=consecutive,
            )

        # Check HTTP health endpoint
        health_url = config.get("health_url")
        custom_check = config.get("custom_check")

        response_time = None
        message = "OK"
        status = HealthStatus.HEALTHY

        if health_url:
            response_time, http_ok, http_msg = await self._check_http(health_url)
            if not http_ok:
                prev = self._container_states.get(name)
                consecutive = (prev.consecutive_failures + 1) if prev else 1
                status = HealthStatus.UNHEALTHY
                message = http_msg
            else:
                prev = self._container_states.get(name)
                consecutive = 0
                # Check response time
                if response_time and response_time > RESPONSE_TIME_CRIT_MS:
                    status = HealthStatus.UNHEALTHY
                    message = f"Response time critical: {response_time:.0f}ms"
                elif response_time and response_time > RESPONSE_TIME_WARN_MS:
                    status = HealthStatus.DEGRADED
                    message = f"Response time slow: {response_time:.0f}ms"
        elif custom_check == "redis_ping":
            ping_ok, ping_time, ping_msg = await self._check_redis()
            if not ping_ok:
                prev = self._container_states.get(name)
                consecutive = (prev.consecutive_failures + 1) if prev else 1
                status = HealthStatus.UNHEALTHY
                message = ping_msg
            else:
                prev = self._container_states.get(name)
                consecutive = 0
                response_time = ping_time
        else:
            consecutive = 0

        # Get resource usage
        cpu, mem_mb, mem_pct = await self._get_container_stats(name)

        # Check resource thresholds
        if status == HealthStatus.HEALTHY:
            if cpu and cpu > RESOURCE_CPU_WARN:
                status = HealthStatus.DEGRADED
                message = f"CPU usage high: {cpu:.1f}%"
            elif mem_pct and mem_pct > RESOURCE_MEM_WARN:
                status = HealthStatus.DEGRADED
                message = f"Memory usage high: {mem_pct:.1f}%"

        return ContainerHealth(
            name=name,
            status=status,
            running=running,
            response_time_ms=response_time,
            cpu_percent=cpu,
            memory_mb=mem_mb,
            memory_percent=mem_pct,
            restart_count=restart_count,
            uptime_seconds=uptime,
            last_check=now,
            message=message,
            consecutive_failures=consecutive,
        )

    async def _check_http(self, url: str) -> Tuple[Optional[float], bool, str]:
        """Check HTTP endpoint health. Returns (response_time_ms, success, message)."""
        session = await self._get_http_session()
        start = time.time()

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                elapsed = (time.time() - start) * 1000

                if resp.status < 500:
                    return elapsed, True, f"HTTP {resp.status}"
                else:
                    return elapsed, False, f"HTTP {resp.status}"
        except asyncio.TimeoutError:
            elapsed = (time.time() - start) * 1000
            return elapsed, False, "Request timed out"
        except aiohttp.ClientConnectorError as exc:
            elapsed = (time.time() - start) * 1000
            return elapsed, False, f"Connection failed: {exc}"
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            return elapsed, False, f"Error: {exc}"

    async def _check_redis(self) -> Tuple[bool, Optional[float], str]:
        """Check Redis health via ping."""
        start = time.time()
        try:
            import redis as redis_lib

            r = redis_lib.Redis(host="localhost", port=6379, socket_timeout=5)
            pong = r.ping()
            elapsed = (time.time() - start) * 1000
            if pong:
                return True, elapsed, "PONG"
            return False, elapsed, "No PONG response"
        except ImportError:
            # Try via Docker exec
            try:
                proc = await asyncio.create_subprocess_exec(
                    "docker", "exec", "aethera-redis", "redis-cli", "ping",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
                elapsed = (time.time() - start) * 1000
                if b"PONG" in stdout:
                    return True, elapsed, "PONG"
                return False, elapsed, stdout.decode().strip()
            except Exception as exc:
                elapsed = (time.time() - start) * 1000
                return False, elapsed, str(exc)
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            return False, elapsed, str(exc)

    async def _get_docker_status(self, container_name: str) -> Tuple[bool, int, Optional[float]]:
        """Get Docker container running status, restart count, and uptime."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "inspect", "--format",
                "{{.State.Running}}|{{.RestartCount}}|{{.State.StartedAt}}",
                container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)

            if proc.returncode != 0:
                return False, 0, None

            output = stdout.decode().strip()
            parts = output.split("|")

            running = parts[0].strip().lower() == "true" if len(parts) > 0 else False
            restart_count = int(parts[1].strip()) if len(parts) > 1 else 0

            uptime = None
            if len(parts) > 2 and running:
                try:
                    started_at_raw = parts[2].strip()
                    # Docker timestamps may have nanosecond precision and trailing Z
                    # Strip Z and truncate fractional seconds to microseconds
                    ts = started_at_raw.rstrip("Z")
                    if "." in ts:
                        base, frac = ts.split(".", 1)
                        ts = base + "." + frac[:6]
                    started_dt = datetime.fromisoformat(ts)
                    uptime = (datetime.now(started_dt.tzinfo) - started_dt).total_seconds()
                except (ValueError, TypeError):
                    pass

            return running, restart_count, uptime

        except (asyncio.TimeoutError, FileNotFoundError, Exception):
            return False, 0, None

    async def _get_container_stats(self, container_name: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Get container CPU and memory usage from Docker stats."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "stats", "--no-stream", "--format",
                "{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}",
                container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)

            if proc.returncode != 0:
                return None, None, None

            output = stdout.decode().strip()
            parts = output.split("|")

            cpu = None
            mem_mb = None
            mem_pct = None

            if len(parts) >= 1:
                try:
                    cpu = float(parts[0].strip().rstrip("%"))
                except ValueError:
                    pass

            if len(parts) >= 2:
                try:
                    mem_str = parts[1].strip()
                    # Parse "123.4MiB / 2048MiB" format
                    used = mem_str.split("/")[0].strip()
                    if "GiB" in used:
                        mem_mb = float(used.replace("GiB", "").strip()) * 1024
                    elif "MiB" in used:
                        mem_mb = float(used.replace("MiB", "").strip())
                except (ValueError, IndexError):
                    pass

            if len(parts) >= 3:
                try:
                    mem_pct = float(parts[2].strip().rstrip("%"))
                except ValueError:
                    pass

            return cpu, mem_mb, mem_pct

        except (asyncio.TimeoutError, FileNotFoundError):
            return None, None, None

    def _create_alert(self, container: str, severity: AlertSeverity, message: str):
        """Create a new alert."""
        self._alert_counter += 1
        alert = Alert(
            id=f"alert-{self._alert_counter}",
            container=container,
            severity=severity,
            message=message,
            timestamp=datetime.now().isoformat(),
        )

        # Check if similar alert already active
        existing = [a for a in self._alerts if a.container == container and not a.resolved and a.severity == severity]
        if existing:
            existing[0].message = message
            existing[0].timestamp = alert.timestamp
            return

        self._alerts.append(alert)

        # Keep last 200 alerts
        if len(self._alerts) > 200:
            self._alerts = self._alerts[-200:]

    def _get_active_alerts(self) -> List[Alert]:
        """Get all unresolved alerts."""
        return [a for a in self._alerts if not a.resolved]

    def resolve_alerts(self, container: str):
        """Resolve all active alerts for a container."""
        for alert in self._alerts:
            if alert.container == container and not alert.resolved:
                alert.resolved = True

    def get_container_health(self, name: str) -> Optional[ContainerHealth]:
        """Get health status for a specific container."""
        return self._container_states.get(name)

    def get_history(self, container: Optional[str] = None, limit: int = 50) -> List[ContainerHealth]:
        """Get health check history."""
        if container:
            health = self._container_states.get(container)
            return [health] if health else []
        return list(self._container_states.values())


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------

_checker: Optional[ContainerHealthChecker] = None


def get_health_checker() -> ContainerHealthChecker:
    global _checker
    if _checker is None:
        _checker = ContainerHealthChecker()
    return _checker


# ---------------------------------------------------------------------------
# HTTP API endpoints
# ---------------------------------------------------------------------------

@app.get("/health/report")
async def health_report():
    """Get comprehensive health report for all containers."""
    checker = get_health_checker()
    return await checker.check_all()


@app.get("/health/container/{name}")
async def container_health(name: str):
    """Get health status for a specific container."""
    checker = get_health_checker()
    health = checker.get_container_health(name)
    if not health:
        raise HTTPException(status_code=404, detail=f"Container {name} not found in monitoring")
    return health


@app.get("/health/alerts")
async def active_alerts():
    """Get all active (unresolved) alerts."""
    checker = get_health_checker()
    return checker._get_active_alerts()


@app.post("/health/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Mark an alert as resolved."""
    checker = get_health_checker()
    for alert in checker._alerts:
        if alert.id == alert_id:
            alert.resolved = True
            return {"status": "resolved"}
    raise HTTPException(status_code=404, detail="Alert not found")


@app.get("/health/containers")
async def list_containers():
    """List all monitored containers and their current status."""
    checker = get_health_checker()
    return {
        name: {
            "status": health.status,
            "running": health.running,
            "response_time_ms": health.response_time_ms,
            "message": health.message,
        }
        for name, health in checker._container_states.items()
    }


@app.get("/health")
async def service_health():
    """Health check for the monitoring service itself."""
    return {"status": "healthy", "service": "aethera-health-check"}


# ---------------------------------------------------------------------------
# Background monitoring loop
# ---------------------------------------------------------------------------

async def monitoring_loop():
    """Background task that periodically checks container health."""
    checker = get_health_checker()

    while True:
        try:
            await checker.check_all()
        except Exception as exc:
            logger.error("Health check loop error: %s", exc)

        await asyncio.sleep(HEALTH_CHECK_INTERVAL)


@app.on_event("startup")
async def startup():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(monitoring_loop())
    logger.info("Aethera Health Check service started")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8504)