"""
TRICARE rules reference.

TRICARE provides health coverage for uniformed service members,
retirees, and their families.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://tricare.mil/"
DEST_DIR = DATA_ROOT / "healthcare" / "payer_specific" / "tricare"
MODULE_NAME = "knowledge_bases.healthcare.payer_specific.tricare"

TRICARE_REFERENCE = {
    "eligible_populations": ["Active duty service members", "National Guard/Reserve members (when activated)", "Retirees and their families", "Survivors of deceased sponsors", "Former spouses (20/20/20 and 20/20/15 rules)", "Medal of Honor recipients and families"],
    "program_options": [
        {"option": "TRICARE Prime", "description": "Managed care option with assigned PCM; lowest out-of-pocket costs; must use network providers", "cost_sharing": "Active duty: $0; Others: copays for visits and prescriptions"},
        {"option": "TRICARE Select", "description": "Preferred provider option; more flexibility in choosing providers; higher cost-sharing", "cost_sharing": "Network: 15-20% after deductible; Non-network: 20-25% after deductible"},
        {"option": "TRICARE For Life", "description": "Medicare-wraparound coverage for beneficiaries with Medicare Part A and B", "cost_sharing": "Pays Medicare deductible and coinsurance; minimal out-of-pocket"},
        {"option": "TRICARE Reserve Select", "description": "Premium-based plan for qualified reserve component members not on active duty", "cost_sharing": "Monthly premium + deductibles and copays similar to Select"},
        {"option": "TRICARE Retired Reserve", "description": "Premium-based plan for retired reserve component members under age 60", "cost_sharing": "Monthly premium + deductibles and copays similar to Select"},
        {"option": "US Family Health Plan", "description": "Designated provider managed care plan in specific geographic areas", "cost_sharing": "Similar to Prime with designated provider networks"},
    ],
    "pharmacy_options": ["TRICARE Pharmacy Home Delivery (mail order)", "TRICARE Retail Pharmacy Network", "Non-network pharmacies"],
    "dental_options": ["TRICARE Dental Program (TDP) - active duty families", "Federal Employees Dental and Vision Insurance Program (FEDVIP) - retirees"],
    "claims_submission": "Most network providers file claims directly; non-network claims filed on DD Form 2642",
    "special_programs": ["Extended Care Health Option (ECHO)", "Autism Care Demonstration", "Supplemental Health Care Program"],
}


async def download(force: bool = False) -> dict:
    """Download TRICARE rules reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "tricare_rules.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading TRICARE rules reference...")
    save_json(TRICARE_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded TRICARE rules reference"}