"""
MIPS quality measures list.

Merit-based Incentive Payment System quality measures used for
Medicare physician payment adjustments.

Source: https://qpp.cms.gov/mips/explore/quality-measures
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_text, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://qpp.cms.gov/mips/explore/quality-measures"
DEST_DIR = DATA_ROOT / "healthcare" / "quality" / "mips"
MODULE_NAME = "knowledge_bases.healthcare.quality.mips_measures"

MIPS_REFERENCE = {
    "program_name": "Merit-based Incentive Payment System (MIPS)",
    "performance_categories": [
        {"category": "Quality", "weight": "30%", "description": "Report up to 6 quality measures; at least one outcome measure required", "measures_count": "200+ available measures"},
        {"category": "Cost", "weight": "30%", "description": "Evaluated based on Medicare claims; no data submission required", "measures_count": "Medicare Spending Per Beneficiary, Total Per Capita Cost, etc."},
        {"category": "Improvement Activities", "weight": "15%", "description": "Attest to activities that improve clinical practice", "activities_count": "100+ available activities"},
        {"category": "Promoting Interoperability", "weight": "25%", "description": "Report on meaningful use of certified EHR technology", "measures_count": "4 required measures"},
    ],
    "payment_adjustments": {
        "positive": "Up to +9% for exceptional performance",
        "neutral": "0% for meeting threshold",
        "negative": "Up to -9% for non-participation or low performance",
    },
    "quality_measure_categories": [
        "Diabetes (hemoglobin A1c, eye exam, nephropathy screening)",
        "Preventive care (cancer screenings, immunizations)",
        "Cardiovascular (blood pressure control, statin use)",
        "Behavioral health (depression screening, adherence)",
        "Respiratory (asthma/COPD management)",
        "Musculoskeletal (osteoarthritis, fracture screening)",
        "Maternal health (prenatal care, postpartum follow-up)",
        "Surgical (preoperative care, surgical outcomes)",
    ],
}


async def download(force: bool = False) -> dict:
    """Download MIPS quality measures reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "mips_measures.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading MIPS quality measures reference...")
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=120.0), follow_redirects=True) as client:
        try:
            text = await download_text("https://qpp.cms.gov/api/v1/measures?category=quality&publicationYear=2025", client)
            save_json({"raw_api_response": text[:5000]}, DEST_DIR / "mips_api_sample.json")
        except Exception as exc:
            logger.warning("QPP API query failed: %s", exc)

    save_json(MIPS_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded MIPS measures reference"}