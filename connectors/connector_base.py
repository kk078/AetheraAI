"""
Aethera Connector Base Class
Connectors provide read-only access to external data sources.
Unlike plugins, connectors don't perform actions - they fetch and normalize data.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ConnectorConfig(BaseModel):
    """Connector configuration schema."""
    name: str
    version: str
    description: str
    base_url: str
    auth_type: str = 'none'  # none, api_key, bearer, oauth
    rate_limit: Optional[int] = None  # Requests per minute
    timeout: int = 30


class ConnectorResult(BaseModel):
    """Standardized connector result."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class AetheraConnector(ABC):
    """
    Base class for all Aethera connectors.

    Connectors provide read-only access to external data sources.
    They normalize responses into a consistent format.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the connector.

        Args:
            config: Connector configuration including API keys
        """
        self.config = config
        self._session = None
        self._last_request = None
        self._request_count = 0

    @abstractmethod
    def get_config(self) -> ConnectorConfig:
        """Return the connector's configuration schema."""
        pass

    @abstractmethod
    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        """
        Fetch data from the connector.

        Args:
            endpoint: API endpoint to fetch
            params: Query parameters

        Returns:
            ConnectorResult with normalized data
        """
        pass

    async def initialize(self) -> bool:
        """Initialize the connector (create session, validate credentials)."""
        try:
            await self._do_initialize()
            return True
        except Exception:
            return False

    async def _do_initialize(self) -> None:
        """Override for custom initialization."""
        pass

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._session:
            await self._session.close()
            self._session = None

    def _check_rate_limit(self) -> None:
        """Check if rate limit allows request."""
        config = self.get_config()
        if not config.rate_limit:
            return

        # Simple rate limiting check
        # In production, use Redis for distributed rate limiting
        pass

    def to_tool_definition(self) -> Dict[str, Any]:
        """Convert connector to a tool definition."""
        config = self.get_config()
        return {
            'type': 'connector',
            'name': config.name,
            'description': config.description,
            'base_url': config.base_url,
            'endpoints': self._get_endpoint_definitions(),
        }

    def _get_endpoint_definitions(self) -> List[Dict[str, Any]]:
        """Override to provide endpoint definitions."""
        return []
