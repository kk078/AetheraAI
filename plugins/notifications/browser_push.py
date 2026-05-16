"""
Browser Push Notifier for Aethera

Provides web push notification operations via the Web Push protocol
(RFC 8291, RFC 8292). Works with VAPID keys for authentication
and supports PWA push subscriptions.
"""
import base64
import hashlib
import json
import os
import struct
import time
import uuid
from typing import Any, Dict, List, Optional

import aiohttp


class BrowserPushNotifier:
    """Send web push notifications via the Web Push protocol."""

    def __init__(
        self,
        vapid_private_key: str = "",
        vapid_public_key: str = "",
        vapid_subject: str = "mailto:admin@aethera.ai",
        ttl: int = 86400,
    ):
        """
        Args:
            vapid_private_key: VAPID EC private key (base64url-encoded).
            vapid_public_key:  VAPID EC public key (base64url-encoded).
            vapid_subject:     VAPID subject (mailto: or https: URL).
            ttl:               Default time-to-live for push messages in seconds.
        """
        self.vapid_private_key = vapid_private_key
        self.vapid_public_key = vapid_public_key
        self.vapid_subject = vapid_subject
        self.ttl = ttl
        self._session: Optional[aiohttp.ClientSession] = None

    # -- Session lifecycle --------------------------------------------------

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # -- VAPID JWT Generation -----------------------------------------------

    def _generate_vapid_jwt(self, origin: str) -> str:
        """Generate a VAPID JWT for push service authentication.

        Uses ECDSA with the P-256 curve for signing.

        Args:
            origin: The origin of the push service URL.

        Returns:
            Signed JWT string.
        """
        try:
            import jwt  # PyJWT
        except ImportError:
            raise ImportError("PyJWT is required for VAPID JWT generation. Install with: pip install PyJWT")

        now = int(time.time())
        claims = {
            "sub": self.vapid_subject,
            "aud": origin,
            "exp": now + 86400,  # 24 hours
            "iat": now,
        }

        # Decode the base64url-encoded private key
        private_key_bytes = self._base64url_decode(self.vapid_private_key)

        # Use PyJWT with ECDSA
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.serialization import load_der_private_key

        try:
            private_key = load_der_private_key(private_key_bytes, password=None)
        except Exception:
            # Try loading as raw SEC1 key
            from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
            private_key = ec.derive_private_key(
                int.from_bytes(private_key_bytes, "big"),
                ec.SECP256R1(),
            )

        token = jwt.encode(claims, private_key, algorithm="ES256")
        return token

    # -- Push Notification Sending ------------------------------------------

    async def send_notification(
        self,
        subscription: Dict[str, Any],
        payload: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> Dict:
        """Send a push notification to a browser subscription.

        Args:
            subscription: Push subscription dict with keys: endpoint, keys (p256dh, auth).
            payload:      Notification payload dict (title, body, icon, etc.).
            ttl:          Time-to-live in seconds (0 = no storage, uses default if None).

        Returns:
            Dict with send status.
        """
        endpoint = subscription.get("endpoint", "")
        if not endpoint:
            raise ValueError("Subscription endpoint is required")

        keys = subscription.get("keys", {})
        p256dh = keys.get("p256dh", "")
        auth = keys.get("auth", "")

        # Prepare the payload
        message = json.dumps(payload)

        # If the subscription has encryption keys, encrypt the payload
        if p256dh and auth:
            encrypted = self._encrypt_payload(message, p256dh, auth)
            body = encrypted["ciphertext"]
            headers = {
                "Content-Type": "application/octet-stream",
                "Content-Encoding": "aes128gcm",
                "TTL": str(ttl if ttl is not None else self.ttl),
                "Encryption": f"salt={encrypted['salt']}",
                "Crypto-Key": f"dh={encrypted['dh']}; p256ecdsa={self.vapid_public_key}",
            }
        else:
            # No encryption keys: send unencrypted (some services reject this)
            body = message.encode("utf-8")
            headers = {
                "Content-Type": "application/octet-stream",
                "Content-Encoding": "aes128gcm",
                "TTL": str(ttl if ttl is not None else self.ttl),
            }

        # Add VAPID Authorization header
        try:
            from urllib.parse import urlparse
            parsed = urlparse(endpoint)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            jwt_token = self._generate_vapid_jwt(origin)
            headers["Authorization"] = f"WebPush {jwt_token}"
        except ImportError:
            pass  # VAPID is optional but recommended

        session = await self._ensure_session()
        async with session.post(endpoint, data=body, headers=headers) as resp:
            status = resp.status
            if status in (200, 201, 204):
                return {
                    "success": True,
                    "status_code": status,
                    "endpoint": endpoint,
                }
            else:
                response_text = await resp.text()
                return {
                    "success": False,
                    "status_code": status,
                    "error": response_text[:500],
                    "endpoint": endpoint,
                }

    async def send_batch(
        self,
        subscriptions: List[Dict[str, Any]],
        payload: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> Dict:
        """Send a push notification to multiple subscriptions.

        Args:
            subscriptions: List of subscription dicts.
            payload:      Notification payload.
            ttl:          Time-to-live.

        Returns:
            Dict with batch results.
        """
        results = []
        for sub in subscriptions:
            result = await self.send_notification(sub, payload, ttl)
            results.append(result)

        succeeded = sum(1 for r in results if r.get("success"))
        failed = len(results) - succeeded

        return {
            "total": len(results),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
        }

    # -- Payload Encryption --------------------------------------------------

    def _encrypt_payload(self, message: str, p256dh: str, auth: str) -> Dict[str, str]:
        """Encrypt a push notification payload using ECDH + AES-128-GCM.

        Implements RFC 8291 (Message Encryption for Web Push).

        Args:
            message: Plain text message.
            p256dh:  Subscriber's public key (base64url).
            auth:    Subscriber's auth secret (base64url).

        Returns:
            Dict with ciphertext, salt, and dh values (all base64url).
        """
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives.serialization import load_der_public_key
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        except ImportError:
            raise ImportError(
                "cryptography is required for payload encryption. "
                "Install with: pip install cryptography"
            )

        # Decode keys
        user_public_key = self._base64url_decode(p256dh)
        auth_secret = self._base64url_decode(auth)

        # Generate application server ECDH key pair
        server_key = ec.generate_private_key(ec.SECP256R1())
        server_public_key = server_key.public_key()

        # Derive shared secret using ECDH
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        user_public = load_der_public_key(user_public_key)
        shared_secret = server_key.exchange(ec.ECDH(), user_public)

        # Serialize server public key for Crypto-Key header
        dh = self._base64url_encode(
            server_public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        )

        # Generate random salt (16 bytes)
        salt = os.urandom(16)
        salt_b64 = self._base64url_encode(salt)

        # Key derivation (RFC 8291)
        # Info segments for HKDF
        auth_info = b"Content-Encoding: auth\x00"
        key_info = self._create_info(b"aes128gcm", user_public_key, server_public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint))
        nonce_info = self._create_info(b"nonce", user_public_key, server_public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint))

        # Derive PRK (pseudo-random key) from auth + shared secret
        prk = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=auth_secret,
            info=auth_info,
        ).derive(shared_secret)

        # Derive content encryption key
        content_key = HKDF(
            algorithm=hashes.SHA256(),
            length=16,
            salt=salt,
            info=key_info,
        ).derive(prk)

        # Derive nonce
        nonce = HKDF(
            algorithm=hashes.SHA256(),
            length=12,
            salt=salt,
            info=nonce_info,
        ).derive(prk)

        # Encrypt with AES-128-GCM
        aesgcm = AESGCM(content_key)

        # Padding: 2-byte big-endian length prefix + padding + message + 0x02 (record padding)
        plaintext = message.encode("utf-8")
        # RFC 8291: prepend 0x00 padding delimiter
        padded = plaintext + b"\x02"
        # Add record padding
        padding_len = max(0, 4096 - len(padded))
        padded = b"\x00" * padding_len + padded

        ciphertext = aesgcm.encrypt(nonce, padded, None)

        return {
            "ciphertext": ciphertext,
            "salt": salt_b64,
            "dh": dh,
        }

    def _create_info(self, content_encoding: bytes, user_key: bytes, server_key: bytes) -> bytes:
        """Create the info parameter for HKDF key derivation (RFC 8291)."""
        return (
            b"Content-Encoding: " + content_encoding + b"\x00"
            + b"P-256\x00\x00" + bytes([len(user_key)]) + user_key
            + bytes([len(server_key)]) + server_key
        )

    # -- Subscription Management ---------------------------------------------

    def validate_subscription(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a push subscription object.

        Returns:
            Dict with validation result.
        """
        issues = []

        if not subscription.get("endpoint"):
            issues.append("Missing endpoint URL")
        else:
            endpoint = subscription["endpoint"]
            if not endpoint.startswith("https://"):
                issues.append("Endpoint must use HTTPS")

        keys = subscription.get("keys", {})
        if not keys.get("p256dh"):
            issues.append("Missing p256dh key")
        if not keys.get("auth"):
            issues.append("Missing auth key")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }

    # -- Key Generation Utility ---------------------------------------------

    @staticmethod
    def generate_vapid_keys() -> Dict[str, str]:
        """Generate a new VAPID key pair.

        Returns:
            Dict with base64url-encoded public and private keys.
        """
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives.serialization import (
                Encoding,
                PublicFormat,
                PrivateFormat,
                NoEncryption,
            )
        except ImportError:
            raise ImportError("cryptography is required. Install with: pip install cryptography")

        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()

        private_bytes = private_key.private_bytes(
            Encoding.DER, PrivateFormat.PKCS8, NoEncryption()
        )
        public_bytes = public_key.public_bytes(
            Encoding.X962, PublicFormat.UncompressedPoint
        )

        def base64url_encode(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

        return {
            "private_key": base64url_encode(private_bytes),
            "public_key": base64url_encode(public_bytes),
        }

    # -- Base64url helpers ---------------------------------------------------

    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        """Decode a base64url-encoded string."""
        padding = 4 - len(data) % 4
        data += "=" * padding
        return base64.urlsafe_b64decode(data)

    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        """Encode bytes to base64url string."""
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")