"""
Aethera AI - PHI/PII redaction for logs.

A logging filter that scrubs PHI/PII from log records before they are emitted,
so patient data never lands in log files or stdout. It reuses the regex pattern
sets that drive sensitivity detection (`orchestrator/sensitivity.py`) so there is
a single source of truth for what counts as sensitive.

Usage (call once at startup):

    from orchestrator.phi_logging import install_phi_log_redaction
    install_phi_log_redaction()
"""

import logging
import re
from typing import List, Pattern

logger = logging.getLogger("aethera.phi_logging")


def _load_patterns() -> List[Pattern]:
    """Compile the PHI + PII regexes from the sensitivity module.

    Falls back to a small built-in set if that module can't be imported, so the
    filter never silently passes raw text through when sensitivity is optional.
    """
    compiled: List[Pattern] = []
    try:
        from orchestrator.sensitivity import PHIDetector, PIIDetector
        for source in (PHIDetector.PHI_PATTERNS, PIIDetector.PII_PATTERNS):
            for patterns in source.values():
                for p in patterns:
                    try:
                        compiled.append(re.compile(p, re.IGNORECASE))
                    except re.error:
                        continue
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Falling back to built-in redaction patterns: %s", exc)

    if not compiled:
        fallback = [
            r"\b\d{3}-?\d{2}-?\d{4}\b",                         # SSN
            r"\bMRN[#:]?\s*\d{4,}\b",                           # MRN
            r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",                    # email
            r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",  # phone
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",              # date (DOB)
        ]
        compiled = [re.compile(p, re.IGNORECASE) for p in fallback]
    return compiled


REDACTION = "[REDACTED]"


class PHIRedactionFilter(logging.Filter):
    """Redacts PHI/PII from a log record's fully-rendered message."""

    def __init__(self, name: str = ""):
        super().__init__(name)
        self._patterns = _load_patterns()

    def redact(self, text: str) -> str:
        if not text:
            return text
        for pattern in self._patterns:
            text = pattern.sub(REDACTION, text)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # Render args into the message now, then redact the result so PHI in
            # either the format string or its arguments is caught.
            rendered = record.getMessage()
            redacted = self.redact(rendered)
            if redacted != rendered:
                record.msg = redacted
                record.args = ()
        except Exception:  # pragma: no cover - never block logging
            pass
        return True


def install_phi_log_redaction(logger_name: str = "") -> PHIRedactionFilter:
    """Attach the redaction filter to a logger and all of its handlers.

    Attaching to handlers (not just the logger) ensures records that propagate
    up from child loggers are also redacted before emission. Idempotent.
    """
    target = logging.getLogger(logger_name)
    existing = next((f for f in target.filters if isinstance(f, PHIRedactionFilter)), None)
    redactor = existing or PHIRedactionFilter()
    if existing is None:
        target.addFilter(redactor)
    for handler in target.handlers:
        if not any(isinstance(f, PHIRedactionFilter) for f in handler.filters):
            handler.addFilter(redactor)
    return redactor
