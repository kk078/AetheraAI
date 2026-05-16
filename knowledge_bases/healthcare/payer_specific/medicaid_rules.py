"""
Medicaid general rules reference.

General Medicaid program rules including eligibility, mandatory
and optional benefits, and federal-state partnership structure.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.medicaid.gov/medicaid/index.html"
DEST_DIR = DATA_ROOT / "healthcare" / "payer_specific" / "medicaid_rules"
MODULE_NAME = "knowledge_bases.healthcare.payer_specific.medicaid_rules"

MEDICAID_REFERENCE = {
    "program_structure": "Federal-state partnership; states administer within federal guidelines; federal matching (FMAP) varies by state",
    "eligibility_groups": ["Children (up to 19, income up to 200-300% FPL in expansion states)", "Pregnant women (income up to 138-220% FPL)", "Parents/caretakers (varies by state)", "Aged/blind/disabled (SSI-based or 209(b) states)", "Expansion adults (18-64, income up to 138% FPL in expansion states)", "Medically needy (spend-down states)", "Special groups (breast/cervical cancer, TB, family planning)"],
    "mandatory_benefits": ["Inpatient hospital services", "Outpatient hospital services", "EPSDT (Early Periodic Screening, Diagnosis, Treatment for children)", "Nursing facility services (21+)", "Home health services", "Physician services", "Rural health clinic services", "FQHC services", "Laboratory and X-ray services", "Pediatric and family nurse practitioner services", "Freestanding birth center services", "Medical/surgical dental services", "Transportation services", "Tobacco cessation counseling for pregnant women"],
    "optional_benefits": ["Prescription drugs", "Clinic services", "Dental services", "Physical therapy", "Occupational therapy", "Speech/hearing/language therapy", "Respiratory care services", "Podiatry services", "Optometry services", "Chiropractic services", "Hospice care", "Case management", "Personal care services", "Habilitative services", "Private duty nursing", "Prosthetics/orthotics", "DME", "Community mental health services", "Rehabilitative services", "TB-related services"],
    "managed_care": "Most states use managed care delivery; MCOs, PIHPs, PAHPs, PCCMs",
    "waivers": ["Section 1115 (research/demonstration)", "Section 1915(b) (freedom of choice)", "Section 1915(c) (home/community-based services)", "Section 1915(i) (HCBS for non-institutional)", "Section 1915(j) (self-direction)", "Section 1915(k) (Community First Choice)"],
}


async def download(force: bool = False) -> dict:
    """Download Medicaid general rules reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "medicaid_rules.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading Medicaid rules reference...")
    save_json(MEDICAID_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded Medicaid rules reference"}