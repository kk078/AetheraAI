"""
Email Template Manager for Aethera

Provides email template CRUD and rendering with variable substitution.
Templates are stored in memory by default and can be persisted to disk.
"""
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp


class TemplateManager:
    """Manage email templates: create, read, update, delete, and render."""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Args:
            storage_path: Optional file path for persisting templates as JSON.
                          If None, templates are kept in memory only.
        """
        self.storage_path = storage_path
        self._templates: Dict[str, Dict[str, Any]] = {}
        if storage_path and os.path.isfile(storage_path):
            self._load_from_disk()

    # -- Persistence --------------------------------------------------------

    def _load_from_disk(self) -> None:
        """Load templates from the JSON storage file."""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                self._templates = json.load(f)
        except (json.JSONDecodeError, OSError):
            self._templates = {}

    def _save_to_disk(self) -> None:
        """Persist templates to the JSON storage file."""
        if not self.storage_path:
            return
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self._templates, f, indent=2, ensure_ascii=False)

    # -- Template CRUD ------------------------------------------------------

    async def create_template(
        self,
        template_id: str,
        subject: str,
        body: str,
        html: bool = False,
        description: str = "",
        variables: Optional[List[str]] = None,
        category: str = "general",
    ) -> Dict:
        """Create a new email template.

        Args:
            template_id: Unique template identifier.
            subject:     Email subject template (supports {variable} syntax).
            body:        Email body template (supports {variable} syntax).
            html:        Whether the body is HTML.
            description: Human-readable description.
            variables:   List of expected variable names.
            category:    Template category (general, marketing, transactional, notification).

        Returns:
            Dict with template details.
        """
        if template_id in self._templates:
            raise ValueError(f"Template '{template_id}' already exists")

        # Auto-detect variables if not provided
        if variables is None:
            all_text = f"{subject} {body}"
            variables = list(set(re.findall(r"\{(\w+)\}", all_text)))

        template = {
            "id": template_id,
            "subject": subject,
            "body": body,
            "html": html,
            "description": description,
            "variables": variables,
            "category": category,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self._templates[template_id] = template
        self._save_to_disk()

        return {
            "id": template_id,
            "subject": subject,
            "variables": variables,
            "category": category,
        }

    async def get_template(self, template_id: str) -> Dict:
        """Get a template by ID.

        Returns:
            Template dict.
        """
        if template_id not in self._templates:
            raise ValueError(f"Template '{template_id}' not found")
        return dict(self._templates[template_id])

    async def update_template(
        self,
        template_id: str,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        html: Optional[bool] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict:
        """Update an existing template.

        Returns:
            Updated template details.
        """
        if template_id not in self._templates:
            raise ValueError(f"Template '{template_id}' not found")

        template = self._templates[template_id]
        if subject is not None:
            template["subject"] = subject
        if body is not None:
            template["body"] = body
        if html is not None:
            template["html"] = html
        if description is not None:
            template["description"] = description
        if category is not None:
            template["category"] = category

        # Re-detect variables
        all_text = f"{template['subject']} {template['body']}"
        template["variables"] = list(set(re.findall(r"\{(\w+)\}", all_text)))
        template["updated_at"] = datetime.now().isoformat()

        self._save_to_disk()
        return {"id": template_id, "subject": template["subject"], "variables": template["variables"]}

    async def delete_template(self, template_id: str) -> bool:
        """Delete a template.

        Returns:
            True on success.
        """
        if template_id not in self._templates:
            raise ValueError(f"Template '{template_id}' not found")
        del self._templates[template_id]
        self._save_to_disk()
        return True

    async def list_templates(self, category: Optional[str] = None) -> List[Dict]:
        """List all templates, optionally filtered by category.

        Returns:
            List of template summary dicts.
        """
        templates = self._templates.values()
        if category:
            templates = [t for t in templates if t.get("category") == category]
        return [
            {
                "id": t["id"],
                "subject": t["subject"],
                "category": t.get("category", "general"),
                "variables": t.get("variables", []),
                "updated_at": t.get("updated_at", ""),
            }
            for t in templates
        ]

    # -- Template Rendering -------------------------------------------------

    async def render_template(
        self,
        template_id: str,
        variables: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """Render a template with variable substitution.

        Args:
            template_id: Template ID to render.
            variables:    Dict of variable names to values.

        Returns:
            Dict with keys: subject, body, html, missing_variables.
        """
        if template_id not in self._templates:
            raise ValueError(f"Template '{template_id}' not found")

        template = self._templates[template_id]
        variables = variables or {}

        # Perform substitution
        subject = template["subject"]
        body = template["body"]

        for key, value in variables.items():
            subject = subject.replace(f"{{{key}}}", str(value))
            body = body.replace(f"{{{key}}}", str(value))

        # Find remaining unsubstituted variables
        remaining_subject = set(re.findall(r"\{(\w+)\}", subject))
        remaining_body = set(re.findall(r"\{(\w+)\}", body))
        missing_variables = list(remaining_subject | remaining_body)

        return {
            "subject": subject,
            "body": body,
            "html": template.get("html", False),
            "missing_variables": missing_variables,
            "template_id": template_id,
        }

    async def render_batch(
        self,
        template_id: str,
        recipients: List[Dict[str, str]],
    ) -> List[Dict]:
        """Render a template for multiple recipients with per-recipient variables.

        Args:
            template_id: Template ID to render.
            recipients:   List of variable dicts (each must include "email" key).

        Returns:
            List of rendered dicts, one per recipient.
        """
        results = []
        for recipient_vars in recipients:
            rendered = await self.render_template(template_id, recipient_vars)
            rendered["recipient_email"] = recipient_vars.get("email", "")
            results.append(rendered)
        return results

    # -- Template Validation ------------------------------------------------

    async def validate_template(self, template_id: str) -> Dict:
        """Validate a template for common issues.

        Returns:
            Dict with validation results.
        """
        if template_id not in self._templates:
            raise ValueError(f"Template '{template_id}' not found")

        template = self._templates[template_id]
        issues: List[str] = []

        # Check for empty subject
        if not template.get("subject", "").strip():
            issues.append("Subject is empty")

        # Check for empty body
        if not template.get("body", "").strip():
            issues.append("Body is empty")

        # Check for unclosed braces
        subject = template.get("subject", "")
        body = template.get("body", "")
        combined = f"{subject} {body}"
        open_braces = combined.count("{") - combined.count("}")
        if open_braces != 0:
            issues.append(f"Mismatched braces detected (difference: {open_braces})")

        # Check for HTML template issues
        if template.get("html"):
            if "<html" not in body.lower() and "<body" not in body.lower():
                issues.append("HTML template missing <html> or <body> tags (may still work as fragment)")

        # Check that declared variables exist in the template
        declared_vars = set(template.get("variables", []))
        actual_vars = set(re.findall(r"\{(\w+)\}", combined))
        undeclared = actual_vars - declared_vars
        if undeclared:
            issues.append(f"Variables used but not declared: {undeclared}")
        unused = declared_vars - actual_vars
        if unused:
            issues.append(f"Variables declared but not used: {unused}")

        return {
            "template_id": template_id,
            "valid": len(issues) == 0,
            "issues": issues,
            "variable_count": len(declared_vars),
        }

    # -- Import/Export ------------------------------------------------------

    async def export_templates(self) -> str:
        """Export all templates as a JSON string.

        Returns:
            JSON string of all templates.
        """
        return json.dumps(self._templates, indent=2, ensure_ascii=False)

    async def import_templates(self, json_data: str, overwrite: bool = False) -> Dict:
        """Import templates from a JSON string.

        Args:
            json_data:  JSON string of templates.
            overwrite:  Whether to overwrite existing templates.

        Returns:
            Dict with import stats.
        """
        imported = json.loads(json_data)
        added = 0
        skipped = 0

        for template_id, template in imported.items():
            if template_id in self._templates and not overwrite:
                skipped += 1
                continue
            self._templates[template_id] = template
            added += 1

        self._save_to_disk()
        return {"added": added, "skipped": skipped, "total": len(imported)}

    # -- Send via Provider (SendGrid/Resend template IDs) -------------------

    async def send_via_provider_template(
        self,
        provider: str,
        api_key: str,
        from_email: str,
        to_emails: List[str],
        provider_template_id: str,
        template_variables: Dict[str, Any],
    ) -> Dict:
        """Send an email using a provider-specific template (SendGrid dynamic template or Resend template).

        Args:
            provider:            "sendgrid" or "resend".
            api_key:            Provider API key.
            from_email:         Sender email.
            to_emails:          Recipient emails.
            provider_template_id: Provider's template ID.
            template_variables: Template variable values.

        Returns:
            Dict with send status.
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        if provider == "sendgrid":
            url = "https://api.sendgrid.com/v3/mail/send"
            data = {
                "personalizations": [
                    {
                        "to": [{"email": e} for e in to_emails],
                        "dynamic_template_data": template_variables,
                    }
                ],
                "from": {"email": from_email},
                "template_id": provider_template_id,
            }
        elif provider == "resend":
            url = "https://api.resend.com/emails"
            data = {
                "from": from_email,
                "to": to_emails,
                "template_id": provider_template_id,
                "react": template_variables,
            }
        else:
            raise ValueError(f"Unknown provider: {provider}")

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as resp:
                if resp.status >= 400:
                    error = await resp.json()
                    raise Exception(f"Provider template send error: {error}")
                return {"status": "sent", "provider": provider, "template_id": provider_template_id}