"""
Aethera Plugin Registry
Auto-discovers and manages plugins.
"""
import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from .plugin_base import AetheraPlugin, PluginConfig, PluginResult


class PluginRegistry:
    """
    Registry for discovering and managing Aethera plugins.

    Plugins are auto-discovered from the plugins/healthcare/, plugins/cloud/, etc. directories.
    """

    _instance: Optional['PluginRegistry'] = None

    def __new__(cls) -> 'PluginRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._plugins: Dict[str, AetheraPlugin] = {}
        self._plugin_configs: Dict[str, PluginConfig] = {}
        self._plugin_dir = Path(__file__).parent
        self._initialized = True

    def register(self, plugin_class: Type[AetheraPlugin], config: Dict[str, Any]) -> bool:
        """
        Register a plugin instance.

        Args:
            plugin_class: The plugin class (not instance)
            config: Configuration for the plugin

        Returns:
            True if registration successful
        """
        try:
            # Create plugin instance
            plugin = plugin_class(config)

            # Get plugin config
            plugin_config = plugin.get_config()

            # Register
            self._plugins[plugin_config.name] = plugin
            self._plugin_configs[plugin_config.name] = plugin_config

            return True
        except Exception as e:
            print(f"Failed to register plugin: {e}")
            return False

    def unregister(self, plugin_name: str) -> bool:
        """Unregister a plugin by name."""
        if plugin_name in self._plugins:
            plugin = self._plugins[plugin_name]
            # Cleanup
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(plugin.cleanup())
                else:
                    loop.run_until_complete(plugin.cleanup())
            except Exception:
                pass

            del self._plugins[plugin_name]
            del self._plugin_configs[plugin_name]
            return True
        return False

    def get_plugin(self, name: str) -> Optional[AetheraPlugin]:
        """Get a plugin instance by name."""
        return self._plugins.get(name)

    def get_plugin_config(self, name: str) -> Optional[PluginConfig]:
        """Get a plugin's configuration schema."""
        return self._plugin_configs.get(name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins."""
        return [
            {
                'name': name,
                'config': config,
                'enabled': self._plugins[name].enabled,
            }
            for name, config in self._plugin_configs.items()
        ]

    def get_capabilities(self) -> Dict[str, List[str]]:
        """Get all plugin capabilities grouped by plugin."""
        capabilities = {}
        for name, plugin in self._plugins.items():
            if plugin.enabled:
                config = self.get_plugin_config(name)
                capabilities[name] = [p.name for p in config.parameters if p.type == 'action']
        return capabilities

    async def execute_plugin(self, plugin_name: str, action: str, parameters: Dict[str, Any]) -> PluginResult:
        """
        Execute a plugin action.

        Args:
            plugin_name: Name of the plugin
            action: Action to perform
            parameters: Action parameters

        Returns:
            PluginResult
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return PluginResult(
                success=False,
                error=f"Plugin '{plugin_name}' not found"
            )

        if not plugin.enabled:
            return PluginResult(
                success=False,
                error=f"Plugin '{plugin_name}' is disabled"
            )

        if not plugin._initialized:
            initialized = await plugin.initialize()
            if not initialized:
                return PluginResult(
                    success=False,
                    error=f"Failed to initialize plugin '{plugin_name}'"
                )

        try:
            return await plugin.execute(action, parameters)
        except Exception as e:
            return PluginResult(
                success=False,
                error=str(e)
            )

    def discover_plugins(self, subdirectory: Optional[str] = None) -> int:
        """
        Auto-discover plugins from the plugin directory.

        Args:
            subdirectory: Optional subdirectory to search (e.g., 'healthcare', 'cloud')

        Returns:
            Number of plugins discovered
        """
        if subdirectory:
            plugin_path = self._plugin_dir / subdirectory
        else:
            plugin_path = self._plugin_dir

        if not plugin_path.exists():
            return 0

        discovered = 0
        for file in plugin_path.glob('*.py'):
            if file.name.startswith('_') or file.name == 'plugin_base.py':
                continue

            module_name = f"plugins.{subdirectory}.{file.stem}" if subdirectory else f"plugins.{file.stem}"

            try:
                # Import the module
                spec = importlib.util.spec_from_file_location(module_name, file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    # Look for register_plugin function
                    if hasattr(module, 'register_plugin'):
                        register_func = module.register_plugin
                        plugin_class, config = register_func()
                        if self.register(plugin_class, config):
                            discovered += 1

            except Exception as e:
                print(f"Failed to load plugin {file.name}: {e}")

        return discovered

    def load_from_config(self, config: Dict[str, Dict[str, Any]]) -> int:
        """
        Load plugins from configuration.

        Args:
            config: Dictionary of plugin configurations {plugin_name: {config}}

        Returns:
            Number of plugins loaded
        """
        loaded = 0
        for plugin_name, plugin_config in config.items():
            # Try to import the plugin module
            try:
                # Determine module path based on plugin type
                if plugin_name.startswith('cloudflare'):
                    module_path = f"plugins.cloud.cloudflare_plugin"
                elif plugin_name.startswith('github'):
                    module_path = f"plugins.dev.github_plugin"
                elif plugin_name.startswith('email'):
                    module_path = f"plugins.communication.email_plugin"
                elif plugin_name.startswith('calendar'):
                    module_path = f"plugins.communication.calendar_plugin"
                else:
                    continue

                module = importlib.import_module(module_path)

                if hasattr(module, 'register_plugin'):
                    plugin_class, _ = module.register_plugin()
                    if self.register(plugin_class, plugin_config):
                        loaded += 1

            except ImportError as e:
                print(f"Plugin {plugin_name} module not found: {e}")
            except Exception as e:
                print(f"Failed to load plugin {plugin_name}: {e}")

        return loaded


# Global registry instance
registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    """Get the global plugin registry instance."""
    return registry
