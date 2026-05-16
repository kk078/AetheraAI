"""
No Surprises Act text reference.

The No Surprises Act protects patients from surprise medical bills
for emergency services, services at in-network facilities by
out-of-network providers, and air ambulance services.

Source: https://www.cms.gov/nosurprises
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, download_text, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/nosurprises"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "no_surprises_act"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.no_surprises_act"

NSA_REFERENCE = {
    "full_name": "No Surprises Act (NSA) - Consolidated Appropriations Act, 2021, Division BB",
    "effective_date": "January 1, 2022",
    "key_provisions": [
        {
            "provision": "Surprise Billing Protection",
            "description": "Prohibits out-of-network providers from billing patients more than the in-network cost-sharing amount for emergency services and certain non-emergency services at in-network facilities",
        },
        {
            "provision": "Independent Dispute Resolution (IDR)",
            "description": "Establishes an independent dispute resolution process for payment disputes between out-of-network providers and health plans",
        },
        {
            "provision": "Good Faith Estimates",
            "description": "Requires providers to give uninsured or self-pay patients good faith estimates of expected charges before services",
        },
        {
            "provision": "Air Ambulance",
            "description": "Limits patient cost-sharing for air ambulance services to in-network rates",
        },
        {
            "provision": "Advanced Explanation of Benefits",
            "description": "Requires health plans to provide an AEOB to insured patients showing estimated costs",
        },
        {
            "provision": "Continuity of Care",
            "description": "Requires plans to provide continuity of care for patients transitioning from out-of-network providers",
        },
    ],
    "idr_process": {
        "initiation": "Either party may initiate IDR within 30 business days of final payment or denial",
        "fees": "$50 administrative fee per dispute; $350-500 for certified IDR entity review",
        "timeline": "IDR entity must decide within 30 business days",
        "criteria": "IDR entity considers qualifying payment amount (QPA), provider training/credentials, market share, patient acuity, and good faith efforts to negotiate",
        "batching": "Similar items/services may be batched for efficiency",
    },
    "qualifying_payment_amount": "Median of contracted rates for the same or similar item/service in the same geographic area",
}


async def download(force: bool = False) -> dict:
    """Download No Surprises Act reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "no_surprises_act.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading No Surprises Act reference...")
    save_json(NSA_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded No Surprises Act reference"}