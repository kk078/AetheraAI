"""
Aethera AI - Token Usage and Cost Tracking

Tracks requests per model, tokens in/out, estimated cost,
session/weekly/daily totals. Stores in SQLite and generates usage reports.
"""

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

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger("aethera.usage_tracker")

DB_PATH = os.getenv("USAGE_DB_PATH", "./data/aethera_usage.db")
REPORTS_DIR = os.getenv("USAGE_REPORTS_DIR", "./data/usage_reports")

# Pricing per 1M tokens (USD) - approximate rates as of 2025
MODEL_PRICING = {
    # Cloud models (Ollama Cloud)
    "qwen3.5:122b": {"input": 0.60, "output": 1.80},
    "deepseek-v4-flash": {"input": 0.14, "output": 0.28},
    "kimi-k2.6": {"input": 0.55, "output": 2.19},
    "gemma4:26b": {"input": 0.20, "output": 0.60},
    "nemotron-3-super": {"input": 0.15, "output": 0.40},
    "qwen3.5:35b": {"input": 0.30, "output": 0.90},
    "glm-5.1": {"input": 0.50, "output": 1.50},
    # Local models (free)
    "qwen3.5:4b": {"input": 0.0, "output": 0.0},
    "gemma4:e2b": {"input": 0.0, "output": 0.0},
    "qwen3.5:9b": {"input": 0.0, "output": 0.0},
    "nomic-embed-text": {"input": 0.0, "output": 0.0},
    # HuggingFace
    "Qwen/Qwen2.5-72B-Instruct": {"input": 0.0, "output": 0.0},
    "mistralai/Mistral-7B-Instruct-v0.3": {"input": 0.0, "output": 0.0},
}

app = FastAPI(title="Aethera Usage Tracker", version="1.0.0")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class UsageEntry(BaseModel):
    model: str
    provider: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    request_type: str  # chat, embedding, tool, voice
    session_id: Optional[str] = None
    specialist: Optional[str] = None
    timestamp: str


class UsageSummary(BaseModel):
    period: str
    total_requests: int
    total_tokens_in: int
    total_tokens_out: int
    total_cost_usd: float
    by_model: Dict[str, Dict[str, Any]]
    by_specialist: Dict[str, Dict[str, Any]]
    by_type: Dict[str, Dict[str, Any]]


class ModelUsage(BaseModel):
    model: str
    requests: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    avg_latency_ms: Optional[float] = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

