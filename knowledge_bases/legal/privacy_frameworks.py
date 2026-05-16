"""
Privacy framework reference.

Privacy and data protection frameworks applicable to healthcare
data including GDPR, CCPA/CPRA, and other state privacy laws.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.hhs.gov/hipaa/index.html"
DEST_DIR = DATA_ROOT / "legal" / "privacy"
MODULE_NAME = "knowledge_bases.legal.privacy_frameworks"

PRIVACY_REFERENCE = {
    "hipaa": {"jurisdiction": "US Healthcare", "scope": "Protected Health Information (PHI) held by covered entities and business associates", "key_requirements": ["Privacy Rule - uses/disclosures of PHI", "Security Rule - ePHI safeguards", "Breach Notification Rule", "Enforcement Rule with penalties"], "individual_rights": ["Access to records", "Amendment requests", "Accounting of disclosures", "Restriction requests", "Confidential communications"]},
    "gdpr": {"jurisdiction": "EU/EEA", "scope": "Personal data of EU residents processed by any organization", "key_requirements": ["Lawful basis for processing", "Data minimization", "Purpose limitation", "Storage limitation", "Data protection impact assessments", "Data Protection Officer appointment", "72-hour breach notification"], "individual_rights": ["Right of access", "Right to rectification", "Right to erasure (right to be forgotten)", "Right to restriction", "Right to data portability", "Right to object", "Rights regarding automated decision-making"], "healthcare_specific": "Article 9: Special category data (health data) requires explicit consent or other Article 9(2) condition; processing for healthcare treatment/payment exempted from consent requirement under 9(2)(h)"},
    "ccpa_cpra": {"jurisdiction": "California", "scope": "Personal information of California consumers collected by for-profit businesses meeting thresholds", "key_requirements": ["Right to know", "Right to delete", "Right to opt out of sale/sharing", "Right to correct", "Right to limit use of sensitive personal information", "Non-discrimination for exercising rights"], "healthcare_exceptions": "Medical information governed by CMIA; HIPAA-covered data generally exempt from CCPA/CPRA; de-identified health data can be used"},
    "state_privacy_laws": [
        {"state": "Virginia", "law": "VCDPA", "effective": "2023", "scope": "Consumer data including health data"},
        {"state": "Colorado", "law": "CPA", "effective": "2023", "scope": "Consumer data with opt-out for targeted ads/sale"},
        {"state": "Connecticut", "law": "CTDPA", "effective": "2023", "scope": "Consumer data with opt-out rights"},
        {"state": "Utah", "law": "UCPA", "effective": "2023", "scope": "Consumer data; less restrictive than other state laws"},
        {"state": "Iowa", "law": "Iowa Consumer Data Protection Act", "effective": "2025", "scope": "Consumer data with opt-out rights"},
        {"state": "Indiana", "law": "Indiana Consumer Data Protection Act", "effective": "2026", "scope": "Consumer data protection"},
        {"state": "Montana", "law": "MCDPA", "effective": "2024", "scope": "Consumer data with opt-out"},
        {"state": "Texas", "law": "Texas Data Privacy and Security Act", "effective": "2024", "scope": "Consumer data protection"},
        {"state": "Oregon", "law": "Oregon Consumer Privacy Act", "effective": "2024", "scope": "Consumer data protection"},
        {"state": "New York", "law": "NYDFS Cybersecurity Regulation", "effective": "2017 (amended 2023)", "scope": "Financial services; applies to health insurers"},
    ],
    "data_localization": [
        {"jurisdiction": "EU", "requirement": "GDPR does not require data localization but restricts transfers outside EEA; adequacy decisions or SCCs required"},
        {"jurisdiction": "China", "requirement": "PIPL requires critical data to be stored in China; cross-border transfer requires security assessment"},
        {"jurisdiction": "Russia", "requirement": "Personal data of Russian citizens must be stored on servers in Russia"},
        {"jurisdiction": "Brazil", "requirement": "LGPD does not require localization but requires adequacy for international transfers"},
    ],
}


async def download(force: bool = False) -> dict:
    """Download privacy framework reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "privacy_frameworks.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading privacy framework reference...")
    save_json(PRIVACY_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded privacy framework reference"}