"""
Aethera AI — Stage 1: Document Classifier

Identifies file type, domain, and sensitivity level for pipeline routing.
"""
import os
import logging
from typing import Dict

from .stages import PipelineStage
from .context import PipelineContext

logger = logging.getLogger("aethera.pipeline.classifier")

# File extension to type mapping
FILE_TYPE_MAP: Dict[str, str] = {
    ".pdf": "pdf", ".docx": "docx", ".doc": "docx",
    ".xlsx": "xlsx", ".xls": "xlsx", ".csv": "csv",
    ".pptx": "pptx", ".ppt": "pptx",
    ".txt": "txt", ".md": "txt", ".rtf": "txt",
    ".html": "html", ".htm": "html",
    ".json": "json", ".xml": "xml", ".yaml": "json", ".yml": "json",
    ".png": "image", ".jpg": "image", ".jpeg": "image",
    ".gif": "image", ".bmp": "image", ".tiff": "image", ".tif": "image",
    ".eml": "email", ".msg": "email",
}

# Domain keyword sets for classification
DOMAIN_KEYWORDS = {
    "healthcare": {
        "diagnosis", "patient", "medical", "clinical", "icd-10", "cpt", "hcpcs",
        "claim", "denial", "payer", "provider", "reimbursement", "medicare",
        "medicaid", "prior auth", "appeal", "eob", "era", "edi", "837", "835",
        "hipaa", "phi", "procedure", "drug", "prescription", "formulary",
        "copay", "deductible", "coinsurance", "out-of-pocket",
    },
    "finance": {
        "revenue", "expense", "profit", "loss", "balance", "invoice",
        "payment", "tax", "interest", "dividend", "portfolio", "investment",
        "accounting", "ledger", "depreciation", "amortization", "forecast",
    },
    "legal": {
        "contract", "agreement", "liability", "compliance", "regulation",
        "statute", "ordinance", "litigation", "defendant", "plaintiff",
        "court", "ruling", "statute of limitations", "breach",
    },
    "technology": {
        "api", "database", "server", "deployment", "docker", "kubernetes",
        "cloud", "infrastructure", "network", "security", "encryption",
        "devops", "ci/cd", "microservice", "container",
    },
}

MIME_TYPE_MAP = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "text/csv": "csv", "text/plain": "txt", "text/html": "html",
    "application/json": "json", "application/xml": "xml", "text/xml": "xml",
    "message/rfc822": "email",
}


class DocumentClassifier(PipelineStage):
    """Stage 1: Classify file type, domain, and sensitivity."""

    name = "classifier"

    @property
    def required_content(self) -> bool:
        return False

    async def execute(self, context: PipelineContext) -> PipelineContext:
        # Handle URL input
        if context.url:
            context.file_type = "url"
        else:
            # Determine file type from extension or content_type
            context.file_type = self._detect_file_type(context)

        # Classify domain from initial content (if available)
        context.domain = self._classify_domain(context)

        # Run sensitivity analysis on available text
        await self._classify_sensitivity(context)

        logger.info(
            f"Classified: type={context.file_type}, domain={context.domain}, "
            f"sensitivity={context.sensitivity}"
        )
        return context

    def _detect_file_type(self, context: PipelineContext) -> str:
        """Detect file type from extension or MIME type."""
        # Try MIME type first
        if context.content_type and context.content_type in MIME_TYPE_MAP:
            return MIME_TYPE_MAP[context.content_type]

        # Try file extension
        _, ext = os.path.splitext(context.filename or context.file_path)
        ext = ext.lower()
        if ext in FILE_TYPE_MAP:
            return FILE_TYPE_MAP[ext]

        # Try content_type partial match
        if context.content_type:
            ct = context.content_type.lower()
            if "pdf" in ct: return "pdf"
            if "word" in ct or "docx" in ct: return "docx"
            if "sheet" in ct or "xlsx" in ct: return "xlsx"
            if "presentation" in ct or "pptx" in ct: return "pptx"
            if "image" in ct: return "image"
            if "html" in ct: return "html"
            if "json" in ct: return "json"
            if "xml" in ct: return "xml"
            if "text" in ct: return "txt"

        return "unknown"

    def _classify_domain(self, context: PipelineContext) -> str:
        """Classify document domain from content keywords."""
        # Use raw_text if already available, or read a preview
        text = context.raw_text
        if not text and context.file_path:
            try:
                with open(context.file_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read(4096)
            except Exception:
                pass

        if not text:
            # Infer from filename
            name_lower = (context.filename or "").lower()
            for domain, keywords in DOMAIN_KEYWORDS.items():
                for kw in keywords:
                    if kw in name_lower:
                        return domain
            return "general"

        text_lower = text.lower()
        scores = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            scores[domain] = sum(1 for kw in keywords if kw in text_lower)

        best_domain = max(scores, key=scores.get) if scores else "general"
        return best_domain if scores.get(best_domain, 0) >= 2 else "general"

    async def _classify_sensitivity(self, context: PipelineContext) -> None:
        """Run PHI/PII detection on available content."""
        text = context.raw_text
        if not text and context.file_path:
            try:
                with open(context.file_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read(4096)
            except Exception:
                pass

        if not text:
            context.sensitivity = "public"
            context.contains_phi = False
            context.contains_pii = False
            return

        try:
            from orchestrator.sensitivity import SensitivityAnalyzer
            analyzer = SensitivityAnalyzer()
            result = analyzer.analyze(text)
            context.sensitivity = result.sensitivity_level.value
            context.contains_phi = result.contains_phi
            context.contains_pii = result.contains_pii
        except Exception:
            # If analyzer unavailable, check for common patterns
            import re
            ssn_pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
            mrn_pattern = re.compile(r"\bMRN[:\s]?\d+\b", re.IGNORECASE)
            if ssn_pattern.search(text) or mrn_pattern.search(text):
                context.sensitivity = "phi"
                context.contains_phi = True
            else:
                context.sensitivity = "public"
                context.contains_phi = False
                context.contains_pii = False