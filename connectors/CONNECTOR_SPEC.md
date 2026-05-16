# Aethera Connector Specification

## Overview

Connectors provide **read-only** access to external data sources. Unlike plugins, connectors do not perform actions -- they fetch and normalize data into a consistent format.

Every connector inherits from `AetheraConnector` (defined in `connectors/connector_base.py`) and implements a standard interface so the orchestrator can discover, invoke, and manage data sources uniformly.

---

## Required Methods

Each connector **must** implement the following methods:

| Method | Signature | Purpose |
|---|---|---|
| `get_config()` | `() -> ConnectorConfig` | Return static configuration (name, version, base URL, auth type, rate limit, timeout). |
| `search()` | `async (query, **params) -> ConnectorResult` | Search the data source by keyword. Returns a list of normalized results. |
| `get()` | `async (item_id, **params) -> ConnectorResult` | Retrieve a single item by its unique identifier. |
| `initialize()` | `async () -> bool` | Set up HTTP client, validate credentials, perform any startup logic. Return `True` on success. |
| `cleanup()` | `async () -> None` | Close HTTP client, release resources, clear caches. |
| `to_tool_definition()` | `() -> Dict` | Convert the connector into a tool definition dict (name, description, endpoints, parameters). |

Additionally, implement `fetch(endpoint, params)` for backward compatibility with the base class abstract method.

---

## File Structure

Place connectors in `connectors/builtin/` as individual modules:

```
connectors/
  connector_base.py        # Base class, ConnectorConfig, ConnectorResult
  connector_registry.py    # Discovery and lifecycle management
  mcp_bridge.py            # MCP protocol bridge
  openapi_bridge.py         # OpenAPI/Swagger dynamic connector
  builtin/
    __init__.py             # Package init with CONNECTOR_REGISTRY
    cms_npi.py
    cms_coverage.py
    openfda.py
    pubmed.py
    ...one file per connector
```

---

## Implementation Pattern

```python
import asyncio
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class MyConnector(AetheraConnector):
    """One-line description of the connector."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://api.example.com/")
        self.api_key = config.get("api_key", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="my_connector",
            version="1.0.0",
            description="My Connector - Short description",
            base_url=self.base_url,
            auth_type="api_key",       # none | api_key | bearer | oauth2
            rate_limit=60,             # requests per minute
            timeout=30,                # seconds
        )

    async def initialize(self) -> bool:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.get_config().timeout,
            headers=headers,
        )
        return True

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _rate_limited_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Execute HTTP request with rate limiting and retry."""
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

    async def search(self, query: str = "", **params) -> ConnectorResult:
        if not query:
            return ConnectorResult(success=False, error="Search query required")
        try:
            response = await self._rate_limited_request("GET", "search", params={"q": query})
            data = response.json()
            return ConnectorResult(
                success=True,
                data=data.get("results", []),
                metadata={"source": "My Connector", "query": query},
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        if not item_id:
            return ConnectorResult(success=False, error="ID required")
        try:
            response = await self._rate_limited_request("GET", f"items/{item_id}")
            data = response.json()
            return ConnectorResult(success=True, data=data, metadata={"source": "My Connector"})
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint == "get":
            return await self.get(params.pop("id", ""), **params)
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

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
                    "description": "Search items",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search query"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Get item by ID",
                    "parameters": [
                        {"name": "id", "type": "string", "required": True, "description": "Item ID"},
                    ],
                },
            ],
        }


def register_connector():
    """Return the connector class and default config dict."""
    import os
    return MyConnector, {
        "base_url": "https://api.example.com/",
        "api_key": os.getenv("MY_API_KEY", ""),
    }
```

---

## Key Requirements

### 1. HTTP Client
- Use **httpx.AsyncClient** for all HTTP requests (not aiohttp).
- Set `base_url`, `timeout`, and `headers` at initialization.
- Always close the client in `cleanup()` via `await self._client.aclose()`.

