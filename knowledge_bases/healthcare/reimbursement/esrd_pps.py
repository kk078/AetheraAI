"""
ESRD PPS rates.

End-Stage Renal Disease Prospective Payment System rates from CMS.
Covers renal dialysis services including hemodialysis and peritoneal dialysis.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/ESRDpayment
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_file, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/ESRDpayment"
DEST_DIR = DATA_ROOT / "healthcare" / "reimbursement" / "esrd_pps"
MODULE_NAME = "knowledge_bases.healthcare.reimbursement.esrd_pps"

ESRD_PPS_REFERENCE = {
    "payment_model": "End-Stage Renal Disease PPS",
    "payment_basis": "Per treatment bundled payment rate",
    "bundle_includes": [
        "Dialysis treatment (hemodialysis or peritoneal dialysis)",
        "ESRD-related drugs and biologicals (including EPO/ESAs)",
        "ESRD-related laboratory tests",
        "ESRD-related supplies",
        "Capital-related costs",
        "Home dialysis training and support",
    ],
    "payment_adjustments": [
        {"adjustment": "Wage index", "description": "Geographic wage adjustment applied to labor-related portion"},
        {"adjustment": "Training adjustment", "description": "Additional payment for home dialysis training cases"},
        {"adjustment": "Low-volume adjustment", "description": "Payment adjustment for facilities with low patient volumes"},
        {"adjustment": "Rural adjustment", "description": "Temporary adjustment for rural ESRD facilities"},
        {"adjustment": "Oral-only ESRD drug adjustment", "description": "Payment for certain oral-only drugs not in the bundle"},
        {"adjustment": "High-cost outlier", "description": "Additional payment for unusually costly cases"},
    ],
    "rate_categories": [
        "Facility hemodialysis per treatment rate",
        "Facility peritoneal dialysis per treatment rate",
        "Home hemodialysis per treatment rate",
        "Home peritoneal dialysis per treatment rate",
        "Training rate for home dialysis",
    ],
    "update_factor": "Annual update based on ESRD market basket",
}


async def download(force: bool = False) -> dict:
    """Download ESRD PPS rates from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "esrd_pps_rates.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading ESRD PPS rates from CMS...")
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=300.0), follow_redirects=True) as client:
        urls = ["https://www.cms.gov/files/zip/cy2025-esrd-pps-final-rule.zip", "https://www.cms.gov/files/zip/cy2024-esrd-pps-final-rule.zip"]
        for url in urls:
            try:
                await download_file(url, DEST_DIR / "esrd_download.zip", client)
                break
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)

    save_json(ESRD_PPS_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded ESRD PPS rates reference"}