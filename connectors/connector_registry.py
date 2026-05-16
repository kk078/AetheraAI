"""
Aethera Connector Registry
Manages data source connectors.
"""
import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from .connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class ConnectorRegistry:
    """Registry for discovering and managing connectors."""

    _instance: Optional['ConnectorRegistry'] = None

    def __new__(cls) -> 'ConnectorRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._connectors: Dict[str, AetheraConnector] = {}
        self._connector_configs: Dict[str, ConnectorConfig] = {}
        self._connector_dir = Path(__file__).parent
        self._initialized = True

    def register(self, connector_class: Type[AetheraConnector], config: Dict[str, Any]) -> bool:
        """Register a connector instance."""
        try:
            connector = connector_class(config)
            connector_config = connector.get_config()

            self._connectors[connector_config.name] = connector
            self._connector_configs[connector_config.name] = connector_config

            return True
        except Exception as e:
            print(f"Failed to register connector: {e}")
            return False

    def unregister(self, connector_name: str) -> bool:
        """Unregister a connector by name."""
        if connector_name in self._connectors:
            connector = self._connectors[connector_name]
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(connector.cleanup())
                else:
                    loop.run_until_complete(connector.cleanup())
            except Exception:
                pass

            del self._connectors[connector_name]
            del self._connector_configs[connector_name]
            return True
        return False

    def get_connector(self, name: str) -> Optional[AetheraConnector]:
        """Get a connector instance by name."""
        return self._connectors.get(name)

    def get_connector_config(self, name: str) -> Optional[ConnectorConfig]:
        """Get a connector's configuration schema."""
        return self._connector_configs.get(name)

    def list_connectors(self) -> List[Dict[str, Any]]:
        """List all registered connectors."""
        return [
            {
                'name': name,
                'config': config,
            }
            for name, config in self._connector_configs.items()
        ]

    async def fetch(self, connector_name: str, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        """Fetch data from a connector."""
        connector = self.get_connector(connector_name)
        if not connector:
            return ConnectorResult(
                success=False,
                error=f"Connector '{connector_name}' not found"
            )

        try:
            return await connector.fetch(endpoint, params)
        except Exception as e:
            return ConnectorResult(
                success=False,
                error=str(e)
            )

    def load_connectors(self, config: Dict[str, Dict[str, Any]]) -> int:
        """
        Load connectors from configuration.

        Returns:
            Number of connectors loaded
        """
        loaded = 0
        connector_map = {
            'npi': 'connectors.npi_connector',
            'cms': 'connectors.cms_connector',
            'openfda': 'connectors.openfda_connector',
            'pubmed': 'connectors.pubmed_connector',
            'rxnorm': 'connectors.rxnorm_connector',
            'fhir': 'connectors.fhir_connector',
        }

        for connector_name, connector_config in config.items():
            module_path = connector_map.get(connector_name)
            if not module_path:
                continue

            try:
                module = importlib.import_module(module_path)
                if hasattr(module, 'register_connector'):
                    connector_class, _ = module.register_connector()
                    if self.register(connector_class, connector_config):
                        loaded += 1
            except ImportError as e:
                print(f"Connector {connector_name} module not found: {e}")
            except Exception as e:
                print(f"Failed to load connector {connector_name}: {e}")

        return loaded


# Global registry instance
registry = ConnectorRegistry()


def get_registry() -> ConnectorRegistry:
    """Get the global connector registry instance."""
    return registry
