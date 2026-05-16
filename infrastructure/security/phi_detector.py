"""
Aethera AI - PHI/PII Detection Engine

Regex patterns from orchestrator/sensitivity.py plus additional
ML-based NER (Named Entity Recognition) if spaCy is available.

Functions: detect_phi, redact_phi, get_confidence, batch_scan.
"""

import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("aethera.phi_detector")


# ---------------------------------------------------------------------------
# Sensitivity levels
# ---------------------------------------------------------------------------

class SensitivityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PHI = "phi"
    PII = "pii"


# ---------------------------------------------------------------------------
# Detection result
# ---------------------------------------------------------------------------

@dataclass
class PHIDetectionResult:
    """Result of PHI/PII detection on text."""
    text: str
    sensitivity_level: SensitivityLevel
    contains_phi: bool
    contains_pii: bool
    detected_categories: List[str] = field(default_factory=list)
    matches: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    redacted_text: Optional[str] = None
    ner_entities: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# PHI patterns (from orchestrator/sensitivity.py, enhanced)
# ---------------------------------------------------------------------------

PHI_PATTERNS = {
    "medical_record_number": [
        r"\bMRN[#:]\s*\d{6,}\b",
        r"\bMRN#\s*\d{6,}\b",
        r"\bMedical Record(?:\s*#)?[:\s]\s*[A-Z0-9]{6,}\b",
        r"\bPatient ID[:\s]\s*[A-Z0-9]{6,}\b",
    ],
    "health_plan_number": [
        r"\bMember ID[:\s]\s*[A-Z0-9]{6,}\b",
        r"\bPolicy Number[:\s]\s*[A-Z0-9]{6,}\b",
        r"\bGroup Number[:\s]\s*[A-Z0-9]{6,}\b",
        r"\bClaim Number[:\s]\s*[A-Z0-9]{6,}\b",
        r"\bInsurance ID[:\s]\s*[A-Z0-9]{6,}\b",
        r"\bMedicare Beneficiary Identifier[:\s]\s*[A-Z0-9]{11}\b",
        r"\bMBI[:\s]\s*[A-Z0-9]{11}\b",
    ],
    "ssn": [
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\bSSN[:\s]\s*\d{3}-?\d{2}-?\d{4}\b",
    ],
    "phone_fax": [
        r"\b(?:phone|fax|tel|telephone)[#:]\s*[\d\s\-\(\)]{10,}\b",
        r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
        r"\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b",
    ],
    "email": [
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    ],
    "url": [
        r"https?://[^\s<>\[\]{}|\\^`\"']+",
    ],
    "ip_address": [
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    ],
    "dates_phi": [
        r"\b(?:admitted|discharged|DOB|birth|seen|treated)[#:]\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
        r"\b(?:DOB|date of birth)[#:]\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
    ],
    "device_id": [
        r"\b(?:device|implant|prosthetic)[#\s:][A-Z0-9]{6,}\b",
        r"\bUDI[:\s]\s*[A-Z0-9]{10,}\b",
    ],
    "npi": [
        r"\bNPI[:\s]\s*\d{10}\b",
    ],
    "dea_number": [
        r"\bDEA[:\s]\s*[A-Z]{2}\d{7}\b",
        r"\b[A-Z]{2}\d{7}\b",
    ],
    "address": [
        r"\b\d{1,5}\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl)\b",
    ],
    "name_context": [
        r"\b(?:name|patient name|member name)[#\s:]\s*[A-Za-z]+\s+[A-Z][a-z]+\b",
    ],
    "credit_card": [
        r"\b4[0-9]{12}(?:[0-9]{3})?\b",
        r"\b5[1-5][0-9]{14}\b",
        r"\b3[47][0-9]{13}\b",
    ],
    "bank_account": [
        r"\b(?:account|acct|checking|savings)[#\s:]\s*\d{8,}\b",
        r"\b(?:routing|ABA)[#\s:]\s*\d{9}\b",
    ],
    "drivers_license": [
        r"\b(?:DL|driver'?s? license|D\.L\.?)[#\s:]\s*[A-Z0-9]{7,}\b",
    ],
    "passport": [
        r"\b(?:passport)[#\s:]\s*[A-Z0-9]{6,9}\b",
    ],
    "dob": [
        r"\b(?:DOB|date of birth|birth date)[#\s:]\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
    ],
    "biometric": [
        r"\b(?:fingerprint|retina|iris|facial recognition|voice print)\b",
    ],
    "icd10_code": [
        r"\b[A-CEG-NP-Z]\d{2}(?:\.\d{1,4})?[A-Z0-9]{0,2}\b",
    ],
    "mrn_barcode": [
        r"\b(?:barcode|QR code)[:\s]\s*[A-Z0-9]{8,}\b",
    ],
}

