"""
Email Plugin for Aethera
Sends and manages emails via SMTP or API (SendGrid, Resend, etc.).
"""
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional
from ..plugin_base import AetheraPlugin, PluginConfig, PluginParameter, PluginResult


class EmailPlugin(AetheraPlugin):
    """Email integration plugin supporting SMTP and API providers."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider = config.get('provider', 'smtp')  # smtp, sendgrid, resend
        self.smtp_host = config.get('smtp_host', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.smtp_user = config.get('smtp_user', '')
        self.smtp_pass = config.get('smtp_pass', '')
        self.from_email = config.get('from_email', '')
        self.api_key = config.get('api_key', '')  # For SendGrid/Resend

    def get_config(self) -> PluginConfig:
        return PluginConfig(
            name='email',
            version='1.0.0',
            description='Send and manage emails via SMTP or API providers',
            author='Aethera AI',
            parameters=[
                PluginParameter(
                    name='action',
                    type='action',
                    description='Action to perform',
                    required=True,
                    choices=['send', 'send_html', 'send_template', 'bulk_send']
                ),
                PluginParameter(name='to', type='str', description='Recipient email', required=False),
                PluginParameter(name='to_list', type='list', description='List of recipients', required=False),
                PluginParameter(name='cc', type='str', description='CC recipient', required=False),
                PluginParameter(name='bcc', type='str', description='BCC recipient', required=False),
                PluginParameter(name='subject', type='str', description='Email subject', required=False),
                PluginParameter(name='body', type='str', description='Email body (plain text)', required=False),
                PluginParameter(name='html_body', type='str', description='Email body (HTML)', required=False),
                PluginParameter(name='template_id', type='str', description='Template ID', required=False),
                PluginParameter(name='template_vars', type='dict', description='Template variables', required=False),
                PluginParameter(name='attachments', type='list', description='Attachment paths', required=False),
                PluginParameter(name='reply_to', type='str', description='Reply-to email', required=False),
            ],
            permissions=['send:email', 'read:contacts'],
            dependencies=[],
        )

    async def execute(self, action: str, parameters: Dict[str, Any]) -> PluginResult:
        """Execute email action."""
        try:
            if action == 'send':
                return await self._send_email(parameters)
            elif action == 'send_html':
                return await self._send_html_email(parameters)
            elif action == 'send_template':
                return await self._send_template_email(parameters)
            elif action == 'bulk_send':
                return await self._bulk_send(parameters)
            else:
                return PluginResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            return PluginResult(success=False, error=str(e))

    async def _send_email(self, params: Dict) -> PluginResult:
        """Send plain text email."""
        to_emails = self._get_recipients(params)
        if not to_emails:
            return PluginResult(success=False, error="No recipients specified")

        subject = params.get('subject', 'No Subject')
        body = params.get('body', '')

        if self.provider == 'smtp':
            await self._send_smtp(to_emails, subject, body, html=False)
        else:
            await self._send_api(to_emails, subject, body, html=False)

        return PluginResult(success=True, data={'sent_to': to_emails, 'subject': subject})

    async def _send_html_email(self, params: Dict) -> PluginResult:
        """Send HTML email."""
        to_emails = self._get_recipients(params)
        if not to_emails:
            return PluginResult(success=False, error="No recipients specified")

        subject = params.get('subject', 'No Subject')
        html_body = params.get('html_body', params.get('body', ''))

        if self.provider == 'smtp':
            await self._send_smtp(to_emails, subject, html_body, html=True)
        else:
            await self._send_api(to_emails, subject, html_body, html=True)

        return PluginResult(success=True, data={'sent_to': to_emails, 'subject': subject})

    async def _send_template_email(self, params: Dict) -> PluginResult:
        """Send email using template."""
        to_emails = self._get_recipients(params)
        if not to_emails:
            return PluginResult(success=False, error="No recipients specified")

        template_id = params.get('template_id')
        template_vars = params.get('template_vars', {})

        if self.provider == 'sendgrid':
            await self._send_sendgrid_template(to_emails, template_id, template_vars)
        elif self.provider == 'resend':
            await self._send_resend_template(to_emails, template_id, template_vars)
        else:
            return PluginResult(success=False, error=f"Template sending not supported for {self.provider}")

        return PluginResult(success=True, data={'sent_to': to_emails, 'template': template_id})

    async def _bulk_send(self, params: Dict) -> PluginResult:
        """Send bulk emails."""
        to_list = params.get('to_list', [])
        if not to_list:
            return PluginResult(success=False, error="No recipients list specified")

        subject = params.get('subject', 'No Subject')
        body = params.get('body', '')
        html = params.get('html_body') is not None

        sent = []
        failed = []

        for to_email in to_list:
            try:
                if self.provider == 'smtp':
                    await self._send_smtp([to_email], subject, body or params.get('html_body', ''), html=html)
                else:
                    await self._send_api([to_email], subject, body or params.get('html_body', ''), html=html)
                sent.append(to_email)
            except Exception as e:
                failed.append({'email': to_email, 'error': str(e)})

        return PluginResult(
            success=len(failed) == 0,
            data={'sent': sent, 'failed': failed},
            metadata={'total': len(to_list), 'sent_count': len(sent), 'failed_count': len(failed)}
        )

    def _get_recipients(self, params: Dict) -> tuple:
        """Extract recipient lists from parameters. Returns (to, cc, bcc) lists."""
        to = []
        cc = []
        bcc = []

        if params.get('to'):
            if isinstance(params['to'], list):
                to.extend(params['to'])
            else:
                to.append(params['to'])
        if params.get('to_list'):
            to.extend(params['to_list'])

        if params.get('cc'):
            if isinstance(params['cc'], list):
                cc.extend(params['cc'])
            else:
                cc.append(params['cc'])

        if params.get('bcc'):
            if isinstance(params['bcc'], list):
                bcc.extend(params['bcc'])
            else:
                bcc.append(params['bcc'])

        return to, cc, bcc

    async def _send_smtp(self, to_emails: List[str], subject: str, body: str,
                         html: bool = False, cc: List[str] = None, bcc: List[str] = None,
                         attachments: List[Dict] = None) -> None:
        """Send email via SMTP."""
        if not self.smtp_user or not self.smtp_pass:
            raise ValueError("SMTP credentials not configured")

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.from_email
        msg['To'] = ', '.join(to_emails)

        if cc:
            msg['Cc'] = ', '.join(cc)
        if bcc:
            # BCC goes in envelope but NOT in headers (privacy)
            pass

        if html:
            msg.attach(MIMEText(body, 'html', 'utf-8'))
        else:
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # Add attachments if provided
        if attachments:
            for att in attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(att.get('content', b''))
                part.add_header('Content-Disposition',
                              f'attachment; filename="{att.get("filename", "attachment")}"')
                msg.attach(part)

        all_recipients = to_emails + (cc or []) + (bcc or [])

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._send_smtp_sync(all_recipients, msg)
        )

    def _send_smtp_sync(self, to_emails: List[str], msg: MIMEMultipart) -> None:
        """Synchronous SMTP send."""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.sendmail(self.from_email, to_emails, msg.as_string())

    async def _send_api(self, to_emails: List[str], subject: str, body: str, html: bool = False) -> None:
        """Send email via API (SendGrid/Resend)."""
        import aiohttp

        if not self.api_key:
            raise ValueError(f"API key not configured for {self.provider}")

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        if self.provider == 'sendgrid':
            url = 'https://api.sendgrid.com/v3/mail/send'
            data = {
                'personalizations': [{'to': [{'email': e} for e in to_emails], 'subject': subject}],
                'from': {'email': self.from_email},
                'content': [{'type': 'text/html' if html else 'text/plain', 'value': body}],
            }
        elif self.provider == 'resend':
            url = 'https://api.resend.com/emails'
            data = {
                'from': self.from_email,
                'to': to_emails,
                'subject': subject,
                'html' if html else 'text': body,
            }
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as resp:
                if resp.status >= 400:
                    error = await resp.json()
                    raise Exception(f"Email API error: {error}")

    async def _send_sendgrid_template(self, to_emails: List[str], template_id: str, template_vars: Dict) -> None:
        """Send SendGrid template email."""
        import aiohttp

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        url = 'https://api.sendgrid.com/v3/mail/send'
        data = {
            'personalizations': [
                {
                    'to': [{'email': e} for e in to_emails],
                    'dynamic_template_data': template_vars,
                }
            ],
            'from': {'email': self.from_email},
            'template_id': template_id,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as resp:
                if resp.status >= 400:
                    error = await resp.json()
                    raise Exception(f"SendGrid error: {error}")

    async def _send_resend_template(self, to_emails: List[str], template_id: str, template_vars: Dict) -> None:
        """Send Resend template email."""
        import aiohttp

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        url = 'https://api.resend.com/emails'
        data = {
            'from': self.from_email,
            'to': to_emails,
            'template_id': template_id,
            'react': template_vars,  # Resend uses React templates
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as resp:
                if resp.status >= 400:
                    error = await resp.json()
                    raise Exception(f"Resend error: {error}")


def register_plugin():
    """Register the Email plugin."""
    import os
    return EmailPlugin, {
        'provider': os.getenv('EMAIL_PROVIDER', 'smtp'),
        'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'smtp_user': os.getenv('SMTP_USER', ''),
        'smtp_pass': os.getenv('SMTP_PASS', ''),
        'from_email': os.getenv('FROM_EMAIL', ''),
        'api_key': os.getenv('EMAIL_API_KEY', ''),
        'enabled': True,
    }
