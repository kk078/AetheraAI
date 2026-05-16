"""
State Medicaid rules (top 10 states by enrollment).

Key Medicaid program rules for the top 10 states by enrollment
including eligibility, benefits, and provider requirements.

Source: https://www.medicaid.gov/state-overviews/index.html
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.medicaid.gov/state-overviews/index.html"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "state_medicaid"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.state_medicaid"

STATE_MEDICAID_SUMMARY = {
    "top_10_states": [
        {
            "state": "California",
            "program_name": "Medi-Cal",
            "expansion_status": "Expanded",
            "managed_care_pct": "~80%",
            "key_features": ["Section 1115 waiver", "In-Home Supportive Services", "Medi-Cal Rx (pharmacy carve-out)"],
        },
        {
            "state": "New York",
            "program_name": "Medicaid",
            "expansion_status": "Expanded",
            "managed_care_pct": "~80%",
            "key_features": ["MLTC for dual eligibles", "FIDA-IDD", "Health and Recovery Plans"],
        },
        {
            "state": "Texas",
            "program_name": "STAR/STAR Health",
            "expansion_status": "Not expanded",
            "managed_care_pct": "~90%",
            "key_features": ["STAR managed care", "STAR Kids (disability)", "STAR Health (foster care)", "1115 waiver"],
        },
        {
            "state": "Florida",
            "program_name": "Medicaid",
            "expansion_status": "Not expanded",
            "managed_care_pct": "~90%",
            "key_features": ["Statewide Medicaid Managed Care (SMMC)", "Long-term care managed care"],
        },
        {
            "state": "Illinois",
            "program_name": "Medicaid",
            "expansion_status": "Expanded",
            "managed_care_pct": "~70%",
            "key_features": ["Medicaid Managed Care Organizations", "IlliniCare", "HealthChoice Illinois"],
        },
        {
            "state": "Pennsylvania",
            "program_name": "HealthChoices",
            "expansion_status": "Expanded",
            "managed_care_pct": "~80%",
            "key_features": ["HealthChoices behavioral health", "Physical Health MCOs", "Community HealthChoices for duals"],
        },
        {
            "state": "Ohio",
            "program_name": "Medicaid",
            "expansion_status": "Expanded",
            "managed_care_pct": "~85%",
            "key_features": ["Managed Care Organizations", "MyCare Ohio (dual eligibles)", "Buckeye Health Plan"],
        },
        {
            "state": "Georgia",
            "program_name": "Medicaid/PeachCare",
            "expansion_status": "Not expanded (partial expansion pending)",
            "managed_care_pct": "~75%",
            "key_features": ["Care Management Organizations", "Georgia Families 360", "Peach State Health Plan"],
        },
        {
            "state": "North Carolina",
            "program_name": "Medicaid",
            "expansion_status": "Expanded (2023)",
            "managed_care_pct": "~70%",
            "key_features": ["Standard Plans", "Tailored Plans (behavioral health)", "NC Medicaid Direct"],
        },
        {
            "state": "Michigan",
            "program_name": "Medicaid",
            "expansion_status": "Expanded (Healthy Michigan Plan)",
            "managed_care_pct": "~80%",
            "key_features": ["Healthy Michigan Plan", "MI Health Link (duals)", "Managed care health plans"],
        },
    ],
    "medicaid_basics": {
        "federal_matching": "FMAP (Federal Medical Assistance Percentage) varies by state per-capita income",
        "eligibility_categories": ["Children", "Pregnant women", "Parents/caretakers", "Aged/blind/disabled", "Expansion adults"],
        "mandatory_benefits": ["Inpatient hospital", "Outpatient hospital", "EPSDT (children)", "Nursing facility", "Home health", "Physician services", "Lab/X-ray", "Transportation"],
        "optional_benefits": ["Prescription drugs", "Dental", "Vision", "Physical therapy", "Hospice", "Personal care"],
    },
}


async def download(force: bool = False) -> dict:
    """Download State Medicaid rules reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "state_medicaid.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading State Medicaid rules reference...")
    save_json(STATE_MEDICAID_SUMMARY, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded State Medicaid rules reference"}