# Healthcare context keywords that trigger stricter detection
HEALTHCARE_CONTEXT_KEYWORDS = [
    "patient", "diagnosis", "treatment", "medication", "prescription",
    "lab result", "test result", "symptom", "condition", "disease",
    "hospital", "clinic", "physician", "doctor", "nurse", "provider",
    "admitted", "discharged", "inpatient", "outpatient", "ER", "ED",
    "surgery", "procedure", "biopsy", "scan", "MRI", "CT", "X-ray",
    "blood", "urine", "specimen", "sample", "pathology", "radiology",
    "oncology", "cardiology", "neurology", "psychiatry", "therapy",
    "dosage", "mg", "ml", "tablet", "capsule", "injection", "infusion",
    "ICU", "NICU", "PICU", "CCU", "stepdown", "telemetry",
    "claim", "EOB", "ERA", "denial", "appeal", "authorization",
    "HIPAA", "PHI", "protected health information", "confidential",
    "EHR", "EMR", "electronic health record", "medical record",
    "insurance", "payer", "Medicare", "Medicaid", "benefits",
    "referral", "prior auth", "pre-certification",
]


# ---------------------------------------------------------------------------
# PHIDetector class
# ---------------------------------------------------------------------------

class PHIDetector:
    """
    Comprehensive PHI/PII detector combining regex pattern matching
    with optional spaCy NER for enhanced detection.
    """

    def __init__(self, enable_ner: Optional[bool] = None):
        self.compiled_patterns = {}
        for category, patterns in PHI_PATTERNS.items():
            self.compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

        # NER (Named Entity Recognition) with spaCy
        self._nlp = None
        self._ner_enabled = False

        if enable_ner is None:
            enable_ner = os.getenv("PHI_NER_ENABLED", "false").lower() == "true"

        if enable_ner:
            self._init_ner()

    def _init_ner(self):
        """Initialize spaCy NER model."""
        try:
            import spacy

            model_name = os.getenv("PHI_NER_MODEL", "en_core_web_sm")

            if spacy.util.is_package(model_name):
                self._nlp = spacy.load(model_name)
            else:
                logger.info("Downloading spaCy model: %s", model_name)
                spacy.cli.download(model_name)
                self._nlp = spacy.load(model_name)

            self._ner_enabled = True
            logger.info("spaCy NER enabled with model: %s", model_name)

        except ImportError:
            logger.info("spaCy not available. Install with: pip install spacy")
        except Exception as exc:
            logger.warning("spaCy NER init failed: %s", exc)

    def detect_phi(self, text: str) -> PHIDetectionResult:
        """
        Detect PHI/PII in text using regex patterns and optional NER.

        Args:
            text: Text to analyze

        Returns:
            PHIDetectionResult with detection details
        """
        detected_categories = []
        all_matches = []

        # Check for healthcare context
        has_healthcare_context = any(
            keyword.lower() in text.lower()
            for keyword in HEALTHCARE_CONTEXT_KEYWORDS
        )

        # Regex pattern matching
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    detected_categories.append(category)
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0] if match else ""
                        all_matches.append({
                            "category": category,
                            "match": str(match),
                            "pattern": pattern.pattern,
                            "method": "regex",
                        })

        # Deduplicate categories
        detected_categories = list(set(detected_categories))

        # NER-based detection
        ner_entities = []
        if self._ner_enabled and self._nlp:
            ner_entities = self._detect_ner(text)

            for entity in ner_entities:
                cat = self._map_ner_label(entity["label"])
                if cat and cat not in detected_categories:
                    detected_categories.append(cat)
                all_matches.append({
                    "category": cat or entity["label"],
                    "match": entity["text"],
                    "pattern": f"NER:{entity['label']}",
                    "method": "ner",
                    "confidence": entity.get("confidence", 0.0),
                })

        # Determine sensitivity
        contains_phi = bool(detected_categories)
        contains_pii = any(
            cat in detected_categories
            for cat in ["ssn", "email", "phone_fax", "ip_address", "credit_card",
                        "bank_account", "drivers_license", "passport", "dob",
                        "address", "name_context"]
        )

        # Calculate confidence
        confidence = min(1.0, len(all_matches) * 0.15)
        if has_healthcare_context and contains_phi:
            confidence = min(1.0, confidence + 0.3)
        ner_confidence = max(
            (m.get("confidence", 0.0) for m in all_matches if m.get("method") == "ner"),
            default=0.0,
        )
        confidence = max(confidence, ner_confidence)

        # Determine final sensitivity level
        if contains_phi and has_healthcare_context:
            sensitivity_level = SensitivityLevel.PHI
        elif contains_pii:
            sensitivity_level = SensitivityLevel.PII
        elif contains_phi:
            sensitivity_level = SensitivityLevel.PHI
        elif has_healthcare_context:
            sensitivity_level = SensitivityLevel.INTERNAL
        else:
            sensitivity_level = SensitivityLevel.PUBLIC

        # Generate redacted text
        redacted_text = self._redact(text, all_matches)

        return PHIDetectionResult(
            text=text,
            sensitivity_level=sensitivity_level,
            contains_phi=contains_phi,
            contains_pii=contains_pii,
            detected_categories=detected_categories,
            matches=all_matches,
            confidence=round(confidence, 3),
            redacted_text=redacted_text,
            ner_entities=ner_entities,
        )

    def _detect_ner(self, text: str) -> List[Dict]:
        """Detect entities using spaCy NER."""
        entities = []

        try:
            doc = self._nlp(text)

            for ent in doc.ents:
                # Map spaCy entity labels to PHI categories
                phi_relevant_labels = {
                    "PERSON", "ORG", "GPE", "LOC", "DATE",
                    "FAC", "NORP", "CARDINAL",
                }

                if ent.label_ in phi_relevant_labels:
                    entities.append({
                        "text": ent.text,
                        "label": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "confidence": 0.7,  # spaCy doesn't provide confidence by default
                    })

        except Exception as exc:
            logger.warning("NER detection error: %s", exc)

        return entities

    def _map_ner_label(self, label: str) -> Optional[str]:
        """Map spaCy NER label to PHI category."""
        label_map = {
            "PERSON": "name_context",
            "GPE": "address",
            "LOC": "address",
            "FAC": "address",
            "DATE": "dates_phi",
            "ORG": "health_plan_number",
            "CARDINAL": None,  # Too generic
            "NORP": None,
        }
        return label_map.get(label)

    def _redact(self, text: str, matches: List[Dict]) -> str:
        """Redact detected PHI/PII from text."""
        redacted = text

        # Sort matches by length (longest first) to avoid partial redactions
        sorted_matches = sorted(
            matches,
            key=lambda m: len(m.get("match", "")),
            reverse=True,
        )

        for match_info in sorted_matches:
            original = match_info.get("match", "")
            category = match_info.get("category", "UNKNOWN")
            redaction = f"[{category.upper()} REDACTED]"
            redacted = redacted.replace(original, redaction)

        return redacted

    def redact_phi(self, text: str, replacement: str = "[REDACTED]") -> str:
        """
        Redact all detected PHI/PII from text.

        Args:
            text: Text to redact
            replacement: Replacement string for redacted content

        Returns:
            Redacted text
        """
        result = self.detect_phi(text)

        redacted = text
        # Re-sort matches for consistent replacement
        sorted_matches = sorted(
            result.matches,
            key=lambda m: len(m.get("match", "")),
            reverse=True,
        )

        for match_info in sorted_matches:
            original = match_info.get("match", "")
            redacted = redacted.replace(original, replacement)

        return redacted

    def get_confidence(self, text: str) -> float:
        """
        Get the confidence score for PHI/PII detection.

        Args:
            text: Text to analyze

        Returns:
            Confidence score between 0.0 and 1.0
        """
        result = self.detect_phi(text)
        return result.confidence

    def batch_scan(self, texts: List[str]) -> List[PHIDetectionResult]:
        """
        Scan multiple texts for PHI/PII.

        Args:
            texts: List of text strings to scan

        Returns:
            List of PHIDetectionResult objects
        """
        results = []
        for text in texts:
            result = self.detect_phi(text)
            results.append(result)

        return results

    def is_safe_for_cloud(self, text: str) -> bool:
        """Check if text is safe to send to cloud models."""
        result = self.detect_phi(text)
        return result.sensitivity_level in [
            SensitivityLevel.PUBLIC,
            SensitivityLevel.INTERNAL,
        ]

    def get_routing_recommendation(self, text: str) -> str:
        """Get model routing recommendation based on sensitivity."""
        result = self.detect_phi(text)

        if result.sensitivity_level == SensitivityLevel.PHI:
            return "aethera-local-fast"
        elif result.sensitivity_level == SensitivityLevel.PII:
            return "aethera-local-fast"
        elif result.sensitivity_level == SensitivityLevel.INTERNAL:
            return "aethera-local-tools"
        else:
            return "any"


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_detector: Optional[PHIDetector] = None


def get_phi_detector() -> PHIDetector:
    """Get or create the singleton PHI detector."""
    global _detector
    if _detector is None:
        _detector = PHIDetector()
    return _detector


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def detect_phi(text: str) -> PHIDetectionResult:
    """Detect PHI/PII in text."""
    return get_phi_detector().detect_phi(text)


def redact_phi(text: str, replacement: str = "[REDACTED]") -> str:
    """Redact all detected PHI/PII from text."""
    return get_phi_detector().redact_phi(text, replacement)


def get_confidence(text: str) -> float:
    """Get confidence score for PHI/PII detection."""
    return get_phi_detector().get_confidence(text)


def batch_scan(texts: List[str]) -> List[PHIDetectionResult]:
    """Scan multiple texts for PHI/PII."""
    return get_phi_detector().batch_scan(texts)


def is_safe_for_cloud(text: str) -> bool:
    """Check if text is safe for cloud model routing."""
    return get_phi_detector().is_safe_for_cloud(text)