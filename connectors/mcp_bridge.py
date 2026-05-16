"""
MCP (Model Context Protocol) Bridge Connector for Aethera
Connects to any MCP-compatible tool server and bridges its tools
into the Aethera connector framework.

MCP spec: https://spec.modelcontextprotocol.io/
Uses JSON-RPC 2.0 over stdio or HTTP/SSE transport.
"""
import asyncio
import json
from typing import Any, Dict, List, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    HAS_TENACITY = True
except ImportError:
    HAS_TENACITY = False

from .connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class MCPBridgeConnector(AetheraConnector):
    """Bridge connector to MCP (Model Context Protocol) servers.

    Supports both HTTP/SSE-based MCP servers and provides a unified
    connector interface for any MCP-compatible tool server.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.server_url = config.get("server_url", "")
        self.server_command = config.get("server_command", "")
        self.server_args = config.get("server_args", [])
        self.server_env = config.get("server_env", {})
        self.transport = config.get("transport", "http")  # 'http' or 'stdio'
        self._client: Optional[httpx.AsyncClient] = None
        self._process: Optional[asyncio.subprocess.Process] = None
        self._tools: List[Dict] = []
        self._resources: List[Dict] = []
        self._request_id = 0
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0
        self._stdio_lock = asyncio.Lock()

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="mcp_bridge",
            version="1.0.0",
            description="MCP Bridge - Connect to any Model Context Protocol server",
            base_url=self.server_url or f"stdio:{self.server_command}",
            auth_type="none",
            rate_limit=60,
            timeout=30,
        )

    async def initialize(self) -> bool:
        """Initialize the MCP connection and discover available tools."""
        if self.transport == "http":
            if not HAS_HTTPX:
                raise ImportError("httpx package required for MCP HTTP transport (pip install httpx)")
            if not self.server_url:
                raise ValueError("MCP server_url required for HTTP transport")
            self._client = httpx.AsyncClient(
                base_url=self.server_url,
                timeout=self.get_config().timeout,
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                },
            )
            # Initialize MCP handshake over HTTP
            init_result = await self._send_jsonrpc_http("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "AetheraAI", "version": "1.0.0"},
            })
            if init_result is None:
                return False

            # Send initialized notification
            await self._send_jsonrpc_http("notifications/initialized", {}, is_notification=True)

        elif self.transport == "stdio":
            if not self.server_command:
                raise ValueError("MCP server_command required for stdio transport")
            self._process = await asyncio.create_subprocess_exec(
                self.server_command,
                *self.server_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**__import__("os").environ, **self.server_env},
            )
            # Initialize MCP handshake over stdio
            init_result = await self._send_jsonrpc_stdio("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "AetheraAI", "version": "1.0.0"},
            })
            if init_result is None:
                return False

            # Send initialized notification
            await self._send_jsonrpc_stdio("notifications/initialized", {}, is_notification=True)

        # Discover tools
        tools_result = await self._call_mcp("tools/list", {})
        if tools_result and isinstance(tools_result, dict):
            self._tools = tools_result.get("tools", [])

        # Discover resources
        resources_result = await self._call_mcp("resources/list", {})
        if resources_result and isinstance(resources_result, dict):
            self._resources = resources_result.get("resources", [])

        return True

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._process:
            self._process.terminate()
            await self._process.wait()
            self._process = None
        self._tools.clear()
        self._resources.clear()

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    # ------------------------------------------------------------------
    # Transport: HTTP
    # ------------------------------------------------------------------

    async def _send_jsonrpc_http(
        self, method: str, params: Dict, is_notification: bool = False
    ) -> Optional[Dict]:
        """Send a JSON-RPC request via HTTP."""
        message: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        if not is_notification:
            message["id"] = self._next_id()

        try:
            response = await self._client.post("/mcp", json=message)
            response.raise_for_status()

            if is_notification:
                return None

            result = response.json()
            if "error" in result:
                return None
            return result.get("result")
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Transport: Stdio
    # ------------------------------------------------------------------

    async def _send_jsonrpc_stdio(
        self, method: str, params: Dict, is_notification: bool = False
    ) -> Optional[Dict]:
        """Send a JSON-RPC request via stdio subprocess."""
        message: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        if not is_notification:
            message["id"] = self._next_id()

        if not self._process or not self._process.stdin or not self._process.stdout:
            return None

        async with self._stdio_lock:
            line = json.dumps(message) + "\n"
            self._process.stdin.write(line.encode("utf-8"))
            await self._process.stdin.drain()

            if is_notification:
                return None

            # Read complete JSON response — accumulate data until we have
            # a valid JSON object, since responses may span multiple lines.
            buf = b""
            timeout = self.get_config().timeout
            while True:
                chunk = await asyncio.wait_for(
                    self._process.stdout.read(4096), timeout=timeout
                )
                if not chunk:
                    return None
                buf += chunk
                try:
                    result = json.loads(buf.decode("utf-8"))
                    break
                except json.JSONDecodeError:
                    # Incomplete JSON — keep reading
                    continue

            if "error" in result:
                return None
            return result.get("result")

    # ------------------------------------------------------------------
    # Unified MCP call
    # ------------------------------------------------------------------

    async def _call_mcp(self, method: str, params: Dict) -> Optional[Dict]:
        """Call an MCP method using the configured transport."""
        if self.transport == "http":
            return await self._send_jsonrpc_http(method, params)
        elif self.transport == "stdio":
            return await self._send_jsonrpc_stdio(method, params)
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(self, query: str = "", **params) -> ConnectorResult:
        """Search MCP resources by name or URI pattern.

        Keyword Args:
            uri_pattern: URI pattern to filter resources.
        """
        # List resources and filter locally
        resources_result = await self._call_mcp("resources/list", {})
        resources = resources_result.get("resources", []) if resources_result else self._resources

        if query:
            query_lower = query.lower()
            resources = [
                r for r in resources
                if query_lower in r.get("name", "").lower()
                or query_lower in r.get("uri", "").lower()
                or query_lower in r.get("description", "").lower()
            ]

        uri_pattern = params.get("uri_pattern", "")
        if uri_pattern:
            resources = [r for r in resources if uri_pattern in r.get("uri", "")]

        return ConnectorResult(
            success=True,
            data=resources,
            metadata={"source": "MCP Bridge", "count": len(resources)},
        )

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Read an MCP resource by URI, or call an MCP tool.

        If item_id matches a known tool name, it calls that tool.
        Otherwise, it reads a resource by URI.

        Args:
            item_id: Resource URI or tool name.
        Keyword Args:
            arguments: Arguments dict for tool calls.
        """
        # Check if it's a tool call
        tool_names = [t.get("name", "") for t in self._tools]
        if item_id in tool_names:
            arguments = params.get("arguments", {})
            return await self.call_tool(item_id, arguments)

        # Otherwise treat as resource read
        try:
            result = await self._call_mcp("resources/read", {"uri": item_id})
            if result is None:
                return ConnectorResult(success=False, error=f"Failed to read resource: {item_id}")

            contents = result.get("contents", [])
            return ConnectorResult(
                success=True,
                data=contents,
                metadata={"source": "MCP Bridge", "uri": item_id},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> ConnectorResult:
        """Call an MCP tool.

        Args:
            tool_name: Name of the MCP tool to call.
            arguments: Tool arguments.
        """
        if arguments is None:
            arguments = {}

        try:
            result = await self._call_mcp("tools/call", {
                "name": tool_name,
                "arguments": arguments,
            })

            if result is None:
                return ConnectorResult(success=False, error=f"MCP tool '{tool_name}' returned no result")

            content = result.get("content", [])
            is_error = result.get("isError", False)

            if is_error:
                error_text = ""
                for c in content:
                    if c.get("type") == "text":
                        error_text += c.get("text", "")
                return ConnectorResult(success=False, error=error_text or f"MCP tool '{tool_name}' returned an error")

            # Extract text content
            data_parts = []
            for c in content:
                if c.get("type") == "text":
                    data_parts.append(c.get("text", ""))
                elif c.get("type") == "image":
                    data_parts.append({"type": "image", "mime_type": c.get("mimeType", ""), "data": c.get("data", "")})
                elif c.get("type") == "resource":
                    data_parts.append({"type": "resource", "uri": c.get("resource", {}).get("uri", "")})

            return ConnectorResult(
                success=True,
                data=data_parts if len(data_parts) != 1 else data_parts[0],
                metadata={"source": "MCP Bridge", "tool": tool_name},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint == "get":
            return await self.get(params.pop("id", params.pop("uri", "")), **params)
        if endpoint == "call_tool":
            tool_name = params.pop("tool_name", params.pop("name", ""))
            arguments = params.pop("arguments", {})
            return await self.call_tool(tool_name, arguments)
        if endpoint == "list_tools":
            return ConnectorResult(
                success=True,
                data=self._tools,
                metadata={"source": "MCP Bridge", "count": len(self._tools)},
            )
        if endpoint == "list_resources":
            return ConnectorResult(
                success=True,
                data=self._resources,
                metadata={"source": "MCP Bridge", "count": len(self._resources)},
            )
        # Allow calling a tool directly by name as endpoint
        tool_names = [t.get("name", "") for t in self._tools]
        if endpoint in tool_names:
            arguments = params.pop("arguments", params)
            return await self.call_tool(endpoint, arguments)
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    def to_tool_definition(self) -> Dict[str, Any]:
        config = self.get_config()
        tool_endpoints = [
            {
                "name": "call_tool",
                "description": f"Call an MCP tool ({len(self._tools)} available)",
                "parameters": [
                    {"name": "tool_name", "type": "string", "required": True, "description": "MCP tool name"},
                    {"name": "arguments", "type": "object", "description": "Tool arguments"},
                ],
            },
            {
                "name": "search",
                "description": "Search MCP resources",
                "parameters": [
                    {"name": "query", "type": "string", "description": "Search query"},
                ],
            },
            {
                "name": "get",
                "description": "Read an MCP resource by URI",
                "parameters": [
                    {"name": "uri", "type": "string", "required": True, "description": "Resource URI"},
                ],
            },
        ]
        # Add each discovered tool as its own endpoint
        for tool in self._tools[:20]:  # Limit to first 20
            tool_endpoints.append({
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": [
                    {"name": p.get("name", ""), "type": "string", "description": p.get("description", "")}
                    for p in tool.get("inputSchema", {}).get("properties", {}).items()
                ] if tool.get("inputSchema") else [],
            })

        return {
            "type": "connector",
            "name": config.name,
            "description": config.description,
            "base_url": config.base_url,
            "auth_type": config.auth_type,
            "endpoints": tool_endpoints,
            "mcp_tools": [t.get("name", "") for t in self._tools],
            "mcp_resources": len(self._resources),
        }


def register_connector():
    return MCPBridgeConnector, {
        "server_url": "",
        "server_command": "",
        "transport": "http",
    }