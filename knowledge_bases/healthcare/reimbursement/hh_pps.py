"""
Home Health PDGM rates.

Home Health Prospective Payment System Patient-Driven Grouping Model
rates from CMS.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/HomeHealthPPS
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_file, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/HomeHealthPPS"
DEST_DIR = DATA_ROOT / "healthcare" / "reimbursement" / "hh_pps"
MODULE_NAME = "knowledge_bases.healthcare.reimbursement.hh_pps"

HH_PDGM_REFERENCE = {
    "payment_model": "Patient-Driven Grouping Model (PDGM)",
    "effective_date": "January 1, 2020",
    "grouping_factors": [
        {"factor": "Timing", "values": ["Early", "Late"], "description": "Early (1-20 days) vs Late (21+ days) in certification period"},
        {"factor": "Clinical Grouping", "values": "12 clinical groups", "description": "Based on primary diagnosis and clinical characteristics"},
        {"factor": "Functional Level", "values": ["Low", "Medium", "High"], "description": "Based on OASIS functional items"},
        {"factor": "Comorbidity", "values": ["None", "Low", "High"], "description": "Based on secondary diagnoses and comorbidity interactions"},
    ],
    "payment_components": [
        "National standardized 60-day episode rate",
        "LUPA (Low Utilization Payment Adjustment) per-visit rate for episodes with fewer visits than threshold",
        "Wage index adjustment",
        "Outlier payment for extraordinarily costly episodes",
    ],
    "certification_period": "60-day episodes",
    "lupa_thresholds": "Varies by clinical grouping; typically 4-6 visits minimum",
}


async def download(force: bool = False) -> dict:
    """Download Home Health PDGM rates from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "hh_pdgm_rates.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading Home Health PDGM rates from CMS...")
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=300.0), follow_redirects=True) as client:
        urls = ["https://www.cms.gov/files/zip/cy2025-home-health-pps-final-rule.zip", "https://www.cms.gov/files/zip/cy2024-home-health-pps-final-rule.zip"]
        for url in urls:
            try:
                await download_file(url, DEST_DIR / "hh_download.zip", client)
                break
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)

    save_json(HH_PDGM_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded Home Health PDGM rates reference"}