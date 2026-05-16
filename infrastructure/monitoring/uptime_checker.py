"""
Aethera AI - External Uptime Monitoring

Periodic checks of all service endpoints. Records uptime percentage,
response times, and incident history. Generates status page data.
"""

import asyncio
import json
import logging
import os
import sqlite3
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from fastapi import FastAPI, Query
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger("aethera.uptime_checker")

DB_PATH = os.getenv("UPTIME_DB_PATH", "./data/aethera_uptime.db")
CHECK_INTERVAL = int(os.getenv("UPTIME_CHECK_INTERVAL", "60"))
TIMEOUT_SECONDS = int(os.getenv("UPTIME_TIMEOUT", "10"))
RETENTION_DAYS = int(os.getenv("UPTIME_RETENTION_DAYS", "90"))

app = FastAPI(title="Aethera Uptime Checker", version="1.0.0")

# ---------------------------------------------------------------------------
# Service definitions
# ---------------------------------------------------------------------------

SERVICES = {
    "orchestrator": {
        "name": "Orchestrator API",
        "url": "http://localhost:8000/api/health",
        "category": "core",
    },
    "litellm": {
        "name": "LiteLLM Proxy",
        "url": "http://localhost:4000/health",
        "category": "core",
    },
    "ollama": {
        "name": "Ollama Inference",
        "url": "http://localhost:11434/api/tags",
        "category": "core",
    },
    "chromadb": {
        "name": "ChromaDB Vector Store",
        "url": "http://localhost:8001/api/v1/heartbeat",
        "category": "core",
    },
    "redis": {
        "name": "Redis Cache",
        "url": None,
        "category": "core",
        "check_type": "redis",
    },
    "searxng": {
        "name": "SearXNG Search",
        "url": "http://localhost:8888/healthz",
        "category": "tools",
    },
    "ui": {
        "name": "Web UI",
        "url": "http://localhost:3000",
        "category": "ui",
    },
    "voice": {
        "name": "Voice Service",
        "url": "http://localhost:8500/api/health",
        "category": "voice",
    },
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CheckResult(BaseModel):
    service_id: str
    service_name: str
    up: bool
    response_time_ms: Optional[float] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
    timestamp: str


class ServiceUptime(BaseModel):
    service_id: str
    service_name: str
    category: str
    current_status: str  # up, down, degraded
    uptime_pct_24h: float
    uptime_pct_7d: float
    uptime_pct_30d: float
    avg_response_ms: Optional[float] = None
    last_check: Optional[str] = None
    last_incident: Optional[str] = None
    total_checks: int
    total_up: int


class Incident(BaseModel):
    id: int
    service_id: str
    service_name: str
    started_at: str
    ended_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    ongoing: bool
    details: str


class StatusPageData(BaseModel):
    overall_status: str  # operational, degraded, major_outage
    last_updated: str
    services: List[ServiceUptime]
    active_incidents: List[Incident]
    recent_incidents: List[Incident]


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

class UptimeDatabase:
    """SQLite database for uptime check results and incidents."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS check_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                    service_id TEXT NOT NULL,
                    up INTEGER NOT NULL,
                    response_time_ms REAL DEFAULT 0,
                    status_code INTEGER DEFAULT 0,
                    error TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_check_timestamp ON check_results(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_check_service ON check_results(service_id)
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    duration_seconds REAL,
                    ongoing INTEGER NOT NULL DEFAULT 1,
                    details TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_incident_service ON incidents(service_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_incident_ongoing ON incidents(ongoing)
            """)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def record_check(self, service_id: str, up: bool, response_time_ms: float = 0,
                     status_code: int = 0, error: str = ""):
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO check_results (service_id, up, response_time_ms, status_code, error)
                   VALUES (?, ?, ?, ?, ?)""",
                (service_id, int(up), response_time_ms, status_code, error),
            )

            # Check for incident state change
            if not up:
                self._start_incident(conn, service_id, error)
            else:
                self._end_incident(conn, service_id)

    def _start_incident(self, conn, service_id: str, details: str):
        """Start a new incident if none is ongoing."""
        existing = conn.execute(
            "SELECT id FROM incidents WHERE service_id = ? AND ongoing = 1",
            (service_id,),
        ).fetchone()

        if not existing:
            conn.execute(
                """INSERT INTO incidents (service_id, started_at, details, ongoing)
                   VALUES (?, datetime('now'), ?, 1)""",
                (service_id, details),
            )
            logger.info("Incident started for %s: %s", service_id, details)

    def _end_incident(self, conn, service_id: str):
        """End any ongoing incident for the service."""
        ongoing = conn.execute(
            "SELECT id, started_at FROM incidents WHERE service_id = ? AND ongoing = 1",
            (service_id,),
        ).fetchall()

        for incident in ongoing:
            conn.execute(
                """UPDATE incidents
                   SET ended_at = datetime('now'),
                       duration_seconds = (julianday(datetime('now')) - julianday(started_at)) * 86400,
                       ongoing = 0
                   WHERE id = ?""",
                (incident["id"],),
            )

    def get_uptime_stats(self, service_id: str, hours: int = 24) -> ServiceUptime:
        """Calculate uptime statistics for a service."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        with self._connect() as conn:
            # 24h stats
            row_24h = conn.execute(
                """SELECT
                    COUNT(*) as total,
                    SUM(up) as up_count,
                    AVG(CASE WHEN up = 1 THEN response_time_ms END) as avg_response
                   FROM check_results
                   WHERE service_id = ? AND timestamp >= datetime('now', '-1 day')""",
                (service_id,),
            ).fetchone()

            total_24h = row_24h["total"] or 0
            up_24h = row_24h["up_count"] or 0
            uptime_24h = (up_24h / total_24h * 100) if total_24h > 0 else 100.0
            avg_response_24h = row_24h["avg_response"] or 0

            # 7d stats
            row_7d = conn.execute(
                """SELECT
                    COUNT(*) as total,
                    SUM(up) as up_count
                   FROM check_results
                   WHERE service_id = ? AND timestamp >= datetime('now', '-7 days')""",
                (service_id,),
            ).fetchone()

            total_7d = row_7d["total"] or 0
            up_7d = row_7d["up_count"] or 0
            uptime_7d = (up_7d / total_7d * 100) if total_7d > 0 else 100.0

            # 30d stats
            row_30d = conn.execute(
                """SELECT
                    COUNT(*) as total,
                    SUM(up) as up_count
                   FROM check_results
                   WHERE service_id = ? AND timestamp >= datetime('now', '-30 days')""",
                (service_id,),
            ).fetchone()

            total_30d = row_30d["total"] or 0
            up_30d = row_30d["up_count"] or 0
            uptime_30d = (up_30d / total_30d * 100) if total_30d > 0 else 100.0

            # Last check
            last = conn.execute(
                """SELECT timestamp, up FROM check_results
                   WHERE service_id = ? ORDER BY id DESC LIMIT 1""",
                (service_id,),
            ).fetchone()

            last_check = last["timestamp"] if last else None
            current_status = "up" if (last and last["up"]) else "down" if last else "unknown"

            # Last incident
            last_inc = conn.execute(
                """SELECT started_at FROM incidents
                   WHERE service_id = ? ORDER BY id DESC LIMIT 1""",
                (service_id,),
            ).fetchone()

            last_incident = last_inc["started_at"] if last_inc else None

            # Total checks and up
            total_all = conn.execute(
                "SELECT COUNT(*) as total, SUM(up) as up_count FROM check_results WHERE service_id = ?",
                (service_id,),
            ).fetchone()

        svc = SERVICES.get(service_id, {})

        return ServiceUptime(
            service_id=service_id,
            service_name=svc.get("name", service_id),
            category=svc.get("category", "unknown"),
            current_status=current_status,
            uptime_pct_24h=round(uptime_24h, 2),
            uptime_pct_7d=round(uptime_7d, 2),
            uptime_pct_30d=round(uptime_30d, 2),
            avg_response_ms=round(avg_response_24h, 1),
            last_check=last_check,
            last_incident=last_incident,
            total_checks=total_all["total"] or 0,
            total_up=total_all["up_count"] or 0,
        )

    def get_active_incidents(self) -> List[Incident]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT i.*, COALESCE(s.name, i.service_id) as service_name
                   FROM incidents i
                   LEFT JOIN (SELECT 'orchestrator' as id, 'Orchestrator' as name) s ON 1=0
                   WHERE i.ongoing = 1
                   ORDER BY i.started_at DESC""",
            ).fetchall()

            results = []
            for r in rows:
                results.append(Incident(
                    id=r["id"],
                    service_id=r["service_id"],
                    service_name=SERVICES.get(r["service_id"], {}).get("name", r["service_id"]),
                    started_at=r["started_at"],
                    ended_at=r["ended_at"],
                    duration_seconds=r["duration_seconds"],
                    ongoing=bool(r["ongoing"]),
                    details=r["details"],
                ))
            return results

    def get_recent_incidents(self, limit: int = 20) -> List[Incident]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM incidents ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()

            results = []
            for r in rows:
                results.append(Incident(
                    id=r["id"],
                    service_id=r["service_id"],
                    service_name=SERVICES.get(r["service_id"], {}).get("name", r["service_id"]),
                    started_at=r["started_at"],
                    ended_at=r["ended_at"],
                    duration_seconds=r["duration_seconds"],
                    ongoing=bool(r["ongoing"]),
                    details=r["details"],
                ))
            return results

    def get_response_times(self, service_id: str, hours: int = 24) -> List[Dict]:
        """Get response time data points for charting."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        with self._connect() as conn:
            rows = conn.execute(
                """SELECT timestamp, response_time_ms
                   FROM check_results
                   WHERE service_id = ? AND timestamp >= ? AND up = 1
                   ORDER BY timestamp""",
                (service_id, cutoff),
            ).fetchall()

            return [{"timestamp": r["timestamp"], "response_ms": r["response_time_ms"]} for r in rows]

    def cleanup_old_data(self):
        """Remove check results older than retention period."""
        cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).isoformat()

        with self._connect() as conn:
            conn.execute(
                "DELETE FROM check_results WHERE timestamp < ?",
                (cutoff,),
            )

        logger.info("Cleaned up check results older than %d days", RETENTION_DAYS)


