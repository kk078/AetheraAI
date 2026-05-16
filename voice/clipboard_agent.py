"""
Aethera AI - Clipboard Agent (Voice Service Shim)

Re-exports from the canonical clipboard module at clipboard/clipboard_agent.py.
This file exists for backward compatibility with imports from the voice package.
"""
from clipboard.clipboard_agent import (
    ClipboardReader,
    ClipboardMonitor,
    AetheraAPIClient,
    DetectionHistory,
    NotificationHandler,
    ClipboardTrayApp,
)

__all__ = [
    "ClipboardReader",
    "ClipboardMonitor",
    "AetheraAPIClient",
    "DetectionHistory",
    "NotificationHandler",
    "ClipboardTrayApp",
]