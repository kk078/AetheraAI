"""
Email Composer for Aethera

Provides draft and send operations for emails with an approval flow.
Supports SMTP and API providers (SendGrid, Resend).
"""
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import Any, Dict, List, Optional

import aiohttp


class EmailComposer:
    """Draft, approve, and send emails via SMTP or API providers."""

    def __init__(
        self,
        provider: str = "smtp",
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_pass: str = "",
        from_email: str = "",
        api_key: str = "",
    ):
        """
        Args:
            provider:   Email provider: "smtp", "sendgrid", or "resend".
            smtp_host:  SMTP server hostname.
            smtp_port:  SMTP server port.
            smtp_user:  SMTP username.
            smtp_pass:  SMTP password or app-specific password.
            from_email: Default "From" email address.
            api_key:    API key for SendGrid or Resend.
        """
        self.provider = provider
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
        self.from_email = from_email
        self.api_key = api_key
        self._drafts: Dict[str, Dict] = {}
        self._approval_required: bool = True

    def set_approval_required(self, required: bool) -> None:
        """Set whether emails require approval before sending."""
        self._approval_required = required

    # -- Drafting -----------------------------------------------------------

    async def create_draft(
        self,
        draft_id: str,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        html: bool = False,
        reply_to: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> Dict:
        """Create an email draft. Drafts require approval before sending.

        Args:
            draft_id:    Unique identifier for this draft.
            to:          List of recipient email addresses.
            subject:     Email subject.
            body:        Email body content.
            cc:          Optional CC list.
            bcc:         Optional BCC list.
            html:        Whether the body is HTML.
            reply_to:    Optional reply-to address.
            attachments: Optional list of file paths to attach.

        Returns:
            Dict with draft details.
        """
        draft = {
            "id": draft_id,
            "to": to,
            "subject": subject,
            "body": body,
            "cc": cc or [],
            "bcc": bcc or [],
            "html": html,
            "reply_to": reply_to,
            "attachments": attachments or [],
            "status": "draft",
            "from": self.from_email,
        }
        self._drafts[draft_id] = draft
        return {"draft_id": draft_id, "status": "draft", "approval_required": self._approval_required}

    async def update_draft(self, draft_id: str, **updates: Any) -> Dict:
        """Update an existing draft.

        Args:
            draft_id: Draft identifier.
            **updates: Fields to update (to, subject, body, cc, bcc, html, etc.).

        Returns:
            Updated draft details.
        """
        if draft_id not in self._drafts:
            raise ValueError(f"Draft '{draft_id}' not found")

        draft = self._drafts[draft_id]
        for key, value in updates.items():
            if key in draft and key != "id" and key != "status":
                draft[key] = value

        return {"draft_id": draft_id, "status": "draft"}

    async def get_draft(self, draft_id: str) -> Dict:
        """Get draft details.

        Returns:
            Draft dict.
        """
        if draft_id not in self._drafts:
            raise ValueError(f"Draft '{draft_id}' not found")
        return self._drafts[draft_id]

    async def list_drafts(self) -> List[Dict]:
        """List all pending drafts.

        Returns:
            List of draft dicts.
        """
        return [
            {"id": d["id"], "subject": d["subject"], "to": d["to"], "status": d["status"]}
            for d in self._drafts.values()
        ]

    async def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft.

        Returns:
            True on success.
        """
        if draft_id not in self._drafts:
            raise ValueError(f"Draft '{draft_id}' not found")
        del self._drafts[draft_id]
        return True

    # -- Approval Flow ------------------------------------------------------

    async def approve_draft(self, draft_id: str) -> Dict:
        """Approve a draft for sending.

        Returns:
            Dict with approval status.
        """
        if draft_id not in self._drafts:
            raise ValueError(f"Draft '{draft_id}' not found")
        self._drafts[draft_id]["status"] = "approved"
        return {"draft_id": draft_id, "status": "approved"}

    async def reject_draft(self, draft_id: str, reason: str = "") -> Dict:
        """Reject a draft.

        Returns:
            Dict with rejection status.
        """
        if draft_id not in self._drafts:
            raise ValueError(f"Draft '{draft_id}' not found")
        self._drafts[draft_id]["status"] = "rejected"
        return {"draft_id": draft_id, "status": "rejected", "reason": reason}

    # -- Sending ------------------------------------------------------------

    async def send_draft(self, draft_id: str) -> Dict:
        """Send an approved draft. If approval is required, the draft must be
        approved first. If approval is not required, any draft can be sent.

        Returns:
            Dict with send status.
        """
        if draft_id not in self._drafts:
            raise ValueError(f"Draft '{draft_id}' not found")

        draft = self._drafts[draft_id]

        if self._approval_required and draft["status"] != "approved":
            raise ValueError(f"Draft '{draft_id}' requires approval before sending")

        # Send the email
        result = await self._send_email(
            to=draft["to"],
            subject=draft["subject"],
            body=draft["body"],
            cc=draft.get("cc", []),
            bcc=draft.get("bcc", []),
            html=draft.get("html", False),
            reply_to=draft.get("reply_to"),
            attachments=draft.get("attachments", []),
        )

        # Update draft status
        draft["status"] = "sent"
        draft["sent_result"] = result

        return {"draft_id": draft_id, "status": "sent", "result": result}

    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        html: bool = False,
        reply_to: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> Dict:
        """Send an email directly without the draft/approval flow.

        Returns:
            Dict with send status.
        """
        return await self._send_email(
            to=to,
            subject=subject,
            body=body,
            cc=cc or [],
            bcc=bcc or [],
            html=html,
            reply_to=reply_to,
            attachments=attachments or [],
        )

    async def _send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: List[str],
        bcc: List[str],
        html: bool,
        reply_to: Optional[str],
        attachments: List[str],
    ) -> Dict:
        """Core email sending logic."""
        if self.provider == "smtp":
            await self._send_smtp(to, subject, body, cc, bcc, html, reply_to, attachments)
        elif self.provider in ("sendgrid", "resend"):
            await self._send_api(to, subject, body, cc, bcc, html, reply_to)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        return {"sent_to": to + cc + bcc, "subject": subject, "provider": self.provider}

    async def _send_smtp(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: List[str],
        bcc: List[str],
        html: bool,
        reply_to: Optional[str],
        attachments: List[str],
    ) -> None:
        """Send email via SMTP."""
        if not self.smtp_user or not self.smtp_pass:
            raise ValueError("SMTP credentials not configured")

        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)
        if reply_to:
            msg["Reply-To"] = reply_to

        # Body part
        alt = MIMEMultipart("alternative")
        if html:
            alt.attach(MIMEText(body, "html", "utf-8"))
        else:
            alt.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(alt)

        # Attachments
        for filepath in attachments:
            if os.path.isfile(filepath):
                with open(filepath, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(filepath)}")
                    msg.attach(part)

        loop = asyncio.get_event_loop()
        all_recipients = to + cc + bcc
        await loop.run_in_executor(
            None,
            lambda: self._send_smtp_sync(all_recipients, msg),
        )

    def _send_smtp_sync(self, recipients: List[str], msg: MIMEMultipart) -> None:
        """Synchronous SMTP send."""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.sendmail(self.from_email, recipients, msg.as_string())

    async def _send_api(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: List[str],
        bcc: List[str],
        html: bool,
        reply_to: Optional[str],
    ) -> None:
        """Send email via API (SendGrid/Resend)."""
        if not self.api_key:
            raise ValueError(f"API key not configured for {self.provider}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if self.provider == "sendgrid":
            url = "https://api.sendgrid.com/v3/mail/send"
            personalization: Dict[str, Any] = {
                "to": [{"email": e} for e in to],
                "subject": subject,
            }
            if cc:
                personalization["cc"] = [{"email": e} for e in cc]
            if bcc:
                personalization["bcc"] = [{"email": e} for e in bcc]

            data: Dict[str, Any] = {
                "personalizations": [personalization],
                "from": {"email": self.from_email},
                "content": [{"type": "text/html" if html else "text/plain", "value": body}],
            }
            if reply_to:
                data["reply_to"] = {"email": reply_to}
        elif self.provider == "resend":
            url = "https://api.resend.com/emails"
            data = {
                "from": self.from_email,
                "to": to,
                "subject": subject,
                "html" if html else "text": body,
            }
            if cc:
                data["cc"] = cc
            if bcc:
                data["bcc"] = bcc
            if reply_to:
                data["reply_to"] = reply_to
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as resp:
                if resp.status >= 400:
                    error = await resp.json()
                    raise Exception(f"Email API error: {error}")

    # -- Bulk Send -----------------------------------------------------------

    async def bulk_send(
        self,
        recipients: List[Dict[str, str]],
        subject: str,
        body_template: str,
        html: bool = False,
    ) -> Dict:
        """Send personalized bulk emails.

        Args:
            recipients:     List of dicts with "email" key and optional template variables.
            subject:       Email subject.
            body_template: Body template (use {variable} for substitution).
            html:          Whether the body is HTML.

        Returns:
            Dict with sent and failed lists.
        """
        sent = []
        failed = []

        for recipient in recipients:
            email_addr = recipient.get("email", "")
            if not email_addr:
                failed.append({"email": "", "error": "Missing email address"})
                continue

            # Simple template substitution
            personalized_body = body_template
            for key, value in recipient.items():
                personalized_body = personalized_body.replace(f"{{{key}}}", str(value))

            try:
                await self._send_email(
                    to=[email_addr],
                    subject=subject,
                    body=personalized_body,
                    cc=[],
                    bcc=[],
                    html=html,
                    reply_to=None,
                    attachments=[],
                )
                sent.append(email_addr)
            except Exception as e:
                failed.append({"email": email_addr, "error": str(e)})

        return {
            "sent": sent,
            "failed": failed,
            "total": len(recipients),
            "sent_count": len(sent),
            "failed_count": len(failed),
        }