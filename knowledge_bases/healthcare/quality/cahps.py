"""
CAHPS survey measures reference.

Consumer Assessment of Healthcare Providers and Systems surveys
measure patient experience across healthcare settings.

Source: https://www.ahrq.gov/cahps/index.html
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.ahrq.gov/cahps/index.html"
DEST_DIR = DATA_ROOT / "healthcare" / "quality" / "cahps"
MODULE_NAME = "knowledge_bases.healthcare.quality.cahps"

CAHPS_SURVEYS = [
    {"survey": "Health Plan Survey", "description": "Measures enrollee experience with health plans", "composites": ["Getting needed care", "Getting care quickly", "Doctor communication", "Customer service", "Rating of health plan", "Rating of health care", "Rating of personal doctor", "Rating of specialist"]},
    {"survey": "Clinician/Group Survey", "description": "Measures patient experience with physicians and medical groups", "composites": ["Access to care", "Communication", "Care coordination", "Office staff", "Rating of provider"]},
    {"survey": "Hospital Survey (HCAHPS)", "description": "Measures patient experience with hospital care", "composites": ["Nurse communication", "Doctor communication", "Hospital environment", "Pain management", "Medication communication", "Discharge information", "Care transition", "Overall hospital rating", "Willingness to recommend"]},
    {"survey": "Home Health Care Survey", "description": "Measures patient experience with home health agencies", "composites": ["Care provision", "Communication", "Specific care issues", "Overall rating", "Willingness to recommend"]},
    {"survey": "Hospice Survey", "description": "Measures caregiver experience with hospice care", "composites": ["Hospice team communication", "Pain management", "Dyspnea management", "Spiritual care", "Emotional support", "Overall rating"]},
    {"survey": "Dialysis Facility Survey", "description": "Measures patient experience with dialysis facilities", "composites": ["Nephrologist communication", "Dialysis staff communication", "Treatment information", "Overall rating"]},
    {"survey": "Surgical Care Survey (S-CAHPS)", "description": "Measures patient experience with surgical care", "composites": ["Pre-operative preparation", "Surgical communication", "Post-operative care", "Overall rating"]},
    {"survey": "Emergency Department Survey", "description": "Measures patient experience in ED settings", "composites": ["ED arrival and wait times", "ED communication", "ED care transition", "Overall ED rating"]},
]


async def download(force: bool = False) -> dict:
    """Download CAHPS survey measures reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "cahps_surveys.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading CAHPS survey measures reference...")
    save_json(CAHPS_SURVEYS, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": f"Downloaded CAHPS surveys reference ({len(CAHPS_SURVEYS)} surveys)"}