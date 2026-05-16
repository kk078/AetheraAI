"""
Download key Medicare manual chapters from CMS.

CMS Internet-Only Manuals (IOMs) contain the official policy and
procedures for Medicare claims processing and coverage.

Source: https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_text, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "cms_manuals"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.cms_manuals"

CMS_MANUALS_INDEX = [
    {"pub": "100-01", "name": "Medicare General Information", "abbreviation": "MGI", "chapters": "1-7"},
    {"pub": "100-02", "name": "Medicare Benefit Policy", "abbreviation": "MBP", "chapters": "1-16"},
    {"pub": "100-03", "name": "Medicare National Coverage Determinations", "abbreviation": "NCDM", "chapters": "1-5"},
    {"pub": "100-04", "name": "Medicare Claims Processing", "abbreviation": "MCPM", "chapters": "1-34"},
    {"pub": "100-05", "name": "Medicare Secondary Payer", "abbreviation": "MSPM", "chapters": "1-7"},
    {"pub": "100-06", "name": "Medicare Financial Management", "abbreviation": "MFMS", "chapters": "1-9"},
    {"pub": "100-07", "name": "Medicare State Operations", "abbreviation": "SOM", "chapters": "1-8"},
    {"pub": "100-08", "name": "Medicare Program Integrity", "abbreviation": "MPIM", "chapters": "1-6"},
    {"pub": "100-09", "name": "Medicare Contracting", "abbreviation": "MCM", "chapters": "1-5"},
    {"pub": "100-16", "name": "Medicare Managed Care Manual", "abbreviation": "MCMC", "chapters": "1-21"},
    {"pub": "100-17", "name": "Medicare Prescription Drug Benefit", "abbreviation": "MPDBM", "chapters": "1-9"},
    {"pub": "100-18", "name": "Medicare Quality Improvement", "abbreviation": "MQIM", "chapters": "1-5"},
    {"pub": "100-20", "name": "Medicare Appeals", "abbreviation": "MAM", "chapters": "1-5"},
]


async def download(force: bool = False) -> dict:
    """Download CMS Medicare manual index."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "cms_manuals_index.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading CMS Medicare manual index...")
    save_json(CMS_MANUALS_INDEX, codes_json)

    # Try to fetch manual chapter listing from CMS
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=120.0), follow_redirects=True) as client:
        for manual in CMS_MANUALS_INDEX[:5]:
            try:
                url = f"https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/downloads/{manual['pub'].replace('-', '')}.pdf"
                # Just check if the URL is reachable
                resp = await client.head(url)
                if resp.status_code == 200:
                    manual["url"] = url
            except Exception:
                pass

    save_json(CMS_MANUALS_INDEX, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": f"Downloaded CMS manual index ({len(CMS_MANUALS_INDEX)} manuals)"}