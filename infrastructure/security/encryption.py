"""
Aethera AI - Encryption Utilities

SQLCipher + file encryption using the cryptography library.
Provides Fernet symmetric encryption, password hashing with passlib,
and file-level encryption for sensitive data at rest.
"""

import base64
import hashlib
import logging
import os
import secrets
from pathlib import Path
from typing import Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes, padding as sym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger("aethera.encryption")

# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------

def generate_key() -> bytes:
    """
    Generate a new Fernet-compatible symmetric encryption key.

    Returns:
        32-byte key (url-safe base64 encoded for Fernet compatibility)
    """
    return Fernet.generate_key()


def derive_key(password: str, salt: Optional[bytes] = None, iterations: int = 600_000) -> Tuple[bytes, bytes]:
    """
    Derive an encryption key from a password using PBKDF2-HMAC-SHA256.

    Args:
        password: User-provided password string
        salt: Optional salt bytes (generated if not provided)
        iterations: PBKDF2 iterations (600,000 per OWASP 2023 recommendations)

    Returns:
        Tuple of (key_bytes, salt_bytes)
    """
    if salt is None:
        salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )

    key = kdf.derive(password.encode("utf-8"))
    # Encode as url-safe base64 for Fernet compatibility
    fernet_key = base64.urlsafe_b64encode(key)

    return fernet_key, salt


def key_from_env(env_var: str = "ENCRYPTION_KEY") -> Optional[bytes]:
    """
    Load an encryption key from an environment variable.

    Returns:
        Key bytes or None if not set
    """
    key = os.getenv(env_var)
    if key:
        return key.encode("utf-8")
    return None


def get_or_create_key(key_path: str = "./data/.encryption_key") -> bytes:
    """
    Get an existing encryption key or create a new one.

    The key is stored in a file with restricted permissions.
    This is a convenience for single-server deployments.

    Args:
        key_path: Path to the key file

    Returns:
        Fernet-compatible key bytes
    """
    path = Path(key_path)

    if path.exists():
        with open(path, "rb") as f:
            key = f.read().strip()
        if len(key) >= 44:  # Fernet keys are 44 bytes base64
            return key

    # Generate new key
    key = generate_key()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(key)

    # Set restrictive permissions (owner only)
    try:
        os.chmod(str(path), 0o600)
    except (OSError, AttributeError):
        pass  # Windows may not support chmod

    logger.info("Generated new encryption key at %s", path)
    return key


# ---------------------------------------------------------------------------
# File encryption
# ---------------------------------------------------------------------------

def encrypt_file(
    input_path: str,
    output_path: Optional[str] = None,
    key: Optional[bytes] = None,
    delete_original: bool = False,
) -> str:
    """
    Encrypt a file using Fernet symmetric encryption.

    Args:
        input_path: Path to file to encrypt
        output_path: Output path (defaults to input_path + .enc)
        key: Encryption key (uses env key or generates one if not provided)
        delete_original: Delete the unencrypted original after encryption

    Returns:
        Path to the encrypted file
    """
    if key is None:
        key = key_from_env() or get_or_create_key()

    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_path is None:
        output_path = str(input_file) + ".enc"

    fernet = Fernet(key)

    with open(input_file, "rb") as f:
        plaintext = f.read()

    ciphertext = fernet.encrypt(plaintext)

    with open(output_path, "wb") as f:
        f.write(ciphertext)

    if delete_original and input_file != Path(output_path):
        input_file.unlink()
        logger.info("Deleted original file: %s", input_path)

    logger.info("Encrypted: %s -> %s (%d bytes)", input_path, output_path, len(ciphertext))
    return output_path