# ---------------------------------------------------------------------------
# Uptime checker
# ---------------------------------------------------------------------------

class UptimeChecker:
    """Performs periodic health checks on all services."""

    def __init__(self):
        self._db = UptimeDatabase()
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._running = False

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        return self._http_session

    async def check_service(self, service_id: str) -> CheckResult:
        """Check a single service."""
        svc = SERVICES.get(service_id, {})
        name = svc.get("name", service_id)
        url = svc.get("url")
        check_type = svc.get("check_type", "http")

        if check_type == "redis":
            return await self._check_redis(service_id, name)

        if not url:
            return CheckResult(
                service_id=service_id,
                service_name=name,
                up=False,
                error="No URL configured",
                timestamp=datetime.now().isoformat(),
            )

        session = await self._get_session()
        start = time.time()

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)) as resp:
                elapsed = (time.time() - start) * 1000
                up = resp.status < 500

                return CheckResult(
                    service_id=service_id,
                    service_name=name,
                    up=up,
                    response_time_ms=round(elapsed, 1),
                    status_code=resp.status,
                    timestamp=datetime.now().isoformat(),
                )
        except asyncio.TimeoutError:
            elapsed = (time.time() - start) * 1000
            return CheckResult(
                service_id=service_id,
                service_name=name,
                up=False,
                response_time_ms=round(elapsed, 1),
                error="Timeout",
                timestamp=datetime.now().isoformat(),
            )
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            return CheckResult(
                service_id=service_id,
                service_name=name,
                up=False,
                response_time_ms=round(elapsed, 1),
                error=str(exc)[:200],
                timestamp=datetime.now().isoformat(),
            )

    async def _check_redis(self, service_id: str, name: str) -> CheckResult:
        """Check Redis via docker exec or direct connection."""
        start = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "exec", "aethera-redis", "redis-cli", "ping",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            elapsed = (time.time() - start) * 1000
            up = b"PONG" in stdout

            return CheckResult(
                service_id=service_id,
                service_name=name,
                up=up,
                response_time_ms=round(elapsed, 1),
                error="" if up else "No PONG",
                timestamp=datetime.now().isoformat(),
            )
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            return CheckResult(
                service_id=service_id,
                service_name=name,
                up=False,
                response_time_ms=round(elapsed, 1),
                error=str(exc)[:200],
                timestamp=datetime.now().isoformat(),
            )

    async def check_all(self) -> List[CheckResult]:
        """Check all services and record results."""
        results = []
        for service_id in SERVICES:
            result = await self.check_service(service_id)
            results.append(result)

            self._db.record_check(
                service_id=result.service_id,
                up=result.up,
                response_time_ms=result.response_time_ms or 0,
                status_code=result.status_code or 0,
                error=result.error or "",
            )

        return results

    def generate_status_page(self) -> StatusPageData:
        """Generate data for a status page."""
        service_uptimes = []
        any_down = False
        any_degraded = False

        for service_id in SERVICES:
            uptime = self._db.get_uptime_stats(service_id)
            service_uptimes.append(uptime)

            if uptime.current_status == "down":
                any_down = True
            elif uptime.uptime_pct_24h < 99.0:
                any_degraded = True

        if any_down:
            overall = "major_outage"
        elif any_degraded:
            overall = "degraded"
        else:
            overall = "operational"

        return StatusPageData(
            overall_status=overall,
            last_updated=datetime.now().isoformat(),
            services=service_uptimes,
            active_incidents=self._db.get_active_incidents(),
            recent_incidents=self._db.get_recent_incidents(10),
        )


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------

