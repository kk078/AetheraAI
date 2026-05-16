"""
Aethera AI - Plugin Tests

Tests for plugin system and plugin execution.
"""
import pytest
import sys
sys.path.insert(0, '..')

from plugins.plugin_registry import PluginRegistry, get_registry
from plugins.plugin_base import PluginConfig, PluginParameter, PluginResult, AetheraPlugin


class TestPluginBase:
    """Test plugin base class."""

    def test_plugin_config(self):
        """Test plugin configuration creation."""
        config = PluginConfig(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test",
            parameters=[
                PluginParameter(
                    name="action",
                    type="action",
                    description="Action to perform",
                    required=True,
                    choices=["action1", "action2"]
                )
            ]
        )

        assert config.name == "test_plugin"
        assert len(config.parameters) == 1

    def test_plugin_result(self):
        """Test plugin result creation."""
        result = PluginResult(
            success=True,
            data={"key": "value"},
            metadata={"processed": True}
        )

        assert result.success is True
        assert result.data["key"] == "value"
        assert result.error is None


class TestPluginRegistry:
    """Test plugin registry."""

    @pytest.fixture
    def registry(self):
        return PluginRegistry()

    def test_register_plugin(self, registry):
        """Test plugin registration."""
        # Create a mock plugin
        class MockPlugin(AetheraPlugin):
            def get_config(self):
                return PluginConfig(
                    name="mock_plugin",
                    version="1.0.0",
                    description="Mock plugin",
                    author="Test"
                )

            async def execute(self, action, parameters):
                return PluginResult(success=True, data={"action": action})

        plugin_class = MockPlugin
        config = {"enabled": True}

        result = registry.register(plugin_class, config)
        assert result is True

        # Verify registration
        plugin = registry.get_plugin("mock_plugin")
        assert plugin is not None

    def test_list_plugins(self, registry):
        """Test listing plugins."""
        plugins = registry.list_plugins()
        assert isinstance(plugins, list)

    def test_execute_plugin(self, registry):
        """Test plugin execution."""
        # Would require registered plugin
        # This tests error handling for unknown plugin
        result = asyncio.run(
            registry.execute_plugin("unknown_plugin", "action", {})
        )
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_get_capabilities(self, registry):
        """Test getting plugin capabilities."""
        capabilities = registry.get_capabilities()
        assert isinstance(capabilities, dict)


class TestCloudflarePlugin:
    """Test Cloudflare plugin (if available)."""

    @pytest.fixture
    def cloudflare_plugin(self):
        try:
            from plugins.cloud.cloudflare_plugin import CloudflarePlugin
            return CloudflarePlugin({
                "api_key": "test_key",
                "account_id": "test_account",
                "enabled": True
            })
        except ImportError:
            return None

    def test_cloudflare_config(self, cloudflare_plugin):
        """Test Cloudflare plugin configuration."""
        if cloudflare_plugin:
            config = cloudflare_plugin.get_config()
            assert config.name == "cloudflare"
            assert "action" in [p.name for p in config.parameters]


if __name__ == "__main__":
    import asyncio
    pytest.main([__file__, "-v"])
