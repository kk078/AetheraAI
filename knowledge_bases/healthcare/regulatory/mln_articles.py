"""
MLN Matters articles index.

Medicare Learning Network (MLN) Matters articles provide education
on Medicare policy changes, coverage updates, and billing guidance.

Source: https://www.cms.gov/Medicare/Coding/Billing-Codes/MLN-Matters-Articles
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, download_text, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Coding/Billing-Codes/MLN-Matters-Articles"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "mln_articles"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.mln_articles"

MLN_ARTICLE_CATEGORIES = [
    {"category": "SE", "name": "Supplier Education", "description": "Articles providing supplier education on Medicare billing and coding"},
    {"category": "MM", "name": "Medicare Matters", "description": "Articles on Medicare policy changes and updates"},
    {"category": "MA", "name": "Medicare Advantage", "description": "Articles specific to Medicare Advantage plans"},
    {"category": "MEDCAC", "name": "Medicare Coverage Advisory", "description": "Advisory Committee meeting summaries and coverage analysis"},
    {"category": "NCD", "name": "National Coverage Determination", "description": "Articles related to NCDs and coverage policy"},
    {"category": "LCD", "name": "Local Coverage Determination", "description": "Articles related to LCDs and MAC-specific coverage"},
    {"category": "CR", "name": "Change Request", "description": "Articles implementing CMS change requests for system updates"},
    {"category": "Trans", "name": "Transmittal", "description": "Articles describing transmittal changes to CMS manuals"},
]


async def download(force: bool = False) -> dict:
    """Download MLN Matters articles index."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "mln_articles_index.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading MLN Matters articles index...")
    save_json(MLN_ARTICLE_CATEGORIES, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": f"Downloaded MLN articles index ({len(MLN_ARTICLE_CATEGORIES)} categories)"}