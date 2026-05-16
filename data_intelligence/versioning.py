"""
Aethera AI — Stage 6: Data Versioning

Track changes to datasets over time with SHA-256 checksums,
version snapshots, and change summaries.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from .context import DataPipelineContext
from .stages import DataPipelineStage

logger = logging.getLogger("aethera.data_intelligence.versioning")

# Base directory for dataset snapshots
SNAPSHOT_DIR = "/data/datasets"


class DataVersioningStage(DataPipelineStage):
    """Create version snapshots with checksums and change summaries."""

    name = "versioning"

    async def execute(self, context: DataPipelineContext) -> DataPipelineContext:
        rows = context.cleaned_rows or context.rows
        if not rows:
            logger.warning("Versioning: no rows to version")
            return context

        # Compute checksum
        content = json.dumps(rows, sort_keys=True, default=str)
        checksum = hashlib.sha256(content.encode()).hexdigest()

        # Get dataset store
        store = self._get_store()
        if not store or not context.dataset_id:
            context.checksum = checksum
            return context

        # Check if this version already exists (same checksum)
        latest_version = store.get_latest_version(context.dataset_id)
        if latest_version and latest_version["checksum"] == checksum:
            # No changes since last version
            context.version_id = latest_version["id"]
            context.version_number = latest_version["version_number"]
            context.checksum = checksum
            logger.info(f"Versioning: no changes since v{context.version_number}")
            return context

        # Compute change summary
        change_summary = None
        if latest_version:
            change_summary = self._compute_change_summary(
                latest_version, rows, context
            )

        # Save snapshot to disk
        storage_path = self._save_snapshot(context, content)

        # Create version record
        version = store.create_version(
            dataset_id=context.dataset_id,
            checksum=checksum,
            row_count=len(rows),
            column_count=len(context.headers) if context.headers else 0,
            storage_path=storage_path,
            change_summary=change_summary,
        )

        context.version_id = version["id"]
        context.version_number = version["version_number"]
        context.checksum = checksum

        # Update dataset row/column count
        store.update_dataset(
            context.dataset_id,
            row_count=len(rows),
            column_count=len(context.headers) if context.headers else 0,
        )

        logger.info(f"Versioning: created v{context.version_number} (checksum={checksum[:8]}...)")
        return context

    def _compute_change_summary(
        self,
        previous_version: Dict,
        current_rows: List[Dict],
        context: DataPipelineContext,
    ) -> Dict[str, int]:
        """Compare current rows with previous version to compute changes."""
        summary = {"added": 0, "removed": 0, "modified": 0}

        # Load previous version snapshot for comparison
        prev_path = previous_version.get("storage_path", "")
        if prev_path and os.path.exists(prev_path):
            try:
                with open(prev_path, "r", encoding="utf-8") as f:
                    prev_rows = json.load(f)

                # Hash each row for comparison
                prev_hashes = {}
                for row in prev_rows:
                    h = hashlib.md5(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()
                    prev_hashes[h] = prev_hashes.get(h, 0) + 1

                curr_hashes = {}
                for row in current_rows:
                    h = hashlib.md5(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()
                    curr_hashes[h] = curr_hashes.get(h, 0) + 1

                # Compute differences
                all_keys = set(prev_hashes.keys()) | set(curr_hashes.keys())
                for key in all_keys:
                    prev_count = prev_hashes.get(key, 0)
                    curr_count = curr_hashes.get(key, 0)
                    if prev_count == 0:
                        summary["added"] += curr_count
                    elif curr_count == 0:
                        summary["removed"] += prev_count
                    elif prev_count != curr_count:
                        diff = abs(curr_count - prev_count)
                        if curr_count > prev_count:
                            summary["added"] += diff
                        else:
                            summary["removed"] += diff
            except Exception as e:
                logger.warning(f"Failed to compute change summary: {e}")
                summary["error"] = str(e)
        else:
            # First version or missing snapshot
            summary["added"] = len(current_rows)

        return summary

    def _save_snapshot(self, context: DataPipelineContext, content: str) -> str:
        """Save a snapshot of the dataset to disk."""
        dataset_dir = os.path.join(SNAPSHOT_DIR, context.dataset_id)
        os.makedirs(dataset_dir, exist_ok=True)

        # Determine format
        fmt = context.format or "json"
        version_num = self._get_next_version_number(context)

        if fmt == "json":
            path = os.path.join(dataset_dir, f"v{version_num}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(context.cleaned_rows or context.rows, f, indent=2, default=str)
        elif fmt == "csv":
            import csv
            path = os.path.join(dataset_dir, f"v{version_num}.csv")
            rows = context.cleaned_rows or context.rows
            if rows:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=context.headers or list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)
        else:
            # Default to JSON
            path = os.path.join(dataset_dir, f"v{version_num}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(context.cleaned_rows or context.rows, f, indent=2, default=str)

        return path

    def _get_next_version_number(self, context: DataPipelineContext) -> int:
        """Get the next version number for a dataset."""
        store = self._get_store()
        if store and context.dataset_id:
            latest = store.get_latest_version(context.dataset_id)
            if latest:
                return latest["version_number"] + 1
        return 1

    def _get_store(self):
        """Lazy-load the dataset store."""
        try:
            from .store import get_dataset_store
            return get_dataset_store()
        except Exception:
            return None