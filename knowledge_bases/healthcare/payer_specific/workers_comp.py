"""
Workers' Compensation rules by state.

Overview of workers' compensation programs by state including
coverage requirements, fee schedules, and claims processes.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.dol.gov/agencies/owcp"
DEST_DIR = DATA_ROOT / "healthcare" / "payer_specific" / "workers_comp"
MODULE_NAME = "knowledge_bases.healthcare.payer_specific.workers_comp"

WC_REFERENCE = {
    "general_principles": {
        "description": "Workers' compensation provides no-fault coverage for work-related injuries/illnesses",
        "exclusive_remedy": "Workers' comp is typically the exclusive remedy for work injuries; employee gives up right to sue employer",
        "coverage": "Most employers required to carry WC insurance; requirements vary by state",
        "benefits": ["Medical treatment", "Wage replacement (temporary/permanent disability)", "Vocational rehabilitation", "Death benefits for survivors"],
    },
    "federal_programs": [
        {"program": "FECA", "description": "Federal Employees' Compensation Act for federal workers"},
        {"program": "LHWCA", "description": "Longshore and Harbor Workers' Compensation Act"},
        {"program": "JONES Act", "description": "Merchant marine/seamen injury claims"},
        {"program": "BLA", "description": "Black Lung Benefits Act for coal miners"},
    ],
    "state_variations": {
        "medical_fee_schedules": "Most states use fee schedules based on Medicare rates (typically 110-150% of MPFS)",
        "choice_of_provider": "Some states allow employee choice of physician; others require employer-directed care initially",
        "utilization_review": "All states have some form of UR; pre-authorization requirements vary",
        "presumption_laws": "Many states have presumptions for first responders (PTSD, cancer, cardiac, respiratory)",
    },
    "billing_considerations": [
        "Separate billing from group health; cannot balance bill patient",
        "Must use WC-specific claim forms and reporting",
        "Authorization requirements for treatment beyond initial visit",
        "Maximum medical improvement (MMI) determination affects ongoing treatment",
        "Impairment rating determines permanent disability benefits",
    ],
}


async def download(force: bool = False) -> dict:
    """Download Workers' Compensation rules reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "workers_comp.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading Workers' Compensation rules reference...")
    save_json(WC_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded Workers' Compensation rules reference"}