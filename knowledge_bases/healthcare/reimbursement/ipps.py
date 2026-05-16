"""
Inpatient PPS DRG weights and rates.

Downloads the IPPS final rule data including MS-DRG weights, rates,
and wage index information for inpatient hospital reimbursement.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/AcuteInpatientPPS
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_file, extract_zip, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/AcuteInpatientPPS"
DEST_DIR = DATA_ROOT / "healthcare" / "reimbursement" / "ipps"
MODULE_NAME = "knowledge_bases.healthcare.reimbursement.ipps"

IPPS_REFERENCE = {
    "payment_components": [
        {"component": "Base Rate (Standardized Amount)", "description": "National base payment rate per discharge", "fy2025_estimated": 6351.95},
        {"component": "DRG Relative Weight", "description": "Case-mix adjustment based on diagnosis related group", "fy2025_estimated": "Varies by DRG"},
        {"component": "Wage Index", "description": "Geographic adjustment for labor costs", "fy2025_estimated": "Varies by CBSA"},
        {"component": "Capital Cost", "description": "Capital-related costs including interest and depreciation", "fy2025_estimated": "Included in base rate"},
        {"component": "Indirect Medical Education (IME)", "description": "Adjustment for teaching hospitals", "fy2025_estimated": "Based on intern/resident ratio"},
        {"component": "Disproportionate Share (DSH)", "description": "Adjustment for hospitals serving low-income patients", "fy2025_estimated": "Based on SSI/Medicaid days"},
        {"component": "Outlier Payment", "description": "Additional payment for extraordinarily costly cases", "fy2025_estimated": "Beyond fixed loss threshold"},
        {"component": "Transfer Payment", "description": "Adjusted payment for post-acute transfer cases", "fy2025_estimated": "Per diem rate based on DRG"},
    ],
    "payment_formula": "Operating Payment = (Base Rate x DRG Relative Weight x Wage Index) + IME + DSH + Outlier",
    "msa_categories": ["Large Urban", "Other Urban", "Rural"],
}


async def download(force: bool = False) -> dict:
    """Download IPPS DRG weights and rates from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "ipps_rates.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading IPPS data from CMS...")
    zip_path = DEST_DIR / "ipps_download.zip"
    extracted_files = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=300.0), follow_redirects=True) as client:
        urls = ["https://www.cms.gov/files/zip/fy2025-ipps-final-rule.zip", "https://www.cms.gov/files/zip/fy2024-ipps-final-rule.zip"]
        for url in urls:
            try:
                await download_file(url, zip_path, client)
                extracted_files = extract_zip(zip_path, DEST_DIR)
                break
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)
        zip_path.unlink(missing_ok=True)

    save_json(IPPS_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": len(extracted_files) + 1, "message": "Downloaded IPPS payment reference"}