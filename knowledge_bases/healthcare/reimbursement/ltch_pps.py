"""
LTCH PPS rates.

Long-Term Care Hospital Prospective Payment System rates from CMS.
LTCHs provide extended medical and rehabilitative care.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/LTCHPPS
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_file, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/LTCHPPS"
DEST_DIR = DATA_ROOT / "healthcare" / "reimbursement" / "ltch_pps"
MODULE_NAME = "knowledge_bases.healthcare.reimbursement.ltch_pps"

LTCH_PPS_REFERENCE = {
    "payment_model": "Long-Term Care Hospital PPS",
    "payment_basis": "Per discharge, case-mix adjusted using LTC-DRGs",
    "key_features": [
        "Based on Long-Term Care Diagnosis Related Groups (LTC-DRGs)",
        "Standard federal rate adjusted by wage index",
        "Short-stay outlier payment for cases discharged before the short-stay threshold",
        "High-cost outlier payment for extraordinarily costly cases",
    ],
    "ltc_drg_description": "LTC-DRGs are similar to MS-DRGs but specifically calibrated for long-term care patient populations",
    "payment_components": [
        "Standard federal rate (urban/rural)",
        "LTC-DRG relative weight",
        "Wage index adjustment",
        "Short-stay outlier adjustment",
        "High-cost outlier payment",
    ],
    "site_neutral_payment": "For site-neutral LTCH admissions, payment is based on the IPPS rate rather than the LTCH PPS rate",
}


async def download(force: bool = False) -> dict:
    """Download LTCH PPS rates from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "ltch_pps_rates.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading LTCH PPS rates from CMS...")
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=300.0), follow_redirects=True) as client:
        urls = ["https://www.cms.gov/files/zip/fy2025-ltch-pps-final-rule.zip", "https://www.cms.gov/files/zip/fy2024-ltch-pps-final-rule.zip"]
        for url in urls:
            try:
                await download_file(url, DEST_DIR / "ltch_download.zip", client)
                break
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)

    save_json(LTCH_PPS_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded LTCH PPS rates reference"}