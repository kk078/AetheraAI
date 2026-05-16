"""
CMS Transmittals index.

CMS transmittals are official instructions that update Medicare
manuals and policies. Each transmittal references specific manual
chapters and provides implementation dates.

Source: https://www.cms.gov/Regulations-and-Guidance/Guidance/Transmittals
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Regulations-and-Guidance/Guidance/Transmittals"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "cms_transmittals"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.cms_transmittals"

TRANSMITTAL_TYPES = [
    {"type": "R", "name": "Regulatory", "description": "Transmittals implementing regulatory changes through rulemaking"},
    {"type": "N", "name": "Non-Regulatory", "description": "Transmittals providing guidance or clarification without regulatory changes"},
    {"type": "CR", "name": "Change Request", "description": "Transmittals implementing system changes and business requirement updates"},
    {"type": "One-Time", "name": "One-Time Notification", "description": "One-time notifications for special situations"},
]

TRANSMITTAL_MANUALS = [
    {"pub": "100-01", "name": "Medicare General Information", "transmittal_prefix": "MGI"},
    {"pub": "100-02", "name": "Medicare Benefit Policy", "transmittal_prefix": "BP"},
    {"pub": "100-03", "name": "Medicare NCD Manual", "transmittal_prefix": "NCD"},
    {"pub": "100-04", "name": "Medicare Claims Processing", "transmittal_prefix": "CP"},
    {"pub": "100-05", "name": "Medicare Secondary Payer", "transmittal_prefix": "MSP"},
    {"pub": "100-08", "name": "Program Integrity", "transmittal_prefix": "PI"},
    {"pub": "100-16", "name": "Medicare Managed Care", "transmittal_prefix": "MC"},
    {"pub": "100-17", "name": "Medicare Part D", "transmittal_prefix": "PD"},
    {"pub": "100-20", "name": "Medicare Appeals", "transmittal_prefix": "AP"},
]


async def download(force: bool = False) -> dict:
    """Download CMS transmittals index."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "cms_transmittals_index.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading CMS transmittals index...")
    transmittal_data = {
        "types": TRANSMITTAL_TYPES,
        "manuals": TRANSMITTAL_MANUALS,
    }
    save_json(transmittal_data, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded CMS transmittals index"}