def decrypt_file(
    input_path: str,
    output_path: Optional[str] = None,
    key: Optional[bytes] = None,
    delete_encrypted: bool = False,
) -> str:
    """
    Decrypt a file that was encrypted with encrypt_file().

    Args:
        input_path: Path to encrypted file
        output_path: Output path (defaults to input_path without .enc)
        key: Decryption key (uses env key if not provided)
        delete_encrypted: Delete the encrypted file after decryption

    Returns:
        Path to the decrypted file

    Raises:
        InvalidToken: If the key is wrong or data is corrupted
    """
    if key is None:
        key = key_from_env()
        if key is None:
            raise ValueError("Decryption key required. Set ENCRYPTION_KEY env var.")

    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_path is None:
        if str(input_file).endswith(".enc"):
            output_path = str(input_file)[:-4]
        else:
            output_path = str(input_file) + ".dec"

    fernet = Fernet(key)

    with open(input_file, "rb") as f:
        ciphertext = f.read()

    try:
        plaintext = fernet.decrypt(ciphertext)
    except InvalidToken:
        raise ValueError("Decryption failed: invalid key or corrupted data")

    with open(output_path, "wb") as f:
        f.write(plaintext)

    if delete_encrypted and input_file != Path(output_path):
        input_file.unlink()
        logger.info("Deleted encrypted file: %s", input_path)

    logger.info("Decrypted: %s -> %s (%d bytes)", input_path, output_path, len(plaintext))
    return output_path


# ---------------------------------------------------------------------------
# Bytes encryption (for database fields, in-memory data)
# ---------------------------------------------------------------------------

def encrypt_bytes(data: bytes, key: Optional[bytes] = None) -> bytes:
    """
    Encrypt raw bytes using Fernet.

    Args:
        data: Plaintext bytes
        key: Encryption key (uses env key or generates one)

    Returns:
        Encrypted bytes (Fernet token)
    """
    if key is None:
        key = key_from_env() or get_or_create_key()

    fernet = Fernet(key)
    return fernet.encrypt(data)


def decrypt_bytes(data: bytes, key: Optional[bytes] = None) -> bytes:
    """
    Decrypt Fernet-encrypted bytes.

    Args:
        data: Encrypted bytes (Fernet token)
        key: Decryption key

    Returns:
        Decrypted plaintext bytes

    Raises:
        InvalidToken: If key is wrong or data corrupted
    """
    if key is None:
        key = key_from_env()
        if key is None:
            raise ValueError("Decryption key required")

    fernet = Fernet(key)
    return fernet.decrypt(data)


def encrypt_string(text: str, key: Optional[bytes] = None) -> str:
    """
    Encrypt a string and return base64-encoded ciphertext.

    Args:
        text: Plaintext string
        key: Encryption key

    Returns:
        Base64-encoded encrypted string
    """
    encrypted = encrypt_bytes(text.encode("utf-8"), key)
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def decrypt_string(encrypted_text: str, key: Optional[bytes] = None) -> str:
    """
    Decrypt a base64-encoded encrypted string.

    Args:
        encrypted_text: Base64-encoded Fernet token
        key: Decryption key

    Returns:
        Decrypted plaintext string
    """
    encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode("ascii"))
    decrypted = decrypt_bytes(encrypted_bytes, key)
    return decrypted.decode("utf-8")


# ---------------------------------------------------------------------------
# AES-256-CBC encryption (alternative for large files / streaming)
# ---------------------------------------------------------------------------

def encrypt_file_aes(
    input_path: str,
    output_path: Optional[str] = None,
    key: Optional[bytes] = None,
    delete_original: bool = False,
) -> str:
    """
    Encrypt a file using AES-256-CBC with PKCS7 padding.
    Suitable for larger files where Fernet's overhead is undesirable.

    The output format is: [16-byte IV][ciphertext]

    Args:
        input_path: Path to file
        output_path: Output path
        key: 32-byte AES key (derived from env if not provided)
        delete_original: Delete original after encryption

    Returns:
        Path to encrypted file
    """
    if key is None:
        env_key = key_from_env()
        if env_key:
            # Derive 32-byte key from Fernet key
            key = hashlib.sha256(env_key).digest()
        else:
            key = os.urandom(32)

    if len(key) != 32:
        key = hashlib.sha256(key).digest()

    input_file = Path(input_path)
    if output_path is None:
        output_path = str(input_file) + ".aes"

    iv = os.urandom(16)

    # Read and pad
    with open(input_file, "rb") as f:
        plaintext = f.read()

    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()

    # Encrypt
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    # Write: IV + ciphertext
    with open(output_path, "wb") as f:
        f.write(iv)
        f.write(ciphertext)

    if delete_original and input_file != Path(output_path):
        input_file.unlink()

    logger.info("AES encrypted: %s -> %s", input_path, output_path)
    return output_path


