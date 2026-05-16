"""
Aethera AI - PHI/PII Sensitivity Detection Module

Detects Protected Health Information (PHI) and Personally Identifiable Information (PII)
in user queries to ensure proper routing (local-only for sensitive data).

HIPAA defines 18 categories of PHI identifiers that must be protected.
This module uses regex patterns and lightweight NLP for detection.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class SensitivityLevel(Enum):
    """Sensitivity levels for query routing."""
    PUBLIC = "public"           # No PHI/PII, can use cloud models
    INTERNAL = "internal"       # Mild sensitivity, prefer local
    PHI = "phi"                 # Contains PHI, MUST use local models only
    PII = "pii"                 # Contains PII, MUST use local models only


@dataclass
class DetectionResult:
    """Result of PHI/PII detection."""
    sensitivity_level: SensitivityLevel
    contains_phi: bool
    contains_pii: bool
    detected_categories: List[str] = field(default_factory=list)
    matched_patterns: List[Dict[str, str]] = field(default_factory=list)
    confidence: float = 0.0
    redacted_text: Optional[str] = None


class PHIDetector:
    """
    Detects Protected Health Information (PHI) per HIPAA Safe Harbor method.

    HIPAA 18 PHI Identifiers:
    1. Names
    2. Geographic data (smaller than state)
    3. Dates (except year) related to individual
    4. Phone numbers
    5. Fax numbers
    6. Email addresses
    7. Social Security Numbers
    8. Medical record numbers
    9. Health plan beneficiary numbers
    10. Account numbers
    11. Certificate/license numbers
    12. Vehicle identifiers
    13. Device identifiers
    14. Web URLs
    15. IP addresses
    16. Biometric identifiers
    17. Full-face photos
    18. Any other unique identifying number/characteristic
    """

    # Regex patterns for PHI detection
    PHI_PATTERNS = {
        # Medical Record Numbers (common formats)
        "medical_record_number": [
            r"\bMRN[#:]\s*\d{6,}\b",
            r"\bMRN#\s*\d{6,}\b",
            r"\bMedical Record(?:\s*#)?[:\s]\s*[A-Z0-9]{6,}\b",
            r"\bPatient ID[:\s]\s*[A-Z0-9]{6,}\b",
            r"\bAccount Number[:\s]\s*[A-Z0-9]{6,}\b",
        ],

        # Health Plan Beneficiary Numbers
        "health_plan_number": [
            r"\bMember ID[:\s]\s*[A-Z0-9]{6,}\b",
            r"\bPolicy Number[:\s]\s*[A-Z0-9]{6,}\b",
            r"\bGroup Number[:\s]\s*[A-Z0-9]{6,}\b",
            r"\bClaim Number[:\s]\s*[A-Z0-9]{6,}\b",
            r"\bInsurance ID[:\s]\s*[A-Z0-9]{6,}\b",
            r"\bMedicare Beneficiary Identifier[:\s]\s*[A-Z0-9]{11}\b",
            r"\bMBI[:\s]\s*[A-Z0-9]{11}\b",
        ],

        # Social Security Numbers
        "ssn": [
            r"\b\d{3}-\d{2}-\d{4}\b",
            r"\bSSN[:\s]\s*\d{3}-?\d{2}-?\d{4}\b",
            r"\bSocial Security[:\s]\s*\d{3}-?\d{2}-?\d{4}\b",
        ],

        # Phone/Fax Numbers (require context prefix to reduce false positives)
        "phone_fax": [
            r"\b(?:phone|fax|tel|telephone|cell|mobile|call|pager)[#:.\s]*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            r"\b(?:phone|fax|tel|telephone|cell|mobile)[#:.\s]+\d[\d\s\-\(\)]{9,}\b",
            r"\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b",
        ],

        # Email Addresses
        "email": [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        ],

        # URLs
        "url": [
            r"https?://[^\s<>\[\]{}|\\^`\"']+",
        ],

        # IP Addresses
        "ip_address": [
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            r"\b[a-fA-F0-9:]+:[a-fA-F0-9:]+:[a-fA-F0-9:]+\b",  # IPv6
        ],

        # Dates (except year) - potential PHI when associated with health info
        "dates_phi": [
            r"\b(?:admitted|discharged|DOB|birth|seen|treated)[#:]\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
            r"\b(?:DOB|date of birth)[#:]\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
        ],

        # Device/Equipment IDs
        "device_id": [
            r"\b(?:device|implant|prosthetic)[#\s:][A-Z0-9]{6,}\b",
            r"\bUDI[:\s]\s*[A-Z0-9]{10,}\b",
        ],

        # Biometric
        "biometric": [
            r"\b(?:fingerprint|retina|iris|facial recognition|voice print)\b",
        ],

        # NPI (National Provider Identifier) - require NPI prefix
        "npi": [
            r"\bNPI[:\s#]\s*\d{10}\b",
            r"\bNational Provider Identifier[:\s#]\s*\d{10}\b",
        ],

        # DEA Number (prescriber identifier)
        "dea_number": [
            r"\bDEA[:\s]\s*[A-Z]{2}\d{7}\b",
            r"\b[A-Z]{2}\d{7}\b",  # Context-dependent
        ],

        # Taxonomy Code
        "taxonomy": [
            r"\b[Tt]axonomy[:\s]\s*\d{2}-[A-Z0-9]{6}\b",
        ],

        # License Numbers
        "license": [
            r"\b(?:license|licence|certification)[#\s:][A-Z0-9]{6,}\b",
        ],
    }

    # Healthcare context keywords that trigger stricter PHI detection
    HEALTHCARE_CONTEXT = [
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
    ]

    def __init__(self):
        self.compiled_patterns = {}
        for category, patterns in self.PHI_PATTERNS.items():
            self.compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def detect(self, text: str) -> DetectionResult:
        """
        Analyze text for PHI/PII and return detection result.

        Args:
            text: User query text to analyze

        Returns:
            DetectionResult with sensitivity level and details
        """
        detected_categories = []
        matched_patterns = []

        # Check for healthcare context (increases sensitivity)
        has_healthcare_context = any(
            keyword.lower() in text.lower()
            for keyword in self.HEALTHCARE_CONTEXT
        )

        # Scan for PHI patterns
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    detected_categories.append(category)
                    for match in matches:
                        matched_patterns.append({
                            "category": category,
                            "match": match,
                            "pattern": pattern.pattern
                        })

        # Determine sensitivity level
        contains_phi = len(detected_categories) > 0
        contains_pii = any(
            cat in detected_categories
            for cat in ["ssn", "email", "phone_fax", "ip_address"]
        )

        # Calculate confidence based on number of detections
        confidence = min(1.0, len(matched_patterns) * 0.2)
        if has_healthcare_context and contains_phi:
            confidence = min(1.0, confidence + 0.3)

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
        redacted_text = self._redact(text, matched_patterns)

        return DetectionResult(
            sensitivity_level=sensitivity_level,
            contains_phi=contains_phi,
            contains_pii=contains_pii,
            detected_categories=list(set(detected_categories)),
            matched_patterns=matched_patterns,
            confidence=confidence,
            redacted_text=redacted_text
        )

    def _redact(self, text: str, matches: List[Dict[str, str]]) -> str:
        """Redact detected PHI/PII from text, preserving structure."""
        redacted = text
        for match_info in matches:
            original = match_info["match"]
            category = match_info["category"]
            # Preserve first/last character for structure, mask the rest
            if len(original) <= 3:
                redaction = f"[{category.upper()} REDACTED]"
            else:
                masked = original[0] + "*" * (len(original) - 2) + original[-1]
                redaction = f"[{category.upper()}:{masked}]"
            redacted = redacted.replace(original, redaction)
        return redacted

    def is_safe_for_cloud(self, text: str) -> bool:
        """Check if text is safe to send to cloud models."""
        result = self.detect(text)
        return result.sensitivity_level in [
            SensitivityLevel.PUBLIC,
            SensitivityLevel.INTERNAL
        ]


class PIIDetector:
    """
    Detects Personally Identifiable Information (PII) beyond HIPAA PHI.

    Includes financial data, personal identifiers, and sensitive personal info.
    """

    PII_PATTERNS = {
        # Credit Card Numbers (require context prefix)
        "credit_card": [
            r"\b(?:credit\s*card|cc|card\s*number|card\s*#)[.:;\s]+\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
            r"\b(?:credit\s*card|cc|card\s*number|card\s*#)[.:;\s]+\d{4}[\s-]?\d{6}[\s-]?\d{5}\b",
        ],

        # Bank Account / Routing
        "bank_account": [
            r"\b(?:account|acct|checking|savings)[#\s:]\s*\d{8,}\b",
            r"\b(?:routing|ABA)[#\s:]\s*\d{9}\b",
        ],

        # Driver's License
        "drivers_license": [
            r"\b(?:DL|driver'?s? license|D\.L\.?)[#\s:]\s*[A-Z0-9]{7,}\b",
        ],

        # Passport
        "passport": [
            r"\b(?:passport)[#\s:]\s*[A-Z0-9]{6,9}\b",
        ],

        # Date of Birth
        "dob": [
            r"\b(?:DOB|date of birth|birth date)[#\s:]\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
        ],

        # Physical Address
        "address": [
            r"\b\d{1,5}\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl)\b",
        ],

        # Names (context-dependent - flagged with keywords)
        "name_context": [
            r"\b(?:name|patient name|member name)[#\s:]\s*[A-Za-z]+\s+[A-Z][a-z]+\b",
        ],
    }

    def __init__(self):
        self.compiled_patterns = {}
        for category, patterns in self.PII_PATTERNS.items():
            self.compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def detect(self, text: str) -> DetectionResult:
        """Analyze text for PII."""
        detected_categories = []
        matched_patterns = []

        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    detected_categories.append(category)
                    for match in matches:
                        matched_patterns.append({
                            "category": category,
                            "match": match,
                            "pattern": pattern.pattern
                        })

        contains_pii = len(detected_categories) > 0
        confidence = min(1.0, len(matched_patterns) * 0.25)

        sensitivity_level = (
            SensitivityLevel.PII if contains_pii
            else SensitivityLevel.PUBLIC
        )

        return DetectionResult(
            sensitivity_level=sensitivity_level,
            contains_phi=False,
            contains_pii=contains_pii,
            detected_categories=list(set(detected_categories)),
            matched_patterns=matched_patterns,
            confidence=confidence,
            redacted_text=text  # PHI detector handles redaction
        )


class SensitivityAnalyzer:
    """
    Combined PHI and PII sensitivity analyzer.
    Primary entry point for the orchestrator.
    """

    def __init__(self):
        self.phi_detector = PHIDetector()
        self.pii_detector = PIIDetector()

    def analyze(self, text: str) -> DetectionResult:
        """
        Perform comprehensive sensitivity analysis.

        Args:
            text: User query to analyze

        Returns:
            Combined DetectionResult from both PHI and PII analysis
        """
        phi_result = self.phi_detector.detect(text)
        pii_result = self.pii_detector.detect(text)

        # Combine results
        all_categories = list(set(
            phi_result.detected_categories + pii_result.detected_categories
        ))
        all_matches = phi_result.matched_patterns + pii_result.matched_patterns

        # Determine highest sensitivity
        if phi_result.sensitivity_level in [SensitivityLevel.PHI]:
            final_level = SensitivityLevel.PHI
        elif pii_result.sensitivity_level == SensitivityLevel.PII:
            final_level = SensitivityLevel.PII
        elif phi_result.sensitivity_level == SensitivityLevel.INTERNAL:
            final_level = SensitivityLevel.INTERNAL
        else:
            final_level = SensitivityLevel.PUBLIC

        # Use PHI detector's redaction if available
        redacted = phi_result.redacted_text or pii_result.redacted_text or text

        return DetectionResult(
            sensitivity_level=final_level,
            contains_phi=phi_result.contains_phi or pii_result.contains_phi,
            contains_pii=phi_result.contains_pii or pii_result.contains_pii,
            detected_categories=all_categories,
            matched_patterns=all_matches,
            confidence=max(phi_result.confidence, pii_result.confidence),
            redacted_text=redacted
        )

    def force_local_model(self, text: str) -> bool:
        """
        Check if query MUST be routed to local model.

        Returns True if text contains PHI or PII that cannot leave the machine.
        """
        result = self.analyze(text)
        return result.sensitivity_level in [
            SensitivityLevel.PHI,
            SensitivityLevel.PII
        ]

    def get_routing_recommendation(self, text: str) -> str:
        """
        Get model routing recommendation based on sensitivity.

        Returns:
            Recommended model name or "any" for cloud-eligible queries
        """
        result = self.analyze(text)

        if result.sensitivity_level == SensitivityLevel.PHI:
            return "aethera-local-fast"  # GPU-accelerated, private
        elif result.sensitivity_level == SensitivityLevel.PII:
            return "aethera-local-fast"
        elif result.sensitivity_level == SensitivityLevel.INTERNAL:
            return "aethera-local-tools"  # Prefer local but not required
        else:
            return "any"  # Cloud-eligible


# Singleton instance for use across the application
_sensitivity_analyzer: Optional[SensitivityAnalyzer] = None


def get_sensitivity_analyzer() -> SensitivityAnalyzer:
    """Get or create the singleton sensitivity analyzer instance."""
    global _sensitivity_analyzer
    if _sensitivity_analyzer is None:
        _sensitivity_analyzer = SensitivityAnalyzer()
    return _sensitivity_analyzer


def analyze_sensitivity(text: str) -> DetectionResult:
    """Convenience function to analyze text sensitivity."""
    return get_sensitivity_analyzer().analyze(text)


def is_safe_for_cloud(text: str) -> bool:
    """Convenience function to check if text is cloud-safe."""
    return not get_sensitivity_analyzer().force_local_model(text)
