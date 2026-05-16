# Aethera Plugin Specification

This document describes how to create new plugins for the Aethera platform.

## Overview

Aethera plugins extend the platform by integrating with external services and APIs. Each plugin lives in its own sub-module directory under `plugins/` and can be imported independently.

## Directory Structure

```
plugins/
  plugin_base.py          # Base class and result types
  plugin_registry.py      # Auto-discovery and registration
  cloudflare/             # Cloudflare sub-module
    __init__.py
    dns_manager.py
    tunnel_manager.py
    ...
  github/                 # GitHub sub-module
    __init__.py
    repos.py
    issues.py
    ...
  email/                  # Email sub-module
    __init__.py
    reader.py
    composer.py
    ...
  calendar/               # Calendar sub-module
    __init__.py
    caldav_client.py
    scheduler.py
  database/               # Database sub-module
    __init__.py
    sqlite_connector.py
    postgres_connector.py
    csv_connector.py
  notifications/          # Notifications sub-module
    __init__.py
    telegram_bot.py
    webhook.py
    browser_push.py
  PLUGIN_SPEC.md          # This file
```

## Creating a New Plugin

### 1. Option A: Full Plugin (integrates with the AetheraPlugin base class)

Create a new Python file in an appropriate sub-directory. Your plugin class must inherit from `AetheraPlugin` and implement the required methods.

```python
from ..plugin_base import AetheraPlugin, PluginConfig, PluginParameter, PluginResult
from typing import Any, Dict


class MyPlugin(AetheraPlugin):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key', '')

    def get_config(self) -> PluginConfig:
        return PluginConfig(
            name='my_plugin',
            version='1.0.0',
            description='What my plugin does',
            author='Your Name',
            parameters=[
                PluginParameter(
                    name='action',
                    type='action',
                    description='Action to perform',
                    required=True,
                    choices=['do_thing', 'do_other'],
                ),
            ],
            permissions=['my_plugin:read'],
            dependencies=['aiohttp'],
        )

    async def _do_initialize(self) -> None:
        # Validate credentials, open connections, etc.
        if not self.api_key:
            raise ValueError("API key is required")

    async def cleanup(self) -> None:
        # Close connections, release resources
        await super().cleanup()

    async def execute(self, action: str, parameters: Dict[str, Any]) -> PluginResult:
        if action == 'do_thing':
            result = await self._do_thing(parameters)
            return PluginResult(success=True, data=result)
        elif action == 'do_other':
            result = await self._do_other(parameters)
            return PluginResult(success=True, data=result)
        return PluginResult(success=False, error=f"Unknown action: {action}")

    async def _do_thing(self, params: Dict) -> Dict:
        # Implementation
        return {"status": "done"}

    async def _do_other(self, params: Dict) -> Dict:
        # Implementation
        return {"status": "also done"}


def register_plugin():
    import os
    return MyPlugin, {
        'api_key': os.getenv('MY_PLUGIN_API_KEY', ''),
        'enabled': True,
    }
```

### 2. Option B: Standalone Module (importable independently)

Create a standalone class that manages its own HTTP session lifecycle. This is the pattern used for sub-module classes.

```python
from typing import Any, Dict, List, Optional
import aiohttp


class MyManager:
    BASE_URL = "https://api.example.com/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def list_items(self) -> List[Dict]:
        session = await self._ensure_session()
        async with session.get(f"{self.BASE_URL}/items") as resp:
            return await resp.json()
```

### 3. Package Init File

Every sub-module directory must have an `__init__.py` that exports its classes:

```python
from .dns_manager import DNSManager
from .tunnel_manager import TunnelManager

__all__ = ["DNSManager", "TunnelManager"]
__version__ = "1.0.0"
```

## Key Design Principles

1. **Independent Importability**: Each module must be importable without requiring the AetheraPlugin base class. Sub-module classes manage their own sessions.

2. **Async-First**: All I/O operations must be async. Use `aiohttp` or `httpx` for HTTP calls. Use `asyncio.run_in_executor` for blocking operations (IMAP, SQLite, etc.).

3. **Session Lifecycle**: Manage HTTP sessions with `_ensure_session()` / `close()` patterns. Sessions are created lazily and must be explicitly closed.

4. **Structured Results**: Return typed dicts with consistent keys. Use `PluginResult` when integrating with the base class.

5. **Error Handling**: Raise exceptions for programming errors. Return error results (PluginResult with success=False) for runtime failures.

6. **No Hardcoded Secrets**: All credentials come from configuration or environment variables. Never store secrets in code.

7. **Type Annotations**: All public methods must have full type annotations for parameters and return types.

## HTTP Client Guidelines

- Use `aiohttp.ClientSession` for async HTTP operations
- Create sessions lazily via `_ensure_session()`
- Set appropriate headers (Authorization, Content-Type, Accept)
- Handle rate limiting with exponential backoff
- Close sessions in `close()` method

## Environment Variables

Plugins read credentials from environment variables. Follow these naming conventions:

| Plugin      | Variables                              |
|-------------|----------------------------------------|
| Cloudflare  | CLOUDFLARE_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_ZONE_ID |
| GitHub      | GITHUB_TOKEN                           |
| Email       | EMAIL_PROVIDER, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, FROM_EMAIL, EMAIL_API_KEY |
| Calendar    | CALENDAR_PROVIDER, GOOGLE_CALENDAR_TOKEN, MICROSOFT_ACCESS_TOKEN |
| Database    | DATABASE_URL (PostgreSQL)             |
| Telegram    | TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID   |

## Registration

Full plugins must provide a `register_plugin()` function at module level:

```python
def register_plugin():
    import os
    return MyPlugin, {
        'api_key': os.getenv('MY_PLUGIN_API_KEY', ''),
        'enabled': True,
    }
```

The PluginRegistry discovers plugins by:
1. Scanning plugin directories for Python files
2. Importing each module
3. Looking for the `register_plugin()` function
4. Calling it to get the plugin class and default config
5. Registering the plugin instance

## Testing

Each module should be testable in isolation:

```python
# Test standalone module
manager = DNSManager(api_key="test", zone_id="zone123")
result = await manager.list_records()
await manager.close()
```

## Available Sub-Modules

| Package        | Modules                                     |
|----------------|---------------------------------------------|
| cloudflare     | dns_manager, tunnel_manager, pages_manager, workers_manager, analytics, security, access_manager, r2_storage |
| github         | repos, issues, actions, code_review        |
| email          | reader, composer, auto_processor, templates |
| calendar       | caldav_client, scheduler                    |
| database       | sqlite_connector, postgres_connector, csv_connector |
| notifications  | telegram_bot, webhook, browser_push        |