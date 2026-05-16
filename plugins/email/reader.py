"""
Email Reader for Aethera

Provides read, search, and categorize operations for emails via IMAP.
Works with Gmail, Outlook, and any IMAP-capable server.
"""
import asyncio
import email
import imaplib
from email.header import decode_header
from email.utils import parseaddr
from typing import Any, Dict, List, Optional, Tuple


class EmailReader:
    """Read, search, and categorize emails via IMAP."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 993,
        use_ssl: bool = True,
    ):
        """
        Args:
            host:     IMAP server hostname.
            username: Email account username.
            password: Email account password or app-specific password.
            port:     IMAP port (default 993 for SSL).
            use_ssl:  Whether to use SSL/TLS.
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.use_ssl = use_ssl
        self._connection: Optional[imaplib.IMAP4_SSL] = None

    # -- Connection lifecycle ------------------------------------------------

    async def connect(self) -> None:
        """Connect and authenticate to the IMAP server."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._connect_sync)

    def _connect_sync(self) -> None:
        if self.use_ssl:
            self._connection = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            self._connection = imaplib.IMAP4(self.host, self.port)
        self._connection.login(self.username, self.password)

    async def disconnect(self) -> None:
        """Logout and close the IMAP connection."""
        if self._connection:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._disconnect_sync)

    def _disconnect_sync(self) -> None:
        try:
            self._connection.close()
        except Exception:
            pass
        try:
            self._connection.logout()
        except Exception:
            pass
        self._connection = None

    async def _ensure_connected(self) -> imaplib.IMAP4_SSL:
        if self._connection is None:
            await self.connect()
        return self._connection

    # -- Helper: decode header ----------------------------------------------

    @staticmethod
    def _decode_header_value(value: str) -> str:
        """Decode an email header value."""
        if not value:
            return ""
        decoded_parts = decode_header(value)
        result_parts = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result_parts.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                result_parts.append(part)
        return "".join(result_parts)

    @staticmethod
    def _parse_message(msg: email.message.Message) -> Dict[str, Any]:
        """Parse an email message into a structured dict."""
        subject = EmailReader._decode_header_value(msg.get("Subject", ""))
        from_header = msg.get("From", "")
        from_name, from_email_addr = parseaddr(from_header)
        from_name = EmailReader._decode_header_value(from_name)

        to_header = msg.get("To", "")
        cc_header = msg.get("Cc", "")
        date_header = msg.get("Date", "")
        message_id = msg.get("Message-ID", "")

        # Extract body
        body_text = ""
        body_html = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))
                if "attachment" in disposition:
                    continue
                if content_type == "text/plain":
                    body_text = part.get_payload(decode=True).decode("utf-8", errors="replace")
                elif content_type == "text/html":
                    body_html = part.get_payload(decode=True).decode("utf-8", errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                content_type = msg.get_content_type()
                decoded = payload.decode("utf-8", errors="replace")
                if content_type == "text/html":
                    body_html = decoded
                else:
                    body_text = decoded

        # Extract attachments info
        attachments = []
        for part in msg.walk():
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition:
                filename = part.get_filename()
                if filename:
                    filename = EmailReader._decode_header_value(filename)
                    attachments.append({
                        "filename": filename,
                        "content_type": part.get_content_type(),
                        "size": len(part.get_payload(decode=True) or b""),
                    })

        return {
            "subject": subject,
            "from_name": from_name,
            "from_email": from_email_addr,
            "to": to_header,
            "cc": cc_header,
            "date": date_header,
            "message_id": message_id,
            "body_text": body_text,
            "body_html": body_html,
            "attachments": attachments,
            "flags": [],
        }

    # -- List / Search -------------------------------------------------------

    async def list_folders(self) -> List[Dict[str, Any]]:
        """List all available IMAP folders/mailboxes.

        Returns:
            List of dicts with keys: name, delimiter, flags.
        """
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()
        status, folders = await loop.run_in_executor(None, conn.list)
        result = []
        if folders:
            for folder in folders:
                if folder:
                    parts = imaplib.ParseFlags(folder.decode() if isinstance(folder, bytes) else folder)
                    result.append({"raw": folder.decode() if isinstance(folder, bytes) else folder})
        return result

    async def list_emails(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        criteria: str = "ALL",
        readonly: bool = True,
    ) -> List[Dict[str, Any]]:
        """List emails from a folder.

        Args:
            folder:   IMAP folder name (default INBOX).
            limit:    Maximum number of emails to return.
            criteria: IMAP search criteria (default ALL).
            readonly: Whether to open the folder in read-only mode.

        Returns:
            List of email dicts with keys: subject, from_email, date, message_id, flags.
        """
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()

        def _list_sync():
            if readonly:
                conn.select(folder, readonly=True)
            else:
                conn.select(folder)
            status, message_ids = conn.search(None, criteria)
            if status != "OK" or not message_ids[0]:
                return []
            ids = message_ids[0].split()
            ids = ids[-limit:]  # Get the most recent
            emails = []
            for mid in ids:
                status, data = conn.fetch(mid, "(RFC822 FLAGS)")
                if status != "OK":
                    continue
                for response_part in data:
                    if isinstance(response_part, tuple):
                        raw_email = response_part[1]
                        msg = email.message_from_bytes(raw_email)
                        parsed = self._parse_message(msg)
                        # Extract flags from the response
                        parsed["id"] = mid.decode()
                        emails.append(parsed)
            return emails

        return await loop.run_in_executor(None, _list_sync)

    async def search_emails(
        self,
        query: str,
        folder: str = "INBOX",
        search_field: str = "SUBJECT",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search emails by field.

        Args:
            query:        Search query string.
            folder:       IMAP folder name.
            search_field:  IMAP search field: SUBJECT, FROM, TO, BODY, TEXT.
            limit:        Maximum results.

        Returns:
            List of matching email dicts.
        """
        criteria = f'({search_field} "{query}")'
        return await self.list_emails(folder=folder, limit=limit, criteria=criteria)

    async def get_email(
        self,
        message_id: str,
        folder: str = "INBOX",
    ) -> Dict[str, Any]:
        """Get a specific email by its IMAP message ID.

        Args:
            message_id: IMAP message sequence number or UID.
            folder:     IMAP folder name.

        Returns:
            Full email dict including body and attachments.
        """
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()

        def _get_sync():
            conn.select(folder, readonly=True)
            status, data = conn.fetch(message_id, "(RFC822)")
            if status != "OK":
                raise Exception(f"Failed to fetch message {message_id}")
            for response_part in data:
                if isinstance(response_part, tuple):
                    raw_email = response_part[1]
                    msg = email.message_from_bytes(raw_email)
                    parsed = self._parse_message(msg)
                    parsed["id"] = message_id
                    return parsed
            raise Exception(f"Message {message_id} not found")

        return await loop.run_in_executor(None, _get_sync)

    # -- Flag / Mark operations ---------------------------------------------

    async def mark_as_read(self, message_id: str, folder: str = "INBOX") -> bool:
        """Mark an email as read.

        Returns:
            True on success.
        """
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()

        def _mark_sync():
            conn.select(folder)
            conn.store(message_id, "+FLAGS", "\\Seen")
            return True

        return await loop.run_in_executor(None, _mark_sync)

    async def mark_as_unread(self, message_id: str, folder: str = "INBOX") -> bool:
        """Mark an email as unread.

        Returns:
            True on success.
        """
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()

        def _mark_sync():
            conn.select(folder)
            conn.store(message_id, "-FLAGS", "\\Seen")
            return True

        return await loop.run_in_executor(None, _mark_sync)

    async def mark_as_flagged(self, message_id: str, folder: str = "INBOX") -> bool:
        """Flag/star an email.

        Returns:
            True on success.
        """
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()

        def _mark_sync():
            conn.select(folder)
            conn.store(message_id, "+FLAGS", "\\Flagged")
            return True

        return await loop.run_in_executor(None, _mark_sync)

    async def move_email(self, message_id: str, dest_folder: str, src_folder: str = "INBOX") -> bool:
        """Move an email to another folder.

        Returns:
            True on success.
        """
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()

        def _move_sync():
            conn.select(src_folder)
            conn.copy(message_id, dest_folder)
            conn.store(message_id, "+FLAGS", "\\Deleted")
            conn.expunge()
            return True

        return await loop.run_in_executor(None, _move_sync)

    async def delete_email(self, message_id: str, folder: str = "INBOX") -> bool:
        """Delete an email.

        Returns:
            True on success.
        """
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()

        def _delete_sync():
            conn.select(folder)
            conn.store(message_id, "+FLAGS", "\\Deleted")
            conn.expunge()
            return True

        return await loop.run_in_executor(None, _delete_sync)