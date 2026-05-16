"""
Contract template download.

Standard contract template references including BAA, NDA, and
healthcare-specific contract structures.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, download_text, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.hhs.gov/hipaa/for-professionals/covered-entities/sample-business-associate-agreement-provisions/index.html"
DEST_DIR = DATA_ROOT / "legal" / "contracts"
MODULE_NAME = "knowledge_bases.legal.contract_templates"

CONTRACT_TYPES = {
    "healthcare_contracts": [
        {"type": "Business Associate Agreement (BAA)", "description": "Required under HIPAA when a covered entity shares PHI with a business associate", "key_provisions": ["Permitted uses/disclosures of PHI", "Safeguards requirements", "Reporting of breaches/incidents", "Return/destruction of PHI at termination", "Subcontractor requirements", "HIPAA compliance obligations"]},
        {"type": "Managed Care Contract", "description": "Agreement between provider and health plan for network participation", "key_provisions": ["Reimbursement rates and fee schedules", "Credentialing requirements", "Utilization management", "Claims submission and payment terms", "Termination provisions", "Quality requirements"]},
        {"type": "Medical Director Agreement", "description": "Contract for physician serving as medical director", "key_provisions": ["Scope of services", "Time commitments", "Fair market value compensation", "Stark Law compliance", "Duties and responsibilities", "Liability and indemnification"]},
        {"type": "Employment Agreement (Physician)", "description": "Employment contract for physicians", "key_provisions": ["Compensation structure", "Productivity incentives", "Non-compete restrictions", "Malpractice coverage", "Partnership track", "Termination provisions"]},
        {"type": "Group Purchasing Agreement", "description": "Contract with GPO for supply procurement", "key_provisions": ["Pricing tiers", "Volume commitments", "Product listings", "Term and renewal", "Compliance requirements"]},
    ],
    "general_contracts": [
        {"type": "Non-Disclosure Agreement (NDA)", "description": "Confidentiality agreement for sharing proprietary information", "key_provisions": ["Definition of confidential information", "Permitted disclosures", "Term of confidentiality", "Remedies for breach"]},
        {"type": "Master Services Agreement (MSA)", "description": "Framework agreement for ongoing service relationships", "key_provisions": ["Statement of work process", "Payment terms", "Intellectual property", "Limitation of liability", "Termination rights"]},
        {"type": "Software License Agreement", "description": "License for software use", "key_provisions": ["License scope", "Usage restrictions", "Support and maintenance", "Warranties", "Indemnification"]},
    ],
}


async def download(force: bool = False) -> dict:
    """Download contract template references."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "contract_templates.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading contract template references...")
    save_json(CONTRACT_TYPES, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded contract template references"}