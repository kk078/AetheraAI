"""
HIPAA rule text from HHS.

Health Insurance Portability and Accountability Act rules including
Privacy, Security, Breach Notification, and Enforcement Rules.

Source: https://www.hhs.gov/hipaa/index.html
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, download_text, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.hhs.gov/hipaa/index.html"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "hipaa"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.hipaa_rules"

HIPAA_RULES = {
    "rules": [
        {
            "name": "Privacy Rule",
            "citation": "45 CFR Parts 160 and 164, Subparts A and E",
            "description": "Establishes national standards for the protection of individually identifiable health information (PHI)",
            "key_provisions": [
                "Uses and disclosures of PHI",
                "Minimum necessary standard",
                "Patient rights (access, amendment, accounting)",
                "Notice of Privacy Practices",
                "Authorization requirements",
                "Business Associate Agreements",
                "De-identification standards (Safe Harbor, Expert Determination)",
                "Marketing and fundraising restrictions",
                "Research provisions",
            ],
            "compliance_date": "April 14, 2003 (most covered entities)",
        },
        {
            "name": "Security Rule",
            "citation": "45 CFR Parts 160 and 164, Subparts A and C",
            "description": "Establishes national standards for the security of electronic protected health information (ePHI)",
            "key_provisions": [
                "Administrative safeguards (workforce training, risk analysis, policies)",
                "Physical safeguards (facility access, workstation security, device/media controls)",
                "Technical safeguards (access controls, audit controls, integrity controls, transmission security)",
                "Organizational requirements (BAA, group health plan requirements)",
                "Policies and procedures documentation",
            ],
            "compliance_date": "April 20, 2005 (most covered entities)",
        },
        {
            "name": "Breach Notification Rule",
            "citation": "45 CFR Parts 160 and 164, Subparts A and D",
            "description": "Requires notification to individuals, HHS, and sometimes media following a breach of unsecured PHI",
            "key_provisions": [
                "Definition of breach",
                "Risk of harm assessment",
                "Notification requirements (timelines, content)",
                "HHS notification (annual for <500, 60 days for 500+)",
                "Media notification for breaches of 500+ in a state/jurisdiction",
                "Exception for unintentional/access/disclosure",
                "Safe harbor for encrypted data",
            ],
            "compliance_date": "September 23, 2009",
        },
        {
            "name": "Enforcement Rule",
            "citation": "45 CFR Part 160, Subparts C and D",
            "description": "Establishes rules for investigation, compliance review, and penalties for HIPAA violations",
            "key_provisions": [
                "Civil monetary penalty tiers (up to $1.5M per violation category per year)",
                "Criminal penalties (up to $250K and 10 years for intentional violations)",
                "Investigation procedures",
                "Compliance review procedures",
                "Willful neglect standards",
            ],
            "compliance_date": "February 16, 2009 (HITECH enhancements)",
        },
    ],
    "covered_entities": [
        "Health care providers who transmit health information electronically",
        "Health plans (insurers, HMOs, employer-sponsored plans, government programs)",
        "Health care clearinghouses",
    ],
    "business_associates": "Persons or entities that perform functions on behalf of a covered entity involving PHI access",
    "hitech_act": {
        "description": "Health Information Technology for Economic and Clinical Health Act (2009)",
        "key_changes": [
            "Extended HIPAA requirements to business associates",
            "Strengthened enforcement and penalty structures",
            "Required breach notification",
            "Promoted adoption of electronic health records",
        ],
    },
}


async def download(force: bool = False) -> dict:
    """Download HIPAA rule reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "hipaa_rules.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading HIPAA rules reference...")
    save_json(HIPAA_RULES, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded HIPAA rules reference"}