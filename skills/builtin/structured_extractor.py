"""
Aethera AI - Structured Extractor Skill

Pull structured fields out of free text using typed patterns (email, phone,
date, SSN, MRN, NPI, money, ICD-10, CPT) or a custom regex/keyword spec.
Domain-agnostic; useful for turning notes, faxes, or OCR output into data.
"""

import re
from typing import Any, Dict, List

from skills.skill_base import AetheraSkill, SkillResult, skill

BUILTIN_PATTERNS: Dict[str, str] = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "phone": r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
    "date": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "mrn": r"\bMRN[#:]?\s*(\d{4,})\b",
    "npi": r"\b\d{10}\b",
    "money": r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\b\d+\.\d{2}\b",
    "icd10": r"\b[A-TV-Z]\d{2}(?:\.\d{1,4})?\b",
    "cpt": r"\b\d{5}\b",
    "zip": r"\b\d{5}(?:-\d{4})?\b",
}


@skill(name="structured_extractor", category="general")
class StructuredExtractorSkill(AetheraSkill):

    @property
    def name(self) -> str:
        return "structured_extractor"

    @property
    def description(self) -> str:
        return (
            "Extract structured fields from free text. Each field uses a built-in "
            "type (email, phone, date, ssn, mrn, npi, money, icd10, cpt, zip) or a "
            "custom 'regex'/'keyword'. Returns the first match per field, or all "
            "matches with action=extract_all."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["extract", "extract_all"]},
                "text": {"type": "string"},
                "fields": {
                    "type": "array",
                    "description": "Field specs: {name, type|regex, keyword?}",
                    "items": {"type": "object"},
                },
            },
            "required": ["text", "fields"],
        }

    def _pattern_for(self, field: Dict[str, Any]) -> str:
        if field.get("regex"):
            return field["regex"]
        if field.get("keyword"):
            # Capture the value following "keyword:" up to end of line.
            kw = re.escape(field["keyword"])
            return rf"{kw}\s*[:#-]?\s*(.+?)(?:\n|$)"
        ftype = str(field.get("type", "")).lower()
        return BUILTIN_PATTERNS.get(ftype, "")

    async def execute(self, **kwargs) -> SkillResult:
        text = kwargs.get("text")
        fields = kwargs.get("fields") or []
        action = kwargs.get("action", "extract")
        if not text:
            return SkillResult(success=False, error="'text' is required")
        if not isinstance(fields, list) or not fields:
            return SkillResult(success=False, error="'fields' must be a non-empty list")

        try:
            results: Dict[str, Any] = {}
            for field in fields:
                name = field.get("name")
                if not name:
                    continue
                pattern = self._pattern_for(field)
                if not pattern:
                    results[name] = None if action == "extract" else []
                    continue
                try:
                    rx = re.compile(pattern, re.IGNORECASE)
                except re.error as e:
                    results[name] = {"error": f"bad pattern: {e}"}
                    continue

                def _value(m):
                    return m.group(1) if m.groups() else m.group(0)

                if action == "extract_all":
                    results[name] = [_value(m).strip() for m in rx.finditer(text)]
                else:
                    m = rx.search(text)
                    results[name] = _value(m).strip() if m else None

            found = sum(1 for v in results.values() if v)
            return SkillResult(success=True, data={
                "extracted": results,
                "fields_requested": len(fields),
                "fields_found": found,
            })
        except Exception as e:
            return SkillResult(success=False, error=str(e))
