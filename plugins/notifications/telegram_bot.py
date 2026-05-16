"""
Telegram Bot Notifier for Aethera

Provides Telegram notification operations via the Bot API:
send messages, photos, files, and manage inline keyboards.
"""
from typing import Any, Dict, List, Optional

import aiohttp


class TelegramBot:
    """Send notifications via the Telegram Bot API."""

    BASE_URL = "https://api.telegram.org/bot{token}"

    def __init__(self, token: str, default_chat_id: str = ""):
        """
        Args:
            token:           Telegram Bot API token.
            default_chat_id: Default chat ID to send messages to.
        """
        self.token = token
        self.default_chat_id = default_chat_id
        self._session: Optional[aiohttp.ClientSession] = None

    # -- Session lifecycle --------------------------------------------------

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _api_url(self, method: str) -> str:
        return self.BASE_URL.format(token=self.token) + f"/{method}"

    async def _request(self, method: str, data: Dict[str, Any]) -> Dict:
        """Make a Telegram Bot API request."""
        session = await self._ensure_session()
        url = self._api_url(method)
        async with session.post(url, json=data) as resp:
            result = await resp.json()
            if not result.get("ok", False):
                description = result.get("description", "Unknown error")
                error_code = result.get("error_code", 0)
                raise Exception(f"Telegram API error ({error_code}): {description}")
            return result.get("result", {})

    async def _request_multipart(self, method: str, data: aiohttp.FormData) -> Dict:
        """Make a Telegram Bot API request with multipart/form-data."""
        session = await self._ensure_session()
        url = self._api_url(method)
        async with session.post(url, data=data) as resp:
            result = await resp.json()
            if not result.get("ok", False):
                description = result.get("description", "Unknown error")
                error_code = result.get("error_code", 0)
                raise Exception(f"Telegram API error ({error_code}): {description}")
            return result.get("result", {})

    # -- Bot Info -----------------------------------------------------------

    async def get_me(self) -> Dict:
        """Get bot information.

        Returns:
            Dict with bot details.
        """
        return await self._request("getMe", {})

    async def get_updates(self, offset: int = 0, limit: int = 100, timeout: int = 0) -> List[Dict]:
        """Get pending updates (messages, callbacks, etc.).

        Returns:
            List of update dicts.
        """
        result = await self._request("getUpdates", {
            "offset": offset,
            "limit": limit,
            "timeout": timeout,
        })
        return result if isinstance(result, list) else []

    # -- Send Text Messages -------------------------------------------------

    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
        disable_notification: bool = False,
        reply_to_message_id: Optional[int] = None,
    ) -> Dict:
        """Send a text message.

        Args:
            text:                   Message text.
            chat_id:                Target chat ID (uses default if None).
            parse_mode:             Parse mode: HTML, Markdown, MarkdownV2.
            disable_notification:   Send silently (no push notification sound).
            reply_to_message_id:    Message ID to reply to.

        Returns:
            Dict with sent message details.
        """
        target = chat_id or self.default_chat_id
        if not target:
            raise ValueError("No chat_id specified and no default_chat_id configured")

        data: Dict[str, Any] = {
            "chat_id": target,
            "text": text,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification,
        }
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        result = await self._request("sendMessage", data)
        return {
            "message_id": result.get("message_id"),
            "chat_id": result.get("chat", {}).get("id"),
            "date": result.get("date"),
        }

    async def send_message_with_keyboard(
        self,
        text: str,
        buttons: List[List[Dict[str, str]]],
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
        one_time_keyboard: bool = False,
        resize_keyboard: bool = True,
    ) -> Dict:
        """Send a message with an inline or reply keyboard.

        Args:
            text:               Message text.
            buttons:            2D list of button dicts. For inline: [{"text": "Label", "callback_data": "value"}].
                                For reply: [{"text": "Label"}].
            chat_id:            Target chat ID.
            parse_mode:         Parse mode.
            one_time_keyboard:  Whether the keyboard disappears after use.
            resize_keyboard:    Whether to resize the keyboard.

        Returns:
            Dict with sent message details.
        """
        target = chat_id or self.default_chat_id
        if not target:
            raise ValueError("No chat_id specified")

        # Determine keyboard type based on button structure
        first_button = buttons[0][0] if buttons and buttons[0] else {}
        if "callback_data" in first_button or "url" in first_button:
            keyboard = {"inline_keyboard": buttons}
        else:
            keyboard = {
                "keyboard": buttons,
                "one_time_keyboard": one_time_keyboard,
                "resize_keyboard": resize_keyboard,
            }

        data: Dict[str, Any] = {
            "chat_id": target,
            "text": text,
            "parse_mode": parse_mode,
            "reply_markup": keyboard,
        }

        result = await self._request("sendMessage", data)
        return {
            "message_id": result.get("message_id"),
            "chat_id": result.get("chat", {}).get("id"),
        }

    # -- Send Media ---------------------------------------------------------

    async def send_photo(
        self,
        photo_url: str,
        caption: str = "",
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
    ) -> Dict:
        """Send a photo.

        Args:
            photo_url:   URL of the photo to send.
            caption:     Photo caption.
            chat_id:     Target chat ID.
            parse_mode:  Caption parse mode.

        Returns:
            Dict with sent message details.
        """
        target = chat_id or self.default_chat_id
        if not target:
            raise ValueError("No chat_id specified")

        data: Dict[str, Any] = {
            "chat_id": target,
            "photo": photo_url,
            "parse_mode": parse_mode,
        }
        if caption:
            data["caption"] = caption

        result = await self._request("sendPhoto", data)
        return {"message_id": result.get("message_id"), "chat_id": result.get("chat", {}).get("id")}

    async def send_document(
        self,
        document_url: str,
        caption: str = "",
        chat_id: Optional[str] = None,
    ) -> Dict:
        """Send a document/file.

        Args:
            document_url: URL or file_id of the document.
            caption:      Document caption.
            chat_id:      Target chat ID.

        Returns:
            Dict with sent message details.
        """
        target = chat_id or self.default_chat_id
        if not target:
            raise ValueError("No chat_id specified")

        data: Dict[str, Any] = {
            "chat_id": target,
            "document": document_url,
        }
        if caption:
            data["caption"] = caption

        result = await self._request("sendDocument", data)
        return {"message_id": result.get("message_id"), "chat_id": result.get("chat", {}).get("id")}

    async def send_file(
        self,
        file_path: str,
        chat_id: Optional[str] = None,
        caption: str = "",
    ) -> Dict:
        """Send a local file as a document.

        Args:
            file_path: Local path to the file.
            chat_id:   Target chat ID.
            caption:   Document caption.

        Returns:
            Dict with sent message details.
        """
        import os
        target = chat_id or self.default_chat_id
        if not target:
            raise ValueError("No chat_id specified")
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        session = await self._ensure_session()
        url = self._api_url("sendDocument")
        data = aiohttp.FormData()
        data.add_field("chat_id", target)
        data.add_field("document", open(file_path, "rb"), filename=os.path.basename(file_path))
        if caption:
            data.add_field("caption", caption)

        async with session.post(url, data=data) as resp:
            result = await resp.json()
            if not result.get("ok", False):
                raise Exception(f"Telegram API error: {result.get('description', 'Unknown')}")
            msg = result.get("result", {})
            return {"message_id": msg.get("message_id"), "chat_id": msg.get("chat", {}).get("id")}

    # -- Message Management -------------------------------------------------

    async def delete_message(self, message_id: int, chat_id: Optional[str] = None) -> bool:
        """Delete a message.

        Returns:
            True on success.
        """
        target = chat_id or self.default_chat_id
        await self._request("deleteMessage", {"chat_id": target, "message_id": message_id})
        return True

    async def edit_message(
        self,
        message_id: int,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
    ) -> Dict:
        """Edit an existing message.

        Returns:
            Dict with edited message details.
        """
        target = chat_id or self.default_chat_id
        result = await self._request("editMessageText", {
            "chat_id": target,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        })
        return {"message_id": result.get("message_id")}

    # -- Chat Management ----------------------------------------------------

    async def get_chat(self, chat_id: Optional[str] = None) -> Dict:
        """Get chat information.

        Returns:
            Dict with chat details.
        """
        target = chat_id or self.default_chat_id
        return await self._request("getChat", {"chat_id": target})

    async def set_webhook(self, url: str, allowed_updates: Optional[List[str]] = None) -> bool:
        """Set a webhook for receiving updates.

        Args:
            url:             Webhook URL.
            allowed_updates: List of update types to receive.

        Returns:
            True on success.
        """
        data: Dict[str, Any] = {"url": url}
        if allowed_updates:
            data["allowed_updates"] = allowed_updates
        await self._request("setWebhook", data)
        return True

    async def delete_webhook(self) -> bool:
        """Remove the webhook.

        Returns:
            True on success.
        """
        await self._request("deleteWebhook", {})
        return True

    async def answer_callback_query(self, callback_query_id: str, text: str = "") -> bool:
        """Answer a callback query from an inline button press.

        Returns:
            True on success.
        """
        data: Dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            data["text"] = text
        await self._request("answerCallbackQuery", data)
        return True