"""
Aethera Plugin Base Class
All plugins must inherit from this base class and implement the required methods.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PluginParameter(BaseModel):
    """Definition of a plugin parameter."""
    name: str
    type: str  # str, int, float, bool, list, dict
    description: str
    required: bool = False
    default: Any = None
    choices: Optional[List[Any]] = None


class PluginConfig(BaseModel):
    """Plugin configuration schema."""
    name: str
    version: str
    description: str
    author: str
    parameters: List[PluginParameter] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)  # e.g., ['read:email', 'write:files']
    dependencies: List[str] = Field(default_factory=list)  # Required pip packages


class PluginResult(BaseModel):
    """Standardized plugin execution result."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AetheraPlugin(ABC):
    """
    Base class for all Aethera plugins.

    Plugins extend Aethera's capabilities by integrating with external services.
    Unlike skills (which perform computations), plugins interact with APIs and services.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the plugin.

        Args:
            config: Plugin configuration including API keys and settings
        """
        self.config = config
        self.enabled = config.get('enabled', True)
        self._initialized = False

    @abstractmethod
    def get_config(self) -> PluginConfig:
        """Return the plugin's configuration schema."""
        pass

    @abstractmethod
    async def execute(self, action: str, parameters: Dict[str, Any]) -> PluginResult:
        """
        Execute a plugin action.

        Args:
            action: The action to perform (e.g., 'send_email', 'get_calendar_events')
            parameters: Action parameters

        Returns:
            PluginResult with success status and data
        """
        pass

    async def initialize(self) -> bool:
        """
        Initialize the plugin (connect to APIs, validate credentials, etc.).

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True

        try:
            await self._do_initialize()
            self._initialized = True
            return True
        except Exception as e:
            self._initialized = False
            return False

    async def _do_initialize(self) -> None:
        """Override this method for custom initialization logic."""
        pass

    async def cleanup(self) -> None:
        """Clean up resources (close connections, etc.)."""
        self._initialized = False

    def validate_parameters(self, action: str, parameters: Dict[str, Any]) -> Optional[str]:
        """
        Validate parameters against the plugin's schema.

        Returns:
            Error message if validation fails, None if valid
        """
        config = self.get_config()

        # Find action in parameters list
        action_param = None
        for param in config.parameters:
            if param.name == action:
                action_param = param
                break

        if action_param and action_param.choices and action not in action_param.choices:
            return f"Invalid action '{action}'. Valid actions: {action_param.choices}"

        return None

    def to_tool_definition(self) -> Dict[str, Any]:
        """Convert plugin to a tool definition for the orchestrator."""
        config = self.get_config()
        return {
            'type': 'plugin',
            'name': config.name,
            'description': config.description,
            'version': config.version,
            'actions': [p.name for p in config.parameters if p.type == 'action'],
            'parameters': [
                {
                    'name': p.name,
                    'type': p.type,
                    'description': p.description,
                    'required': p.required,
                }
                for p in config.parameters
            ],
        }
