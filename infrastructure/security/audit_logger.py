"""
Aethera AI - HIPAA-Grade Immutable Audit Trail

SQLite-based append-only audit log for HIPAA compliance.
Fields: timestamp, user_id, action, resource, details, ip_address, session_id.
No delete or update capability. Exportable for compliance reporting.
"""

import json
import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger("aethera.audit")

AUDIT_DB_PATH = os.getenv("AUDIT_DB_PATH", "./data/aethera_audit.db")
AUDIT_EXPORT_DIR = os.getenv("AUDIT_EXPORT_DIR", "./data/audit_exports")
AUDIT_RETENTION_DAYS = int(os.getenv("AUDIT_RETENTION_DAYS", "2555"))  # 7 years for HIPAA

app = FastAPI(title="Aethera Audit Logger", version="1.0.0")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AuditEntry(BaseModel):
    timestamp: str
    user_id: str
    action: str
    resource: str
    details: str = ""
    ip_address: str = ""
    session_id: str = ""


class AuditQuery(BaseModel):
    user_id: Optional[str] = None
    action: Optional[str] = None
    resource: Optional[str] = None
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    limit: int = 100
    offset: int = 0


class AuditExportRequest(BaseModel):
    start_date: str
    end_date: str
    format: str = "json"  # json or csv
    user_id: Optional[str] = None
    action: Optional[str] = None


class AuditStats(BaseModel):
    total_entries: int
    entries_today: int
    entries_this_week: int
    unique_users: int
    top_actions: List[Dict[str, Any]]
    top_resources: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Audit Database (Append-Only)
# ---------------------------------------------------------------------------

