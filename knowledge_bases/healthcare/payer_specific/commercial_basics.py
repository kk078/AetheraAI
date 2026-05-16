"""
Commercial insurance fundamentals reference.

Key concepts and structures of commercial health insurance
relevant to healthcare billing and claims.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.ahip.org/"
DEST_DIR = DATA_ROOT / "healthcare" / "payer_specific" / "commercial_basics"
MODULE_NAME = "knowledge_bases.healthcare.payer_specific.commercial_basics"

COMMERCIAL_REFERENCE = {
    "plan_types": [
        {"type": "HMO", "description": "Health Maintenance Organization; requires PCP and referrals; in-network only (except emergency)", "cost_sharing": "Low copays; no deductible typically for in-network"},
        {"type": "PPO", "description": "Preferred Provider Organization; no PCP/referral requirement; out-of-network available at higher cost", "cost_sharing": "Moderate copays and deductibles; higher OON cost-sharing"},
        {"type": "EPO", "description": "Exclusive Provider Organization; no PCP/referral; in-network only (except emergency)", "cost_sharing": "Similar to HMO but no referrals; lower premiums than PPO"},
        {"type": "POS", "description": "Point of Service; hybrid of HMO and PPO; PCP and referrals for in-network", "cost_sharing": "In-network: HMO-like; Out-of-network: PPO-like with higher cost"},
        {"type": "HDHP", "description": "High Deductible Health Plan; paired with HSA; higher deductible lower premium", "cost_sharing": "High deductible ($1,600+ individual / $3,200+ family in 2024); HSA eligible"},
        {"type": "Indemnity", "description": "Traditional fee-for-service; no network; submit claims for reimbursement", "cost_sharing": "Higher premiums; freedom of choice; typically 80/20 coinsurance"},
    ],
    "key_concepts": [
        {"concept": "Premium", "description": "Monthly payment for insurance coverage"},
        {"concept": "Deductible", "description": "Amount paid out-of-pocket before insurance begins paying"},
        {"concept": "Copay", "description": "Fixed dollar amount paid per service (e.g., $25 PCP visit)"},
        {"concept": "Coinsurance", "description": "Percentage of cost shared after deductible (e.g., 20% patient / 80% plan)"},
        {"concept": "Out-of-Pocket Maximum", "description": "Maximum annual out-of-pocket spending; includes deductible, copays, coinsurance"},
        {"concept": "In-Network", "description": "Providers contracted with the plan at negotiated rates"},
        {"concept": "Out-of-Network", "description": "Providers not contracted; higher cost-sharing and balance billing possible"},
        {"concept": "Prior Authorization", "description": "Plan approval required before certain services are provided"},
        {"concept": "Step Therapy", "description": "Requirement to try less expensive treatment before more expensive option"},
        {"concept": "Formulary", "description": "List of covered prescription drugs with tiered cost-sharing"},
        {"concept": "Explanation of Benefits (EOB)", "description": "Statement from plan showing how claim was processed"},
    ],
    "cob_rules": [
        "Birthday rule: In couples, plan of person whose birthday falls earliest in the year is primary",
        "Active vs COBRA: Active employee plan is primary over COBRA",
        "Employer size: Larger employer plan is primary",
        "Medicare: Usually secondary for working-age beneficiaries with employer coverage",
    ],
    "aca_essential_health_benefits": ["Ambulatory patient services", "Emergency services", "Hospitalization", "Maternity/newborn care", "Mental health/substance use disorder", "Prescription drugs", "Rehabilitative/habilitative services", "Laboratory services", "Preventive/wellness services", "Pediatric services including dental/vision"],
}


async def download(force: bool = False) -> dict:
    """Download commercial insurance fundamentals reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "commercial_basics.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading commercial insurance fundamentals reference...")
    save_json(COMMERCIAL_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded commercial insurance fundamentals reference"}