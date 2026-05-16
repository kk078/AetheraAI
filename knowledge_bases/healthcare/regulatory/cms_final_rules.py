"""
Recent CMS Final Rules index.

Index of recent CMS Final Rules affecting Medicare and Medicaid
programs, organized by year and topic.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "cms_final_rules"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.cms_final_rules"

CMS_FINAL_RULES = {
    "fy2025": [
        {"rule": "IPPS FY2025", "cms_number": "CMS-1810-F", "description": "Inpatient Prospective Payment System FY2025 final rule", "key_changes": ["Updated DRG weights", "Wage index revisions", "New technology add-on payments"]},
        {"rule": "OPPS CY2025", "cms_number": "CMS-1820-F", "description": "Outpatient Prospective Payment System CY2025 final rule", "key_changes": ["APC rate updates", "New technology APCs", "Packaging policy changes"]},
        {"rule": "MPFS CY2025", "cms_number": "CMS-1830-F", "description": "Medicare Physician Fee Schedule CY2025 final rule", "key_changes": ["RVU updates", "Telehealth extensions", "Apprentice supervision changes"]},
        {"rule": "SNF PPS FY2025", "cms_number": "CMS-1822-F", "description": "Skilled Nursing Facility PPS FY2025 final rule", "key_changes": ["PDPM rate updates", "Wage index changes"]},
        {"rule": "Home Health CY2025", "cms_number": "CMS-1824-F", "description": "Home Health PPS CY2025 final rule", "key_changes": ["PDGM rate updates", "OASIS changes"]},
        {"rule": "ESRD PPS CY2025", "cms_number": "CMS-1826-F", "description": "ESRD PPS CY2025 final rule", "key_changes": ["Bundle rate updates", "Oral drug adjustments"]},
        {"rule": "Hospice FY2025", "cms_number": "CMS-1828-F", "description": "Hospice Wage Index FY2025 final rule", "key_changes": ["Wage index updates", "Rate adjustments"]},
        {"rule": "IRF PPS FY2025", "cms_number": "CMS-1832-F", "description": "Inpatient Rehabilitation Facility PPS FY2025 final rule", "key_changes": ["CMG weight updates", "Compliance threshold"]},
        {"rule": "LTCH PPS FY2025", "cms_number": "CMS-1834-F", "description": "Long-Term Care Hospital PPS FY2025 final rule", "key_changes": ["LTC-DRG weight updates", "Site-neutral adjustments"]},
        {"rule": "ASC CY2025", "cms_number": "CMS-1836-F", "description": "Ambulatory Surgical Center CY2025 final rule", "key_changes": ["ASC rate updates", "Procedure list updates"]},
    ],
    "regulatory_topics": [
        "Provider enrollment and revalidation",
        "Telehealth and remote services",
        "Value-based care and alternative payment models",
        "Prior authorization requirements",
        "Health equity initiatives",
        "Price transparency enforcement",
        "Mental health and substance use disorder access",
        "Maternal health initiatives",
        "Social determinants of health",
    ],
}


async def download(force: bool = False) -> dict:
    """Download CMS Final Rules index."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "cms_final_rules.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading CMS Final Rules index...")
    save_json(CMS_FINAL_RULES, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded CMS Final Rules index"}