"""
Notifications Plugin Package for Aethera

Sub-modules:
    telegram_bot        - Telegram notifications via Bot API
    webhook             - Generic webhook notifications
    browser_push        - Web push notifications via PWA
    notifications_plugin - Unified multi-channel orchestrator
"""

from .telegram_bot import TelegramBot
from .webhook import WebhookNotifier
from .browser_push import BrowserPushNotifier
from .notifications_plugin import NotificationsPlugin

__all__ = [
    "TelegramBot",
    "WebhookNotifier",
    "BrowserPushNotifier",
    "NotificationsPlugin",
]

__version__ = "1.0.0"