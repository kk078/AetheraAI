"""
Program Integrity Manual reference.

Key chapters from Pub. 100-08 Medicare Program Integrity Manual,
covering fraud, abuse, and program safeguards.

Source: https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/downloads/PIM.pdf
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/downloads/PIM.pdf"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "program_integrity"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.program_integrity_manual"

PI_MANUAL_CHAPTERS = [
    {"chapter": 1, "title": "Introduction", "key_topics": ["Program integrity overview", "Legal basis", "OIG coordination"]},
    {"chapter": 2, "title": "Sanctions and Exclusions", "key_topics": ["Exclusion authorities", "Sanction actions", "Reinstatement", "OIG exclusions"]},
    {"chapter": 3, "title": "Protecting Provider Integrity", "key_topics": ["Enrollment screening", "Fingerprinting", "Site visits", "Provider enrollment moratoria"]},
    {"chapter": 4, "title": "Claims Review", "key_topics": ["Medical review", "ZPIC/UPIC reviews", "Prepayment review", "Post-payment review"]},
    {"chapter": 5, "title": "Recovery Audit Program", "key_topics": ["RAC audits", "Automated review", "Complex review", "Discussion period"]},
    {"chapter": 6, "title": "Fraud and Abuse", "key_topics": ["Fraud indicators", "Abuse patterns", "Referral to law enforcement", "Qui tam actions"]},
]


async def download(force: bool = False) -> dict:
    """Download Program Integrity Manual chapter index."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "program_integrity_manual.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading Program Integrity Manual chapter index...")
    save_json(PI_MANUAL_CHAPTERS, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": f"Downloaded Program Integrity Manual index ({len(PI_MANUAL_CHAPTERS)} chapters)"}