### 2. Rate Limiting
- Every connector must include a `_rate_limited_request()` method.
- Use `asyncio.Lock` to serialize requests and enforce minimum intervals.
- Rate limit values go in `ConnectorConfig.rate_limit` (requests per minute).

### 3. Retries
- Use **tenacity** with exponential backoff:
  - `stop=stop_after_attempt(3)`
  - `wait=wait_exponential(multiplier=1, min=1, max=10)`
  - Retry on `httpx.TimeoutException` and `httpx.ConnectError`.

### 4. Error Handling
- Catch `httpx.HTTPStatusError` and return `ConnectorResult(success=False, error=...)`.
- Catch generic `Exception` as a fallback.
- Never raise exceptions from `search()`, `get()`, or `fetch()` -- always return a `ConnectorResult`.

### 5. Data Normalization
- Normalize API responses into a consistent dict structure.
- Provide a `_normalize_*()` static method for each entity type.
- Include meaningful keys, not raw API field names.

### 6. Tool Definition
- `to_tool_definition()` returns a dict with `type`, `name`, `description`, `base_url`, `auth_type`, and `endpoints`.
- Each endpoint has `name`, `description`, and `parameters` (list of dicts with `name`, `type`, `required`, `description`).

### 7. Registration
- Every connector file must export a `register_connector()` function.
- It returns `(ConnectorClass, default_config_dict)`.
- Default config should read API keys from environment variables.

---

## ConnectorConfig Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | str | Yes | Unique connector identifier (lowercase, underscored) |
| `version` | str | Yes | Semantic version |
| `description` | str | Yes | One-line human description |
| `base_url` | str | Yes | API base URL |
| `auth_type` | str | No | `none`, `api_key`, `bearer`, or `oauth2` (default `none`) |
| `rate_limit` | int | No | Requests per minute (None = unlimited) |
| `timeout` | int | No | Request timeout in seconds (default 30) |

## ConnectorResult Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `success` | bool | Yes | Whether the request succeeded |
| `data` | Any | No | Normalized response data |
| `error` | str | No | Error message when success is False |
| `metadata` | dict | No | Extra context (source, counts, pagination) |
| `timestamp` | str | No | ISO timestamp (auto-generated) |

---

## Registering a New Connector

1. Create `connectors/builtin/my_connector.py` following the pattern above.
2. Import it in `connectors/builtin/__init__.py` and add to `__all__` and `CONNECTOR_REGISTRY`.
3. Add the module mapping in `ConnectorRegistry.load_connectors()` inside `connector_registry.py`.
4. Add environment variable references to the `register_connector()` function.
5. Test by instantiating and calling `initialize()`, `search()`, `get()`, and `cleanup()`.

---

## Special Connectors

### MCP Bridge (`mcp_bridge.py`)
Connects to any Model Context Protocol server. Supports HTTP and stdio transports. Discovers tools and resources dynamically via MCP's `tools/list` and `resources/list` methods. Tool calls go through `tools/call`.

### OpenAPI Bridge (`openapi_bridge.py`)
Takes an OpenAPI/Swagger spec URL or dict, parses all operations, and generates a connector dynamically. Operations can be called by their `operationId` or `METHOD /path` format. Supports Swagger 2.x (auto-converts to OpenAPI 3.x structure).

---

## Testing Checklist

- [ ] `initialize()` returns `True` and creates the HTTP client
- [ ] `search("")` returns an appropriate error (empty query)
- [ ] `search("valid term")` returns `ConnectorResult(success=True, data=[...])`
- [ ] `get("valid_id")` returns a single normalized item
- [ ] `get("invalid_id")` returns `ConnectorResult(success=False)`
- [ ] `cleanup()` closes the client without error
- [ ] `to_tool_definition()` returns a valid dict with endpoints
- [ ] Rate limiting enforces minimum intervals between requests
- [ ] Retries handle transient network failures
- [ ] API errors (4xx/5xx) are caught and returned as error results, not raised