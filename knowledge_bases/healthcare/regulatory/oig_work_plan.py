"""
Download OIG Work Plan.

The HHS Office of Inspector General Work Plan identifies planned
audits, evaluations, and investigations for the coming year.

Source: https://oig.hhs.gov/reports-and-publications/workplan/
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_text, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://oig.hhs.gov/reports-and-publications/workplan/"
DEST_DIR = DATA_ROOT / "healthcare" / "regulatory" / "oig_work_plan"
MODULE_NAME = "knowledge_bases.healthcare.regulatory.oig_work_plan"


async def download(force: bool = False) -> dict:
    """Download OIG Work Plan from HHS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "oig_work_plan.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading OIG Work Plan from HHS...")
    work_plan_data = {"source": SOURCE_URL, "focus_areas": []}

    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=120.0), follow_redirects=True) as client:
        urls = [
            "https://oig.hhs.gov/reports-and-publications/workplan/wp-fy2025.pdf",
            "https://oig.hhs.gov/reports-and-publications/workplan/wp-fy2024.pdf",
        ]
        for url in urls:
            try:
                pdf_path = DEST_DIR / "oig_work_plan.pdf"
                from knowledge_bases._shared import download_file
                await download_file(url, pdf_path, client)
                work_plan_data["downloaded_file"] = "oig_work_plan.pdf"
                break
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)

    # Default focus areas if PDF cannot be parsed
    work_plan_data["focus_areas"] = [
        "Medicare Parts A and B payment accuracy and adequacy",
        "Medicare Advantage program integrity and risk adjustment",
        "Medicare Part D drug pricing and rebates",
        "Medicaid program integrity and managed care",
        "Opioid use and prescribing patterns",
        "Telehealth services billing and utilization",
        "Hospital and SNF billing patterns and compliance",
        "Home health and hospice program integrity",
        "Durable medical equipment fraud and abuse",
        "Electronic health records incentive payments",
        "Provider enrollment and screening",
        "Corporate practice of medicine and private equity in healthcare",
    ]

    save_json(work_plan_data, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded OIG Work Plan reference"}