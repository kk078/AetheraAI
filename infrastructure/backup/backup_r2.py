"""
Aethera AI - Backup to Cloudflare R2

S3-compatible object storage backup with incremental uploads,
compression, and retention policy management.
"""

import gzip
import hashlib
import json
import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import boto3
from botocore.config import Config as BotoConfig

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger("aethera.backup_r2")

R2_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "aethera-backups")
R2_ENDPOINT_URL = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else ""

BACKUP_SOURCES = os.getenv("BACKUP_SOURCES", "./data").split(",")
BACKUP_PREFIX = os.getenv("BACKUP_PREFIX", "aethera")
COMPRESSION_ENABLED = os.getenv("BACKUP_COMPRESSION", "true").lower() == "true"
RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
RETENTION_WEEKLY = int(os.getenv("BACKUP_RETENTION_WEEKLY", "12"))
RETENTION_MONTHLY = int(os.getenv("BACKUP_RETENTION_MONTHLY", "12"))

CHUNK_SIZE = 8 * 1024 * 1024  # 8MB multipart upload chunks

# ---------------------------------------------------------------------------
# R2 Client
# ---------------------------------------------------------------------------

class R2Client:
    """
    Cloudflare R2 (S3-compatible) client for backup operations.
    Uses boto3 with R2 endpoint configuration.
    """

    def __init__(
        self,
        account_id: str = R2_ACCOUNT_ID,
        access_key_id: str = R2_ACCESS_KEY_ID,
        secret_access_key: str = R2_SECRET_ACCESS_KEY,
        bucket: str = R2_BUCKET_NAME,
    ):
        if not all([account_id, access_key_id, secret_access_key]):
            raise ValueError(
                "R2 credentials required: CLOUDFLARE_ACCOUNT_ID, "
                "R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY"
            )

        self.endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
        self.bucket = bucket

        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=BotoConfig(
                region_name="auto",
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

        # Ensure bucket exists
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Create the bucket if it does not exist."""
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except self._client.exceptions.NoSuchBucket:
            try:
                self._client.create_bucket(Bucket=self.bucket)
                logger.info("Created R2 bucket: %s", self.bucket)
            except Exception as exc:
                logger.error("Failed to create bucket: %s", exc)
                raise
        except Exception as exc:
            logger.warning("Bucket check error: %s", exc)

    def upload_file(self, local_path: str, remote_key: str) -> Dict:
        """
        Upload a file to R2.

        Args:
            local_path: Path to local file
            remote_key: Object key in R2

        Returns:
            Dict with upload details
        """
        file_size = os.path.getsize(local_path)

        if file_size > 100 * 1024 * 1024:  # > 100MB, use multipart
            return self._multipart_upload(local_path, remote_key, file_size)

        with open(local_path, "rb") as f:
            self._client.put_object(
                Bucket=self.bucket,
                Key=remote_key,
                Body=f,
            )

        logger.info("Uploaded: %s -> %s (%d bytes)", local_path, remote_key, file_size)

        return {
            "key": remote_key,
            "size": file_size,
            "hash": self._file_hash(local_path),
        }

    def upload_bytes(self, data: bytes, remote_key: str, content_type: str = "application/octet-stream") -> Dict:
        """Upload raw bytes to R2."""
        self._client.put_object(
            Bucket=self.bucket,
            Key=remote_key,
            Body=data,
            ContentType=content_type,
        )

        logger.info("Uploaded bytes: %s (%d bytes)", remote_key, len(data))

        return {
            "key": remote_key,
            "size": len(data),
            "hash": hashlib.sha256(data).hexdigest()[:16],
        }

    def _multipart_upload(self, local_path: str, remote_key: str, file_size: int) -> Dict:
        """Upload large file using multipart upload."""
        mpu = self._client.create_multipart_upload(
            Bucket=self.bucket,
            Key=remote_key,
        )
        upload_id = mpu["UploadId"]

        parts = []
        part_number = 1

        try:
            with open(local_path, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break

                    response = self._client.upload_part(
                        Bucket=self.bucket,
                        Key=remote_key,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=chunk,
                    )

                    parts.append({
                        "PartNumber": part_number,
                        "ETag": response["ETag"],
                    })

                    part_number += 1

            self._client.complete_multipart_upload(
                Bucket=self.bucket,
                Key=remote_key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )

            logger.info("Multipart upload complete: %s (%d parts)", remote_key, len(parts))

            return {
                "key": remote_key,
                "size": file_size,
                "parts": len(parts),
                "hash": self._file_hash(local_path),
            }

        except Exception:
            self._client.abort_multipart_upload(
                Bucket=self.bucket,
                Key=remote_key,
                UploadId=upload_id,
            )
            raise

    def download_file(self, remote_key: str, local_path: str):
        """Download a file from R2."""
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        self._client.download_file(
            Bucket=self.bucket,
            Key=remote_key,
            Filename=local_path,
        )

        logger.info("Downloaded: %s -> %s", remote_key, local_path)

    def list_objects(self, prefix: str = "") -> List[Dict]:
        """List objects in the bucket with optional prefix."""
        objects = []
        paginator = self._client.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                objects.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                    "etag": obj.get("ETag", ""),
                })

        return objects

    def delete_object(self, remote_key: str):
        """Delete an object from R2."""
        self._client.delete_object(Bucket=self.bucket, Key=remote_key)
        logger.info("Deleted: %s", remote_key)

    def object_exists(self, remote_key: str) -> bool:
        """Check if an object exists in R2."""
        try:
            self._client.head_object(Bucket=self.bucket, Key=remote_key)
            return True
        except self._client.exceptions.NoSuchKey:
            return False
        except Exception:
            return False

    def _file_hash(self, path: str) -> str:
        """Compute SHA-256 hash of a file."""
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha.update(chunk)
        return sha.hexdigest()[:16]


# ---------------------------------------------------------------------------
# Incremental backup state
# ---------------------------------------------------------------------------

class BackupState:
    """
    Tracks backup state for incremental uploads.
    Stores file hashes to detect changes.
    """

    def __init__(self, state_dir: str = "./data/backup_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self.state_dir / "backup_state.db"
        self._init_db()

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_state (
                    path TEXT PRIMARY KEY,
                    hash TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    last_backed_up TEXT NOT NULL,
                    remote_key TEXT NOT NULL
                )
            """)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self._db_path))
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def get_state(self, path: str) -> Optional[Dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM file_state WHERE path = ?", (str(path),)
            ).fetchone()
            if row:
                return {"path": row[0], "hash": row[1], "size": row[2],
                        "last_backed_up": row[3], "remote_key": row[4]}
        return None

    def update_state(self, path: str, file_hash: str, size: int, remote_key: str):
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO file_state (path, hash, size, last_backed_up, remote_key)
                   VALUES (?, ?, ?, datetime('now'), ?)""",
                (str(path), file_hash, size, remote_key),
            )

    def get_all_states(self) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM file_state").fetchall()
            return [{"path": r[0], "hash": r[1], "size": r[2],
                     "last_backed_up": r[3], "remote_key": r[4]} for r in rows]


# ---------------------------------------------------------------------------
# R2 Backup Manager
# ---------------------------------------------------------------------------

class R2BackupManager:
    """
    Manages backup operations to Cloudflare R2.

    Features:
    - Incremental uploads (only changed files)
    - Compression (gzip)
    - Retention policy (daily/weekly/monthly)
    - Backup verification
    """

    def __init__(self):
        self._r2 = R2Client()
        self._state = BackupState()

    def backup_directory(self, source_dir: str, prefix: str = BACKUP_PREFIX) -> Dict:
        """
        Back up a directory to R2 with incremental change detection.

        Returns summary of backup operation.
        """
        source_path = Path(source_dir)
        if not source_path.exists():
            return {"error": f"Source directory not found: {source_dir}"}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        remote_prefix = f"{prefix}/{date_prefix}"

        uploaded = []
        skipped = []
        errors = []

        for file_path in source_path.rglob("*"):
            if not file_path.is_file():
                continue

            # Skip temp and lock files
            if file_path.suffix in (".tmp", ".lock", ".pid"):
                continue

            file_hash = self._hash_file(file_path)
            file_size = file_path.stat().st_size
            relative_path = file_path.relative_to(source_path)
            remote_key = f"{remote_prefix}/{relative_path}"

            if COMPRESSION_ENABLED and file_size > 1024:
                remote_key += ".gz"

            # Check if file changed since last backup
            prev_state = self._state.get_state(str(file_path))
            if prev_state and prev_state["hash"] == file_hash:
                skipped.append(str(relative_path))
                continue

            try:
                if COMPRESSION_ENABLED and file_size > 1024:
                    # Compress and upload
                    compressed_path = self._compress_file(file_path)
                    result = self._r2.upload_file(str(compressed_path), remote_key)
                    Path(compressed_path).unlink(missing_ok=True)
                else:
                    result = self._r2.upload_file(str(file_path), remote_key)

                # Update state
                self._state.update_state(str(file_path), file_hash, file_size, remote_key)

                uploaded.append({
                    "path": str(relative_path),
                    "size": file_size,
                    "remote_key": remote_key,
                })

            except Exception as exc:
                logger.error("Failed to back up %s: %s", file_path, exc)
                errors.append({"path": str(relative_path), "error": str(exc)})

        # Upload backup manifest
        manifest_key = f"{remote_prefix}/manifest.json"
        manifest = {
            "timestamp": timestamp,
            "source": source_dir,
            "prefix": prefix,
            "uploaded": len(uploaded),
            "skipped": len(skipped),
            "errors": len(errors),
            "items": uploaded,
            "compression": COMPRESSION_ENABLED,
        }

        self._r2.upload_bytes(
            json.dumps(manifest, indent=2).encode("utf-8"),
            manifest_key,
            content_type="application/json",
        )

        logger.info(
            "Backup complete: %d uploaded, %d skipped, %d errors",
            len(uploaded), len(skipped), len(errors),
        )

        return manifest

    def restore_from_r2(self, date_prefix: str, dest_dir: str, prefix: str = BACKUP_PREFIX) -> Dict:
        """
        Restore backup from R2 for a specific date.

        Args:
            date_prefix: Date path like "2025/01/15"
            dest_dir: Local directory to restore to
            prefix: Backup prefix in R2
        """
        remote_prefix = f"{prefix}/{date_prefix}"
        objects = self._r2.list_objects(prefix=remote_prefix)

        restored = []
        errors = []

        dest_path = Path(dest_dir)
        dest_path.mkdir(parents=True, exist_ok=True)

        for obj in objects:
            key = obj["key"]

            # Skip manifest
            if key.endswith("manifest.json"):
                continue

            # Calculate local path
            relative_key = key.replace(f"{remote_prefix}/", "")
            if relative_key.endswith(".gz"):
                local_path = dest_path / relative_key[:-3]  # Remove .gz
            else:
                local_path = dest_path / relative_key

            local_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                # Download
                temp_path = str(local_path) + (".gz" if key.endswith(".gz") else "")
                self._r2.download_file(key, temp_path)

                # Decompress if needed
                if key.endswith(".gz"):
                    self._decompress_file(temp_path, str(local_path))
                    Path(temp_path).unlink(missing_ok=True)

                restored.append(str(local_path))

            except Exception as exc:
                logger.error("Failed to restore %s: %s", key, exc)
                errors.append({"key": key, "error": str(exc)})

        logger.info("Restore complete: %d files restored, %d errors", len(restored), len(errors))

        return {"restored": len(restored), "errors": len(errors), "files": restored}

    def apply_retention_policy(self):
        """
        Apply backup retention policy.

        Keeps:
        - Daily backups for RETENTION_DAYS days
        - Weekly backups (Sundays) for RETENTION_WEEKLY weeks
        - Monthly backups (1st) for RETENTION_MONTHLY months
        """
        objects = self._r2.list_objects(prefix=BACKUP_PREFIX)

        daily_cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
        weekly_cutoff = datetime.now() - timedelta(weeks=RETENTION_WEEKLY)
        monthly_cutoff = datetime.now() - timedelta(days=RETENTION_MONTHLY * 30)

        deleted = 0

        for obj in objects:
            key = obj["key"]

            # Extract date from key pattern: prefix/YYYY/MM/DD/...
            parts = key.split("/")
            if len(parts) < 5:
                continue

            try:
                year, month, day = int(parts[1]), int(parts[2]), int(parts[3])
                obj_date = datetime(year, month, day)
            except (ValueError, IndexError):
                continue

            # Determine retention category
            is_monthly = day == 1
            is_weekly = datetime(year, month, day).weekday() == 6  # Sunday

            should_delete = False

            if is_monthly:
                if obj_date < monthly_cutoff:
                    should_delete = True
            elif is_weekly:
                if obj_date < weekly_cutoff:
                    should_delete = True
            else:
                if obj_date < daily_cutoff:
                    should_delete = True

            if should_delete:
                try:
                    self._r2.delete_object(key)
                    deleted += 1
                except Exception as exc:
                    logger.warning("Failed to delete %s: %s", key, exc)

        logger.info("Retention policy applied: deleted %d objects", deleted)
        return {"deleted": deleted}

    def list_backups(self) -> List[Dict]:
        """List available backups by date."""
        objects = self._r2.list_objects(prefix=BACKUP_PREFIX)

        # Find manifest files
        manifests = [obj for obj in objects if obj["key"].endswith("manifest.json")]

        backups = []
        for m in manifests:
            parts = m["key"].split("/")
            if len(parts) >= 5:
                date_str = f"{parts[1]}-{parts[2]}-{parts[3]}"
                backups.append({
                    "date": date_str,
                    "manifest_key": m["key"],
                    "last_modified": m["last_modified"],
                })

        return sorted(backups, key=lambda x: x["date"], reverse=True)

    def _hash_file(self, path: Path) -> str:
        """Compute SHA-256 hash of a file for change detection."""
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha.update(chunk)
        return sha.hexdigest()

    def _compress_file(self, path: Path) -> str:
        """Gzip compress a file. Returns path to compressed file."""
        compressed_path = str(path) + ".gz"

        with open(path, "rb") as f_in:
            with gzip.open(compressed_path, "wb", compresslevel=6) as f_out:
                while True:
                    chunk = f_in.read(65536)
                    if not chunk:
                        break
                    f_out.write(chunk)

        return compressed_path

    def _decompress_file(self, compressed_path: str, output_path: str):
        """Decompress a gzip file."""
        with gzip.open(compressed_path, "rb") as f_in:
            with open(output_path, "wb") as f_out:
                while True:
                    chunk = f_in.read(65536)
                    if not chunk:
                        break
                    f_out.write(chunk)


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------

def main():
    """CLI entry point for R2 backup operations."""
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Aethera AI R2 Backup")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Run backup to R2")
    backup_parser.add_argument("--source", default="./data", help="Source directory")
    backup_parser.add_argument("--prefix", default=BACKUP_PREFIX, help="R2 key prefix")

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from R2")
    restore_parser.add_argument("--date", required=True, help="Date to restore (YYYY/MM/DD)")
    restore_parser.add_argument("--dest", default="./data_restored", help="Destination directory")

    # List command
    subparsers.add_parser("list", help="List available backups")

    # Retention command
    subparsers.add_parser("retention", help="Apply retention policy")

    args = parser.parse_args()
    manager = R2BackupManager()

    if args.command == "backup":
        result = manager.backup_directory(args.source, args.prefix)
        print(json.dumps(result, indent=2))

    elif args.command == "restore":
        result = manager.restore_from_r2(args.date, args.dest)
        print(json.dumps(result, indent=2))

    elif args.command == "list":
        backups = manager.list_backups()
        for b in backups:
            print(f"  {b['date']}  (key: {b['manifest_key']})")

    elif args.command == "retention":
        result = manager.apply_retention_policy()
        print(f"Deleted {result['deleted']} expired backup objects")


if __name__ == "__main__":
    main()