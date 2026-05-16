"""
Price transparency rules reference.

CMS Hospital Price Transparency and Transparency in Coverage rules
requiring hospitals and insurers to make pricing data publicly available.

Source: https://www.cms.gov/hospital-price-transparency
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/hospital-price-transparency"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "price_transparency"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.price_transparency"

PRICE_TRANSPARENCY_REFERENCE = {
    "hospital_rule": {
        "name": "CMS Hospital Price Transparency Rule",
        "citation": "45 CFR 180",
        "effective_date": "January 1, 2021",
        "requirements": [
            "Publish machine-readable file with standard charges for all items/services",
            "Display shoppable services in consumer-friendly format (minimum 300 services)",
            "Include gross charges, payer-specific negotiated rates, cash prices, and de-identified minimum/maximum rates",
            "Update machine-readable file at least annually",
        ],
        "standard_charge_types": [
            {"type": "Gross Charges", "description": "Hospital's full list prices before any discounts"},
            {"type": "Discounted Cash Price", "description": "Price for self-pay or cash-paying patients"},
            {"type": "Payer-Specific Negotiated Rates", "description": "Negotiated rates for each third-party payer plan"},
            {"type": "De-identified Minimum Negotiated Rate", "description": "Lowest negotiated rate across all payers (de-identified)"},
            {"type": "De-identified Maximum Negotiated Rate", "description": "Highest negotiated rate across all payers (de-identified)"},
        ],
        "penalties": "Up to $2M per year for non-compliance (based on bed count)",
    },
    "insurer_rule": {
        "name": "Transparency in Coverage Rule",
        "citation": "45 CFR Part 153 and 26 CFR Part 54",
        "effective_date": "July 1, 2022",
        "requirements": [
            "Publish machine-readable files with in-network rates and out-of-network allowed amounts",
            "Publish negotiated rates for all covered items/services for each plan",
            "Provide online self-service tool for members to get cost estimates",
            "Update machine-readable files monthly",
        ],
        "file_types": [
            {"type": "In-Network File", "description": "Negotiated rates for in-network providers by plan"},
            {"type": "Out-of-Network File", "description": "Allowed amounts and billed charges for out-of-network providers"},
            {"type": "Prescription Drug File", "description": "Negotiated rates for prescription drugs by plan (pending)"},
        ],
    },
}


async def download(force: bool = False) -> dict:
    """Download price transparency rules reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "price_transparency.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading price transparency rules reference...")
    save_json(PRICE_TRANSPARENCY_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded price transparency reference"}