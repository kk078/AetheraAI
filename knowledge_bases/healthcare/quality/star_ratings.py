"""
MA Star Ratings methodology reference.

Medicare Advantage Star Ratings measure plan quality and performance
on a 1-5 star scale. Used for quality bonus payments and enrollment
messaging.

Source: https://www.cms.gov/Medicare/Prescription-Drug-Coverage/PrescriptionDrugCovGenIn
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Prescription-Drug-Coverage/PrescriptionDrugCovGenIn"
DEST_DIR = DATA_ROOT / "healthcare" / "quality" / "star_ratings"
MODULE_NAME = "knowledge_bases.healthcare.quality.star_ratings"

STAR_RATINGS_REFERENCE = {
    "methodology": "CMS assigns Star Ratings on a 1-5 scale based on plan performance across quality measures",
    "rating_categories": [
        {"category": "Staying Healthy", "description": "Preventive care, screenings, and vaccinations", "example_measures": ["Breast cancer screening", "Colorectal cancer screening", "Diabetes screening", "Flu shot"]},
        {"category": "Managing Chronic Conditions", "description": "Care for members with chronic conditions", "example_measures": ["Diabetes care", "Blood pressure control", "Cholesterol management", "Osteoporosis management"]},
        {"category": "Member Experience", "description": "CAHPS survey results and complaints", "example_measures": ["Getting needed care", "Getting appointments quickly", "Rating of health plan", "Complaints about plan"]},
        {"category": "Member Complaints and Performance", "description": "Complaints, enrollment changes, and customer service", "example_measures": ["Complaints about plan", "Members choosing to leave plan", "Call center performance"]},
        {"category": "Customer Service", "description": "Plan administration and service", "example_measures": ["Call center timeliness", "Appeals auto-forwarded", "Plan timeliness for appeals"]},
    ],
    "quality_bonus_payment": {
        "description": "Plans rated 4+ stars receive a quality bonus payment that increases their rebate percentage",
        "rebate_percentage": "5-star plans can receive up to the full benchmark as rebate",
    },
    "special_needs_plans": "D-SNP, C-SNP, and I-SNP plans have additional measures for special needs populations",
}


async def download(force: bool = False) -> dict:
    """Download MA Star Ratings methodology reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "star_ratings.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading MA Star Ratings methodology reference...")
    save_json(STAR_RATINGS_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded Star Ratings reference"}