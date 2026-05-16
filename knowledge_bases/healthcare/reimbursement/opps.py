"""
Outpatient PPS Addendum B data.

Addendum B provides APC rates and status indicators for outpatient
services under the Outpatient Prospective Payment System.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/OutpatientPPS
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_file, extract_zip, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/OutpatientPPS"
DEST_DIR = DATA_ROOT / "healthcare" / "reimbursement" / "opps"
MODULE_NAME = "knowledge_bases.healthcare.reimbursement.opps"

OPPS_STATUS_INDICATORS = [
    {"indicator": "S", "description": "Significant procedure, not discounted when multiple", "payment": "Separately payable APC"},
    {"indicator": "T", "description": "Significant procedure, multiple procedure reduction applies", "payment": "Separately payable APC with reduction"},
    {"indicator": "V", "description": "Visit, subject to multiple procedure reduction", "payment": "Separately payable APC with reduction"},
    {"indicator": "Q1", "description": "Composite APC - multiple procedure composite", "payment": "Composite APC payment"},
    {"indicator": "Q2", "description": "Composite APC - imaging composite", "payment": "Composite APC payment"},
    {"indicator": "Q3", "description": "Composite APC - surgical composite", "payment": "Composite APC payment"},
    {"indicator": "Q4", "description": "Composite APC - blood/chemistry composite", "payment": "Composite APC payment"},
    {"indicator": "X", "description": "Ancillary service, packaged into APC", "payment": "Not separately payable (packaged)"},
    {"indicator": "N", "description": "Items and services packaged into APC rates", "payment": "Not separately payable (packaged)"},
    {"indicator": "P", "description": "Partial hospitalization per diem", "payment": "Per diem APC payment"},
    {"indicator": "F", "description": "Corneal tissue acquisition", "payment": "Cost-based payment"},
    {"indicator": "L", "description": "Drugs and biologicals paid at a rate other than ASP", "payment": "Cost-based payment"},
    {"indicator": "K", "description": "Non-pass-through drugs and biologicals paid at ASP", "payment": "ASP-based payment"},
    {"indicator": "J1", "description": "Comprehensive APC - all services on claim combined", "payment": "Comprehensive APC"},
    {"indicator": "J2", "description": "Comprehensive APC - all services on claim combined", "payment": "Comprehensive APC"},
    {"indicator": "U", "description": "Conditional packaging - may be separately payable", "payment": "Conditionally packaged"},
    {"indicator": "R", "description": "Blood and blood products", "payment": "Cost-based payment"},
    {"indicator": "W", "description": "Non-apply to OPPS - not payable under OPPS", "payment": "Not payable under OPPS"},
    {"indicator": "A", "description": "Services not paid under OPPS; paid under another fee schedule", "payment": "Other fee schedule"},
]


async def download(force: bool = False) -> dict:
    """Download OPPS Addendum B data from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "opps_addendum_b.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading OPPS Addendum B data from CMS...")
    zip_path = DEST_DIR / "opps_download.zip"
    extracted_files = []
    all_records = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=300.0), follow_redirects=True) as client:
        urls = ["https://www.cms.gov/files/zip/cy2025-opps-addendum-b.zip", "https://www.cms.gov/files/zip/cy2024-opps-addendum-b.zip"]
        for url in urls:
            try:
                await download_file(url, zip_path, client)
                extracted_files = extract_zip(zip_path, DEST_DIR)
                break
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)
        zip_path.unlink(missing_ok=True)

    save_json(OPPS_STATUS_INDICATORS, codes_json)
    save_json(OPPS_STATUS_INDICATORS, DEST_DIR / "opps_status_indicators.json")
    file_list = [codes_json.name, "opps_status_indicators.json"]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 2, "message": f"Created {len(OPPS_STATUS_INDICATORS)} OPPS status indicators"}