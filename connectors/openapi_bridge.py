"""
OpenAPI/Swagger Bridge Connector for Aethera
Auto-generates a connector class from an OpenAPI/Swagger specification.
Parses the spec, generates methods dynamically, and provides a standard
connector interface for any REST API described by OpenAPI 3.x or Swagger 2.x.
"""
import asyncio
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class OpenAPIBridgeConnector(AetheraConnector):
    """Dynamic connector generated from an OpenAPI/Swagger specification.

    Provide a spec_url or spec_dict at initialization. The connector will
    parse the specification and generate methods for each operation.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.spec_url = config.get("spec_url", "")
        self.spec_dict = config.get("spec_dict", {})
        self.base_url = config.get("base_url", "")
        self.auth_type_cfg = config.get("auth_type", "none")
        self.api_key = config.get("api_key", "")
        self.bearer_token = config.get("bearer_token", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0
        self._spec: Dict = {}
        self._operations: List[Dict] = []
        self._security_schemes: Dict = {}

    def get_config(self) -> ConnectorConfig:
        info = self._spec.get("info", {})
        title = info.get("title", "OpenAPI Bridge")
        version = info.get("version", "1.0.0")
        return ConnectorConfig(
            name=self._sanitize_name(title),
            version=version,
            description=info.get("description", f"Auto-generated connector for {title}"),
            base_url=self.base_url or self._resolve_base_url(),
            auth_type=self.auth_type_cfg,
            rate_limit=60,
            timeout=30,
        )

    async def initialize(self) -> bool:
        """Load and parse the OpenAPI spec, then configure the HTTP client."""
        if self.spec_url:
            await self._load_spec_from_url()
        elif self.spec_dict:
            self._spec = self._spec_dict

        if not self._spec:
            raise ValueError("OpenAPI spec required (spec_url or spec_dict)")

        # Normalize Swagger 2.x to OpenAPI 3.x structure
        self._normalize_spec()

        # Resolve base URL from spec if not provided
        if not self.base_url:
            self.base_url = self._resolve_base_url()

        # Parse operations
        self._operations = self._parse_operations()

        # Parse security schemes
        self._security_schemes = self._spec.get("components", {}).get("securitySchemes", {})

        # Build HTTP client
        headers: Dict[str, str] = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.api_key:
            # Apply API key based on security scheme location
            for name, scheme in self._security_schemes.items():
                if scheme.get("type") == "apiKey" and scheme.get("in") == "header":
                    headers[scheme.get("name", "X-API-Key")] = self.api_key

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
        self._operations.clear()
        self._spec.clear()

    async def _load_spec_from_url(self) -> None:
        """Fetch OpenAPI spec from URL."""
        async with httpx.AsyncClient(timeout=30) as temp_client:
            try:
                resp = await temp_client.get(self.spec_url)
                resp.raise_for_status()
                self._spec = resp.json()
            except Exception:
                raise ValueError(f"Failed to load OpenAPI spec from {self.spec_url}")

    def _normalize_spec(self) -> None:
        """Normalize Swagger 2.x specs to OpenAPI 3.x structure."""
        if self._spec.get("swagger"):
            # Convert Swagger 2.x host/basePath to servers
            host = self._spec.get("host", "localhost")
            base_path = self._spec.get("basePath", "/")
            schemes = self._spec.get("schemes", ["https"])
            scheme = schemes[0] if schemes else "https"
            self._spec.setdefault("servers", [{"url": f"{scheme}://{host}{base_path}"}])

            # Move securityDefinitions to components.securitySchemes
            sec_defs = self._spec.get("securityDefinitions", {})
            if sec_defs:
                self._spec.setdefault("components", {}).setdefault("securitySchemes", sec_defs)

    def _resolve_base_url(self) -> str:
        """Resolve the base URL from the spec's server definitions."""
        servers = self._spec.get("servers", [])
        if servers:
            first_server = servers[0]
            url = first_server.get("url", "")
            # Replace variables in server URL
            variables = first_server.get("variables", {})
            for var_name, var_def in variables.items():
                default_val = var_def.get("default", "")
                url = url.replace(f"{{{var_name}}}", default_val)
            return url.rstrip("/")
        return self.base_url

    def _parse_operations(self) -> List[Dict]:
        """Parse all operations from the spec."""
        operations: List[Dict] = []
        paths = self._spec.get("paths", {})

        for path, path_item in paths.items():
            for method in ("get", "post", "put", "patch", "delete", "options", "head"):
                operation = path_item.get(method)
                if not operation:
                    continue

                op_id = operation.get("operationId", f"{method}_{path.replace('/', '_').strip('_')}")
                # Clean up operation ID
                op_id = re.sub(r"[^a-zA-Z0-9_]", "_", op_id)

                parameters = []
                # Path-level parameters
                for param in path_item.get("parameters", []):
                    parameters.append(self._normalize_parameter(param))
                # Operation-level parameters
                for param in operation.get("parameters", []):
                    parameters.append(self._normalize_parameter(param))

                # Request body (OpenAPI 3.x)
                request_body = operation.get("requestBody", {})
                content_types = request_body.get("content", {})

                operations.append({
                    "id": op_id,
                    "method": method.upper(),
                    "path": path,
                    "summary": operation.get("summary", ""),
                    "description": operation.get("description", ""),
                    "parameters": parameters,
                    "request_body": bool(request_body),
                    "content_types": list(content_types.keys()),
                    "deprecated": operation.get("deprecated", False),
                    "tags": operation.get("tags", []),
                })

        return operations

    @staticmethod
    def _normalize_parameter(param: Dict) -> Dict:
        """Normalize a parameter definition."""
        schema = param.get("schema", {})
        return {
            "name": param.get("name", ""),
            "in": param.get("in", "query"),
            "description": param.get("description", ""),
            "required": param.get("required", False),
            "type": schema.get("type", "string"),
            "default": schema.get("default"),
            "enum": schema.get("enum", []),
        }

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Convert a spec title to a valid connector name."""
        name = re.sub(r"[^a-zA-Z0-9]", "_", name)
        name = re.sub(r"_+", "_", name).strip("_").lower()
        return name or "openapi_bridge"

    async def _rate_limited_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        config = self.get_config()
        if config.rate_limit:
            min_interval = 60.0 / config.rate_limit
            async with self._rate_limit_lock:
                now = time.monotonic()
                elapsed = now - self._last_request_time
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
                self._last_request_time = time.monotonic()

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(self, query: str = "", **params) -> ConnectorResult:
        """Search available API operations by keyword.

        Keyword Args:
            tag: Filter by operation tag.
            method: Filter by HTTP method.
        """
        query_lower = query.lower() if query else ""
        tag_filter = params.get("tag", "").lower()
        method_filter = params.get("method", "").upper()

        matches = []
        for op in self._operations:
            if method_filter and op["method"] != method_filter:
                continue
            if tag_filter and tag_filter not in [t.lower() for t in op.get("tags", [])]:
                continue
            if query_lower:
                searchable = f"{op['id']} {op['summary']} {op['description']} {' '.join(op.get('tags', []))}".lower()
                if query_lower not in searchable:
                    continue
            matches.append({
                "id": op["id"],
                "method": op["method"],
                "path": op["path"],
                "summary": op["summary"],
                "description": op["description"],
                "parameters": op["parameters"],
                "tags": op.get("tags", []),
            })

        return ConnectorResult(
            success=True,
            data=matches,
            metadata={
                "source": "OpenAPI Bridge",
                "total_operations": len(self._operations),
                "returned": len(matches),
            },
        )

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Execute an API operation by its operationId or path.

        Args:
            item_id: Operation ID (e.g. 'listUsers') or 'METHOD /path'.
        Keyword Args:
            path_params: Dict of path parameters (e.g. {'id': '123'}).
            query_params: Dict of query parameters.
            body: Request body (dict or string).
            headers: Additional headers.
        """
        operation = self._find_operation(item_id)
        if not operation:
            return ConnectorResult(success=False, error=f"Operation '{item_id}' not found")

        return await self._execute_operation(operation, **params)

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint == "get":
            return await self.get(params.pop("operation_id", params.pop("id", "")), **params)
        if endpoint == "spec":
            return ConnectorResult(
                success=True,
                data={
                    "info": self._spec.get("info", {}),
                    "operations": [{"id": o["id"], "method": o["method"], "path": o["path"]} for o in self._operations],
                    "servers": self._spec.get("servers", []),
                },
                metadata={"source": "OpenAPI Bridge"},
            )
        # Try to match an operation ID
        operation = self._find_operation(endpoint)
        if operation:
            return await self._execute_operation(operation, **params)
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    def _find_operation(self, identifier: str) -> Optional[Dict]:
        """Find an operation by ID, 'METHOD /path', or path."""
        # Exact operation ID match
        for op in self._operations:
            if op["id"] == identifier:
                return op

        # 'METHOD /path' format
        if " " in identifier:
            parts = identifier.split(" ", 1)
            method = parts[0].upper()
            path = parts[1].strip()
            for op in self._operations:
                if op["method"] == method and op["path"] == path:
                    return op

        # Path-only match (first GET)
        for op in self._operations:
            if op["path"] == identifier and op["method"] == "GET":
                return op

        return None

    async def _execute_operation(self, operation: Dict, **params) -> ConnectorResult:
        """Execute a parsed API operation."""
        path_params = params.get("path_params", {})
        query_params_dict = params.get("query_params", params.get("queryParams", {}))
        body = params.get("body", params.get("request_body", None))
        extra_headers = params.get("headers", {})

        # Build URL by substituting path parameters
        url = operation["path"]
        for param_name, param_value in path_params.items():
            url = url.replace(f"{{{param_name}}}", str(param_value))

        # Build query parameters
        qp: Dict[str, Any] = {}
        for param in operation["parameters"]:
            if param["in"] == "query":
                value = query_params_dict.get(param["name"], param.get("default"))
                if value is not None:
                    qp[param["name"]] = value

        # Merge any additional query params
        qp.update(query_params_dict)

        # Build request kwargs
        kwargs: Dict[str, Any] = {"params": {k: v for k, v in qp.items() if v is not None}}
        if extra_headers:
            kwargs["headers"] = extra_headers
        if body is not None and operation["method"] in ("POST", "PUT", "PATCH"):
            if isinstance(body, dict):
                kwargs["json"] = body
            else:
                kwargs["content"] = str(body)

        try:
            response = await self._rate_limited_request(
                operation["method"], url, **kwargs
            )
            content_type = response.headers.get("content-type", "")

            if "application/json" in content_type:
                data = response.json()
            else:
                data = response.text

            return ConnectorResult(
                success=True,
                data=data,
                metadata={
                    "source": "OpenAPI Bridge",
                    "operation_id": operation["id"],
                    "method": operation["method"],
                    "path": operation["path"],
                    "status_code": response.status_code,
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(
                success=False,
                error=f"API error ({exc.response.status_code}): {exc.response.text[:500]}",
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    def to_tool_definition(self) -> Dict[str, Any]:
        config = self.get_config()
        # Build endpoint definitions from parsed operations
        endpoints = []
        for op in self._operations[:50]:  # Limit to first 50 operations
            param_defs = []
            for p in op["parameters"]:
                param_defs.append({
                    "name": p["name"],
                    "type": p.get("type", "string"),
                    "required": p.get("required", False),
                    "description": p.get("description", ""),
                })
            endpoints.append({
                "name": op["id"],
                "description": op["summary"] or op["description"] or f"{op['method']} {op['path']}",
                "parameters": param_defs,
            })

        return {
            "type": "connector",
            "name": config.name,
            "description": config.description,
            "base_url": config.base_url,
            "auth_type": config.auth_type,
            "version": config.version,
            "endpoints": endpoints,
            "operation_count": len(self._operations),
        }


def register_connector():
    return OpenAPIBridgeConnector, {"spec_url": "", "spec_dict": {}}