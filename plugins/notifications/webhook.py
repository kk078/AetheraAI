"""
Webhook Notifier for Aethera

Provides generic webhook notification operations: send payloads,
manage webhook endpoints, verify signatures, and retry failed deliveries.
"""
import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Dict, List, Optional

import aiohttp


class WebhookNotifier:
    """Send and manage webhook notifications."""

    def __init__(
        self,
        default_url: str = "",
        secret: str = "",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Args:
            default_url: Default webhook URL.
            secret:      Shared secret for HMAC signature signing.
            timeout:     Request timeout in seconds.
            max_retries: Maximum retry attempts for failed deliveries.
            retry_delay: Delay between retries in seconds.
        """
        self.default_url = default_url
        self.secret = secret
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._session: Optional[aiohttp.ClientSession] = None
        self._delivery_log: List[Dict[str, Any]] = []

    # -- Session lifecycle --------------------------------------------------

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # -- Signature Generation ------------------------------------------------

    def generate_signature(self, payload: str, secret: Optional[str] = None) -> str:
        """Generate an HMAC-SHA256 signature for a payload.

        Args:
            payload: JSON string of the webhook payload.
            secret:  Override default secret.

        Returns:
            Hex digest of the HMAC signature.
        """
        key = (secret or self.secret).encode("utf-8")
        return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def generate_headers(self, payload: str, secret: Optional[str] = None) -> Dict[str, str]:
        """Generate standard webhook headers including signature.

        Args:
            payload: JSON string of the webhook payload.
            secret:  Override default secret.

        Returns:
            Headers dict.
        """
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-ID": str(uuid.uuid4()),
            "X-Webhook-Timestamp": str(int(time.time())),
        }
        if secret or self.secret:
            signature = self.generate_signature(payload, secret)
            headers["X-Webhook-Signature"] = f"sha256={signature}"
        return headers

    # -- Send Webhook -------------------------------------------------------

    async def send(
        self,
        payload: Dict[str, Any],
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        secret: Optional[str] = None,
    ) -> Dict:
        """Send a webhook notification.

        Args:
            payload: Webhook payload dict.
            url:     Override default URL.
            headers: Additional headers (merged with generated headers).
            secret:  Override default secret for signing.

        Returns:
            Dict with delivery details.
        """
        target_url = url or self.default_url
        if not target_url:
            raise ValueError("No webhook URL specified")

        payload_str = json.dumps(payload, default=str)
        generated_headers = self.generate_headers(payload_str, secret)
        if headers:
            generated_headers.update(headers)

        delivery_id = generated_headers.get("X-Webhook-ID", str(uuid.uuid4()))

        # Send with retries
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                session = await self._ensure_session()
                async with session.post(
                    target_url,
                    data=payload_str,
                    headers=generated_headers,
                ) as resp:
                    response_body = await resp.text()
                    status_code = resp.status

                    if status_code < 400:
                        result = {
                            "delivery_id": delivery_id,
                            "url": target_url,
                            "status_code": status_code,
                            "success": True,
                            "attempt": attempt,
                        }
                        self._delivery_log.append(result)
                        return result
                    else:
                        last_error = f"HTTP {status_code}: {response_body[:500]}"
            except Exception as e:
                last_error = str(e)

            # Wait before retry (except on last attempt)
            if attempt < self.max_retries:
                import asyncio
                await asyncio.sleep(self.retry_delay * attempt)

        result = {
            "delivery_id": delivery_id,
            "url": target_url,
            "success": False,
            "error": last_error,
            "attempts": self.max_retries,
        }
        self._delivery_log.append(result)
        return result

    async def send_batch(
        self,
        payloads: List[Dict[str, Any]],
        url: Optional[str] = None,
    ) -> Dict:
        """Send multiple webhook notifications.

        Args:
            payloads: List of payload dicts.
            url:     Override default URL.

        Returns:
            Dict with batch delivery stats.
        """
        results = []
        for payload in payloads:
            result = await self.send(payload, url)
            results.append(result)

        succeeded = sum(1 for r in results if r.get("success"))
        failed = len(results) - succeeded

        return {
            "total": len(results),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
        }

    # -- Signature Verification -----------------------------------------------

    @staticmethod
    def verify_signature(
        payload: str,
        signature: str,
        secret: str,
        algorithm: str = "sha256",
    ) -> bool:
        """Verify a webhook signature.

        Args:
            payload:   Raw payload string.
            signature: Signature to verify (with or without "sha256=" prefix).
            secret:    Shared secret.
            algorithm: Hash algorithm ("sha256" or "sha1").

        Returns:
            True if the signature is valid.
        """
        # Strip algorithm prefix if present
        if signature.startswith(f"{algorithm}="):
            signature = signature[len(algorithm) + 1:]

        if algorithm == "sha256":
            expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        elif algorithm == "sha1":
            expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha1).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        return hmac.compare_digest(expected, signature)

    # -- Delivery Log -------------------------------------------------------

    def get_delivery_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get the delivery log.

        Returns:
            List of delivery result dicts.
        """
        return self._delivery_log[-limit:]

    def clear_delivery_log(self) -> None:
        """Clear the delivery log."""
        self._delivery_log.clear()

    # -- Webhook Endpoint Management -----------------------------------------

    _endpoints: Dict[str, Dict[str, Any]] = {}

    async def register_endpoint(
        self,
        name: str,
        url: str,
        secret: str = "",
        events: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """Register a webhook endpoint for later use.

        Args:
            name:    Endpoint name/identifier.
            url:     Webhook URL.
            secret:  Optional signing secret.
            events:  List of event types this endpoint subscribes to.
            headers: Additional headers to send.

        Returns:
            Dict with endpoint details.
        """
        endpoint = {
            "name": name,
            "url": url,
            "secret": secret,
            "events": events or ["*"],
            "headers": headers or {},
            "created_at": time.time(),
        }
        self._endpoints[name] = endpoint  # type: ignore
        return {"name": name, "url": url, "events": endpoint["events"]}

    async def notify_event(
        self,
        event_type: str,
        data: Dict[str, Any],
    ) -> Dict:
        """Send a notification to all endpoints subscribed to an event type.

        Args:
            event_type: Event type string.
            data:       Event data dict.

        Returns:
            Dict with notification results per endpoint.
        """
        payload = {
            "event": event_type,
            "data": data,
            "timestamp": time.time(),
        }

        results = {}
        for name, endpoint in self._endpoints.items():  # type: ignore
            events = endpoint.get("events", ["*"])
            if "*" in events or event_type in events:
                result = await self.send(
                    payload,
                    url=endpoint["url"],
                    headers=endpoint.get("headers"),
                    secret=endpoint.get("secret") or None,
                )
                results[name] = result

        return {"event": event_type, "deliveries": results}