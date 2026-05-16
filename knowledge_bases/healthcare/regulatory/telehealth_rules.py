"""
Telehealth regulations by state.

State-specific telehealth regulations including prescribing rules,
consent requirements, and reimbursement policies.

Source: https://www.cchpca.org/topic/state-telehealth-laws-and-reimbursement-policies
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, download_text, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cchpca.org/topic/state-telehealth-laws-and-reimbursement-policies"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "telehealth"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.telehealth_rules"

TELEHEALTH_FEDERAL = {
    "medicare_telehealth": {
        "description": "Medicare covers telehealth services when the patient is at an eligible originating site",
        "originating_sites": ["Office", "Rural Health Clinic", "FQHC", "Hospital-based renal dialysis center", "SNF", "Hospital", "Community Mental Health Center"],
        "post_covid_permanent": [
            "Audio-only telehealth for mental health services",
            "FQHC/RHC as distant site providers",
            "Certain services can be delivered via telehealth permanently",
        ],
        "geographic_restrictions_removed": "Post-COVID, geographic restrictions are waived for certain telehealth services",
    },
    "prescribing_via_telehealth": {
        "dea_requirements": "Ryan Haight Act requires in-person examination for controlled substance prescribing via telehealth, with limited exceptions",
        "dea_telehealth_exception": "During COVID PHE, DEA allowed prescribing via telehealth; extended flexibilities are being phased in",
    },
}

STATE_TELEHEALTH_SUMMARY = {
    "common_elements": [
        "Informed consent requirements (most states require documented consent)",
        "Licensing requirements (provider must be licensed in the state where patient is located)",
        "Prescribing restrictions (vary by state, especially for controlled substances)",
        "Reimbursement parity (many states require parity with in-person visits)",
        "Modality requirements (some states specify synchronous vs asynchronous)",
    ],
    "categories": [
        "Full parity states: Require reimbursement at same rate as in-person",
        "Partial parity states: Require coverage but not necessarily same rate",
        "Limited telehealth states: Limited requirements for coverage/reimbursement",
    ],
}


async def download(force: bool = False) -> dict:
    """Download telehealth regulations reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "telehealth_rules.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading telehealth regulations reference...")
    combined = {"federal": TELEHEALTH_FEDERAL, "state_summary": STATE_TELEHEALTH_SUMMARY}
    save_json(combined, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded telehealth regulations reference"}