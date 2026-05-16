"""
Major clinical guideline references.

Index of major clinical practice guidelines from professional
organizations and evidence-based medicine resources.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.ahrq.gov/gam/index.html"
DEST_DIR = DATA_ROOT / "healthcare" / "clinical" / "clinical_guidelines"
MODULE_NAME = "knowledge_bases.healthcare.clinical.clinical_guidelines"

CLINICAL_GUIDELINES = {
    "cardiology": [
        {"org": "AHA/ACC", "topic": "Hypertension", "year": 2017, "key_recommendation": "BP target <130/80 for most adults; lifestyle modifications as first-line"},
        {"org": "AHA/ACC", "topic": "Heart Failure", "year": 2022, "key_recommendation": "ARNI/ACEI/ARB + beta-blocker + MRA + SGLT2i for HFrEF"},
        {"org": "AHA/ACC", "topic": "Atrial Fibrillation", "year": 2023, "key_recommendation": "Rate vs rhythm control; DOACs preferred for anticoagulation"},
        {"org": "AHA/ACC", "topic": "Valvular Heart Disease", "year": 2021, "key_recommendation": "TAVR for severe AS in patients 65+ or intermediate surgical risk"},
        {"org": "AHA/ACC", "topic": "Chest Pain Evaluation", "year": 2021, "key_recommendation": "Standardized pathway for acute chest pain; hs-troponin preferred"},
    ],
    "endocrinology": [
        {"org": "ADA", "topic": "Standards of Medical Care in Diabetes", "year": 2024, "key_recommendation": "A1c <7% for most; individualize targets; SGLT2i/GLP-1RA for ASCVD/CKD"},
        {"org": "AACE", "topic": "Diabetes Management Algorithm", "year": 2023, "key_recommendation": "Weight management central; GLP-1 RA first-line for weight loss"},
        {"org": "ATA", "topic": "Thyroid Nodule/Differentiated Thyroid Cancer", "year": 2015, "key_recommendation": "Molecular testing for indeterminate nodules; risk-stratified management"},
    ],
    "pulmonology": [
        {"org": "GOLD", "topic": "COPD Management", "year": 2024, "key_recommendation": "LABA/LAMA for symptomatic COPD; ICS for exacerbations; SABAs for rescue"},
        {"org": "GINA", "topic": "Asthma Management", "year": 2024, "key_recommendation": "ICS-formoterol as needed for mild asthma; biologic therapy for severe"},
    ],
    "oncology": [
        {"org": "NCCN", "topic": "Clinical Practice Guidelines in Oncology", "year": "Annual updates", "key_recommendation": "Disease-specific guidelines; molecular testing for targeted therapy"},
        {"org": "ASCO", "topic": "Various Cancer Guidelines", "year": "Ongoing", "key_recommendation": "Evidence-based recommendations for cancer treatment and surveillance"},
    ],
    "infectious_disease": [
        {"org": "IDSA", "topic": "Antibiotic Stewardship", "year": 2016, "key_recommendation": "Antibiotic time-out at 48-72 hours; narrow spectrum when possible"},
        {"org": "CDC/IDSA", "topic": "COVID-19 Treatment Guidelines", "year": "Ongoing", "key_recommendation": "Risk-based treatment; Paxlovid for high-risk outpatients"},
    ],
    "gastroenterology": [
        {"org": "AGA", "topic": "IBD Management", "year": "Ongoing", "key_recommendation": "Treat-to-target approach; biologic therapy for moderate-severe"},
        {"org": "ACG", "topic": "GERD Management", "year": 2022, "key_recommendation": "PPIs most effective; step-down approach for maintenance"},
    ],
    "neurology": [
        {"org": "AAN", "topic": "Dementia Management", "year": 2018, "key_recommendation": "Cholinesterase inhibitors for mild-moderate Alzheimer's; non-pharmacologic first-line"},
        {"org": "AHA/ASA", "topic": "Stroke Prevention", "year": 2021, "key_recommendation": "DOACs for non-valvular AF; carotid endarterectomy for symptomatic stenosis"},
    ],
}


async def download(force: bool = False) -> dict:
    """Download clinical guidelines reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "clinical_guidelines.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading clinical guidelines reference...")
    save_json(CLINICAL_GUIDELINES, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    total = sum(len(v) for v in CLINICAL_GUIDELINES.values() if isinstance(v, list))
    return {"files_downloaded": 1, "message": f"Downloaded clinical guidelines reference ({total} guidelines)"}