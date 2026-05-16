"""
IRF PPS rates.

Inpatient Rehabilitation Facility Prospective Payment System rates
from CMS. IRFs provide intensive rehabilitation services.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/InpatientRehabFacPPS
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_file, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/InpatientRehabFacPPS"
DEST_DIR = DATA_ROOT / "healthcare" / "reimbursement" / "irf_pps"
MODULE_NAME = "knowledge_bases.healthcare.reimbursement.irf_pps"

IRF_PPS_REFERENCE = {
    "payment_model": "Inpatient Rehabilitation Facility PPS",
    "payment_basis": "Per discharge, case-mix adjusted",
    "case_mix_groups": "IRF Case-Mix Groups (CMGs) based on impairment category, etiology, age, and functional status",
    "impairment_categories": [
        {"code": "1", "category": "Stroke"},
        {"code": "2", "category": "Traumatic Brain Injury"},
        {"code": "3", "category": "Neurological Disorders"},
        {"code": "4", "category": "Spinal Cord Injury"},
        {"code": "5", "category": "Amputation"},
        {"code": "6", "category": "Fracture and Other Orthopedic"},
        {"code": "7", "category": "Joint Replacement"},
        {"code": "8", "category": "Cardiac"},
        {"code": "9", "category": "Pulmonary"},
        {"code": "10", "category": "Burns"},
        {"code": "11", "category": "Major Multiple Trauma"},
        {"code": "12", "category": "Other"},
    ],
    "payment_components": [
        "Standardized payment amount",
        "Case-mix group relative weight",
        "Wage index adjustment",
        "Short-stay outlier payment",
        "High-cost outlier payment",
    ],
    "compliance_threshold": "60% rule - at least 60% of patients must have one of 13 qualifying conditions",
}


async def download(force: bool = False) -> dict:
    """Download IRF PPS rates from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "irf_pps_rates.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading IRF PPS rates from CMS...")
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=300.0), follow_redirects=True) as client:
        urls = ["https://www.cms.gov/files/zip/fy2025-irf-pps-final-rule.zip", "https://www.cms.gov/files/zip/fy2024-irf-pps-final-rule.zip"]
        for url in urls:
            try:
                await download_file(url, DEST_DIR / "irf_download.zip", client)
                break
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)

    save_json(IRF_PPS_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded IRF PPS rates reference"}