_checker: Optional[UptimeChecker] = None


def get_checker() -> UptimeChecker:
    global _checker
    if _checker is None:
        _checker = UptimeChecker()
    return _checker


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------

@app.get("/uptime/status")
async def status_page():
    """Get status page data for all services."""
    checker = get_checker()
    return checker.generate_status_page()


@app.get("/uptime/service/{service_id}")
async def service_status(service_id: str):
    """Get uptime stats for a specific service."""
    if service_id not in SERVICES:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Service {service_id} not monitored")
    db = get_checker()._db
    return db.get_uptime_stats(service_id)


@app.get("/uptime/service/{service_id}/response-times")
async def service_response_times(service_id: str, hours: int = Query(24, ge=1, le=168)):
    """Get response time data points for a service."""
    db = get_checker()._db
    return db.get_response_times(service_id, hours)


@app.get("/uptime/incidents")
async def incidents(limit: int = Query(20, ge=1, le=100)):
    """Get recent incidents."""
    db = get_checker()._db
    return db.get_recent_incidents(limit)


@app.get("/uptime/incidents/active")
async def active_incidents():
    """Get currently active (ongoing) incidents."""
    db = get_checker()._db
    return db.get_active_incidents()


@app.post("/uptime/check")
async def trigger_check():
    """Manually trigger a check of all services."""
    checker = get_checker()
    results = await checker.check_all()
    return results


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "aethera-uptime-checker"}


# ---------------------------------------------------------------------------
# Background monitoring loop
# ---------------------------------------------------------------------------

async def monitoring_loop():
    """Periodically check all services."""
    checker = get_checker()

    # Run initial check
    await checker.check_all()

    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL)
            await checker.check_all()

            # Cleanup old data daily (every 1440 checks ~ 24h at 60s interval)
            if int(time.time()) % 86400 < CHECK_INTERVAL:
                checker._db.cleanup_old_data()

        except Exception as exc:
            logger.error("Uptime check loop error: %s", exc)
            await asyncio.sleep(10)


@app.on_event("startup")
async def startup():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(monitoring_loop())
    logger.info("Aethera Uptime Checker service started")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8506)