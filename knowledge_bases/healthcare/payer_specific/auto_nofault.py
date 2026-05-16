"""
Auto/no-fault insurance reference.

No-fault automobile insurance and personal injury protection (PIP)
coverage for healthcare providers treating auto accident injuries.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.iii.org/article/background-on-compulsory-auto-uninsured-motorists"
DEST_DIR = DATA_ROOT / "healthcare" / "payer_specific" / "auto_nofault"
MODULE_NAME = "knowledge_bases.healthcare.payer_specific.auto_nofault"

AUTO_NOFAULT_REFERENCE = {
    "no_fault_states": ["Florida", "Hawaii", "Kansas", "Kentucky", "Massachusetts", "Michigan", "Minnesota", "New Jersey", "New York", "North Dakota", "Pennsylvania", "Utah"],
    "pip_coverage": {
        "description": "Personal Injury Protection (PIP) covers medical expenses, lost wages, and replacement services regardless of fault",
        "typical_limits": "Varies by state: $10K to unlimited (Michigan had unlimited; changed to options in 2020)",
        "covered_services": ["Emergency medical treatment", "Hospital and physician services", "Rehabilitation", "Diagnostic tests", "Lost wage replacement", "Replacement services (household help)"],
    },
    "billing_requirements": [
        "File PIP claims directly with auto insurer; not with health insurance",
        "Use state-specific claim forms (e.g., NF-3 in New York, HIPAA release in Florida)",
        "Timely filing requirements vary by state (30-90 days typical)",
        "PIP fee schedules vary by state; some use Medicare-based rates",
        "Pre-authorization may be required for treatment beyond initial period",
        "Must document causal relationship to auto accident",
    ],
    "coordination_of_benefits": [
        "PIP is primary for auto accident injuries in no-fault states",
        "Health insurance may be secondary or may not cover auto injuries",
        "Workers' comp primary if injury occurred during employment",
        "Medicare conditional payment if auto insurer denies or delays",
    ],
    "verbal_threshold_states": ["New Jersey", "Pennsylvania", "Kentucky"],
    "serious_injury_threshold": "In some states, can sue for pain/suffering only if injury meets serious injury threshold (e.g., significant disfigurement, fracture, permanent limitation)",
}


async def download(force: bool = False) -> dict:
    """Download auto/no-fault insurance reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "auto_nofault.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading auto/no-fault insurance reference...")
    save_json(AUTO_NOFAULT_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded auto/no-fault insurance reference"}