def decrypt_file_aes(
    input_path: str,
    output_path: Optional[str] = None,
    key: Optional[bytes] = None,
    delete_encrypted: bool = False,
) -> str:
    """
    Decrypt a file encrypted with encrypt_file_aes().

    Args:
        input_path: Path to .aes encrypted file
        output_path: Output path
        key: 32-byte AES key
        delete_encrypted: Delete encrypted file after decryption

    Returns:
        Path to decrypted file
    """
    if key is None:
        env_key = key_from_env()
        if env_key:
            key = hashlib.sha256(env_key).digest()
        else:
            raise ValueError("AES decryption key required")

    if len(key) != 32:
        key = hashlib.sha256(key).digest()

    input_file = Path(input_path)
    if output_path is None:
        if str(input_file).endswith(".aes"):
            output_path = str(input_file)[:-4]
        else:
            output_path = str(input_file) + ".dec"

    with open(input_file, "rb") as f:
        iv = f.read(16)
        ciphertext = f.read()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()

    # Unpad
    unpadder = sym_padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded) + unpadder.finalize()

    with open(output_path, "wb") as f:
        f.write(plaintext)

    if delete_encrypted and input_file != Path(output_path):
        input_file.unlink()

    logger.info("AES decrypted: %s -> %s", input_path, output_path)
    return output_path


# ---------------------------------------------------------------------------
# Password hashing (for user authentication)
# ---------------------------------------------------------------------------

def hash_password(password: str, rounds: int = 12) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password
        rounds: Bcrypt work factor (12 = ~250ms, 14 = ~1s)

    Returns:
        Bcrypt hash string (includes salt and parameters)
    """
    try:
        from passlib.hash import bcrypt as passlib_bcrypt
        return passlib_bcrypt.using(rounds=rounds).hash(password)
    except ImportError:
        pass

    # Fallback using cryptography library's bcrypt
    try:
        import bcrypt
        salt = bcrypt.gensalt(rounds=rounds)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    except ImportError:
        pass

    # Last resort: PBKDF2-based hash
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    derived = kdf.derive(password.encode("utf-8"))
    hash_str = base64.b64encode(derived).decode("ascii")
    salt_str = base64.b64encode(salt).decode("ascii")
    return f"$pbkdf2${salt_str}${hash_str}"


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password to verify
        password_hash: Previously stored hash

    Returns:
        True if password matches
    """
    try:
        from passlib.hash import bcrypt as passlib_bcrypt
        return passlib_bcrypt.verify(password, password_hash)
    except ImportError:
        pass

    try:
        import bcrypt
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ImportError:
        pass

    # PBKDF2 fallback
    if password_hash.startswith("$pbkdf2$"):
        parts = password_hash.split("$")
        if len(parts) >= 4:
            salt = base64.b64decode(parts[2])
            stored_hash = base64.b64decode(parts[3])

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100_000,
            )
            derived = kdf.derive(password.encode("utf-8"))
            return secrets.compare_digest(derived, stored_hash)

    return False


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def secure_delete(file_path: str, passes: int = 3):
    """
    Securely delete a file by overwriting it before deletion.

    Args:
        file_path: Path to file
        passes: Number of overwrite passes
    """
    path = Path(file_path)
    if not path.exists():
        return

    size = path.stat().st_size

    with open(path, "r+b") as f:
        for _ in range(passes):
            f.seek(0)
            f.write(os.urandom(size))
            f.flush()
            os.fsync(f.fileno())

    path.unlink()
    logger.info("Securely deleted: %s (%d bytes, %d passes)", file_path, size, passes)


def generate_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))