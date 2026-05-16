"""
False Claims Act (FCA) text reference.

The FCA imposes liability on persons who knowingly submit or cause
the submission of false claims to the federal government. Primary
tool for combating healthcare fraud.

Source: 31 U.S.C. 3729-3733
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.justice.gov/civil/false-claims-act"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "false_claims_act"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.false_claims_act"

FCA_REFERENCE = {
    "full_name": "False Claims Act (FCA) - Lincoln Law",
    "citation": "31 U.S.C. 3729-3733",
    "prohibited_conduct": [
        "Knowingly presenting a false or fraudulent claim for payment",
        "Knowingly making or using a false record material to a false claim",
        "Conspiring to commit a violation of the FCA",
        "Having possession of government property and intending to defraud",
        "Delivering less property than was certified",
        "Certifying receipt of property that was not received",
        "Making a false statement to avoid paying a debt to the government",
        "Concealing or avoiding an obligation to pay the government",
    ],
    "knowledge_standard": "Actual knowledge, deliberate ignorance, or reckless disregard of truth or falsity (no specific intent required)",
    "qui_tam_provisions": {
        "description": "Allows private citizens (relators/whistleblowers) to file suit on behalf of the government",
        "relator_share": "15-30% of recovery depending on government intervention",
        "filing_requirements": "Complaint filed under seal in federal court; served on DOJ",
        "statute_of_limitations": "6 years from violation or 3 years from material disclosure (max 10 years)",
    },
    "penalties": [
        "Treble damages (3x the government's actual damages)",
        "Civil penalties per claim ($11,803 to $23,607 as of 2024, adjusted for inflation)",
        "Per-claim basis means each individual claim counts as a separate violation",
    ],
    "defenses": [
        "No knowledge of falsity",
        "Public disclosure bar (original source exception)",
        "First-to-file bar",
        "Government intervention decision",
    ],
    "healthcare_examples": [
        "Upcoding (billing for higher service level than provided)",
        "Billing for services not rendered",
        "Unbundling (separately billing services that should be bundled)",
        "Falsifying diagnosis codes to support medical necessity",
        "Billing for non-covered services using covered codes",
        "Kickback-driven referrals resulting in false claims",
        "Double billing for the same service",
    ],
}


async def download(force: bool = False) -> dict:
    """Download False Claims Act reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "false_claims_act.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading False Claims Act reference...")
    save_json(FCA_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded False Claims Act reference"}