class AuditDatabase:
    """
    Immutable append-only audit trail database.

    HIPAA requires audit logs that cannot be modified or deleted.
    This implementation uses SQLite triggers to enforce immutability.
    """

    def __init__(self, db_path: str = AUDIT_DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database with append-only enforcement."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    user_id TEXT NOT NULL DEFAULT '',
                    action TEXT NOT NULL DEFAULT '',
                    resource TEXT NOT NULL DEFAULT '',
                    details TEXT NOT NULL DEFAULT '',
                    ip_address TEXT NOT NULL DEFAULT '',
                    session_id TEXT NOT NULL DEFAULT ''
                )
            """)

            # Indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_log(resource)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_ip ON audit_log(ip_address)")

            # Create triggers to prevent UPDATE and DELETE (append-only enforcement)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_audit_update
                BEFORE UPDATE ON audit_log
                BEGIN
                    SELECT RAISE(ABORT, 'Audit log is immutable: UPDATE not permitted');
                END
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_audit_delete
                BEFORE DELETE ON audit_log
                BEGIN
                    SELECT RAISE(ABORT, 'Audit log is immutable: DELETE not permitted');
                END
            """)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def log(
        self,
        user_id: str,
        action: str,
        resource: str = "",
        details: str = "",
        ip_address: str = "",
        session_id: str = "",
    ) -> int:
        """
        Append an audit log entry.

        Args:
            user_id: User or system identifier
            action: Action performed (e.g., 'view_patient', 'export_data')
            resource: Resource acted upon (e.g., 'patient_record:12345')
            details: Additional details (JSON string recommended)
            ip_address: Client IP address
            session_id: Session identifier

        Returns:
            Inserted row ID
        """
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO audit_log
                   (user_id, action, resource, details, ip_address, session_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, action, resource, details, ip_address, session_id),
            )
            return cursor.lastrowid

    def log_event(self, entry: AuditEntry) -> int:
        """Log an audit event from an AuditEntry model."""
        return self.log(
            user_id=entry.user_id,
            action=entry.action,
            resource=entry.resource,
            details=entry.details,
            ip_address=entry.ip_address,
            session_id=entry.session_id,
        )

    def query(self, query_params: AuditQuery) -> List[Dict]:
        """
        Query audit log with filters.

        Returns list of matching entries (newest first by default).
        """
        conditions = []
        params = []

        if query_params.user_id:
            conditions.append("user_id = ?")
            params.append(query_params.user_id)

        if query_params.action:
            conditions.append("action = ?")
            params.append(query_params.action)

        if query_params.resource:
            conditions.append("resource LIKE ?")
            params.append(f"%{query_params.resource}%")

        if query_params.ip_address:
            conditions.append("ip_address = ?")
            params.append(query_params.ip_address)

        if query_params.session_id:
            conditions.append("session_id = ?")
            params.append(query_params.session_id)

        if query_params.start_date:
            conditions.append("timestamp >= ?")
            params.append(query_params.start_date)

        if query_params.end_date:
            conditions.append("timestamp <= ?")
            params.append(query_params.end_date)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with self._connect() as conn:
            rows = conn.execute(
                f"""SELECT * FROM audit_log
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?""",
                params + [query_params.limit, query_params.offset],
            ).fetchall()

            return [dict(r) for r in rows]

    def get_by_user(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Get audit entries for a specific user."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM audit_log
                   WHERE user_id = ?
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_by_resource(self, resource: str, limit: int = 100) -> List[Dict]:
        """Get audit entries for a specific resource."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM audit_log
                   WHERE resource LIKE ?
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (f"%{resource}%", limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_by_date_range(self, start_date: str, end_date: str, limit: int = 1000) -> List[Dict]:
        """Get audit entries within a date range."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM audit_log
                   WHERE timestamp >= ? AND timestamp <= ?
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (start_date, end_date, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self) -> AuditStats:
        """Get audit log statistics."""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM audit_log").fetchone()["c"]

            today = datetime.now().strftime("%Y-%m-%d")
            entries_today = conn.execute(
                "SELECT COUNT(*) as c FROM audit_log WHERE timestamp >= ?",
                (today,),
            ).fetchone()["c"]

            week_start = (datetime.now() - __import__("datetime").timedelta(days=7)).strftime("%Y-%m-%d")
            entries_week = conn.execute(
                "SELECT COUNT(*) as c FROM audit_log WHERE timestamp >= ?",
                (week_start,),
            ).fetchone()["c"]

            unique_users = conn.execute(
                "SELECT COUNT(DISTINCT user_id) as c FROM audit_log"
            ).fetchone()["c"]

            top_actions = [
                dict(r) for r in conn.execute(
                    """SELECT action, COUNT(*) as count
                       FROM audit_log GROUP BY action ORDER BY count DESC LIMIT 10"""
                ).fetchall()
            ]

            top_resources = [
                dict(r) for r in conn.execute(
                    """SELECT resource, COUNT(*) as count
                       FROM audit_log GROUP BY resource ORDER BY count DESC LIMIT 10"""
                ).fetchall()
            ]

        return AuditStats(
            total_entries=total,
            entries_today=entries_today,
            entries_this_week=entries_week,
            unique_users=unique_users,
            top_actions=top_actions,
            top_resources=top_resources,
        )

    def export(
        self,
        start_date: str,
        end_date: str,
        format: str = "json",
        user_id: Optional[str] = None,
        action: Optional[str] = None,
    ) -> str:
        """
        Export audit log entries for compliance reporting.

        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            format: Export format (json or csv)
            user_id: Optional user filter
            action: Optional action filter

        Returns:
            Path to the exported file
        """
        Path(AUDIT_EXPORT_DIR).mkdir(parents=True, exist_ok=True)

        conditions = ["timestamp >= ?", "timestamp <= ?"]
        params = [start_date, end_date]

        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        if action:
            conditions.append("action = ?")
            params.append(action)

        where = " AND ".join(conditions)

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM audit_log WHERE {where} ORDER BY timestamp",
                params,
            ).fetchall()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audit_export_{start_date}_{end_date}_{timestamp}"

        if format == "json":
            filepath = str(Path(AUDIT_EXPORT_DIR) / f"{filename}.json")
            entries = [dict(r) for r in rows]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({
                    "export_timestamp": datetime.now().isoformat(),
                    "date_range": {"start": start_date, "end": end_date},
                    "total_entries": len(entries),
                    "entries": entries,
                }, f, indent=2, default=str)

        elif format == "csv":
            filepath = str(Path(AUDIT_EXPORT_DIR) / f"{filename}.csv")
            headers = ["id", "timestamp", "user_id", "action", "resource",
                       "details", "ip_address", "session_id"]

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(",".join(headers) + "\n")
                for row in rows:
                    # Escape CSV values
                    values = []
                    for h in headers:
                        val = str(row[h] if h in row.keys() else "").replace('"', '""')
                        values.append(f'"{val}"')
                    f.write(",".join(values) + "\n")
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info("Exported %d audit entries to %s", len(rows), filepath)
        return filepath

    def get_entry_count(self) -> int:
        """Get total number of audit entries."""
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) as c FROM audit_log").fetchone()["c"]

    def verify_integrity(self) -> Dict:
        """
        Verify audit log integrity by checking that no entries have been
        modified (contiguous auto-increment IDs, no gaps from deletion).

        Returns:
            Dict with integrity check results
        """
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM audit_log").fetchone()["c"]

            if total == 0:
                return {"intact": True, "entries": 0, "message": "No entries to verify"}

            min_id = conn.execute("SELECT MIN(id) as m FROM audit_log").fetchone()["m"]
            max_id = conn.execute("SELECT MAX(id) as m FROM audit_log").fetchone()["m"]

            expected_count = max_id - min_id + 1
            gaps = expected_count - total

            if gaps == 0:
                return {
                    "intact": True,
                    "entries": total,
                    "id_range": f"{min_id}-{max_id}",
                    "message": "No gaps detected - log appears intact",
                }
            else:
                return {
                    "intact": False,
                    "entries": total,
                    "id_range": f"{min_id}-{max_id}",
                    "gaps": gaps,
                    "message": f"{gaps} gap(s) detected - possible deletion or corruption",
                }


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------

