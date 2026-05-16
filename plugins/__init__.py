"""
Aethera Plugins Package

Plugins extend Aethera's capabilities by integrating with external services.
Unlike skills (which perform computations), plugins interact with APIs and services.

Plugin categories:
    cloud          - Cloud infrastructure (Cloudflare)
    cloudflare     - Cloudflare services (DNS, Tunnels, Workers, R2, Security, Access, Pages, Analytics)
    communication  - Communication services (Email, Calendar)
    database       - Database connectors (SQLite, PostgreSQL, CSV)
    dev            - Developer tools (GitHub)
    email          - Email services (Reader, Composer, Templates, Auto-processor)
    github         - GitHub integration (Repos, Issues, Actions, Code Review)
    notifications  - Multi-channel notifications (Telegram, Webhook, Browser Push)
    user           - User-facing services
"""

from .plugin_base import AetheraPlugin, PluginConfig, PluginParameter, PluginResult
from .plugin_registry import PluginRegistry, get_registry

__all__ = [
    "AetheraPlugin",
    "PluginConfig",
    "PluginParameter",
    "PluginResult",
    "PluginRegistry",
    "get_registry",
]

__version__ = "1.0.0"