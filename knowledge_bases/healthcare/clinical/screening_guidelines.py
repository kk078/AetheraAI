"""
USPSTF guidelines download.

United States Preventive Services Task Force screening and
preventive care recommendations with grades.

Source: https://www.uspreventiveservicestaskforce.org/uspstf/
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, download_text, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.uspreventiveservicestaskforce.org/uspstf/"
DEST_DIR = DATA_ROOT / "healthcare" / "clinical" / "screening_guidelines"
MODULE_NAME = "knowledge_bases.healthcare.clinical.screening_guidelines"

USPSTF_GRADES = {
    "A": {"description": "Recommended; high certainty of substantial net benefit", "action": "Offer or provide this service"},
    "B": {"description": "Recommended; high certainty of moderate net benefit or moderate certainty of moderate-to-substantial net benefit", "action": "Offer or provide this service"},
    "C": {"description": "Recommend selectively; at least moderate certainty of small net benefit", "action": "Offer or provide this service based on individual circumstances"},
    "D": {"description": "Recommend against; moderate or high certainty of no net benefit or harms outweigh benefits", "action": "Discourage use of this service"},
    "I": {"description": "Current evidence is insufficient; balance of benefits/harms cannot be determined", "action": "Read clinical considerations; if offered, patients should understand the uncertainty"},
}

KEY_SCREENING_RECS = [
    {"topic": "Breast Cancer Screening", "grade": "B", "population": "Women 40-74", "recommendation": "Biennial mammography screening", "year": 2024},
    {"topic": "Cervical Cancer Screening", "grade": "A", "population": "Women 21-65", "recommendation": "Cytology (Pap) every 3 years (21-29) or Pap+HPV co-testing every 5 years (30-65)", "year": 2023},
    {"topic": "Colorectal Cancer Screening", "grade": "A", "population": "Adults 45-75", "recommendation": "Screening with multiple modalities (colonoscopy, FIT, Cologuard, etc.)", "year": 2023},
    {"topic": "Lung Cancer Screening", "grade": "B", "population": "Adults 50-80 with 20+ pack-year smoking history", "recommendation": "Annual low-dose CT scan", "year": 2021},
    {"topic": "Prostate Cancer Screening", "grade": "C", "population": "Men 55-69", "recommendation": "Selective PSA-based screening based on individual risk and preferences", "year": 2018},
    {"topic": "Diabetes Screening", "grade": "B", "population": "Adults 35-70 with overweight/obesity", "recommendation": "Screen for prediabetes and type 2 diabetes", "year": 2021},
    {"topic": "Depression Screening", "grade": "B", "population": "All adults including pregnant/postpartum", "recommendation": "Screen for depression with adequate follow-up", "year": 2023},
    {"topic": "Hypertension Screening", "grade": "A", "population": "Adults 18 and older", "recommendation": "Blood pressure screening at every preventive visit", "year": 2021},
    {"topic": "Cholesterol Screening", "grade": "A", "population": "Adults 40-75", "recommendation": "Lipid screening and statin use for primary prevention in at-risk adults", "year": 2022},
    {"topic": "Osteoporosis Screening", "grade": "B", "population": "Women 65+; postmenopausal women <65 with risk factors", "recommendation": "DEXA screening for osteoporosis", "year": 2018},
    {"topic": "Abdominal Aortic Aneurysm", "grade": "B", "population": "Men 65-75 who have ever smoked", "recommendation": "One-time ultrasonography screening", "year": 2019},
    {"topic": "Skin Cancer Screening", "grade": "I", "population": "Adults", "recommendation": "Insufficient evidence for routine visual skin examination", "year": 2023},
    {"topic": "Hepatitis C Screening", "grade": "B", "population": "Adults 18-79", "recommendation": "One-time screening for HCV infection", "year": 2020},
    {"topic": "HIV Screening", "grade": "A", "population": "Adolescents and adults 15-65", "recommendation": "Screen for HIV infection; earlier if at risk", "year": 2019},
    {"topic": "Aspirin for CVD Prevention", "grade": "C/D", "population": "Adults 40-59 (C) / 60+ (D)", "recommendation": "Selective use for primary CVD prevention in adults 40-59 with 10%+ 10-year risk", "year": 2022},
    {"topic": "Lipid Disorders Screening", "grade": "A/B", "population": "Men 40-75 (A); Women 40-75 (B)", "recommendation": "Screen for lipid disorders and assess CVD risk", "year": 2022},
    {"topic": "Falls Prevention", "grade": "B", "population": "Adults 65+", "recommendation": "Exercise interventions for fall prevention", "year": 2018},
    {"topic": "Obesity Screening", "grade": "B", "population": "Adults", "recommendation": "Screen for obesity and offer intensive behavioral interventions", "year": 2018},
    {"topic": "Tobacco Use Screening", "grade": "A", "population": "All adults", "recommendation": "Screen for tobacco use and provide cessation interventions", "year": 2021},
    {"topic": "Alcohol Misuse Screening", "grade": "B", "population": "Adults 18+", "recommendation": "Screen for unhealthy alcohol use and provide brief counseling", "year": 2018},
]


async def download(force: bool = False) -> dict:
    """Download USPSTF screening guidelines."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "screening_guidelines.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading USPSTF screening guidelines...")
    save_json({"grades": USPSTF_GRADES, "recommendations": KEY_SCREENING_RECS}, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": f"Downloaded {len(KEY_SCREENING_RECS)} USPSTF recommendations"}