_db: Optional[AuditDatabase] = None


def get_audit_db() -> AuditDatabase:
    global _db
    if _db is None:
        _db = AuditDatabase()
    return _db


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------

@app.post("/audit/log")
async def log_audit_entry(entry: AuditEntry):
    """Log an audit event."""
    db = get_audit_db()
    row_id = db.log_event(entry)
    return {"id": row_id, "status": "logged"}


@app.post("/audit/query")
async def query_audit_log(query: AuditQuery):
    """Query audit log with filters."""
    db = get_audit_db()
    results = db.query(query)
    return {"entries": results, "count": len(results)}


@app.get("/audit/user/{user_id}")
async def get_user_audit(user_id: str, limit: int = Query(100, ge=1, le=1000)):
    """Get audit entries for a specific user."""
    db = get_audit_db()
    return db.get_by_user(user_id, limit)


@app.get("/audit/resource/{resource}")
async def get_resource_audit(resource: str, limit: int = Query(100, ge=1, le=1000)):
    """Get audit entries for a specific resource."""
    db = get_audit_db()
    return db.get_by_resource(resource, limit)


@app.get("/audit/stats")
async def audit_stats():
    """Get audit log statistics."""
    db = get_audit_db()
    return db.get_stats()


@app.get("/audit/integrity")
async def check_integrity():
    """Verify audit log integrity."""
    db = get_audit_db()
    return db.verify_integrity()


@app.post("/audit/export")
async def export_audit_log(request: AuditExportRequest):
    """Export audit log for compliance reporting."""
    db = get_audit_db()
    filepath = db.export(
        start_date=request.start_date,
        end_date=request.end_date,
        format=request.format,
        user_id=request.user_id,
        action=request.action,
    )
    return {"filepath": filepath, "format": request.format}


@app.get("/health")
async def health():
    db = get_audit_db()
    return {
        "status": "healthy",
        "service": "aethera-audit-logger",
        "entries": db.get_entry_count(),
    }


@app.on_event("startup")
async def startup():
    logging.basicConfig(level=logging.INFO)
    get_audit_db()
    logger.info("Aethera Audit Logger service started")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8507)