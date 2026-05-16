"""
SNF PDPM rates.

Skilled Nursing Facility Patient-Driven Payment Model rates from
CMS. Replaced RUG-IV system effective October 1, 2019.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/SNFPPS
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_file, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/SNFPPS"
DEST_DIR = DATA_ROOT / "healthcare" / "reimbursement" / "snf_pps"
MODULE_NAME = "knowledge_bases.healthcare.reimbursement.snf_pps"

SNF_PDPM_REFERENCE = {
    "payment_model": "Patient-Driven Payment Model (PDPM)",
    "effective_date": "October 1, 2019",
    "case_mix_groups": [
        {"group": "PT", "name": "Physical Therapy", "description": "Based on functional and cognitive status"},
        {"group": "OT", "name": "Occupational Therapy", "description": "Based on functional and cognitive status"},
        {"group": "SLP", "name": "Speech-Language Pathology", "description": "Based on swallowing, cognitive, and SLP-related comorbidities"},
        {"group": "NTG", "name": "Non-Therapy Ancillary", "description": "Based on pharmacy, IV therapy, and other ancillary services"},
        {"group": "NCA", "name": "Nursing", "description": "Based on clinical category, cognitive level, and nursing comorbidities"},
    ],
    "payment_components": [
        "Base rate (federal urban/rural rates)",
        "Case-mix adjusted per diem rate for each of the 5 PDPM components",
        "Variable per diem adjustment (declining over stay)",
        "Wage index adjustment",
    ],
    "variable_per_diem": {
        "days_1_20": "Full rate",
        "days_21_100": "Reduced by 2% per day from day 21 to 100",
        "beyond_100": "Further reduced per diem rate",
    },
}


async def download(force: bool = False) -> dict:
    """Download SNF PDPM rates from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "snf_pdpm_rates.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading SNF PDPM rates from CMS...")
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=300.0), follow_redirects=True) as client:
        urls = ["https://www.cms.gov/files/zip/fy2025-snf-pps-final-rule.zip", "https://www.cms.gov/files/zip/fy2024-snf-pps-final-rule.zip"]
        for url in urls:
            try:
                await download_file(url, DEST_DIR / "snf_download.zip", client)
                break
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)

    save_json(SNF_PDPM_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded SNF PDPM rates reference"}