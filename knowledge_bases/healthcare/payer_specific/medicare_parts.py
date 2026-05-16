"""
Medicare Parts A/B/C/D rules reference.

Comprehensive reference for Medicare program structure including
coverage, cost-sharing, and enrollment rules for each part.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.medicare.gov/basics/get-started-with-medicare"
DEST_DIR = DATA_ROOT / "healthcare" / "payer_specific" / "medicare_parts"
MODULE_NAME = "knowledge_bases.healthcare.payer_specific.medicare_parts"

MEDICARE_PARTS = {
    "part_a": {"name": "Hospital Insurance", "premium": "Usually $0 if 40+ quarters of Medicare taxes; up to $505/month otherwise", "deductible": "$1,676 per benefit period (2025)", "coinsurance": "Days 1-60: $0; Days 61-90: $419/day; Days 91+: $838 lifetime reserve days", "covers": ["Inpatient hospital care", "Skilled nursing facility (up to 100 days)", "Home health services", "Hospice care", "Religious non-medical health care institution care"]},
    "part_b": {"name": "Medical Insurance", "premium": "$174.70/month standard (2024); higher for incomes >$103K", "deductible": "$240/year (2024)", "coinsurance": "20% of Medicare-approved amount after deductible", "covers": ["Physician/clinician services", "Outpatient hospital care", "Preventive services", "Durable medical equipment", "Mental health services", "Ambulance services", "Clinical laboratory services", "Some home health services"]},
    "part_c": {"name": "Medicare Advantage", "description": "Private health plans that contract with Medicare to provide Part A and B benefits, usually including Part D", "types": ["HMO", "PPO", "PFFS", "SNP", "HMO-POS", "MSA", "Cost plans"], "extra_benefits": ["Vision", "Dental", "Hearing", "Wellness programs", "OTC allowances"], "enrollment": "Annual enrollment period: Oct 15 - Dec 7; Open enrollment: Jan 1 - Mar 31"},
    "part_d": {"name": "Prescription Drug Coverage", "premium": "Varies by plan; average ~$55/month", "deductible": "Up to $545/year (2024); many plans waive or reduce", "coverage_gap": "Donut hole: after $5,030 total drug costs until $8,000 out-of-pocket; then catastrophic coverage with $0 cost-sharing", "covers": ["Formulary prescription drugs", "Vaccines", "Selected OTC items per plan formulary"]},
    "medigap": {"name": "Medicare Supplement Insurance", "description": "Private insurance that helps pay costs not covered by Parts A and B (copays, coinsurance, deductibles)", "plans": "Plans A, B, C, D, F, G, K, L, M, N (standardized in most states)", "enrollment": "Open enrollment: 6 months after turning 65 and enrolling in Part B", "notes": "Plan F and C not available to those who turned 65 after January 1, 2020"},
}


async def download(force: bool = False) -> dict:
    """Download Medicare Parts reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "medicare_parts.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading Medicare Parts reference...")
    save_json(MEDICARE_PARTS, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded Medicare Parts A/B/C/D reference"}