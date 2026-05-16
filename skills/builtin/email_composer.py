"""
Aethera AI - Email Composer Skill

Draft emails using templates with style presets (formal, casual, medical professional).
Supports template variables, subject line generation, CC/BCC, and multiple writing styles.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Style presets
# ---------------------------------------------------------------------------
STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "formal": {
        "greeting": "Dear",
        "closing": "Sincerely",
        "signature_hint": "Include full name and title",
        "tone": "professional, respectful, and concise",
    },
    "casual": {
        "greeting": "Hi",
        "closing": "Best",
        "signature_hint": "First name is fine",
        "tone": "friendly, relaxed, and conversational",
    },
    "medical_professional": {
        "greeting": "Dear",
        "closing": "Respectfully",
        "signature_hint": "Include full name, credentials, and facility",
        "tone": "clinical, precise, and empathetic",
    },
}

# ---------------------------------------------------------------------------
# Built-in templates
# ---------------------------------------------------------------------------
BUILTIN_TEMPLATES: Dict[str, str] = {
    "general": (
        "{{greeting}} {{recipient}},\n\n"
        "{{body}}\n\n"
        "{{closing}},\n{{sender}}"
    ),
    "meeting_request": (
        "{{greeting}} {{recipient}},\n\n"
        "I would like to request a meeting to discuss {{topic}}. "
        "Would you be available on {{proposed_date}} at {{proposed_time}}?\n\n"
        "Please let me know if this works for you or if you would prefer an alternative time.\n\n"
        "{{closing}},\n{{sender}}"
    ),
    "follow_up": (
        "{{greeting}} {{recipient}},\n\n"
        "I am following up on our previous conversation regarding {{topic}}. "
        "As discussed, {{body}}\n\n"
        "Please let me know if you have any questions or need further information.\n\n"
        "{{closing}},\n{{sender}}"
    ),
    "thank_you": (
        "{{greeting}} {{recipient}},\n\n"
        "Thank you for {{reason}}. {{body}}\n\n"
        "I truly appreciate your {{specific_appreciation}}.\n\n"
        "{{closing}},\n{{sender}}"
    ),
    "introduction": (
        "{{greeting}} {{recipient}},\n\n"
        "My name is {{sender}}, and I am reaching out to introduce myself as "
        "{{your_role}}. {{body}}\n\n"
        "I would welcome the opportunity to connect and discuss how we might collaborate.\n\n"
        "{{closing}},\n{{sender}}"
    ),
    "medical_referral": (
        "{{greeting}} {{recipient}},\n\n"
        "I am writing to refer {{patient_description}} for {{referral_reason}}. "
        "Relevant clinical details:\n\n"
        "{{clinical_details}}\n\n"
        "Please do not hesitate to contact me if you require additional information.\n\n"
        "{{closing}},\n{{sender}}"
    ),
}


@skill(name="email_composer", category="general")
class EmailComposerSkill(AetheraSkill):
    """
    Compose emails with templates, style presets, and variable substitution.
    """

    @property
    def name(self) -> str:
        return "email_composer"

    @property
    def description(self) -> str:
        return "Draft emails with templates, style presets, and subject line generation"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["compose", "generate_subject", "list_templates", "list_styles"],
                    "description": (
                        "'compose' to draft an email, "
                        "'generate_subject' to suggest subject lines, "
                        "'list_templates' to see available templates, "
                        "'list_styles' to see available style presets"
                    ),
                },
                "to": {
                    "type": "string",
                    "description": "Recipient email address or name"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line"
                },
                "body": {
                    "type": "string",
                    "description": "Email body content (plain text). Used as-is or merged into a template."
                },
                "cc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CC recipients"
                },
                "bcc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "BCC recipients"
                },
                "style": {
                    "type": "string",
                    "enum": ["formal", "casual", "medical_professional"],
                    "description": "Writing style preset",
                    "default": "formal"
                },
                "template": {
                    "type": "string",
                    "description": "Template name to use (e.g. 'general', 'meeting_request', 'follow_up')"
                },
                "variables": {
                    "type": "object",
                    "description": "Template variables to substitute (key-value pairs)"
                },
                "sender": {
                    "type": "string",
                    "description": "Sender name"
                },
                "context": {
                    "type": "string",
                    "description": "Brief context for subject line generation"
                },
            },
            "required": ["action"],
        }

    @property
    def examples(self) -> list:
        return [
            {
                "input": {
                    "action": "compose",
                    "to": "dr.smith@example.com",
                    "subject": "Follow-up on lab results",
                    "body": "The patient's CBC results are within normal limits.",
                    "style": "medical_professional",
                    "sender": "Dr. Jane Doe",
                }
            },
            {
                "input": {
                    "action": "compose",
                    "template": "meeting_request",
                    "variables": {
                        "recipient": "Team",
                        "topic": "Q3 planning",
                        "proposed_date": "July 15",
                        "proposed_time": "10:00 AM",
                        "sender": "Alice",
                    },
                    "style": "casual",
                }
            },
            {
                "input": {"action": "generate_subject", "context": "Requesting extension on project deadline"},
            },
        ]

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")

        try:
            if action == "compose":
                return self._compose(kwargs)
            elif action == "generate_subject":
                return self._generate_subject(kwargs)
            elif action == "list_templates":
                return self._list_templates()
            elif action == "list_styles":
                return self._list_styles()
            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            logger.exception("Email composer error")
            return SkillResult(success=False, error=str(e))

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def _compose(self, kwargs: dict) -> SkillResult:
        to_addr = kwargs.get("to", "")
        subject = kwargs.get("subject", "")
        body = kwargs.get("body", "")
        cc = kwargs.get("cc", [])
        bcc = kwargs.get("bcc", [])
        style_name = kwargs.get("style", "formal")
        template_name = kwargs.get("template", "")
        variables = kwargs.get("variables", {})
        sender = kwargs.get("sender", "")

        if not to_addr:
            return SkillResult(success=False, error="'to' is required for compose action")

        preset = STYLE_PRESETS.get(style_name, STYLE_PRESETS["formal"])

        # Extract recipient first name for greeting
        recipient_name = self._extract_name(to_addr)

        # Build merged variables: preset values + user variables + defaults
        merged_vars: Dict[str, Any] = {
            "greeting": preset["greeting"],
            "closing": preset["closing"],
            "recipient": recipient_name,
            "sender": sender,
            "body": body,
        }
        merged_vars.update(variables)

        # Generate email body
        if template_name:
            template_text = BUILTIN_TEMPLATES.get(template_name)
            if template_text is None:
                return SkillResult(
                    success=False,
                    error=f"Unknown template: {template_name}. Use list_templates to see available options."
                )
            email_body = self._render_template(template_text, merged_vars)
        else:
            # Use the general template with the provided body
            email_body = self._render_template(BUILTIN_TEMPLATES["general"], merged_vars)

        # Auto-generate subject if not provided
        if not subject:
            subject = self._infer_subject(body or str(variables), style_name)

        # Build structured result
        email_data: Dict[str, Any] = {
            "to": to_addr,
            "subject": subject,
            "body": email_body,
            "style": style_name,
            "template": template_name or "general",
        }
        if cc:
            email_data["cc"] = cc
        if bcc:
            email_data["bcc"] = bcc

        return SkillResult(success=True, data=email_data)

    # ------------------------------------------------------------------
    # Generate subject lines
    # ------------------------------------------------------------------

    def _generate_subject(self, kwargs: dict) -> SkillResult:
        context = kwargs.get("context", "")
        style_name = kwargs.get("style", "formal")

        if not context:
            return SkillResult(success=False, error="'context' is required for generate_subject action")

        # Generate multiple subject line candidates based on style
        subjects = self._craft_subject_lines(context, style_name)

        return SkillResult(
            success=True,
            data={
                "context": context,
                "style": style_name,
                "suggestions": subjects,
            }
        )

    # ------------------------------------------------------------------
    # List helpers
    # ------------------------------------------------------------------

    def _list_templates(self) -> SkillResult:
        templates = [
            {"name": name, "preview": tpl[:120].strip() + ("..." if len(tpl) > 120 else "")}
            for name, tpl in BUILTIN_TEMPLATES.items()
        ]
        return SkillResult(success=True, data={"templates": templates})

    def _list_styles(self) -> SkillResult:
        styles = [
            {
                "name": name,
                "greeting": preset["greeting"],
                "closing": preset["closing"],
                "tone": preset["tone"],
                "signature_hint": preset["signature_hint"],
            }
            for name, preset in STYLE_PRESETS.items()
        ]
        return SkillResult(success=True, data={"styles": styles})

    # ------------------------------------------------------------------
    # Template rendering
    # ------------------------------------------------------------------

    @staticmethod
    def _render_template(template: str, variables: Dict[str, Any]) -> str:
        """Replace {{variable}} placeholders with values from the variables dict."""
        def replacer(match: re.Match) -> str:
            key = match.group(1).strip()
            value = variables.get(key, match.group(0))
            return str(value)

        return re.sub(r"\{\{(\w+)\}\}", replacer, template)

    # ------------------------------------------------------------------
    # Subject inference / generation
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_subject(body: str, style_name: str) -> str:
        """Create a simple subject line from the body text."""
        # Take the first sentence (up to 80 chars) as subject basis
        first_sentence = body.split(".")[0].strip()[:80]
        if not first_sentence:
            return "No Subject"

        prefix_map = {
            "formal": "Re: ",
            "casual": "",
            "medical_professional": "RE: ",
        }
        prefix = prefix_map.get(style_name, "")
        return f"{prefix}{first_sentence}"

    @staticmethod
    def _craft_subject_lines(context: str, style_name: str) -> List[str]:
        """Generate several subject line candidates from context."""
        # Trim context for subject-friendly length
        short = context.strip()
        if len(short) > 100:
            short = short[:97] + "..."

        if style_name == "formal":
            return [
                f"Re: {short}",
                f"Regarding {short}",
                f"Follow-Up: {short}",
                f"Inquiry: {short}",
            ]
        elif style_name == "casual":
            return [
                short,
                f"Quick question: {short}",
                f"Touching base - {short}",
                f"Hey, about {short}",
            ]
        elif style_name == "medical_professional":
            return [
                f"RE: {short}",
                f"Referral: {short}",
                f"Clinical Update: {short}",
                f"Consultation Request: {short}",
            ]
        else:
            return [short]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_name(to_addr: str) -> str:
        """
        Extract a display name from an email address or name string.
        'Dr. Smith <smith@example.com>' -> 'Dr. Smith'
        'smith@example.com' -> 'Smith'
        'Jane Doe' -> 'Jane Doe'
        """
        # Handle "Name <email>" format
        match = re.match(r"^(.+?)\s*<.*>$", to_addr)
        if match:
            return match.group(1).strip()

        # Handle plain email
        if "@" in to_addr:
            local = to_addr.split("@")[0]
            # Convert dots/underscores to spaces, title-case
            name = local.replace(".", " ").replace("_", " ").title()
            return name

        # Assume it's already a name
        return to_addr.strip()