class UsageDatabase:
    """
    SQLite-based usage tracking database.
    Append-only design for accurate auditing.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                    model TEXT NOT NULL,
                    provider TEXT NOT NULL DEFAULT '',
                    tokens_in INTEGER NOT NULL DEFAULT 0,
                    tokens_out INTEGER NOT NULL DEFAULT 0,
                    cost_usd REAL NOT NULL DEFAULT 0.0,
                    request_type TEXT NOT NULL DEFAULT 'chat',
                    session_id TEXT DEFAULT '',
                    specialist TEXT DEFAULT '',
                    latency_ms REAL DEFAULT 0.0,
                    metadata TEXT DEFAULT '{}'
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_timestamp
                ON usage_logs(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_model
                ON usage_logs(model)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_session
                ON usage_logs(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_specialist
                ON usage_logs(specialist)
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

    def record_usage(
        self,
        model: str,
        tokens_in: int,
        tokens_out: int,
        provider: str = "",
        request_type: str = "chat",
        session_id: str = "",
        specialist: str = "",
        latency_ms: float = 0.0,
        metadata: Optional[Dict] = None,
    ) -> int:
        """
        Record a usage event.

        Returns the inserted row ID.
        """
        cost = self._calculate_cost(model, tokens_in, tokens_out)

        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO usage_logs
                   (model, provider, tokens_in, tokens_out, cost_usd,
                    request_type, session_id, specialist, latency_ms, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    model, provider, tokens_in, tokens_out, cost,
                    request_type, session_id, specialist, latency_ms,
                    json.dumps(metadata or {}),
                ),
            )
            return cursor.lastrowid

    def _calculate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        """Calculate estimated cost based on token usage and model pricing."""
        pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
        input_cost = (tokens_in / 1_000_000) * pricing["input"]
        output_cost = (tokens_out / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def get_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily",
    ) -> UsageSummary:
        """
        Get usage summary for a time period.

        Args:
            start_date: ISO date string (default: based on period)
            end_date: ISO date string (default: now)
            period: daily, weekly, monthly, session
        """
        now = datetime.now()

        if not end_date:
            end_date = now.isoformat()

        if not start_date:
            if period == "daily":
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "weekly":
                start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "monthly":
                start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "session":
                start = now - timedelta(hours=5)
            else:
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = start.isoformat()

        with self._connect() as conn:
            # Overall totals
            row = conn.execute(
                """SELECT
                    COUNT(*) as total_requests,
                    COALESCE(SUM(tokens_in), 0) as total_tokens_in,
                    COALESCE(SUM(tokens_out), 0) as total_tokens_out,
                    COALESCE(SUM(cost_usd), 0.0) as total_cost_usd
                   FROM usage_logs
                   WHERE timestamp >= ? AND timestamp <= ?""",
                (start_date, end_date),
            ).fetchone()

            total_requests = row["total_requests"]
            total_tokens_in = row["total_tokens_in"]
            total_tokens_out = row["total_tokens_out"]
            total_cost = row["total_cost_usd"]

            # Per model breakdown
            by_model = {}
            model_rows = conn.execute(
                """SELECT model,
                    COUNT(*) as requests,
                    COALESCE(SUM(tokens_in), 0) as tokens_in,
                    COALESCE(SUM(tokens_out), 0) as tokens_out,
                    COALESCE(SUM(cost_usd), 0.0) as cost_usd,
                    COALESCE(AVG(latency_ms), 0.0) as avg_latency_ms
                   FROM usage_logs
                   WHERE timestamp >= ? AND timestamp <= ?
                   GROUP BY model
                   ORDER BY cost_usd DESC""",
                (start_date, end_date),
            ).fetchall()

            for r in model_rows:
                by_model[r["model"]] = {
                    "requests": r["requests"],
                    "tokens_in": r["tokens_in"],
                    "tokens_out": r["tokens_out"],
                    "cost_usd": round(r["cost_usd"], 6),
                    "avg_latency_ms": round(r["avg_latency_ms"], 1),
                }

            # Per specialist breakdown
            by_specialist = {}
            spec_rows = conn.execute(
                """SELECT specialist,
                    COUNT(*) as requests,
                    COALESCE(SUM(tokens_in), 0) as tokens_in,
                    COALESCE(SUM(tokens_out), 0) as tokens_out,
                    COALESCE(SUM(cost_usd), 0.0) as cost_usd
                   FROM usage_logs
                   WHERE timestamp >= ? AND timestamp <= ?
                   GROUP BY specialist
                   ORDER BY requests DESC""",
                (start_date, end_date),
            ).fetchall()

            for r in spec_rows:
                by_specialist[r["specialist"] or "unspecified"] = {
                    "requests": r["requests"],
                    "tokens_in": r["tokens_in"],
                    "tokens_out": r["tokens_out"],
                    "cost_usd": round(r["cost_usd"], 6),
                }

            # Per request type breakdown
            by_type = {}
            type_rows = conn.execute(
                """SELECT request_type,
                    COUNT(*) as requests,
                    COALESCE(SUM(tokens_in), 0) as tokens_in,
                    COALESCE(SUM(tokens_out), 0) as tokens_out,
                    COALESCE(SUM(cost_usd), 0.0) as cost_usd
                   FROM usage_logs
                   WHERE timestamp >= ? AND timestamp <= ?
                   GROUP BY request_type
                   ORDER BY requests DESC""",
                (start_date, end_date),
            ).fetchall()

            for r in type_rows:
                by_type[r["request_type"]] = {
                    "requests": r["requests"],
                    "tokens_in": r["tokens_in"],
                    "tokens_out": r["tokens_out"],
                    "cost_usd": round(r["cost_usd"], 6),
                }

        return UsageSummary(
            period=f"{start_date} to {end_date}",
            total_requests=total_requests,
            total_tokens_in=total_tokens_in,
            total_tokens_out=total_tokens_out,
            total_cost_usd=round(total_cost, 6),
            by_model=by_model,
            by_specialist=by_specialist,
            by_type=by_type,
        )

    def get_session_usage(self, session_id: str) -> UsageSummary:
        """Get usage for a specific session."""
        return self.get_summary(period="session", start_date="", end_date=datetime.now().isoformat())

    def get_daily_usage(self, days: int = 7) -> List[Dict]:
        """Get daily usage for the past N days."""
        results = []
        now = datetime.now()

        with self._connect() as conn:
            for i in range(days):
                day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
                next_day = (now - timedelta(days=i-1)).strftime("%Y-%m-%d") if i > 0 else (now + timedelta(days=1)).strftime("%Y-%m-%d")

                row = conn.execute(
                    """SELECT
                        COUNT(*) as requests,
                        COALESCE(SUM(tokens_in), 0) as tokens_in,
                        COALESCE(SUM(tokens_out), 0) as tokens_out,
                        COALESCE(SUM(cost_usd), 0.0) as cost_usd
                       FROM usage_logs
                       WHERE timestamp >= ? AND timestamp < ?""",
                    (f"{day}T00:00:00", f"{next_day}T00:00:00"),
                ).fetchone()

                results.append({
                    "date": day,
                    "requests": row["requests"],
                    "tokens_in": row["tokens_in"],
                    "tokens_out": row["tokens_out"],
                    "cost_usd": round(row["cost_usd"], 6),
                })

        return results

    def get_recent_entries(self, limit: int = 50) -> List[Dict]:
        """Get most recent usage entries."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id, timestamp, model, provider, tokens_in, tokens_out,
                          cost_usd, request_type, session_id, specialist, latency_ms
                   FROM usage_logs
                   ORDER BY id DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()

            return [dict(r) for r in rows]

    def export_report(self, start_date: str, end_date: str, format: str = "json") -> str:
        """
        Export a usage report for the given date range.

        Returns path to the exported report file.
        """
        Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)

        summary = self.get_summary(start_date, end_date, period="monthly")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"usage_report_{start_date[:10]}_{end_date[:10]}_{timestamp}"

        if format == "json":
            filepath = str(Path(REPORTS_DIR) / f"{filename}.json")
            with open(filepath, "w") as f:
                json.dump(summary.dict(), f, indent=2, default=str)

        elif format == "csv":
            filepath = str(Path(REPORTS_DIR) / f"{filename}.csv")
            with self._connect() as conn:
                rows = conn.execute(
                    """SELECT timestamp, model, provider, tokens_in, tokens_out,
                              cost_usd, request_type, session_id, specialist, latency_ms
                       FROM usage_logs
                       WHERE timestamp >= ? AND timestamp <= ?
                       ORDER BY timestamp""",
                    (start_date, end_date),
                ).fetchall()

                with open(filepath, "w") as f:
                    headers = ["timestamp", "model", "provider", "tokens_in", "tokens_out",
                               "cost_usd", "request_type", "session_id", "specialist", "latency_ms"]
                    f.write(",".join(headers) + "\n")
                    for row in rows:
                        f.write(",".join(str(row[h]) for h in headers) + "\n")
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info("Exported usage report: %s", filepath)
        return filepath


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------

