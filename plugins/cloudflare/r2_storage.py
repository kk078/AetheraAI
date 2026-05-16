"""
Cloudflare R2 Storage Manager for Aethera

Provides R2 object storage operations (bucket and object CRUD)
via the Cloudflare API v4 and S3-compatible API.
"""
from typing import Any, Dict, List, Optional

import aiohttp


class R2StorageManager:
    """Manage Cloudflare R2 buckets and objects."""

    BASE_URL = "https://api.cloudflare.com/client/v4"

    def __init__(self, api_key: str, account_id: str):
        """
        Args:
            api_key:    Cloudflare API bearer token.
            account_id: Cloudflare account identifier.
        """
        self.api_key = api_key
        self.account_id = account_id
        self._session: Optional[aiohttp.ClientSession] = None

    # -- session lifecycle --------------------------------------------------

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # -- low-level request --------------------------------------------------

    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/{endpoint}"
        async with session.request(method, url, json=data) as resp:
            result = await resp.json()
            if not result.get("success", False):
                errors = result.get("errors", [{"message": "Unknown error"}])
                raise Exception(f"Cloudflare API error: {errors[0]['message']}")
            return result.get("result", {})

    # -- Bucket Operations --------------------------------------------------

    async def list_buckets(self) -> List[Dict]:
        """List all R2 buckets.

        Returns:
            List of dicts with keys: name, creation_date.
        """
        result = await self._request("GET", f"accounts/{self.account_id}/r2/buckets")
        buckets = result.get("buckets", result if isinstance(result, list) else [])
        return [
            {
                "name": b["name"],
                "creation_date": b.get("creation_date", ""),
            }
            for b in buckets
        ]

    async def get_bucket(self, bucket_name: str) -> Dict:
        """Get details for a specific R2 bucket.

        Returns:
            Dict with bucket details.
        """
        result = await self._request("GET", f"accounts/{self.account_id}/r2/buckets/{bucket_name}")
        return {
            "name": result.get("name", bucket_name),
            "creation_date": result.get("creation_date", ""),
            "location": result.get("location", ""),
        }

    async def create_bucket(self, bucket_name: str, location_hint: Optional[str] = None) -> Dict:
        """Create a new R2 bucket.

        Args:
            bucket_name:   Name for the new bucket.
            location_hint: Optional location hint (e.g. "wnam", "enam", "eeur").

        Returns:
            Dict with bucket name.
        """
        data: Dict[str, Any] = {"name": bucket_name}
        if location_hint:
            data["location_hint"] = location_hint

        result = await self._request("POST", f"accounts/{self.account_id}/r2/buckets", data)
        return {"name": result.get("name", bucket_name)}

    async def delete_bucket(self, bucket_name: str) -> bool:
        """Delete an R2 bucket. Bucket must be empty.

        Returns:
            True on success.
        """
        await self._request("DELETE", f"accounts/{self.account_id}/r2/buckets/{bucket_name}")
        return True

    # -- Object Operations (via S3-compatible API) --------------------------
    # R2 supports the S3 API for object-level operations. Use the
    # S3-compatible endpoint with AWS Signature V4 for object CRUD.

    def _get_s3_endpoint(self, bucket_name: str) -> str:
        """Build the S3-compatible endpoint URL for a bucket."""
        return f"https://{bucket_name}.{self.account_id}.r2.cloudflarestorage.com"

    async def list_objects(
        self,
        bucket_name: str,
        prefix: str = "",
        max_keys: int = 1000,
        access_key_id: str = "",
        secret_access_key: str = "",
    ) -> Dict:
        """List objects in an R2 bucket using the S3-compatible API.

        This requires R2 API tokens (Access Key ID + Secret Access Key)
        rather than the Cloudflare bearer token.

        Args:
            bucket_name:      Target bucket.
            prefix:           Object key prefix for filtering.
            max_keys:         Maximum number of keys to return.
            access_key_id:    R2 S3-compatible access key ID.
            secret_access_key: R2 S3-compatible secret access key.

        Returns:
            Dict with keys: objects (list), is_truncated (bool), next_marker.
        """
        endpoint = self._get_s3_endpoint(bucket_name)
        url = f"{endpoint}/"
        params = {"list-type": "2", "max-keys": str(max_keys)}
        if prefix:
            params["prefix"] = prefix

        # Use AWS SigV4 for S3-compatible requests
        headers = await self._sign_s3_request(
            "GET", url, params, access_key_id, secret_access_key
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                text = await resp.text()
                # Parse XML response
                import xml.etree.ElementTree as ET
                root = ET.fromstring(text)
                ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

                objects = []
                for content in root.findall("s3:Contents", ns):
                    objects.append({
                        "key": content.findtext("s3:Key", default="", namespaces=ns),
                        "size": int(content.findtext("s3:Size", default="0", namespaces=ns)),
                        "last_modified": content.findtext("s3:LastModified", default="", namespaces=ns),
                        "etag": content.findtext("s3:ETag", default="", namespaces=ns),
                    })

                is_truncated = root.findtext("s3:IsTruncated", default="false", namespaces=ns) == "true"
                next_marker = root.findtext("s3:NextContinuationToken", default="", namespaces=ns)

                return {
                    "objects": objects,
                    "is_truncated": is_truncated,
                    "next_marker": next_marker,
                }

    async def get_object(
        self,
        bucket_name: str,
        key: str,
        access_key_id: str = "",
        secret_access_key: str = "",
    ) -> bytes:
        """Download an object from an R2 bucket.

        Returns:
            Object content as bytes.
        """
        endpoint = self._get_s3_endpoint(bucket_name)
        url = f"{endpoint}/{key}"

        headers = await self._sign_s3_request(
            "GET", url, {}, access_key_id, secret_access_key
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                return await resp.read()

    async def put_object(
        self,
        bucket_name: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        access_key_id: str = "",
        secret_access_key: str = "",
    ) -> Dict:
        """Upload an object to an R2 bucket.

        Args:
            bucket_name:      Target bucket.
            key:              Object key (path in the bucket).
            data:             Object content as bytes.
            content_type:     MIME type for the object.
            access_key_id:    R2 S3-compatible access key ID.
            secret_access_key: R2 S3-compatible secret access key.

        Returns:
            Dict with etag and version_id.
        """
        endpoint = self._get_s3_endpoint(bucket_name)
        url = f"{endpoint}/{key}"

        headers = await self._sign_s3_request(
            "PUT", url, {}, access_key_id, secret_access_key, content_type=content_type
        )

        async with aiohttp.ClientSession() as session:
            async with session.put(url, data=data, headers=headers) as resp:
                etag = resp.headers.get("ETag", "")
                version_id = resp.headers.get("x-amz-version-id", "")
                return {"etag": etag, "version_id": version_id}

    async def delete_object(
        self,
        bucket_name: str,
        key: str,
        access_key_id: str = "",
        secret_access_key: str = "",
    ) -> bool:
        """Delete an object from an R2 bucket.

        Returns:
            True on success.
        """
        endpoint = self._get_s3_endpoint(bucket_name)
        url = f"{endpoint}/{key}"

        headers = await self._sign_s3_request(
            "DELETE", url, {}, access_key_id, secret_access_key
        )

        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as resp:
                return resp.status == 204

    # -- AWS Signature V4 signing helper ------------------------------------

    async def _sign_s3_request(
        self,
        method: str,
        url: str,
        params: Dict,
        access_key_id: str,
        secret_access_key: str,
        content_type: str = "",
        region: str = "auto",
        service: str = "s3",
    ) -> Dict[str, str]:
        """Sign an S3-compatible request using AWS Signature V4.

        Returns:
            Headers dict including Authorization.
        """
        import hashlib
        import hmac
        from datetime import datetime, timezone
        from urllib.parse import urlparse, urlencode

        now = datetime.now(timezone.utc)
        date_stamp = now.strftime("%Y%m%d")
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")

        parsed = urlparse(url)
        host = parsed.netloc
        canonical_uri = parsed.path or "/"

        canonical_querystring = urlencode(sorted(params.items())) if params else ""

        headers_dict: Dict[str, str] = {
            "host": host,
            "x-amz-date": amz_date,
        }
        if content_type:
            headers_dict["content-type"] = content_type

        signed_headers = ";".join(sorted(headers_dict.keys()))
        canonical_headers = "".join(f"{k}:{v}\n" for k, v in sorted(headers_dict.items()))

        payload_hash = hashlib.sha256(b"").hexdigest() if method != "PUT" else "UNSIGNED-PAYLOAD"
        if method == "PUT":
            headers_dict["x-amz-content-sha256"] = "UNSIGNED-PAYLOAD"
            signed_headers = ";".join(sorted(headers_dict.keys()))
            canonical_headers = "".join(f"{k}:{v}\n" for k, v in sorted(headers_dict.items()))

        canonical_request = "\n".join([
            method,
            canonical_uri,
            canonical_querystring,
            canonical_headers,
            signed_headers,
            payload_hash,
        ])

        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ])

        def sign(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode(), hashlib.sha256).digest()

        signing_key = sign(sign(sign(sign(
            f"AWS4{secret_access_key}".encode(), date_stamp), region), service), "aws4_request")

        signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

        authorization = (
            f"AWS4-HMAC-SHA256 "
            f"Credential={access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        headers_dict["Authorization"] = authorization
        return headers_dict