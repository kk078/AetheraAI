"""
VA Community Care rules reference.

VA Community Care provides access to care in the community when VA
cannot provide needed services in a timely manner or location.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.va.gov/communitycare/"
DEST_DIR = DATA_ROOT / "healthcare" / "payer_specific" / "va_community_care"
MODULE_NAME = "knowledge_bases.healthcare.payer_specific.va_community_care"

VA_CC_REFERENCE = {
    "eligibility_criteria": [
        "VA cannot provide care within designated access standards (wait time or drive time)",
        "Service is not available at a VA facility",
        "Veteran qualifies under specific eligibility criteria (MISSION Act)",
        "Care is in the best interest of the veteran's health",
        "Veteran is eligible for VA health care",
    ],
    "access_standards": [
        {"type": "Primary care/Mental health", "wait_time": "20 days", "drive_time": "30 minutes"},
        {"type": "Specialty care", "wait_time": "20 days", "drive_time": "60 minutes"},
        {"type": "Urgent care", "wait_time": "Same day/next day", "drive_time": "30 minutes"},
    ],
    "programs": [
        {"program": "Community Care (Mission Act)", "description": "Eligible veterans can receive care from community providers when VA access standards are not met"},
        {"program": "VA Urgent Care", "description": "Walk-in retail clinics and urgent care centers for minor illnesses/injuries without prior authorization"},
        {"program": "Emergency Care", "description": "Community emergency department care when VA emergency care is not readily available; must notify VA within 72 hours"},
        {"program": "Veteran Community Care Program (VCCP)", "description": "The consolidated community care program replacing Choice, MISSION Act, and other legacy programs"},
    ],
    "claims_submission": {
        "preferred_method": "Submit through VA's Community Care Network (CCN) third-party administrator",
        "authorization": "Most care requires prior authorization except urgent/emergency care",
        "payment": "VA pays provider directly at Medicare rates or contracted rates",
    },
}


async def download(force: bool = False) -> dict:
    """Download VA Community Care rules reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "va_community_care.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading VA Community Care rules reference...")
    save_json(VA_CC_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded VA Community Care rules reference"}