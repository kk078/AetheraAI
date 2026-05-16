"""
Anti-Kickback Statute (AKS) text reference.

The AKS prohibits offering, paying, soliciting, or receiving anything
of value to induce or reward referrals for federal health care program
services.

Source: 42 U.S.C. 1320a-7b(b)
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Fraud-Abuse-Prevention/AntiKickbackStatute"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "anti_kickback"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.anti_kickback"

AKS_REFERENCE = {
    "full_name": "Anti-Kickback Statute (AKS)",
    "citation": "42 U.S.C. 1320a-7b(b)",
    "prohibition": "Prohibits knowingly and willfully offering, paying, soliciting, or receiving anything of value to induce or reward referrals for services or items covered by federal health care programs",
    "intent_requirement": "Requires specific intent to induce or reward referrals (unlike Stark Law which is strict liability)",
    "scope": "Applies to all federal health care programs (not just Medicare/Medicaid)",
    "safe_harbors": [
        {"safe_harbor": "Investment Interests", "description": "Certain investment interests in entities that provide health care items/services"},
        {"safe_harbor": "Space Rental", "description": "Rental of office space at fair market value with arm's-length terms"},
        {"safe_harbor": "Equipment Rental", "description": "Rental of equipment at fair market value with arm's-length terms"},
        {"safe_harbor": "Personal Services and Management Contracts", "description": "Compensation arrangements for services at fair market value"},
        {"safe_harbor": "Sale of Practice", "description": "Sale of a physician practice to a hospital or other entity"},
        {"safe_harbor": "Referral Services", "description": "Payments for referral services under certain conditions"},
        {"safe_harbor": "Warranties", "description": "Warranty arrangements meeting specific requirements"},
        {"safe_harbor": "Discounts", "description": "Discounts properly disclosed and meeting statutory requirements"},
        {"safe_harbor": "Employee Compensation", "description": "Compensation paid by employer to employee for employment"},
        {"safe_harbor": "Group Purchasing Organization", "description": "Payments by GPOs to vendors meeting specified conditions"},
        {"safe_harbor": "Ambulance Restocking", "description": "Arrangements for restocking ambulance supplies"},
        {"safe_harbor": "Electronic Health Records", "description": "Donation of EHR technology meeting specified conditions"},
        {"safe_harbor": "Community-Wide Health Information Systems", "description": "Interoperable health information technology donations"},
        {"safe_harbor": "Obstetrical Malpractice Insurance Premiums", "description": "Hospital subsidies of OB malpractice insurance premiums"},
        {"safe_harbor": "Increased Coverage/Coordination of Care", "description": "Value-based arrangements that improve care coordination"},
        {"safe_harbor": "Part-Time Employment Arrangements", "description": "Part-time physician employment by hospitals in underserved areas"},
        {"safe_harbor": "Group Practice Prepaid Plans", "description": "Prepaid plans offered by group practices"},
    ],
    "penalties": [
        "Criminal penalties: Up to $100,000 fine and 10 years imprisonment per violation",
        "Civil monetary penalties: Up to $50,000 per violation",
        "Exclusion from federal health care programs",
        "False Claims Act liability for claims resulting from kickbacks",
    ],
}


async def download(force: bool = False) -> dict:
    """Download Anti-Kickback Statute reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "anti_kickback.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading Anti-Kickback Statute reference...")
    save_json(AKS_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded Anti-Kickback Statute reference"}