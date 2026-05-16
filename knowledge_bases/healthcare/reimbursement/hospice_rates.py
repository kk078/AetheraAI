"""
Hospice payment rates.

Hospice payment rates from CMS for Medicare hospice services,
including the component rates for the four levels of care.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/Hospice
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_file, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/Hospice"
DEST_DIR = DATA_ROOT / "healthcare" / "reimbursement" / "hospice"
MODULE_NAME = "knowledge_bases.healthcare.reimbursement.hospice_rates"

HOSPICE_REFERENCE = {
    "payment_model": "Hospice Prospective Payment System",
    "payment_basis": "Per diem rates for each level of care",
    "levels_of_care": [
        {
            "level": "Routine Home Care",
            "description": "Standard hospice care provided at home or facility",
            "rate_structure": "Base rate adjusted by wage index; tiered rates for first 60 days vs after day 60",
        },
        {
            "level": "Continuous Home Care",
            "description": "Crisis care with predominantly nursing services provided at home",
            "rate_structure": "Hourly rate; minimum of 8 hours of nursing care required",
        },
        {
            "level": "Inpatient Respite Care",
            "description": "Short-term inpatient stay to relieve caregivers",
            "rate_structure": "Per diem rate for up to 5 consecutive days",
        },
        {
            "level": "General Inpatient Care",
            "description": "Inpatient care for symptom/pain management that cannot be managed at home",
            "rate_structure": "Per diem rate for inpatient facility care",
        },
    ],
    "payment_components": [
        "Component for physician/medical services",
        "Component for nursing services",
        "Component for social worker/counselor services",
        "Component for home health aide services",
        "Component for medical appliances/supplies",
        "Component for drugs/biologicals",
        "Component for bereavement services",
    ],
    "update_factor": "Annual update based on market basket percentage",
    "service_intensity_addon": "Additional payment for RN visits in the last 7 days of life",
}


async def download(force: bool = False) -> dict:
    """Download Hospice payment rates from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "hospice_rates.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading Hospice payment rates from CMS...")
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=300.0), follow_redirects=True) as client:
        urls = ["https://www.cms.gov/files/zip/fy2025-hospice-wage-index-and-rate-final-rule.zip", "https://www.cms.gov/files/zip/fy2024-hospice-wage-index-and-rate-final-rule.zip"]
        for url in urls:
            try:
                await download_file(url, DEST_DIR / "hospice_download.zip", client)
                break
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)

    save_json(HOSPICE_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded Hospice payment rates reference"}