"""
ASC fee schedule.

Downloads the Ambulatory Surgical Center fee schedule from CMS,
which determines payment rates for surgical procedures performed in
ASCs.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/ASCPayment
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_file, extract_zip, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/ASCPayment"
DEST_DIR = DATA_ROOT / "healthcare" / "reimbursement" / "asc"
MODULE_NAME = "knowledge_bases.healthcare.reimbursement.asc_fee_schedule"

ASC_REFERENCE = {
    "payment_methodology": "ASC procedures are paid based on the ASC payment rate, which is a percentage of the OPPS rate.",
    "asc_cy2025_rate": "Approximately 79% of OPPS rate for most procedures",
    "covered_procedures": "Procedures approved for ASC setting by CMS",
    "not_covered_in_asc": "Procedures that must be performed in hospital outpatient or inpatient setting",
    "payment_indicators": [
        {"indicator": "C", "description": "Inpatient-only procedure; not payable in ASC"},
        {"indicator": "N", "description": "Not an ASC-covered procedure"},
        {"indicator": "P", "description": "Pass-through device or drug payment"},
        {"indicator": "S", "description": "Significant procedure; separately payable in ASC"},
        {"indicator": "T", "description": "Significant procedure; multiple reduction applies in ASC"},
        {"indicator": "V", "description": "Visit; subject to multiple reduction in ASC"},
        {"indicator": "X", "description": "Ancillary service; packaged in ASC"},
    ],
}


async def download(force: bool = False) -> dict:
    """Download ASC fee schedule from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "asc_fee_schedule.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading ASC fee schedule from CMS...")
    zip_path = DEST_DIR / "asc_download.zip"
    extracted_files = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=300.0), follow_redirects=True) as client:
        urls = ["https://www.cms.gov/files/zip/cy2025-asc-list-of-covered-procedures.zip", "https://www.cms.gov/files/zip/cy2024-asc-list-of-covered-procedures.zip"]
        for url in urls:
            try:
                await download_file(url, zip_path, client)
                extracted_files = extract_zip(zip_path, DEST_DIR)
                break
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)
        zip_path.unlink(missing_ok=True)

    save_json(ASC_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": len(extracted_files) + 1, "message": "Downloaded ASC fee schedule reference"}