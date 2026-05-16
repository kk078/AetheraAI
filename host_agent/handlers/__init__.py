"""
Aethera AI — Host Agent Handler Registry
Maps action prefixes to handler classes.
"""
from typing import Dict, Type, Optional

from .filesystem import FilesystemHandler
from .app_launcher import AppLauncherHandler
from .shell_executor import ShellExecutorHandler
from .screen_capture import ScreenCaptureHandler
from .clipboard import ClipboardHandler
from .system_monitor import SystemMonitorHandler
from .browser import BrowserHandler


# Action prefix -> handler class mapping
HANDLER_MAP: Dict[str, Type] = {
    "filesystem": FilesystemHandler,
    "app": AppLauncherHandler,
    "shell": ShellExecutorHandler,
    "screen": ScreenCaptureHandler,
    "clipboard": ClipboardHandler,
    "system": SystemMonitorHandler,
    "browser": BrowserHandler,
}


def get_handler(action: str) -> Optional[object]:
    """
    Get the appropriate handler for an action string.

    Args:
        action: Action string like "filesystem.browse" or "system.stats"

    Returns:
        Handler instance or None if no handler matches
    """
    prefix = action.split(".")[0] if "." in action else action
    handler_class = HANDLER_MAP.get(prefix)
    if handler_class is None:
        return None
    return handler_class()