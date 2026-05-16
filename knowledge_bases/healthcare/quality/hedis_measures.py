"""
HEDIS measure specs (public summary).

Healthcare Effectiveness Data and Information Set measures are used
to assess health plan performance. Full specifications require NCQA
license.

Source: https://www.ncqa.org/hedis/
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_placeholder, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.ncqa.org/hedis/"
DEST_DIR = DATA_ROOT / "healthcare" / "quality" / "hedis"
MODULE_NAME = "knowledge_bases.healthcare.quality.hedis_measures"

HEDIS_MEASURES = [
    {"domain": "Effectiveness of Care", "measures": [
        "Breast Cancer Screening (BCS)", "Cervical Cancer Screening (CCS)", "Colorectal Cancer Screening (COL)",
        "Chlamydia Screening (CHL)", "Childhood Immunizations (CIS)", "Immunizations for Adolescents (IMA)",
        "Flu Vaccinations (FLU)", "Pneumococcal Vaccination (PNE)", "Diabetes Care (CDC)", "Hemoglobin A1c Control (CBP)",
    ]},
    {"domain": "Access/Availability of Care", "measures": [
        "Adults Access to Preventive Care (AAP)", "Children Access to Primary Care (CAP)",
        "Well-Child Visits (W30)", "Prenatal/Postpartum Care (PPC)",
    ]},
    {"domain": "Experience of Care", "measures": [
        "CAHPS Health Plan Survey", "CAHPS Clinician/Group Survey",
    ]},
    {"domain": "Utilization and Risk-Adjusted Utilization", "measures": [
        "Inpatient Utilization (IPU)", "Ambulatory Care (AMB)", "Emergency Department Utilization (EDU)",
        "Acute Hospital Utilization (AHU)", "Mental Health Utilization (MHU)",
    ]},
    {"domain": "Health Plan Descriptive Information", "measures": [
        "Board Certification (BDC)", "Practitioner Turnover (PTC)",
    ]},
    {"domain": "Measures Collected Using Electronic Clinical Data Systems", "measures": [
        "Controlling High Blood Pressure (CBP-E)", "Diabetes Care (CDC-E)",
        "Hemoglobin A1c Control (CBP-E)",
    ]},
]


async def download(force: bool = False) -> dict:
    """Download HEDIS measures reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "hedis_measures.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading HEDIS measures reference...")
    save_json(HEDIS_MEASURES, codes_json)
    write_placeholder(DEST_DIR, MODULE_NAME, "HEDIS Full Specifications",
        "Full HEDIS specifications require an NCQA license.\n1. Visit https://www.ncqa.org/hedis/\n2. Purchase HEDIS Volume 1 and Volume 2\n3. Place the specification files in this directory\n4. Re-run to generate structured JSON",
        SOURCE_URL)
    file_list = [codes_json.name, "LICENSED_DATA_INSTRUCTIONS.json"]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 2, "message": f"Downloaded HEDIS measures reference ({len(HEDIS_MEASURES)} domains)"}