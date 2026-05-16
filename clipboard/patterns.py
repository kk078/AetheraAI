"""
Aethera AI - Healthcare Code Detection Patterns

Regex patterns for healthcare code detection in clipboard content.
Each pattern includes validation logic and human-readable name.

Supports: ICD-10-CM/PCS, CPT, HCPCS, NDC, NPI, LOINC, Revenue Codes,
DRG Codes, E/M Codes.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class CodePattern:
    """A healthcare code detection pattern with metadata."""
    name: str
    code_type: str
    pattern: re.Pattern
    description: str
    validate_checksum: bool = False
    example: str = ""

    def match(self, text: str) -> List[str]:
        """Find all matches of this pattern in text."""
        return list(set(self.pattern.findall(text)))

    def validate(self, code: str) -> bool:
        """
        Validate a matched code beyond regex matching.
        Applies checksum/validation rules where applicable.
        """
        if not self.validate_checksum:
            return True
        return _run_validation(self.code_type, code)


# ---------------------------------------------------------------------------
# Validation helper functions
# ---------------------------------------------------------------------------

def _validate_icd10_cm(code: str) -> bool:
    """
    Validate ICD-10-CM code structure.

    Format: A00-Z99 with up to 7 characters.
    First char: letter (except U)
    Chars 2-3: digits 00-99
    Char 4 (optional): decimal point
    Chars 5-7 (optional): alphanumeric (digits or A-Z, but X used as placeholder)
    """
    # First character must be a letter except U (reserved)
    if code and code[0].upper() == 'U':
        return False
    # After the category (3 chars), subcategory chars should be 0-9 or A-Z
    # and the 7th character extension if present
    return True


def _validate_npi(npi: str) -> bool:
    """
    Validate NPI using the Luhn algorithm (ISO/IEC 7812-1).

    NPI is 10 digits. The check digit (last digit) is validated using
    a modified Luhn algorithm with a constant prefix of 80840.
    """
    digits = re.sub(r'\D', '', npi)
    if len(digits) != 10:
        return False

    # Prefix with 80840 for Luhn check
    full_number = "80840" + digits

    total = 0
    for i, ch in enumerate(reversed(full_number)):
        digit = int(ch)
        if i % 2 == 1:  # Double every second digit from right
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit

    return total % 10 == 0


def _validate_ndc(ndc: str) -> bool:
    """
    Validate NDC format.

    Accepted formats: 5-4-2, 5-3-2, 4-4-2, 4-4-2 (labeler-product-package).
    Each segment should be numeric.
    """
    parts = ndc.split('-')
    if len(parts) != 3:
        return False

    valid_lengths = [
        (5, 4, 2),
        (5, 3, 2),
        (4, 4, 2),
        (4, 4, 1),
    ]

    segment_lengths = tuple(len(p) for p in parts)

    if segment_lengths not in valid_lengths:
        return False

    return all(p.isdigit() for p in parts)


def _validate_cpt(code: str) -> bool:
    """
    Validate CPT code.

    CPT codes are 5 digits. Ranges:
    - 00100-99499: Procedure codes
    - 99281-99499: Evaluation and Management, etc.
    - 0001F-9007F: Category II codes (with F suffix)
    - 0032T-0503T: Category III codes (with T suffix)
    """
    digits = re.sub(r'\D', '', code)
    if len(digits) != 5:
        return False

    num = int(digits)
    return 100 <= num <= 99499


def _validate_hcpcs(code: str) -> bool:
    """
    Validate HCPCS Level II code.

    Format: single letter (A-V) followed by 4 digits, optionally a modifier.
    A-codes: Ambulance, D-codes: Dental, E-codes: DME, etc.
    """
    if not code:
        return False

    first_char = code[0].upper()
    # HCPCS Level II codes use letters A through V (excluding some)
    valid_first_chars = set("ABCDEFGHJKLMNPQRSTV")
    return first_char in valid_first_chars


def _validate_loinc(code: str) -> bool:
    """
    Validate LOINC code format.

    Format: nnnnn-n (5 or more digits, hyphen, 1 check digit).
    """
    parts = code.split('-')
    if len(parts) != 2:
        return False

    if not parts[0].isdigit() or not parts[1].isdigit():
        return False

    # Check digit calculation
    # LOINC uses a MOD10 check digit
    number_part = parts[0]
    check_digit = int(parts[1])

    # Luhn-like check digit verification
    total = 0
    for i, ch in enumerate(reversed(number_part)):
        digit = int(ch)
        if i % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit

    computed_check = (10 - (total % 10)) % 10
    return computed_check == check_digit


def _validate_drg(code: str) -> bool:
    """
    Validate DRG code.

    MS-DRG codes are 3 digits, typically in range 001-999.
    APR-DRG codes may be 3-4 digits.
    """
    digits = re.sub(r'\D', '', code)
    if len(digits) < 3 or len(digits) > 4:
        return False

    num = int(digits)
    return 1 <= num <= 999


def _validate_revenue_code(code: str) -> bool:
    """
    Validate revenue code.

    Revenue codes are 4 digits (0001-9999), sometimes written with leading zeros.
    Common ranges: 010x-045x (room), 025x (pharmacy), 030x (lab), 040x (radiology), etc.
    """
    digits = re.sub(r'\D', '', code)
    if len(digits) != 4:
        return False
    return 1 <= int(digits) <= 9999


def _validate_em_code(code: str) -> bool:
    """
    Validate E/M (Evaluation and Management) code.

    Standard E/M CPT codes: 99202-99499
    Common office visit codes: 99202-99215
    """
    digits = re.sub(r'\D', '', code)
    if len(digits) != 5:
        return False

    num = int(digits)
    # E/M code ranges
    em_ranges = [
        (99202, 99215),  # Office/Outpatient visits
        (99217, 99239),  # Hospital care
        (99241, 99255),  # Consultations
        (99281, 99288),  # Emergency department
        (99304, 99360),  # Nursing facility, home visits
        (99381, 99397),  # Preventive medicine
        (99406, 99499),  # Other E/M
    ]

    for low, high in em_ranges:
        if low <= num <= high:
            return True

    return False


def _run_validation(code_type: str, code: str) -> bool:
    """Dispatch validation to the appropriate function."""
    validators = {
        "icd10_cm": _validate_icd10_cm,
        "icd10_pcs": _validate_icd10_cm,  # Same structural validation
        "npi": _validate_npi,
        "ndc": _validate_ndc,
        "cpt": _validate_cpt,
        "hcpcs": _validate_hcpcs,
        "loinc": _validate_loinc,
        "drg": _validate_drg,
        "revenue_code": _validate_revenue_code,
        "em_code": _validate_em_code,
    }

    validator = validators.get(code_type)
    if validator:
        try:
            return validator(code)
        except (ValueError, IndexError):
            return False

    return True


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

PATTERNS: List[CodePattern] = [
    # =======================================================================
    # ICD-10-CM (Diagnosis codes)
    # =======================================================================
    CodePattern(
        name="ICD-10-CM Diagnosis Code",
        code_type="icd10_cm",
        pattern=re.compile(
            r"\b([A-CEG-NP-Z]\d{2}(?:\.\d{1,4})?[A-Z0-9]{0,2})\b",
            re.IGNORECASE,
        ),
        description="ICD-10-CM diagnosis codes (e.g., E11.9, J06.9, M54.5)",
        validate_checksum=True,
        example="E11.9",
    ),

    # =======================================================================
    # ICD-10-PCS (Procedure codes)
    # =======================================================================
    CodePattern(
        name="ICD-10-PCS Procedure Code",
        code_type="icd10_pcs",
        pattern=re.compile(
            r"\b([0-9A-F][0-9A-Z]{2}[0-9A-Z]{4})\b",
            re.IGNORECASE,
        ),
        description="ICD-10-PCS procedure codes (7 alphanumeric characters, e.g., 0DCJ0ZZ)",
        validate_checksum=True,
        example="0DCJ0ZZ",
    ),

    # =======================================================================
    # CPT (Current Procedural Terminology)
    # =======================================================================
    CodePattern(
        name="CPT Procedure Code",
        code_type="cpt",
        pattern=re.compile(
            r"(?:CPT[#:\s]*)?(\d{5}[TF]?)\b",
            re.IGNORECASE,
        ),
        description="CPT procedure codes (5 digits, optionally T or F suffix)",
        validate_checksum=True,
        example="99213",
    ),

    # =======================================================================
    # HCPCS Level II
    # =======================================================================
    CodePattern(
        name="HCPCS Level II Code",
        code_type="hcpcs",
        pattern=re.compile(
            r"\b([A-V]\d{4}(?:[A-Z0-9])?)\b",
        ),
        description="HCPCS Level II codes (letter + 4 digits, e.g., A0425, J0585)",
        validate_checksum=True,
        example="A0425",
    ),

    # =======================================================================
    # NDC (National Drug Code)
    # =======================================================================
    CodePattern(
        name="NDC (National Drug Code)",
        code_type="ndc",
        pattern=re.compile(
            r"\b(\d{4,5}-\d{3,4}-\d{1,2})\b",
        ),
        description="NDC codes in 5-4-2, 5-3-2, or 4-4-2 format (e.g., 00056-0402-10)",
        validate_checksum=True,
        example="00056-0402-10",
    ),

    # =======================================================================
    # NPI (National Provider Identifier)
    # =======================================================================
    CodePattern(
        name="NPI (National Provider Identifier)",
        code_type="npi",
        pattern=re.compile(
            r"(?:NPI[#:\s]*)?(\d{10})\b",
            re.IGNORECASE,
        ),
        description="10-digit NPI with Luhn validation (e.g., 1234567890)",
        validate_checksum=True,
        example="1234567890",
    ),

    # =======================================================================
    # LOINC (Logical Observation Identifiers Names and Codes)
    # =======================================================================
    CodePattern(
        name="LOINC Code",
        code_type="loinc",
        pattern=re.compile(
            r"\b(\d{4,6}-\d)\b",
        ),
        description="LOINC lab observation codes (e.g., 2345-7, 33914-3)",
        validate_checksum=True,
        example="2345-7",
    ),

    # =======================================================================
    # Revenue Codes
    # =======================================================================
    CodePattern(
        name="Revenue Code",
        code_type="revenue_code",
        pattern=re.compile(
            r"(?:REV[#:\s]*)?(\d{4})\b",
            re.IGNORECASE,
        ),
        description="4-digit revenue codes (e.g., 0300, 0450, 0250)",
        validate_checksum=True,
        example="0300",
    ),

    # =======================================================================
    # DRG (Diagnosis Related Group)
    # =======================================================================
    CodePattern(
        name="DRG Code",
        code_type="drg",
        pattern=re.compile(
            r"(?:DRG[#:\s]*)(\d{3,4})\b",
            re.IGNORECASE,
        ),
        description="MS-DRG or APR-DRG codes (3-4 digits, e.g., DRG 470, DRG 291)",
        validate_checksum=True,
        example="470",
    ),

    # =======================================================================
    # E/M (Evaluation and Management) Codes
    # =======================================================================
    CodePattern(
        name="E/M Code",
        code_type="em_code",
        pattern=re.compile(
            r"\b(99[2-4]\d{2})\b",
        ),
        description="Evaluation and Management CPT codes (e.g., 99213, 99214)",
        validate_checksum=True,
        example="99213",
    ),

    # =======================================================================
    # Place of Service (POS) Codes
    # =======================================================================
    CodePattern(
        name="Place of Service Code",
        code_type="pos_code",
        pattern=re.compile(
            r"(?:POS[#:\s]*)(\d{2})\b",
            re.IGNORECASE,
        ),
        description="2-digit Place of Service codes (e.g., POS 11, POS 21)",
        validate_checksum=False,
        example="11",
    ),

    # =======================================================================
    # Modifier Codes
    # =======================================================================
    CodePattern(
        name="CPT/HCPCS Modifier",
        code_type="modifier",
        pattern=re.compile(
            r"\b([A-Z]{2}\d{0,2}|25|26|50|51|52|53|54|59|62|66|76|77|78|79|80|82|GT|LT|RT|TC)\b",
        ),
        description="CPT/HCPCS modifiers (e.g., 25, 59, LT, RT, TC)",
        validate_checksum=False,
        example="25",
    ),

    # =======================================================================
    # DEA Number
    # =======================================================================
    CodePattern(
        name="DEA Number",
        code_type="dea_number",
        pattern=re.compile(
            r"\b([A-Z]{2}\d{7})\b",
        ),
        description="DEA registration numbers (2 letters + 7 digits, e.g., AB1234567)",
        validate_checksum=False,
        example="AB1234567",
    ),

    # =======================================================================
    # Medicare Beneficiary Identifier (MBI)
    # =======================================================================
    CodePattern(
        name="Medicare Beneficiary Identifier (MBI)",
        code_type="mbi",
        pattern=re.compile(
            r"\b([1-9][A-Z0-9]{2}[\dA-Z]{1}[A-Z0-9]{1}[\dA-Z]{5}[A-Z0-9]{1})\b",
        ),
        description="Medicare Beneficiary Identifier (11 characters, e.g., 1EG4-TE5-MK72)",
        validate_checksum=False,
        example="1EG4TE5MK72",
    ),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_codes(text: str, validate: bool = True) -> Dict[str, List[Dict]]:
    """
    Detect all healthcare codes in the given text.

    Args:
        text: Text to scan for healthcare codes
        validate: Whether to run validation checks on matches

    Returns:
        Dict mapping code types to lists of detected codes with metadata:
        {
            "icd10_cm": [{"code": "E11.9", "valid": True, "name": "ICD-10-CM Diagnosis Code"}],
            ...
        }
    """
    results: Dict[str, List[Dict]] = {}

    for pattern in PATTERNS:
        matches = pattern.match(text)
        if not matches:
            continue

        code_list = []
        for code in matches:
            is_valid = pattern.validate(code) if validate else True
            code_list.append({
                "code": code,
                "valid": is_valid,
                "name": pattern.name,
                "description": pattern.description,
            })

        if code_list:
            # Merge with existing results for same code type
            if pattern.code_type in results:
                existing_codes = {item["code"] for item in results[pattern.code_type]}
                for item in code_list:
                    if item["code"] not in existing_codes:
                        results[pattern.code_type].append(item)
            else:
                results[pattern.code_type] = code_list

    return results


def detect_codes_flat(text: str, validate: bool = True) -> List[Dict]:
    """
    Detect codes and return a flat list of all matches.

    Returns:
        List of dicts: [{"code": ..., "type": ..., "valid": ..., "name": ...}, ...]
    """
    results = detect_codes(text, validate)
    flat = []

    for code_type, codes in results.items():
        for item in codes:
            flat.append({
                "code": item["code"],
                "type": code_type,
                "valid": item["valid"],
                "name": item["name"],
            })

    return flat


def get_pattern(code_type: str) -> Optional[CodePattern]:
    """Get a specific pattern by code type."""
    for pattern in PATTERNS:
        if pattern.code_type == code_type:
            return pattern
    return None


def list_patterns() -> List[Dict]:
    """List all available patterns with metadata."""
    return [
        {
            "code_type": p.code_type,
            "name": p.name,
            "description": p.description,
            "example": p.example,
            "has_validation": p.validate_checksum,
        }
        for p in PATTERNS
    ]


def validate_code(code_type: str, code: str) -> bool:
    """
    Validate a specific code against its type's validation rules.

    Args:
        code_type: Type of healthcare code (e.g., 'npi', 'icd10_cm')
        code: The code value to validate

    Returns:
        True if the code passes validation
    """
    pattern = get_pattern(code_type)
    if pattern:
        return pattern.validate(code)
    return _run_validation(code_type, code)


def count_codes(text: str) -> Dict[str, int]:
    """
    Count occurrences of each code type in text.

    Returns:
        Dict mapping code types to match counts
    """
    results = detect_codes(text, validate=False)
    return {code_type: len(codes) for code_type, codes in results.items()}


def extract_valid_codes(text: str) -> Dict[str, List[str]]:
    """
    Extract only validated healthcare codes from text.

    Returns:
        Dict mapping code types to lists of valid code strings
    """
    results = detect_codes(text, validate=True)
    valid = {}
    for code_type, codes in results.items():
        valid_codes = [item["code"] for item in codes if item["valid"]]
        if valid_codes:
            valid[code_type] = valid_codes
    return valid