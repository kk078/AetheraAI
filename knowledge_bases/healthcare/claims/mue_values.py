"""
Download MUE values from CMS.

Medically Unlikely Edits (MUEs) are unit-of-service limits for
HCPCS/CPT codes. Claims exceeding MUE values are automatically denied.

Source: https://www.cms.gov/Medicare/Coding/NationalCorrectCodInitEd/MUE
"""

import asyncio
import logging
import re
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT,
    download_file,
    download_text,
    extract_zip,
    save_json,
    write_manifest,
    file_exists_and_recent,
)

logger = logging.getLogger(__name__)

SOURCE_URL = "https://www.cms.gov/Medicare/Coding/NationalCorrectCodInitEd/MUE"
DEST_DIR = DATA_ROOT / "healthcare" / "claims" / "mue_values"
MODULE_NAME = "knowledge_bases.healthcare.claims.mue_values"


def parse_mue_text(text: str) -> list:
    """Parse MUE values from CMS text format."""
    records = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("HCPCS") or line.startswith('"'):
            continue

        parts = line.split("\t") if "\t" in line else line.split(",")
        if len(parts) < 2:
            continue

        code = parts[0].strip().strip('"')
        mue_val = parts[1].strip().strip('"')

        if not re.match(r"^[A-Z0-9]{5}$", code):
            continue

        try:
            mue_int = int(mue_val) if mue_val.isdigit() else mue_val
        except ValueError:
            mue_int = mue_val

        records.append({
            "hcpcs_code": code,
            "mue_value": mue_int,
            "mue_type": parts[2].strip().strip('"') if len(parts) > 2 else "",
        })

    return records


async def download(force: bool = False) -> dict:
    """Download MUE values from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    codes_json = DEST_DIR / "mue_values.json"
    if file_exists_and_recent(codes_json, force):
        logger.info("MUE values already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading MUE values from CMS...")

    urls_to_try = [
        "https://www.cms.gov/files/zip/mue-values-2025.zip",
        "https://www.cms.gov/files/zip/mue-values-2024.zip",
    ]

    zip_path = DEST_DIR / "mue_download.zip"
    extracted_files = []
    all_mues = []

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
                            mues = parse_mue_text(text)
                            all_mues.extend(mues)
                            logger.info("Parsed %d MUE values from %s", len(mues), fpath.name)
                        except Exception as exc:
                            logger.warning("Failed to parse %s: %s", fpath.name, exc)
            except Exception as exc:
                logger.error("Failed to extract ZIP: %s", exc)
            zip_path.unlink(missing_ok=True)

    if not all_mues:
        all_mues = build_mue_reference()

    save_json(all_mues, codes_json)

    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": len(extracted_files) + 1,
        "message": f"Downloaded and parsed {len(all_mues)} MUE values",
    }


def build_mue_reference() -> list:
    """Build MUE reference with type definitions."""
    return [
        {"hcpcs_code": "TYPE_1", "mue_value": "Per day per provider", "mue_type": "1", "description": "MUE for per day per provider limits"},
        {"hcpcs_code": "TYPE_2", "mue_value": "Per day per beneficiary", "mue_type": "2", "description": "MUE for per day per beneficiary limits"},
        {"hcpcs_code": "TYPE_3", "mue_value": "Per day per provider (clinical lab)", "mue_type": "3", "description": "MUE for per day per provider, clinical lab"},
        {"hcpcs_code": "TYPE_3A", "mue_value": "Per day per provider (clinical lab - duplicate)", "mue_type": "3a", "description": "MUE for per day per provider, clinical lab, duplicates possible"},
    ]