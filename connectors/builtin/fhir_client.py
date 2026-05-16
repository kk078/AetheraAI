"""
Generic FHIR R4 Client Connector for Aethera
Configurable endpoint for any FHIR R4-compliant server.
https://www.hl7.org/fhir/
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult

_FHIR_RESOURCE_TYPES = [
    "Patient", "Practitioner", "Organization", "Location",
    "Observation", "Condition", "Procedure", "MedicationRequest",
    "MedicationDispense", "DiagnosticReport", "Encounter",
    "Claim", "ExplanationOfBenefit", "Coverage", "CarePlan",
    "AllergyIntolerance", "Immunization", "DocumentReference",
    "ServiceRequest", "Task", "Goal", "Device",
]


class FHIRClientConnector(AetheraConnector):
    """Generic FHIR R4 client connector for any FHIR-compliant endpoint."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "")
        self.auth_type_cfg = config.get("auth_type", "bearer")
        self.access_token = config.get("access_token", "")
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.token_url = config.get("token_url", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="fhir_client",
            version="1.0.0",
            description="FHIR R4 Client - Configurable healthcare data exchange",
            base_url=self.base_url,
            auth_type=self.auth_type_cfg,
            rate_limit=100,
            timeout=30,
        )

    async def initialize(self) -> bool:
        if not self.base_url:
            raise ValueError("FHIR base URL required")

        headers: Dict[str, str] = {"Accept": "application/fhir+json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.get_config().timeout,
            headers=headers,
            follow_redirects=True,
        )

        # Validate connection by fetching server capability statement
        try:
            resp = await self._client.get("metadata")
            if resp.status_code != 200:
                return False
        except Exception:
            return False

        return True

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _rate_limited_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        config = self.get_config()
        if config.rate_limit:
            min_interval = 60.0 / config.rate_limit
            async with self._rate_limit_lock:
                now = asyncio.get_event_loop().time()
                elapsed = now - self._last_request_time
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
                self._last_request_time = asyncio.get_event_loop().time()

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
            reraise=True,
        )
        async def _do_request() -> httpx.Response:
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        return await _do_request()

    async def _refresh_token(self) -> None:
        """Refresh OAuth2 access token using client credentials flow."""
        if not self.token_url or not self.client_id or not self.client_secret:
            return

        async with httpx.AsyncClient() as temp_client:
            resp = await temp_client.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            if resp.status_code == 200:
                token_data = resp.json()
                self.access_token = token_data.get("access_token", "")
                self._client.headers["Authorization"] = f"Bearer {self.access_token}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(self, query: str = "", **params) -> ConnectorResult:
        """Search FHIR resources.

        Keyword Args:
            resource_type: FHIR resource type (e.g. 'Patient', 'Observation').
            patient: Patient ID to filter by.
            name: Name filter (for Patient/Practitioner).
            identifier: Identifier filter.
            code: Code filter (for Observation/Condition).
            category: Category filter.
            status: Status filter.
            date: Date or date range filter.
            _count: Max results per page (1-100, default 20).
            _sort: Sort parameter.
            _lastUpdated: Last updated filter.
        """
        resource_type = params.pop("resource_type", "Patient")
        qp: Dict[str, Any] = {"_count": min(int(params.pop("_count", 20)), 100)}

        if query:
            qp["_text"] = query

        # Map common FHIR search parameters
        for key in ("patient", "identifier", "name", "code", "category",
                     "status", "date", "birthdate", "gender", "_sort", "_lastUpdated"):
            if key in params and params[key]:
                qp[key] = params[key]

        try:
            response = await self._rate_limited_request("GET", resource_type, params=qp)
            data = response.json()

            if data.get("resourceType") == "Bundle":
                entries = data.get("entry", [])
                resources = [e.get("resource", {}) for e in entries]
                return ConnectorResult(
                    success=True,
                    data=resources,
                    metadata={
                        "source": "FHIR",
                        "resource_type": resource_type,
                        "total": data.get("total", len(resources)),
                        "next": self._get_next_link(data),
                    },
                )
            else:
                return ConnectorResult(
                    success=True,
                    data=data,
                    metadata={"source": "FHIR", "resource_type": resource_type},
                )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(
                success=False,
                error=f"FHIR API error ({exc.response.status_code}): {exc.response.text[:500]}",
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Retrieve a specific FHIR resource by ID.

        Args:
            item_id: Resource ID.
        Keyword Args:
            resource_type: FHIR resource type (required, default 'Patient').
        """
        resource_type = params.pop("resource_type", "Patient")

        try:
            response = await self._rate_limited_request("GET", f"{resource_type}/{item_id}")
            data = response.json()
            return ConnectorResult(
                success=True,
                data=data,
                metadata={"source": "FHIR", "resource_type": resource_type, "id": item_id},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return ConnectorResult(success=False, error=f"{resource_type}/{item_id} not found")
            return ConnectorResult(success=False, error=f"FHIR API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def capability_statement(self) -> ConnectorResult:
        """Fetch the server's capability statement (metadata)."""
        try:
            response = await self._rate_limited_request("GET", "metadata")
            data = response.json()
            return ConnectorResult(
                success=True,
                data=data,
                metadata={"source": "FHIR", "type": "CapabilityStatement"},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(**params)
        if endpoint == "get":
            item_id = params.pop("id", "")
            return await self.get(item_id, **params)
        if endpoint == "metadata":
            return await self.capability_statement()
        # Allow direct resource type as endpoint
        if endpoint in _FHIR_RESOURCE_TYPES:
            params["resource_type"] = endpoint
            return await self.search(**params)
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    @staticmethod
    def _get_next_link(bundle: Dict) -> Optional[str]:
        for link in bundle.get("link", []):
            if link.get("relation") == "next":
                return link.get("url")
        return None

    def to_tool_definition(self) -> Dict[str, Any]:
        config = self.get_config()
        return {
            "type": "connector",
            "name": config.name,
            "description": config.description,
            "base_url": config.base_url,
            "auth_type": config.auth_type,
            "endpoints": [
                {
                    "name": "search",
                    "description": "Search FHIR resources by type and criteria",
                    "parameters": [
                        {"name": "resource_type", "type": "string", "description": f"One of: {', '.join(_FHIR_RESOURCE_TYPES[:8])}..."},
                        {"name": "query", "type": "string", "description": "Text search"},
                        {"name": "patient", "type": "string", "description": "Patient ID"},
                        {"name": "_count", "type": "integer", "description": "Max results (1-100)"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Retrieve a specific resource by type and ID",
                    "parameters": [
                        {"name": "resource_type", "type": "string", "required": True},
                        {"name": "id", "type": "string", "required": True, "description": "Resource ID"},
                    ],
                },
                {
                    "name": "metadata",
                    "description": "Get server capability statement",
                    "parameters": [],
                },
            ],
        }


def register_connector():
    import os
    return FHIRClientConnector, {
        "base_url": os.getenv("FHIR_BASE_URL", ""),
        "access_token": os.getenv("FHIR_ACCESS_TOKEN", ""),
    }