_db: Optional[UsageDatabase] = None


def get_db() -> UsageDatabase:
    global _db
    if _db is None:
        _db = UsageDatabase()
    return _db


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------

@app.get("/usage/summary")
async def usage_summary(
    period: str = Query("daily", regex="^(daily|weekly|monthly|session)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Get usage summary for the specified period."""
    db = get_db()
    return db.get_summary(start_date, end_date, period)


@app.get("/usage/daily")
async def daily_usage(days: int = Query(7, ge=1, le=365)):
    """Get daily usage totals for the past N days."""
    db = get_db()
    return db.get_daily_usage(days)


@app.get("/usage/recent")
async def recent_usage(limit: int = Query(50, ge=1, le=500)):
    """Get most recent usage entries."""
    db = get_db()
    return db.get_recent_entries(limit)


@app.get("/usage/models")
async def model_usage():
    """Get usage breakdown by model."""
    db = get_db()
    summary = db.get_summary(period="monthly")
    return summary.by_model


@app.get("/usage/specialists")
async def specialist_usage():
    """Get usage breakdown by specialist."""
    db = get_db()
    summary = db.get_summary(period="monthly")
    return summary.by_specialist


@app.post("/usage/record")
async def record_usage(entry: UsageEntry):
    """Manually record a usage entry."""
    db = get_db()
    row_id = db.record_usage(
        model=entry.model,
        tokens_in=entry.tokens_in,
        tokens_out=entry.tokens_out,
        request_type=entry.request_type,
        session_id=entry.session_id or "",
        specialist=entry.specialist or "",
    )
    return {"id": row_id, "status": "recorded"}


@app.post("/usage/export")
async def export_report(
    start_date: str,
    end_date: str,
    format: str = Query("json", regex="^(json|csv)$"),
):
    """Export usage report for a date range."""
    db = get_db()
    filepath = db.export_report(start_date, end_date, format)
    return {"filepath": filepath, "format": format}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "aethera-usage-tracker"}


@app.on_event("startup")
async def startup():
    logging.basicConfig(level=logging.INFO)
    get_db()
    logger.info("Aethera Usage Tracker service started")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8505)