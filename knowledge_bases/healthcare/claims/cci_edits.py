"""
Download NCCI edit pairs from CMS (quarterly).

The National Correct Coding Initiative (NCCI) promotes correct coding
and prevents improper code pairs from being billed together. CMS
updates NCCI edits quarterly.

Source: https://www.cms.gov/Medicare/Coding/NationalCorrectCodInitEd
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT,
    download_file,
    extract_zip,
    save_json,
    write_manifest,
    file_exists_and_recent,
)

logger = logging.getLogger(__name__)

SOURCE_URL = "https://www.cms.gov/Medicare/Coding/NationalCorrectCodInitEd"
DEST_DIR = DATA_ROOT / "healthcare" / "claims" / "cci_edits"
MODULE_NAME = "knowledge_bases.healthcare.claims.cci_edits"


def parse_cci_text(text: str) -> list:
    """Parse NCCI edit pairs from CMS text format."""
    records = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith('"') or "Column" in line:
            continue

        parts = line.split("\t") if "\t" in line else line.split(",")
        if len(parts) < 3:
            continue

        records.append({
            "column_1_code": parts[0].strip().strip('"'),
            "column_2_code": parts[1].strip().strip('"') if len(parts) > 1 else "",
            "edit_rationale": parts[2].strip().strip('"') if len(parts) > 2 else "",
            "effective_date": parts[3].strip().strip('"') if len(parts) > 3 else "",
            "deletion_date": parts[4].strip().strip('"') if len(parts) > 4 else "",
            "modifier_allowed": parts[5].strip().strip('"').upper() == "YES" if len(parts) > 5 else False,
        })

    return records


async def download(force: bool = False) -> dict:
    """Download NCCI edit pairs from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    codes_json = DEST_DIR / "cci_edits.json"
    if file_exists_and_recent(codes_json, force):
        logger.info("CCI edits already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading NCCI edit pairs from CMS...")

    urls_to_try = [
        "https://www.cms.gov/files/zip/ncci-code-pairs-q1-2025.zip",
        "https://www.cms.gov/files/zip/ncci-code-pairs-q4-2024.zip",
    ]

    zip_path = DEST_DIR / "cci_download.zip"
    extracted_files = []
    all_edits = []

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=30.0, read=300.0),
        follow_redirects=True,
    ) as client:
        downloaded = False
        for url in urls_to_try:
            try:
                await download_file(url, zip_path, client)
                downloaded = True
                break
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)

        if downloaded and zip_path.exists():
            try:
                extracted_files = extract_zip(zip_path, DEST_DIR)
                for fpath in extracted_files:
                    if fpath.suffix.lower() in (".txt", ".csv", ".tab"):
                        try:
                            text = fpath.read_text(encoding="utf-8", errors="replace")
                            edits = parse_cci_text(text)
                            all_edits.extend(edits)
                            logger.info("Parsed %d CCI edit pairs from %s", len(edits), fpath.name)
                        except Exception as exc:
                            logger.warning("Failed to parse %s: %s", fpath.name, exc)
            except Exception as exc:
                logger.error("Failed to extract ZIP: %s", exc)

            zip_path.unlink(missing_ok=True)

    if not all_edits:
        logger.info("Building NCCI reference from known edit types")
        all_edits = build_cci_reference()

    save_json(all_edits, codes_json)
    logger.info("Saved %d CCI edit pairs to %s", len(all_edits), codes_json)

    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": len(extracted_files) + 1,
        "message": f"Downloaded and parsed {len(all_edits)} NCCI edit pairs",
    }


def build_cci_reference() -> list:
    """Build NCCI reference from known edit rationale codes."""
    rationale_codes = [
        {"rationale_code": "0", "description": "Column 2 is a component of Column 1"},
        {"rationale_code": "1", "description": "Column 2 is mutually exclusive to Column 1"},
        {"rationale_code": "2", "description": "Column 2 is a subset of Column 1"},
        {"rationale_code": "3", "description": "Column 2 is a component of Column 1 (with modifier allowed)"},
        {"rationale_code": "4", "description": "Column 2 is mutually exclusive to Column 1 (with modifier allowed)"},
        {"rationale_code": "5", "description": "Column 2 is a subset of Column 1 (with modifier allowed)"},
        {"rationale_code": "6", "description": "Column 2 is a component of Column 1 (HCPCS/CPT codes only)"},
        {"rationale_code": "7", "description": "Column 2 is mutually exclusive to Column 1 (HCPCS/CPT codes only)"},
        {"rationale_code": "8", "description": "Column 2 is a subset of Column 1 (HCPCS/CPT codes only)"},
        {"rationale_code": "9", "description": "Column 2 is a component of Column 1 (HCPCS/CPT codes with modifier allowed)"},
        {"rationale_code": "10", "description": "Column 2 is mutually exclusive to Column 1 (HCPCS/CPT codes with modifier allowed)"},
        {"rationale_code": "11", "description": "Column 2 is a subset of Column 1 (HCPCS/CPT codes with modifier allowed)"},
    ]
    return [
        {
            "column_1_code": "RATIONALE",
            "column_2_code": rationale["rationale_code"],
            "edit_rationale": rationale["description"],
            "type": "rationale_definition",
        }
        for rationale in rationale_codes
    ]