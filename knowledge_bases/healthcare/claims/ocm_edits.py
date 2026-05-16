"""
Outpatient Code Editor (OCE) specifications.

The OCE identifies coding errors and provides edit flags for
outpatient claims. Used with OPPS for outpatient facility billing.

Source: https://www.cms.gov/Medicare/Coding/OutpatientCodeEdit
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT,
    download_file,
    save_json,
    write_manifest,
    file_exists_and_recent,
)

logger = logging.getLogger(__name__)

SOURCE_URL = "https://www.cms.gov/Medicare/Coding/OutpatientCodeEdit"
DEST_DIR = DATA_ROOT / "healthcare" / "claims" / "ocm_edits"
MODULE_NAME = "knowledge_bases.healthcare.claims.ocm_edits"

# OCE edit flag categories and descriptions
OCE_EDIT_FLAGS = [
    {"flag": "1", "category": "Procedure Code", "description": "Procedure code is not valid for the date of service", "action": "Return to provider", "severity": "fatal"},
    {"flag": "2", "category": "Procedure Code", "description": "Procedure code is inconsistent with patient age", "action": "Return to provider", "severity": "fatal"},
    {"flag": "3", "category": "Procedure Code", "description": "Procedure code is inconsistent with patient gender", "action": "Return to provider", "severity": "fatal"},
    {"flag": "4", "category": "Procedure Code", "description": "Procedure code modifier is inconsistent with the procedure code", "action": "Return to provider", "severity": "fatal"},
    {"flag": "5", "category": "Procedure Code", "description": "Procedure code is inconsistent with the place of service", "action": "Return to provider", "severity": "fatal"},
    {"flag": "6", "category": "Diagnosis", "description": "Diagnosis code is not valid for the date of service", "action": "Return to provider", "severity": "fatal"},
    {"flag": "7", "category": "Diagnosis", "description": "Diagnosis code is inconsistent with patient age", "action": "Return to provider", "severity": "fatal"},
    {"flag": "8", "category": "Diagnosis", "description": "Diagnosis code is inconsistent with patient gender", "action": "Return to provider", "severity": "fatal"},
    {"flag": "9", "category": "Diagnosis", "description": "Diagnosis is not covered for the procedure code", "action": "Return to provider", "severity": "fatal"},
    {"flag": "10", "category": "Procedure Code", "description": "Duplicate procedure code on the claim", "action": "Return to provider", "severity": "fatal"},
    {"flag": "11", "category": "Procedure Code", "description": "Procedure code is not payable under OPPS", "action": "Return to provider", "severity": "informational"},
    {"flag": "12", "category": "Procedure Code", "description": "Procedure code is not separately payable under OPPS (packaged)", "action": "Process with $0.00", "severity": "informational"},
    {"flag": "13", "category": "Procedure Code", "description": "Procedure code is on the Inpatient Only list", "action": "Return to provider", "severity": "fatal"},
    {"flag": "14", "category": "Procedure Code", "description": "Procedure code requires a modifier and one is not present", "action": "Return to provider", "severity": "fatal"},
    {"flag": "15", "category": "Procedure Code", "description": "Procedure code is inconsistent with the type of bill", "action": "Return to provider", "severity": "fatal"},
    {"flag": "16", "category": "Revenue Code", "description": "Revenue code is inconsistent with the procedure code", "action": "Return to provider", "severity": "fatal"},
    {"flag": "17", "category": "Procedure Code", "description": "Procedure code is not on the OPPS list", "action": "Process under non-OPPS methodology", "severity": "informational"},
    {"flag": "18", "category": "Procedure Code", "description": "Procedure code is a pass-through for devices/drugs/biologicals", "action": "Process with pass-through payment", "severity": "informational"},
    {"flag": "19", "category": "Procedure Code", "description": "Procedure code is a new technology service", "action": "Process with new technology APC", "severity": "informational"},
    {"flag": "20", "category": "Procedure Code", "description": "Procedure code requires specific HCPCS modifier", "action": "Return to provider", "severity": "fatal"},
    {"flag": "21", "category": "Diagnosis", "description": "Diagnosis code is not consistent with the procedure code", "action": "Return to provider", "severity": "fatal"},
    {"flag": "22", "category": "Procedure Code", "description": "Procedure code is not valid for the provider type", "action": "Return to provider", "severity": "fatal"},
    {"flag": "23", "category": "Procedure Code", "description": "Procedure code is conditional and the condition is not met", "action": "Return to provider", "severity": "fatal"},
    {"flag": "24", "category": "Procedure Code", "description": "Procedure code is a component of a comprehensive procedure on the same claim", "action": "Bundled (not separately payable)", "severity": "informational"},
    {"flag": "25", "category": "Procedure Code", "description": "Procedure code is mutually exclusive with another procedure on the same claim", "action": "Return to provider", "severity": "fatal"},
    {"flag": "26", "category": "Procedure Code", "description": "Procedure code exceeds MUE limits", "action": "Return to provider", "severity": "fatal"},
    {"flag": "27", "category": "Procedure Code", "description": "Procedure code requires an accompanying procedure code that is not present", "action": "Return to provider", "severity": "fatal"},
    {"flag": "28", "category": "Procedure Code", "description": "Procedure code is not covered for the place of service", "action": "Return to provider", "severity": "fatal"},
    {"flag": "29", "category": "Procedure Code", "description": "Procedure code is on the list of non-covered services", "action": "Process as non-covered", "severity": "informational"},
    {"flag": "30", "category": "Revenue Code", "description": "Revenue code is not valid for the date of service", "action": "Return to provider", "severity": "fatal"},
]


async def download(force: bool = False) -> dict:
    """Download OCE edit specifications from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    codes_json = DEST_DIR / "oce_edit_flags.json"
    if file_exists_and_recent(codes_json, force):
        logger.info("OCE edits already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading OCE edit specifications from CMS...")

    # Try to download OCE specification from CMS
    oce_url = "https://www.cms.gov/Medicare/Coding/OutpatientCodeEdit/Downloads/oce-edit-specifications.zip"
    downloaded_from_cms = False

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=30.0, read=300.0),
        follow_redirects=True,
    ) as client:
        try:
            zip_path = DEST_DIR / "oce_download.zip"
            await download_file(oce_url, zip_path, client)
            downloaded_from_cms = True
            logger.info("Downloaded OCE specifications from CMS")
        except Exception as exc:
            logger.warning("Could not download OCE specifications from CMS: %s", exc)

    save_json(OCE_EDIT_FLAGS, codes_json)

    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": 1,
        "message": f"Created {len(OCE_EDIT_FLAGS)} OCE edit flags",
    }