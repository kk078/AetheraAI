"""
Value-Based Programs (VBP) models reference.

CMS value-based care programs that tie payment to quality and
outcomes rather than volume of services.

Source: https://www.cms.gov/Medicare/Quality-Initiatives-Patient-Assessment-Instruments/Value-Based-Programs
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Quality-Initiatives-Patient-Assessment-Instruments/Value-Based-Programs"
DEST_DIR = DATA_ROOT / "healthcare" / "quality" / "value_based_programs"
MODULE_NAME = "knowledge_bases.healthcare.quality.value_based_programs"

VBP_MODELS = {
    "hospital_vbp": [
        {"program": "Hospital Value-Based Purchasing (VBP)", "description": "Adjusts hospital payments based on quality performance in 4 domains", "domains": ["Clinical Outcomes", "Person and Community Engagement", "Safety", "Efficiency and Cost Reduction"], "adjustment": "Up to 2% payment adjustment"},
        {"program": "Hospital-Acquired Condition (HAC) Reduction Program", "description": "Reduces payments for hospitals with high rates of hospital-acquired conditions", "measures": ["CLABSI", "CAUTI", "SSI", "MRSA", "C. diff", "Falls/trauma", "Pressure ulcers", "DVT/PE"], "adjustment": "1% payment reduction for worst-performing quartile"},
        {"program": "Hospital Readmissions Reduction Program (HRRP)", "description": "Reduces payments for hospitals with excess readmissions", "measures": ["AMI readmission", "HF readmission", "Pneumonia readmission", "CABG readmission", "Hip/knee replacement readmission", "COPD readmission"], "adjustment": "Up to 3% payment reduction"},
    ],
    "physician_vbp": [
        {"program": "MIPS", "description": "Adjusts physician payments based on quality, cost, improvement activities, and promoting interoperability", "adjustment": "Up to +9% bonus or -9% penalty"},
        {"program": "Advanced APMs", "description": "Alternative Payment Models that qualify for 5% lump-sum bonus", "examples": ["MSSP ACOs", "Next Gen ACOs", "Bundled Payments", "Oncology Care Model"], "qualifying_criteria": "25% of payments or 20% of patients through APM"},
    ],
    "aco_models": [
        {"program": "Medicare Shared Savings Program (MSSP)", "description": "ACOs that coordinate care to reduce costs while meeting quality standards", "tracks": ["Basic Track (A, B, C, D, E)", "Enhanced Track"], "quality_measures": "Quality performance score affects shared savings"},
        {"program": "ACO REACH", "description": "Replaced Global and Professional Direct Contracting; test of capitated payments", "options": ["Global option (100% risk)", "Professional option (50% risk)"], "start_date": "2023"},
    ],
    "bundled_payment_models": [
        {"program": "Bundled Payments for Care Improvement Advanced (BPCI-A)", "description": "Test of bundled payment for episodes of care", "episodes": "29 clinical episodes including major joint replacement, cardiac procedures", "model_type": "Retrospective bundled payment with spending target"},
    ],
    "specialty_models": [
        {"program": "End-Stage Renal Disease Treatment Choice (ETC)", "description": "Encourages home dialysis and kidney transplantation", "adjustment": "Payment adjustment based on home dialysis and transplant rates"},
        {"program": "Oncology Care Model (OCM)", "description": "Episode-based payment for cancer care", "status": "Ended 2022; successor model pending"},
        {"program": "Primary Care First (PCF)", "description": "Tests primary care payment models with 5 regions", "options": ["General", "High Needs Populations"], "status": "Ended 2023"},
    ],
    "demonstration_projects": [
        "State Innovation Models (SIM)",
        "Financial Alignment Initiative (dual eligibles)",
        "Medicaid Health Home State Plan Amendment",
        "Delivery System Reform Incentive Payment (DSRIP)",
        "Accountable Health Communities Model",
    ],
}


async def download(force: bool = False) -> dict:
    """Download Value-Based Programs reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "value_based_programs.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading Value-Based Programs reference...")
    save_json(VBP_MODELS, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded Value-Based Programs reference"}