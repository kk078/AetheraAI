"""
Stark Law text reference.

The Physician Self-Referral Law (Stark Law) prohibits physician
referrals for designated health services to entities with which
the physician has a financial relationship.

Source: 42 U.S.C. 1395nn; 42 CFR 411.350-411.389
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Fraud-Abuse-Prevention/PhysicianSelfReferral"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "stark_law"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.stark_law"

STARK_LAW_REFERENCE = {
    "full_name": "Physician Self-Referral Law (Stark Law)",
    "citation": "42 U.S.C. 1395nn; 42 CFR 411.350-411.389",
    "prohibition": "A physician may not refer Medicare/Medicaid patients for designated health services (DHS) to an entity with which the physician (or immediate family member) has a financial relationship, unless an exception applies",
    "designated_health_services": [
        "Clinical laboratory services",
        "Physical therapy services",
        "Occupational therapy services",
        "Radiology services (including MRI, CT, ultrasound)",
        "Radiation therapy services and supplies",
        "Durable medical equipment and supplies",
        "Parenteral and enteral nutrients, equipment, and supplies",
        "Prosthetics, orthotics, and prosthetic devices and supplies",
        "Home health services",
        "Outpatient prescription drugs",
        "Inpatient and outpatient hospital services",
    ],
    "financial_relationships": [
        {"type": "Ownership/Investment", "description": "Direct or indirect ownership or investment interest in the entity"},
        {"type": "Compensation", "description": "Direct or indirect compensation arrangement with the entity"},
    ],
    "key_exceptions": [
        {"exception": "In-Office Ancillary Services", "description": "Services performed in the same building as the physician's practice (for certain DHS only)"},
        {"exception": "Physician Services", "description": "Services personally performed by the referring physician or group practice member"},
        {"exception": "Prepaid Plans", "description": "Services under a prepaid plan (HMO)"},
        {"exception": "Fair Market Value", "description": "Compensation at fair market value, not determined by volume/value of referrals"},
        {"exception": "Bona Fide Employment", "description": "Employee compensation that would be paid regardless of referrals"},
        {"exception": "Group Practice Withhold", "description": "Group practice profit sharing based on overall profitability"},
        {"exception": "Academic Medical Center", "description": "Special rules for academic medical centers"},
        {"exception": "Rural Provider", "description": "Exception for providers in rural areas"},
        {"exception": "Iso-Referral", "description": "One-way referrals between physicians"},
        {"exception": "Medical Staff Incidental Benefit", "description": "Benefits incidental to medical staff membership"},
    ],
    "penalties": [
        "Denial of payment for DHS claims from prohibited referrals",
        "Refund of amounts collected from prohibited referrals",
        "Civil monetary penalties up to $15,000 per claim",
        "Exclusion from federal health care programs",
        "False Claims Act liability for false claims based on prohibited referrals",
    ],
}


async def download(force: bool = False) -> dict:
    """Download Stark Law reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "stark_law.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading Stark Law reference...")
    save_json(STARK_LAW_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded Stark Law reference"}