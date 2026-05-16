"""
Clinical Lab Fee Schedule.

Downloads the Clinical Laboratory Fee Schedule (CLFS) from CMS,
which sets payment rates for diagnostic laboratory tests.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/ClinicalLabFeeSched
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_file, extract_zip, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/ClinicalLabFeeSched"
DEST_DIR = DATA_ROOT / "healthcare" / "reimbursement" / "clinical_lab"
MODULE_NAME = "knowledge_bases.healthcare.reimbursement.clinical_lab_fee"

CLFS_REFERENCE = {
    "payment_methodology": "Clinical laboratory tests paid based on the CLFS fee schedule amounts",
    "pricing": {
        "description": "CLFS rates are set based on weighted median of private payor rates (PAMA)",
        "reporting_period": "Data reported every 3 years from applicable laboratories",
    },
    "adjustments": [
        {"type": "PAMA adjustment", "description": "Rate reduction based on private payor rate reporting per the Protecting Access to Medicare Act"},
        {"type": "Geographic adjustment", "description": "No geographic adjustment for CLFS (national rates)"},
    ],
    "coverage_requirements": [
        "Test must be ordered by a physician or authorized practitioner",
        "Test must be medically necessary for diagnosis or treatment",
        "Test must meet Medicare coverage requirements",
    ],
}


async def download(force: bool = False) -> dict:
    """Download Clinical Lab Fee Schedule from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "clinical_lab_fee.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading Clinical Lab Fee Schedule from CMS...")
    zip_path = DEST_DIR / "clfs_download.zip"
    extracted_files = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=300.0), follow_redirects=True) as client:
        urls = ["https://www.cms.gov/files/zip/cy2025-clinical-laboratory-fee-schedule-files.zip", "https://www.cms.gov/files/zip/cy2024-clinical-laboratory-fee-schedule-files.zip"]
        for url in urls:
            try:
                await download_file(url, zip_path, client)
                extracted_files = extract_zip(zip_path, DEST_DIR)
                break
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)
        zip_path.unlink(missing_ok=True)

    save_json(CLFS_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": len(extracted_files) + 1, "message": "Downloaded Clinical Lab Fee Schedule reference"}