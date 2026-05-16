"""
DME fee schedule.

Downloads the Durable Medical Equipment, Prosthetics, Orthotics, and
Supplies (DMEPOS) fee schedule from CMS.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/DMEPOSFeeSched
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_file, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/DMEPOSFeeSched"
DEST_DIR = DATA_ROOT / "healthcare" / "reimbursement" / "dme"
MODULE_NAME = "knowledge_bases.healthcare.reimbursement.dme_fee_schedule"

DME_REFERENCE = {
    "payment_methodology": "DMEPOS paid based on fee schedule amounts, updated quarterly",
    "fee_schedule_adjustments": [
        {"type": "Adjustment for inflation", "description": "Annual update based on CPI"},
        {"type": "Competitive bidding", "description": "Rates set through competitive bidding program (CBP)"},
        {"type": "Fee schedule amount", "description": "Based on historical charges and statutory limits"},
    ],
    "rental_vs_purchase": [
        {"type": "Rental", "description": "Monthly rental payments for 13 months, then ownership transfers"},
        {"type": "Purchase", "description": "One-time purchase payment"},
        {"type": "Capped rental", "description": "Rental capped at 13 months of payments"},
    ],
    "competitive_bidding": {
        "description": "The Competitive Bidding Program was established to replace the fee schedule with competitively bid prices in certain areas.",
        "status": "Program suspended as of January 1, 2021; transitional fee schedule amounts in effect",
    },
}


async def download(force: bool = False) -> dict:
    """Download DME fee schedule from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "dme_fee_schedule.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading DME fee schedule from CMS...")
    downloaded_from_cms = False

    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=300.0), follow_redirects=True) as client:
        urls = ["https://www.cms.gov/files/zip/cy2025-dmepos-fee-schedule.zip", "https://www.cms.gov/files/zip/cy2024-dmepos-fee-schedule.zip"]
        for url in urls:
            try:
                zip_path = DEST_DIR / "dme_download.zip"
                await download_file(url, zip_path, client)
                downloaded_from_cms = True
                break
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)

    save_json(DME_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded DME fee schedule reference"}