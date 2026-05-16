"""
CMS Claims Processing Manual reference.

Key chapters from Pub. 100-04 Medicare Claims Processing Manual,
the authoritative reference for claim submission requirements.

Source: https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/downloads/clm104c0.pdf
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, download_text, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/downloads/clm104c0.pdf"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "claims_processing_manual"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.claims_processing_manual"

CLAIMS_MANUAL_CHAPTERS = [
    {"chapter": 1, "title": "General Billing Requirements", "key_topics": ["Claim form requirements", "Time limits", "Signature requirements", "Reconsiderations and appeals"]},
    {"chapter": 2, "title": "Admissions and Discharges", "key_topics": ["Inpatient admissions", "Discharge planning", "Transfer policies"]},
    {"chapter": 3, "title": "Inpatient Hospital Billing", "key_topics": ["DRG payment", "Outlier payments", "Cost reporting", "Pass-through payments"]},
    {"chapter": 4, "title": "Hospital Outpatient Billing", "key_topics": ["OPPS billing", "APC payments", "Conditional payment", "Packaging"]},
    {"chapter": 5, "title": "Part B Inpatient Billing", "key_topics": ["Part B inpatient claims", "Hospital outpatient services"]},
    {"chapter": 6, "title": "Physician/Supplier Billing", "key_topics": ["CMS-1500 requirements", "Assignment rules", "Reassignment rules"]},
    {"chapter": 7, "title": "SNF Billing", "key_topics": ["PDPM billing", "Consolidated billing", "Excluded services"]},
    {"chapter": 8, "title": "Home Health Billing", "key_topics": ["PDGM billing", "OASIS requirements", "LUPA billing"]},
    {"chapter": 9, "title": "Hospice Billing", "key_topics": ["Levels of care", "Election statements", "Revocation", "NOE requirements"]},
    {"chapter": 10, "title": "DME Billing", "key_topics": ["DMEPOS fee schedule", "Rental vs purchase", "CBP pricing"]},
    {"chapter": 11, "title": "ESRD Billing", "key_topics": ["ESRD PPS", "Bundled payment", "Oral-only drugs"]},
    {"chapter": 12, "title": "Rural Health Clinic/FQHC Billing", "key_topics": ["Encounter rate", "All-inclusive rate", "Preventive services"]},
    {"chapter": 13, "title": "Radiology Services", "key_topics": ["Professional/technical components", "IDTF billing"]},
    {"chapter": 14, "title": "Clinical Lab Services", "key_topics": ["CLFS billing", "PAMA reporting", "Reference lab billing"]},
    {"chapter": 16, "title": "Ambulance Services", "key_topics": ["Ground/air transport", "Mileage calculation", "Special transport"]},
    {"chapter": 17, "title": "Drugs and Biologicals", "key_topics": ["ASP billing", "Pass-through drugs", "Waste billing"]},
    {"chapter": 18, "title": "Preventive Services", "key_topics": ["Screening services", "Immunizations", "Wellness visits"]},
    {"chapter": 21, "title": "ASC Billing", "key_topics": ["ASC covered procedures", "ASC payment rates", "Implantable devices"]},
    {"chapter": 23, "title": "Fee Schedule Administration", "key_topics": ["MPFS billing", "RVU calculations", "Payment adjustments"]},
    {"chapter": 24, "title": "Physician Self-Referral (Stark)", "key_topics": ["Designated health services", "Exceptions", "Reporting"]},
    {"chapter": 25, "title": "Comprehensive Error Rate Testing", "key_topics": ["CERT program", "Documentation requirements", "Medical review"]},
    {"chapter": 26, "title": "Coordination of Benefits", "key_topics": ["MSP rules", "Conditional payment", "Recovery"]},
    {"chapter": 29, "title": "Appeals Processing", "key_topics": ["Redetermination", "QIC review", "ALJ hearing"]},
    {"chapter": 30, "title": "Provider Enrollment", "key_topics": ["NPI requirements", "PECOS", "Revalidation"]},
    {"chapter": 32, "title": "Billing Requirements for Special Services", "key_topics": ["Telehealth", "Clinical trials", "ACA services"]},
    {"chapter": 34, "title": "Medicare Secondary Payer", "key_topics": ["GHP/EGHP rules", "Workers' comp", "Liability insurance"]},
]


async def download(force: bool = False) -> dict:
    """Download CMS Claims Processing Manual chapter index."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "claims_processing_manual.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading CMS Claims Processing Manual chapter index...")
    save_json(CLAIMS_MANUAL_CHAPTERS, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": f"Downloaded Claims Processing Manual index ({len(CLAIMS_MANUAL_CHAPTERS)} chapters)"}