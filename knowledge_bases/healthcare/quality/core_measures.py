"""
CMS Core Measures reference.

Core measure sets used for quality reporting across Medicare
programs.

Source: https://www.cms.gov/Medicare/Quality-Initiatives-Patient-Assessment-Instruments/QualityMeasures
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Quality-Initiatives-Patient-Assessment-Instruments/QualityMeasures"
DEST_DIR = DATA_ROOT / "healthcare" / "quality" / "core_measures"
MODULE_NAME = "knowledge_bases.healthcare.quality.core_measures"

CMS_CORE_MEASURES = {
    "hospital_core_measures": {
        "program": "Hospital Quality Reporting (IQR)",
        "measure_domains": ["Mortality", "Safety of Care", "Readmissions", "Patient Experience", "Timeliness", "Effectiveness of Care", "Medical Imaging", "Payment"],
        "key_measures": [
            "30-day mortality (AMI, HF, pneumonia, CABG)",
            "30-day readmissions (AMI, HF, pneumonia, CABG, hip/knee replacement)",
            "Central line-associated bloodstream infection (CLABSI)",
            "Catheter-associated urinary tract infection (CAUTI)",
            "Surgical site infection (SSI)",
            "Hospital-acquired conditions (HAC)",
            "Medicare Spending Per Beneficiary (MSPB)",
        ],
    },
    "physician_quality_measures": {
        "program": "MIPS Quality Category",
        "key_measures": [
            "Controlling high blood pressure",
            "Diabetes: hemoglobin A1c control",
            "Breast cancer screening",
            "Colorectal cancer screening",
            "Falls: screening for future fall risk",
            "Preventive care and screening: tobacco use",
            "Depression screening and follow-up",
        ],
    },
    "post_acute_measures": {
        "programs": ["SNF QRP", "HH QRP", "IRF QRP", "LTCH QRP", "Hospice QRP"],
        "key_measures": [
            "Functional status assessment",
            "Skin integrity / pressure ulcers",
            "Falls with major injury",
            "Hospital readmission",
            "Discharge to community",
            "Drug regimen review",
        ],
    },
}


async def download(force: bool = False) -> dict:
    """Download CMS Core Measures reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "core_measures.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading CMS Core Measures reference...")
    save_json(CMS_CORE_MEASURES, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded CMS Core Measures reference"}