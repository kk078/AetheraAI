"""
EMTALA text reference.

The Emergency Medical Treatment and Labor Act requires hospitals
with emergency departments to provide screening and stabilization
regardless of ability to pay.

Source: 42 U.S.C. 1395dd; 42 CFR 489.24
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Regulations-and-Guidance/Legislation/EMTALA"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "emtala"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.emtala"

EMTALA_REFERENCE = {
    "full_name": "Emergency Medical Treatment and Labor Act (EMTALA)",
    "citation": "42 U.S.C. 1395dd; 42 CFR 489.24",
    "applicable_hospitals": "All Medicare-participating hospitals with dedicated emergency departments",
    "key_requirements": [
        {
            "requirement": "Medical Screening Examination (MSE)",
            "description": "Hospital must provide an appropriate MSE to anyone who comes to the ED requesting examination or treatment for a medical condition. The MSE must be conducted within the hospital's capacity and may not be delayed to inquire about payment or insurance.",
        },
        {
            "requirement": "Stabilization",
            "description": "If the MSE reveals an emergency medical condition (EMC), the hospital must either stabilize the condition within its capability or transfer the patient to another facility with the appropriate capability.",
        },
        {
            "requirement": "Appropriate Transfer",
            "description": "If a patient with an EMC is transferred, the hospital must meet transfer requirements including providing treatment to minimize risks, obtaining informed consent, sending medical records, and ensuring the receiving facility has capacity.",
        },
    ],
    "emergency_medical_condition": "A condition manifesting itself by acute symptoms of sufficient severity that absence of immediate medical attention could result in serious jeopardy to health, serious impairment to bodily functions, or serious dysfunction of any bodily organ or part",
    "penalties": [
        "Civil monetary penalties up to $50,000 per violation (adjusted for inflation)",
        "Hospitals with <100 beds: up to $25,000 per violation",
        "Physicians: up to $50,000 per violation",
        "Exclusion from Medicare/Medicaid for repeated violations",
    ],
    "special_situations": [
        "Psychiatric emergencies (including substance abuse)",
        "Pregnant women in labor (must be admitted and treated)",
        "On-call physician availability requirements",
        "Hospitals with specialized capabilities (must accept appropriate transfers)",
    ],
}


async def download(force: bool = False) -> dict:
    """Download EMTALA reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "emtala.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading EMTALA reference...")
    save_json(EMTALA_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded EMTALA reference"}