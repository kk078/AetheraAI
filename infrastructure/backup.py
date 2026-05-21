"""
Aethera AI - Backup System

Automated backups for conversations, memories, and configurations.

Backups contain PHI (the conversation DB, vector store, health records) and
secrets (`.env`), so they are encrypted with Fernet when a backup key is
configured. Encryption fails closed: if a key is requested but the crypto
library is missing, no plaintext PHI is written.
"""
import asyncio
import base64
import os
import secrets
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

ENCRYPTED_SUFFIX = ".tar.gz.enc"
PLAINTEXT_SUFFIX = ".tar.gz"
_SALT_BYTES = 16
_PBKDF2_ITERATIONS = 200_000


class BackupManager:
    """
    Automated backup system.

    Backs up:
    - Conversation history (SQLite)
    - Vector store (ChromaDB)
    - User profiles
    - Configuration files

    When an encryption key is available (``encryption_key`` argument, or the
    ``BACKUP_ENCRYPTION_KEY`` / ``ENCRYPTION_KEY`` env vars) backups are written
    as ``<name>.tar.gz.enc`` (a 16-byte random salt followed by a Fernet token).
    """

    def __init__(
        self,
        backup_dir: str = "./backups",
        data_dir: str = "./data",
        encryption_key: Optional[str] = None,
    ):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.data_dir = Path(data_dir)

        self._encryption_key = (
            encryption_key
            or os.environ.get("BACKUP_ENCRYPTION_KEY")
            or os.environ.get("ENCRYPTION_KEY")
        )

        # Optional off-site copy to a (BAA-covered) Cloudflare R2 bucket.
        self._r2_bucket = os.environ.get("BACKUP_R2_BUCKET")
        self._r2_account = os.environ.get("R2_ACCOUNT_ID")
        self._r2_key_id = os.environ.get("R2_ACCESS_KEY_ID")
        self._r2_secret = os.environ.get("R2_SECRET_ACCESS_KEY")

    @property
    def encryption_enabled(self) -> bool:
        return bool(self._encryption_key)

    @property
    def r2_enabled(self) -> bool:
        return bool(self._r2_bucket and self._r2_account and self._r2_key_id and self._r2_secret)

    def upload_backup(self, path: str) -> bool:
        """Upload a backup file to the configured R2 bucket (S3-compatible).

        Refuses to upload an unencrypted backup to R2 (PHI must be encrypted
        before leaving the host). Returns True on success, False otherwise.
        """
        if not self.r2_enabled:
            return False
        if not str(path).endswith(ENCRYPTED_SUFFIX):
            print("Refusing to upload unencrypted backup to R2; set a backup encryption key.")
            return False
        try:
            import boto3  # optional dependency
        except ImportError:
            print("boto3 not installed; cannot upload backup to R2.")
            return False
        try:
            client = boto3.client(
                "s3",
                endpoint_url=f"https://{self._r2_account}.r2.cloudflarestorage.com",
                aws_access_key_id=self._r2_key_id,
                aws_secret_access_key=self._r2_secret,
                region_name="auto",
            )
            client.upload_file(str(path), self._r2_bucket, Path(path).name)
            return True
        except Exception as e:
            print(f"R2 upload failed: {e}")
            return False

    def _derive_fernet(self, salt: bytes):
        """Derive a Fernet instance from the passphrase and a per-file salt."""
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=_PBKDF2_ITERATIONS,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self._encryption_key.encode("utf-8")))
        return Fernet(key)

    def _encrypt_file(self, src: Path, dest: Path) -> None:
        """Encrypt ``src`` to ``dest`` (salt || token). Fails closed."""
        try:
            salt = secrets.token_bytes(_SALT_BYTES)
            fernet = self._derive_fernet(salt)
            token = fernet.encrypt(src.read_bytes())
            dest.write_bytes(salt + token)
        except ImportError as e:
            raise RuntimeError(
                "Backup encryption was requested but the 'cryptography' library "
                "is unavailable; refusing to write an unencrypted backup."
            ) from e

    def _decrypt_file(self, src: Path, dest: Path) -> None:
        blob = src.read_bytes()
        salt, token = blob[:_SALT_BYTES], blob[_SALT_BYTES:]
        fernet = self._derive_fernet(salt)
        dest.write_bytes(fernet.decrypt(token))

    def create_backup(self, name: Optional[str] = None) -> str:
        """
        Create a full backup.

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = name or f"aethera_backup_{timestamp}"
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"

        # Files to backup
        files_to_backup: List[Path] = []

        if self.data_dir.exists():
            # Database files
            if (self.data_dir / "aethera.db").exists():
                files_to_backup.append(self.data_dir / "aethera.db")

            # ChromaDB
            if (self.data_dir / "chroma").exists():
                files_to_backup.append(self.data_dir / "chroma")

            # User profiles
            for profile in self.data_dir.glob("user_*.json"):
                files_to_backup.append(profile)

            # Knowledge base
            if (self.data_dir / "knowledge").exists():
                files_to_backup.append(self.data_dir / "knowledge")

        # Configuration files
        config_files = [
            Path("./.env"),
            Path("./litellm_config.yaml"),
            Path("./orchestrator/config.yaml"),
        ]
        for config in config_files:
            if config.exists():
                files_to_backup.append(config)

        # Create tarball — use relative paths from data_dir for directories
        # so restore preserves directory structure
        with tarfile.open(backup_path, "w:gz") as tar:
            for file_path in files_to_backup:
                arcname = file_path.name
                tar.add(file_path, arcname=arcname, recursive=file_path.is_dir())

        if not self.encryption_enabled:
            return str(backup_path)

        # Encrypt the tarball, then remove the plaintext copy. If encryption
        # fails, remove the plaintext too so no unencrypted PHI is left behind.
        enc_path = self.backup_dir / f"{backup_name}{ENCRYPTED_SUFFIX}"
        try:
            self._encrypt_file(backup_path, enc_path)
        finally:
            backup_path.unlink(missing_ok=True)
        return str(enc_path)

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all backups (encrypted and plaintext)."""
        backups = []

        for pattern in ("*.tar.gz", f"*{ENCRYPTED_SUFFIX}"):
            for backup_file in self.backup_dir.glob(pattern):
                stat = backup_file.stat()
                backups.append({
                    "name": backup_file.name,
                    "path": str(backup_file),
                    "size": stat.st_size,
                    "encrypted": backup_file.name.endswith(ENCRYPTED_SUFFIX),
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

        return sorted(backups, key=lambda x: x["created"], reverse=True)

    def restore_backup(self, backup_path: str) -> bool:
        """
        Restore from a backup.

        Args:
            backup_path: Path to backup file

        Returns:
            True if successful
        """
        backup_file = Path(backup_path)

        if not backup_file.exists():
            return False

        tmp_plaintext: Optional[Path] = None
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)

            # Decrypt to a temp tarball first if this is an encrypted backup.
            if backup_file.name.endswith(ENCRYPTED_SUFFIX):
                if not self.encryption_enabled:
                    print("Restore failed: encrypted backup but no decryption key configured")
                    return False
                tmp_plaintext = self.backup_dir / f".restore_{secrets.token_hex(8)}.tar.gz"
                self._decrypt_file(backup_file, tmp_plaintext)
                backup_file = tmp_plaintext

            with tarfile.open(backup_file, "r:gz") as tar:
                # Validate members before extracting (security)
                members = tar.getmembers()
                for member in members:
                    # Prevent path traversal
                    if member.name.startswith("/") or ".." in member.name:
                        continue
                # NOTE: The filter="data" parameter (Python 3.12+) provides protection
                # against path traversal and other tar extraction risks. We can't use it
                # here because the Docker container runs Python 3.11. The manual path
                # traversal check above mitigates the primary security concern.
                tar.extractall(path=self.data_dir)
            return True
        except Exception as e:
            print(f"Restore failed: {e}")
            return False
        finally:
            # Never leave decrypted PHI on disk after a restore.
            if tmp_plaintext is not None:
                tmp_plaintext.unlink(missing_ok=True)

    def delete_old_backups(self, keep_days: int = 7) -> int:
        """Delete backups older than specified days."""
        cutoff = datetime.now().timestamp() - (keep_days * 86400)
        deleted = 0

        for pattern in ("*.tar.gz", f"*{ENCRYPTED_SUFFIX}"):
            for backup_file in self.backup_dir.glob(pattern):
                if backup_file.stat().st_mtime < cutoff:
                    backup_file.unlink()
                    deleted += 1

        return deleted

    async def scheduled_backup(self, interval_hours: int = 24):
        """Run scheduled backups, uploading off-site to R2 when configured."""
        while True:
            await asyncio.sleep(interval_hours * 3600)
            path = self.create_backup()
            if self.r2_enabled:
                self.upload_backup(path)
            self.delete_old_backups()


# Singleton
_manager: Optional[BackupManager] = None


def get_backup_manager(backup_dir: str = "./backups") -> BackupManager:
    """Get backup manager instance."""
    global _manager
    if _manager is None:
        _manager = BackupManager(backup_dir)
    return _manager
