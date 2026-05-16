"""
Aethera Notifications Plugin

Multi-channel notification orchestrator that unifies Telegram, webhooks,
and browser push notifications with priority levels, deduplication,
rate limiting, and delivery tracking.
"""

import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional
from collections import defaultdict

from ..plugin_base import AetheraPlugin, PluginConfig, PluginParameter, PluginResult


class NotificationsPlugin(AetheraPlugin):
    """
    Unified notification plugin supporting multiple channels.
    Routes notifications to Telegram, webhooks, and browser push
    based on priority, channel preferences, and rate limits.
    """

    # Priority levels
    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_URGENT = "urgent"

    # Channel types
    CHANNEL_TELEGRAM = "telegram"
    CHANNEL_WEBHOOK = "webhook"
    CHANNEL_BROWSER = "browser"
    CHANNEL_ALL = "all"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.telegram_bot = None
        self.webhook_notifier = None
        self.browser_push = None
        self._delivery_log: List[Dict[str, Any]] = []
        self._dedup_cache: Dict[str, float] = {}
        self._rate_limits: Dict[str, List[float]] = defaultdict(list)
        self._max_delivery_log = 1000
        self._dedup_window = 300  # 5 minutes
        self._rate_limit_per_channel = 60  # max 60 per minute per channel

    def get_config(self) -> PluginConfig:
        return PluginConfig(
            name="notifications",
            version="1.0.0",
            description="Multi-channel notification system: Telegram, webhooks, browser push",
            author="Aethera AI",
            parameters=[
                PluginParameter(
                    name="send",
                    type="action",
                    description="Send a notification through one or more channels",
                    required=True,
                ),
                PluginParameter(
                    name="send_batch",
                    type="action",
                    description="Send multiple notifications at once",
                ),
                PluginParameter(
                    name="list_channels",
                    type="action",
                    description="List available notification channels and their status",
                ),
                PluginParameter(
                    name="get_delivery_log",
                    type="action",
                    description="Get recent notification delivery history",
                ),
                PluginParameter(
                    name="test_channel",
                    type="action",
                    description="Send a test notification to verify a channel works",
                ),
                PluginParameter(
                    name="message",
                    type="str",
                    description="Notification message text",
                    required=True,
                ),
                PluginParameter(
                    name="title",
                    type="str",
                    description="Notification title/subject",
                ),
                PluginParameter(
                    name="channels",
                    type="list",
                    description="Target channels: telegram, webhook, browser, or all",
                    default=["all"],
                ),
                PluginParameter(
                    name="priority",
                    type="str",
                    description="Priority level: low, normal, high, urgent",
                    default="normal",
                    choices=["low", "normal", "high", "urgent"],
                ),
                PluginParameter(
                    name="deduplicate",
                    type="bool",
                    description="Deduplicate identical messages within the dedup window",
                    default=True,
                ),
                PluginParameter(
                    name="metadata",
                    type="dict",
                    description="Additional metadata to include with the notification",
                ),
            ],
            permissions=["send:telegram", "send:webhook", "send:browser_push"],
            dependencies=["aiohttp"],
        )

    async def _do_initialize(self) -> None:
        """Initialize notification sub-channels."""
        # Telegram bot
        telegram_token = self.config.get("telegram_token") or self.config.get("TELEGRAM_BOT_TOKEN", "")
        if telegram_token:
            try:
                from notifications.telegram_bot import TelegramBot
                self.telegram_bot = TelegramBot({"token": telegram_token})
                await self.telegram_bot.initialize() if hasattr(self.telegram_bot, 'initialize') else None
            except ImportError:
                self.telegram_bot = None

        # Webhook notifier
        webhook_urls = self.config.get("webhook_urls", [])
        if webhook_urls:
            try:
                from notifications.webhook import WebhookNotifier
                self.webhook_notifier = WebhookNotifier({"urls": webhook_urls})
            except ImportError:
                self.webhook_notifier = None

        # Browser push
        vapid_private_key = self.config.get("vapid_private_key") or self.config.get("VAPID_PRIVATE_KEY", "")
        vapid_public_key = self.config.get("vapid_public_key") or self.config.get("VAPID_PUBLIC_KEY", "")
        vapid_subject = self.config.get("vapid_subject", "mailto:admin@aethera.ai")
        if vapid_private_key:
            try:
                from notifications.browser_push import BrowserPushNotifier
                self.browser_push = BrowserPushNotifier({
                    "vapid_private_key": vapid_private_key,
                    "vapid_public_key": vapid_public_key,
                    "vapid_subject": vapid_subject,
                })
            except ImportError:
                self.browser_push = None

    async def cleanup(self) -> None:
        """Clean up notification resources."""
        if self.webhook_notifier and hasattr(self.webhook_notifier, 'close'):
            await self.webhook_notifier.close()
        if self.telegram_bot and hasattr(self.telegram_bot, 'close'):
            await self.telegram_bot.close()
        self._initialized = False

    async def execute(self, action: str, parameters: Dict[str, Any]) -> PluginResult:
        """Execute a notification action."""
        if action == "send":
            return await self._send_notification(parameters)
        elif action == "send_batch":
            return await self._send_batch(parameters)
        elif action == "list_channels":
            return self._list_channels()
        elif action == "get_delivery_log":
            return self._get_delivery_log(parameters)
        elif action == "test_channel":
            return await self._test_channel(parameters)
        else:
            return PluginResult(success=False, error=f"Unknown action: {action}")

    async def _send_notification(self, params: Dict[str, Any]) -> PluginResult:
        """Send a single notification through specified channels."""
        message = params.get("message", "")
        title = params.get("title", "")
        channels = params.get("channels", ["all"])
        priority = params.get("priority", "normal")
        deduplicate = params.get("deduplicate", True)
        metadata = params.get("metadata", {})

        if not message:
            return PluginResult(success=False, error="Message is required")

        # Deduplication check
        if deduplicate:
            msg_hash = self._hash_message(message, title, priority)
            if msg_hash in self._dedup_cache:
                last_sent = self._dedup_cache[msg_hash]
                if time.time() - last_sent < self._dedup_window:
                    return PluginResult(
                        success=True,
                        data={"status": "deduplicated", "message_hash": msg_hash},
                        metadata={"reason": f"Duplicate message suppressed (sent {int(time.time() - last_sent)}s ago)"}
                    )
            self._dedup_cache[msg_hash] = time.time()
            self._prune_dedup_cache()

        # Resolve "all" to available channels
        target_channels = self._resolve_channels(channels, priority)

        results = {}
        for channel in target_channels:
            # Rate limit check
            if not self._check_rate_limit(channel):
                results[channel] = {"status": "rate_limited", "detail": "Too many notifications, try again later"}
                continue

            try:
                if channel == self.CHANNEL_TELEGRAM and self.telegram_bot:
                    results[channel] = await self._send_telegram(message, title, priority, metadata)
                elif channel == self.CHANNEL_WEBHOOK and self.webhook_notifier:
                    results[channel] = await self._send_webhook(message, title, priority, metadata)
                elif channel == self.CHANNEL_BROWSER and self.browser_push:
                    results[channel] = await self._send_browser_push(message, title, priority, metadata)
                else:
                    results[channel] = {"status": "unavailable", "detail": f"Channel {channel} not configured"}
            except Exception as e:
                results[channel] = {"status": "error", "detail": str(e)}

            # Log delivery
            self._log_delivery(channel, message, title, priority, results.get(channel, {}))

        # Determine overall success
        successful = sum(1 for r in results.values() if r.get("status") == "sent")
        total = len(target_channels)

        return PluginResult(
            success=successful > 0,
            data={
                "message_id": self._hash_message(message, title, priority)[:12],
                "channels_targeted": total,
                "channels_sent": successful,
                "results": results,
            },
            metadata={"priority": priority}
        )

    async def _send_batch(self, params: Dict[str, Any]) -> PluginResult:
        """Send multiple notifications at once."""
        notifications = params.get("notifications", [])
        if not notifications:
            return PluginResult(success=False, error="notifications list is required")

        results = []
        for notif in notifications:
            result = await self._send_notification(notif)
            results.append({
                "message": notif.get("message", "")[:50],
                "success": result.success,
                "data": result.data,
            })

        sent = sum(1 for r in results if r["success"])
        return PluginResult(
            success=sent > 0,
            data={
                "total": len(notifications),
                "sent": sent,
                "failed": len(notifications) - sent,
                "results": results,
            }
        )

    def _list_channels(self) -> PluginResult:
        """List available notification channels."""
        channels = []
        if self.telegram_bot:
            channels.append({
                "channel": self.CHANNEL_TELEGRAM,
                "status": "configured",
                "details": {"has_token": bool(self.config.get("telegram_token") or self.config.get("TELEGRAM_BOT_TOKEN"))}
            })
        else:
            channels.append({
                "channel": self.CHANNEL_TELEGRAM,
                "status": "not_configured",
                "details": {"reason": "No TELEGRAM_BOT_TOKEN set"}
            })

        webhook_urls = self.config.get("webhook_urls", [])
        if self.webhook_notifier:
            channels.append({
                "channel": self.CHANNEL_WEBHOOK,
                "status": "configured",
                "details": {"url_count": len(webhook_urls)}
            })
        elif webhook_urls:
            channels.append({
                "channel": self.CHANNEL_WEBHOOK,
                "status": "error",
                "details": {"reason": "WebhookNotifier failed to initialize"}
            })
        else:
            channels.append({
                "channel": self.CHANNEL_WEBHOOK,
                "status": "not_configured",
                "details": {"reason": "No webhook_urls set"}
            })

        vapid_key = self.config.get("vapid_private_key") or self.config.get("VAPID_PRIVATE_KEY", "")
        if self.browser_push:
            channels.append({
                "channel": self.CHANNEL_BROWSER,
                "status": "configured",
                "details": {"has_vapid_key": bool(vapid_key)}
            })
        elif vapid_key:
            channels.append({
                "channel": self.CHANNEL_BROWSER,
                "status": "error",
                "details": {"reason": "BrowserPushNotifier failed to initialize"}
            })
        else:
            channels.append({
                "channel": self.CHANNEL_BROWSER,
                "status": "not_configured",
                "details": {"reason": "No VAPID_PRIVATE_KEY set"}
            })

        return PluginResult(
            success=True,
            data={"channels": channels, "total_configured": sum(1 for c in channels if c["status"] == "configured")}
        )

    def _get_delivery_log(self, params: Dict[str, Any]) -> PluginResult:
        """Get recent notification delivery history."""
        limit = min(params.get("limit", 50), 200)
        channel_filter = params.get("channel")

        entries = self._delivery_log
        if channel_filter:
            entries = [e for e in entries if e["channel"] == channel_filter]

        return PluginResult(
            success=True,
            data={
                "entries": entries[-limit:],
                "total": len(self._delivery_log),
                "showing": min(limit, len(entries))
            }
        )

    async def _test_channel(self, params: Dict[str, Any]) -> PluginResult:
        """Send a test notification to a specific channel."""
        channel = params.get("channel", "all")
        test_message = params.get("message", "Aethera notification test - if you see this, the channel is working!")
        return await self._send_notification({
            "message": test_message,
            "title": "Test Notification",
            "channels": [channel],
            "priority": "normal",
            "deduplicate": False,
        })

    # ------------------------------------------------------------------
    # Channel-specific send methods
    # ------------------------------------------------------------------

    async def _send_telegram(self, message: str, title: str, priority: str, metadata: Dict) -> Dict:
        """Send notification via Telegram bot."""
        priority_emoji = {
            "low": "📝",
            "normal": "💬",
            "high": "⚠️",
            "urgent": "🚨",
        }
        emoji = priority_emoji.get(priority, "💬")

        text_parts = []
        if title:
            text_parts.append(f"{emoji} *{title}*")
        text_parts.append(message)
        if metadata:
            for key, value in metadata.items():
                text_parts.append(f"_{key}: {value}_")

        text = "\n".join(text_parts)

        chat_id = self.config.get("telegram_chat_id") or self.config.get("TELEGRAM_CHAT_ID", "")
        if not chat_id:
            return {"status": "error", "detail": "No TELEGRAM_CHAT_ID configured"}

        try:
            result = await self.telegram_bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
            return {"status": "sent", "channel": "telegram", "message_id": result.get("message_id")}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    async def _send_webhook(self, message: str, title: str, priority: str, metadata: Dict) -> Dict:
        """Send notification via webhook."""
        payload = {
            "message": message,
            "title": title,
            "priority": priority,
            "timestamp": time.time(),
            "source": "aethera",
            **metadata,
        }

        try:
            result = await self.webhook_notifier.send(payload, event_type="notification")
            return {"status": "sent", "channel": "webhook", "detail": str(result)[:100]}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    async def _send_browser_push(self, message: str, title: str, priority: str, metadata: Dict) -> Dict:
        """Send notification via browser push."""
        subscriptions = self.config.get("push_subscriptions", [])
        if not subscriptions:
            return {"status": "unavailable", "detail": "No push subscriptions registered"}

        try:
            results = await self.browser_push.send_batch(
                subscriptions=subscriptions,
                title=title or "Aethera Notification",
                body=message,
                data=metadata,
                tag=f"aethera-{priority}",
            )
            sent = sum(1 for r in results if r.get("success"))
            return {"status": "sent", "channel": "browser", "sent": sent, "total": len(subscriptions)}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_channels(self, channels: List[str], priority: str) -> List[str]:
        """Resolve channel list, expanding 'all' and handling priority escalation."""
        if "all" in channels or self.CHANNEL_ALL in channels:
            resolved = []
            if self.telegram_bot:
                resolved.append(self.CHANNEL_TELEGRAM)
            if self.webhook_notifier:
                resolved.append(self.CHANNEL_WEBHOOK)
            if self.browser_push:
                resolved.append(self.CHANNEL_BROWSER)
            return resolved or [self.CHANNEL_WEBHOOK]

        # Urgent priority adds all available channels regardless of specification
        if priority == self.PRIORITY_URGENT:
            resolved = list(set(channels))
            if self.telegram_bot and self.CHANNEL_TELEGRAM not in resolved:
                resolved.append(self.CHANNEL_TELEGRAM)
            return resolved

        return [ch for ch in channels if ch in [self.CHANNEL_TELEGRAM, self.CHANNEL_WEBHOOK, self.CHANNEL_BROWSER]]

    def _check_rate_limit(self, channel: str) -> bool:
        """Check if the channel is within rate limits."""
        now = time.time()
        window = 60  # 1 minute window
        max_per_window = self._rate_limit_per_channel

        # Clean old entries
        self._rate_limits[channel] = [t for t in self._rate_limits[channel] if now - t < window]

        if len(self._rate_limits[channel]) >= max_per_window:
            return False

        self._rate_limits[channel].append(now)
        return True

    def _hash_message(self, message: str, title: str, priority: str) -> str:
        """Generate a dedup hash for a message."""
        content = f"{title}:{message}:{priority}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _prune_dedup_cache(self):
        """Remove expired entries from the dedup cache."""
        now = time.time()
        expired = [k for k, v in self._dedup_cache.items() if now - v > self._dedup_window]
        for k in expired:
            del self._dedup_cache[k]

    def _log_delivery(self, channel: str, message: str, title: str, priority: str, result: Dict):
        """Log a notification delivery."""
        entry = {
            "timestamp": time.time(),
            "channel": channel,
            "priority": priority,
            "title": title,
            "message_preview": message[:100],
            "result": result,
        }
        self._delivery_log.append(entry)
        # Trim log
        if len(self._delivery_log) > self._max_delivery_log:
            self._delivery_log = self._delivery_log[-self._max_delivery_log:]


def register_plugin():
    """Register the notifications plugin."""
    import os
    return NotificationsPlugin, {
        "telegram_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
        "webhook_urls": os.getenv("WEBHOOK_URLS", "").split(",") if os.getenv("WEBHOOK_URLS") else [],
        "vapid_private_key": os.getenv("VAPID_PRIVATE_KEY", ""),
        "vapid_public_key": os.getenv("VAPID_PUBLIC_KEY", ""),
        "vapid_subject": os.getenv("VAPID_SUBJECT", "mailto:admin@aethera.ai"),
        "push_subscriptions": [],
        "enabled": True,
    }