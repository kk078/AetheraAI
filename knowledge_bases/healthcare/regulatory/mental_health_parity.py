"""
MHPAEA text reference.

The Mental Health Parity and Addiction Equity Act requires that
financial requirements and treatment limitations for mental health
and substance use disorder benefits be comparable to medical/surgical
benefits.

Source: 29 U.S.C. 1185a; 42 U.S.C. 300gg-26
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.dol.gov/agencies/ebsa/laws-and-regulations/laws/mental-health-parity"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "mental_health_parity"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.mental_health_parity"

MHPAEA_REFERENCE = {
    "full_name": "Mental Health Parity and Addiction Equity Act (MHPAEA)",
    "citation": "29 U.S.C. 1185a; 42 U.S.C. 300gg-26; 45 CFR Part 146",
    "effective_date": "January 1, 2010 (group health plans); July 1, 2010 (non-federal governmental plans)",
    "key_requirements": [
        {
            "requirement": "Financial Requirements Parity",
            "description": "Cost-sharing (deductibles, copays, coinsurance) for MH/SUD benefits must be no more restrictive than for medical/surgical benefits in the same classification",
        },
        {
            "requirement": "Treatment Limitation Parity",
            "description": "Day/visit limits, facility limits, and geographic limits for MH/SUD must be no more restrictive than medical/surgical in the same classification",
        },
        {
            "requirement": "Non-Quantitative Treatment Limitations (NQTL)",
            "description": "Medical management standards, formulary design, network adequacy, and standards for provider admission must be comparable for MH/SUD and medical/surgical",
        },
    ],
    "benefit_classifications": [
        "Inpatient in-network",
        "Inpatient out-of-network",
        "Outpatient in-network",
        "Outpatient out-of-network",
        "Emergency care",
        "Prescription drugs",
    ],
    "parity_analysis": "For each classification, the plan must analyze whether MH/SUD benefits are subject to more restrictive requirements than the predominant medical/surgical benefits",
    "non_quantitative_treatment_limitations": [
        "Medical management standards (prior auth, step therapy, fail-first requirements)",
        "Formulary design for prescription drugs",
        "Standards for provider type and admission to network",
        "Plan methods for determining reimbursement rates",
        "Service restrictions based on facility type or location",
        "Exclusions based on failure to complete a course of treatment",
    ],
    "enforcement": "Enforced by DOL, HHS, and state insurance commissioners; plans must perform and document NQTL comparative analyses",
}


async def download(force: bool = False) -> dict:
    """Download MHPAEA reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "mental_health_parity.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading MHPAEA reference...")
    save_json(MHPAEA_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded MHPAEA reference"}