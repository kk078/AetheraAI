"""
Aethera AI — Dataset Store

SQLite-backed persistence for datasets, versions, annotations,
and quality scores.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("aethera.data_intelligence.store")


class DatasetStore:
    """
    SQLite-backed store for data intelligence metadata.

    Tables:
    - di_datasets: registered datasets
    - di_versions: dataset version snapshots
    - di_annotations: data labels (category, sentiment, entity, relationship)
    - di_quality_scores: quality metrics per dataset version
    """

    def __init__(self, db_path: str = "/data/aethera.db"):
        self.db_path = db_path
        self._conn: Optional[object] = None

    def initialize(self):
        """Create tables and indexes."""
        import sqlite3
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS di_datasets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                source_type TEXT NOT NULL,
                source_path TEXT,
                format TEXT,
                row_count INTEGER DEFAULT 0,
                column_count INTEGER DEFAULT 0,
                schema_json JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS di_versions (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL REFERENCES di_datasets(id) ON DELETE CASCADE,
                version_number INTEGER NOT NULL,
                checksum TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                column_count INTEGER NOT NULL,
                storage_path TEXT,
                change_summary JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(dataset_id, version_number)
            );

            CREATE TABLE IF NOT EXISTS di_annotations (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL REFERENCES di_datasets(id) ON DELETE CASCADE,
                version_id TEXT REFERENCES di_versions(id) ON DELETE SET NULL,
                row_index INTEGER,
                column_name TEXT,
                annotation_type TEXT NOT NULL,
                annotation_value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source TEXT DEFAULT 'manual',
                metadata_json JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS di_quality_scores (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL REFERENCES di_datasets(id) ON DELETE CASCADE,
                version_id TEXT REFERENCES di_versions(id) ON DELETE SET NULL,
                completeness REAL NOT NULL,
                accuracy REAL NOT NULL,
                consistency REAL NOT NULL,
                timeliness REAL NOT NULL,
                overall REAL NOT NULL,
                details JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_di_datasets_name ON di_datasets(name);
            CREATE INDEX IF NOT EXISTS idx_di_versions_dataset ON di_versions(dataset_id);
            CREATE INDEX IF NOT EXISTS idx_di_annotations_dataset ON di_annotations(dataset_id);
            CREATE INDEX IF NOT EXISTS idx_di_annotations_type ON di_annotations(annotation_type);
            CREATE INDEX IF NOT EXISTS idx_di_quality_dataset ON di_quality_scores(dataset_id);
        """)

        self._conn.commit()
        logger.info("Dataset store initialized")

    def _get_conn(self):
        if self._conn is None:
            self.initialize()
        return self._conn

    # ---- Dataset CRUD ----

    def create_dataset(
        self,
        name: str,
        source_type: str,
        source_path: str = "",
        description: str = "",
        format: str = "csv",
        row_count: int = 0,
        column_count: int = 0,
        schema_json: Optional[Dict] = None,
    ) -> Dict:
        """Register a new dataset and return its metadata."""
        ds_id = f"ds_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        conn = self._get_conn()
        conn.execute(
            """INSERT INTO di_datasets
               (id, name, description, source_type, source_path, format,
                row_count, column_count, schema_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ds_id, name, description, source_type, source_path, format,
             row_count, column_count,
             json.dumps(schema_json) if schema_json else None,
             now, now),
        )
        conn.commit()

        return dict(conn.execute(
            "SELECT * FROM di_datasets WHERE id = ?", (ds_id,)
        ).fetchone())

    def get_dataset(self, dataset_id: str) -> Optional[Dict]:
        """Get dataset metadata by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM di_datasets WHERE id = ?", (dataset_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_datasets(
        self,
        source_type: Optional[str] = None,
        format: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """List datasets with optional filtering."""
        conn = self._get_conn()
        query = "SELECT * FROM di_datasets WHERE 1=1"
        params = []

        if source_type:
            query += " AND source_type = ?"
            params.append(source_type)
        if format:
            query += " AND format = ?"
            params.append(format)

        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def update_dataset(self, dataset_id: str, **kwargs) -> Optional[Dict]:
        """Update dataset metadata fields."""
        conn = self._get_conn()

        # Build SET clause from kwargs
        allowed = {"name", "description", "row_count", "column_count",
                    "schema_json", "source_path", "format"}
        updates = {}
        for key, value in kwargs.items():
            if key in allowed:
                if key == "schema_json" and isinstance(value, dict):
                    value = json.dumps(value)
                updates[key] = value

        if not updates:
            return self.get_dataset(dataset_id)

        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [dataset_id]

        conn.execute(
            f"UPDATE di_datasets SET {set_clause} WHERE id = ?", values
        )
        conn.commit()
        return self.get_dataset(dataset_id)

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset and all associated data."""
        conn = self._get_conn()
        conn.execute("DELETE FROM di_quality_scores WHERE dataset_id = ?", (dataset_id,))
        conn.execute("DELETE FROM di_annotations WHERE dataset_id = ?", (dataset_id,))
        conn.execute("DELETE FROM di_versions WHERE dataset_id = ?", (dataset_id,))
        conn.execute("DELETE FROM di_datasets WHERE id = ?", (dataset_id,))
        conn.commit()
        return conn.total_changes > 0

    def get_stats(self) -> Dict:
        """Get aggregate stats across all datasets."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) as cnt FROM di_datasets").fetchone()["cnt"]
        by_format = dict(conn.execute(
            "SELECT format, COUNT(*) as cnt FROM di_datasets GROUP BY format"
        ).fetchall())
        total_rows = conn.execute(
            "SELECT COALESCE(SUM(row_count), 0) as cnt FROM di_datasets"
        ).fetchone()["cnt"]
        total_versions = conn.execute("SELECT COUNT(*) as cnt FROM di_versions").fetchone()["cnt"]
        total_annotations = conn.execute("SELECT COUNT(*) as cnt FROM di_annotations").fetchone()["cnt"]

        return {
            "total_datasets": total,
            "by_format": by_format,
            "total_rows": total_rows,
            "total_versions": total_versions,
            "total_annotations": total_annotations,
        }

    # ---- Version management ----

    def create_version(
        self,
        dataset_id: str,
        checksum: str,
        row_count: int,
        column_count: int,
        storage_path: str = "",
        change_summary: Optional[Dict] = None,
    ) -> Dict:
        """Create a new version snapshot for a dataset."""
        conn = self._get_conn()

        # Get next version number
        max_ver = conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) as v FROM di_versions WHERE dataset_id = ?",
            (dataset_id,),
        ).fetchone()["v"]
        version_number = max_ver + 1

        ver_id = f"ver_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        conn.execute(
            """INSERT INTO di_versions
               (id, dataset_id, version_number, checksum, row_count, column_count,
                storage_path, change_summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ver_id, dataset_id, version_number, checksum, row_count, column_count,
             storage_path, json.dumps(change_summary) if change_summary else None, now),
        )
        conn.commit()

        return dict(conn.execute(
            "SELECT * FROM di_versions WHERE id = ?", (ver_id,)
        ).fetchone())

    def get_version(self, version_id: str) -> Optional[Dict]:
        """Get a version by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM di_versions WHERE id = ?", (version_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_versions(self, dataset_id: str, limit: int = 20) -> List[Dict]:
        """List versions for a dataset, newest first."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM di_versions WHERE dataset_id = ? ORDER BY version_number DESC LIMIT ?",
            (dataset_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_latest_version(self, dataset_id: str) -> Optional[Dict]:
        """Get the most recent version for a dataset."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM di_versions WHERE dataset_id = ? ORDER BY version_number DESC LIMIT 1",
            (dataset_id,),
        ).fetchone()
        return dict(row) if row else None

    # ---- Annotations ----

    def add_annotation(
        self,
        dataset_id: str,
        annotation_type: str,
        annotation_value: str,
        row_index: Optional[int] = None,
        column_name: Optional[str] = None,
        version_id: Optional[str] = None,
        confidence: float = 1.0,
        source: str = "llm",
        metadata_json: Optional[Dict] = None,
    ) -> Dict:
        """Add an annotation to a dataset."""
        ann_id = f"ann_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        conn = self._get_conn()
        conn.execute(
            """INSERT INTO di_annotations
               (id, dataset_id, version_id, row_index, column_name,
                annotation_type, annotation_value, confidence, source, metadata_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ann_id, dataset_id, version_id, row_index, column_name,
             annotation_type, annotation_value, confidence, source,
             json.dumps(metadata_json) if metadata_json else None, now),
        )
        conn.commit()

        return dict(conn.execute(
            "SELECT * FROM di_annotations WHERE id = ?", (ann_id,)
        ).fetchone())

    def add_annotations_batch(self, annotations: List[Dict]) -> List[str]:
        """Add multiple annotations in a single transaction."""
        conn = self._get_conn()
        ids = []

        for ann in annotations:
            ann_id = f"ann_{uuid.uuid4().hex[:12]}"
            ids.append(ann_id)
            conn.execute(
                """INSERT INTO di_annotations
                   (id, dataset_id, version_id, row_index, column_name,
                    annotation_type, annotation_value, confidence, source, metadata_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ann_id, ann["dataset_id"], ann.get("version_id"),
                 ann.get("row_index"), ann.get("column_name"),
                 ann["annotation_type"], ann["annotation_value"],
                 ann.get("confidence", 1.0), ann.get("source", "llm"),
                 json.dumps(ann["metadata_json"]) if ann.get("metadata_json") else None,
                 datetime.now().isoformat()),
            )

        conn.commit()
        return ids

    def get_annotations(
        self,
        dataset_id: str,
        annotation_type: Optional[str] = None,
        version_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Get annotations for a dataset with optional filtering."""
        conn = self._get_conn()
        query = "SELECT * FROM di_annotations WHERE dataset_id = ?"
        params = [dataset_id]

        if annotation_type:
            query += " AND annotation_type = ?"
            params.append(annotation_type)
        if version_id:
            query += " AND version_id = ?"
            params.append(version_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    # ---- Quality scores ----

    def store_quality_score(
        self,
        dataset_id: str,
        completeness: float,
        accuracy: float,
        consistency: float,
        timeliness: float,
        overall: float,
        version_id: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> Dict:
        """Store quality scores for a dataset version."""
        qs_id = f"qs_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        conn = self._get_conn()
        conn.execute(
            """INSERT INTO di_quality_scores
               (id, dataset_id, version_id, completeness, accuracy, consistency,
                timeliness, overall, details, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (qs_id, dataset_id, version_id, completeness, accuracy, consistency,
             timeliness, overall, json.dumps(details) if details else None, now),
        )
        conn.commit()

        return dict(conn.execute(
            "SELECT * FROM di_quality_scores WHERE id = ?", (qs_id,)
        ).fetchone())

    def get_quality_score(self, dataset_id: str, version_id: Optional[str] = None) -> Optional[Dict]:
        """Get the latest quality score for a dataset."""
        conn = self._get_conn()
        query = "SELECT * FROM di_quality_scores WHERE dataset_id = ?"
        params = [dataset_id]

        if version_id:
            query += " AND version_id = ?"
            params.append(version_id)

        query += " ORDER BY created_at DESC LIMIT 1"
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None

    def list_quality_history(self, dataset_id: str, limit: int = 10) -> List[Dict]:
        """List quality score history for a dataset."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM di_quality_scores WHERE dataset_id = ? ORDER BY created_at DESC LIMIT ?",
            (dataset_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# Singleton
_store: Optional[DatasetStore] = None


def get_dataset_store(db_path: str = "/data/aethera.db") -> DatasetStore:
    """Get the global dataset store instance."""
    global _store
    if _store is None:
        _store = DatasetStore(db_path)
        _store.initialize()
    return _store