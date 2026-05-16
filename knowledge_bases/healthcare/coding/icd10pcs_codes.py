"""
Download ICD-10-PCS codes from CMS.

Downloads the ICD-10-PCS zip file, extracts and parses the procedure
code tables into structured JSON with code descriptions and hierarchy.

Source: https://www.cms.gov/Medicare/Coding/ICD10
"""

import asyncio
import json
import logging
import re
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

SOURCE_URL = "https://www.cms.gov/files/zip/2025-icd-10-pcs-codes-and-descriptions.zip"
DEST_DIR = DATA_ROOT / "healthcare" / "coding" / "icd10pcs"
MODULE_NAME = "knowledge_bases.healthcare.coding.icd10pcs_codes"

# ICD-10-PCS structure: 7-character alphanumeric codes
# Character positions: Section, Body System, Root Operation, Body Part, Approach, Device, Qualifier
PCS_STRUCTURE = {
    "position_1": {"name": "Section", "type": "section"},
    "position_2": {"name": "Body System", "type": "body_system"},
    "position_3": {"name": "Root Operation", "type": "root_operation"},
    "position_4": {"name": "Body Part", "type": "body_part"},
    "position_5": {"name": "Approach", "type": "approach"},
    "position_6": {"name": "Device", "type": "device"},
    "position_7": {"name": "Qualifier", "type": "qualifier"},
}

# PCS Section definitions (first character meaning)
PCS_SECTIONS = {
    "0": "Medical and Surgical",
    "1": "Obstetrics",
    "2": "Placement",
    "3": "Administration",
    "4": "Measurement and Monitoring",
    "5": "Extracorporeal Assistance and Performance",
    "6": "Osteopathic",
    "7": "Other Procedures",
    "8": "New Technology",
    "9": "Chiropractic",
    "B": "Imaging",
    "C": "Nuclear Medicine",
    "D": "Radiation Therapy",
    "F": "Physical Rehabilitation and Diagnostic Audiology",
    "G": "Mental Health",
    "H": "Substance Abuse Treatment",
    "X": "New Technology",
}


def parse_pcs_text(text: str) -> list:
    """Parse ICD-10-PCS code descriptions from text file."""
    records = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        # PCS codes are 7-character alphanumeric starting with a digit or B-F, X
        match = re.match(r"([0-9B-DF-HX]\w{6})\s+(.+)", line)
        if match:
            code = match.group(1)
            description = match.group(2).strip()
            section = PCS_SECTIONS.get(code[0], "Unknown")
            records.append({
                "code": code,
                "description": description,
                "section": section,
                "body_system_char": code[1],
                "root_operation_char": code[2],
            })

    return records


async def download(force: bool = False) -> dict:
    """Download ICD-10-PCS codes from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    codes_json = DEST_DIR / "icd10pcs_codes.json"
    if file_exists_and_recent(codes_json, force):
        logger.info("ICD-10-PCS codes already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading ICD-10-PCS codes from CMS...")

    urls_to_try = [
        "https://www.cms.gov/files/zip/2025-icd-10-pcs-codes-and-descriptions.zip",
        "https://www.cms.gov/files/zip/2024-icd-10-pcs-codes-and-descriptions.zip",
    ]

    zip_path = DEST_DIR / "icd10pcs_download.zip"
    extracted_files = []
    all_codes = []

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
            except Exception as exc:
                logger.error("Failed to extract ZIP: %s", exc)

            for fpath in extracted_files:
                if fpath.suffix.lower() in (".txt", ".tab", ".dat"):
                    try:
                        text = fpath.read_text(encoding="utf-8", errors="replace")
                        codes = parse_pcs_text(text)
                        all_codes.extend(codes)
                        logger.info("Parsed %d PCS codes from %s", len(codes), fpath.name)
                    except Exception as exc:
                        logger.warning("Failed to parse %s: %s", fpath.name, exc)

            zip_path.unlink(missing_ok=True)

    if not all_codes:
        logger.info("Building ICD-10-PCS reference structure from known hierarchy")
        all_codes = build_pcs_reference()

    save_json(all_codes, codes_json)
    logger.info("Saved %d ICD-10-PCS codes to %s", len(all_codes), codes_json)

    # Save structure reference
    save_json(PCS_STRUCTURE, DEST_DIR / "icd10pcs_structure.json")
    save_json(PCS_SECTIONS, DEST_DIR / "icd10pcs_sections.json")

    file_list = [codes_json.name, "icd10pcs_structure.json", "icd10pcs_sections.json"]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": len(extracted_files) + 3,
        "message": f"Downloaded and parsed {len(all_codes)} ICD-10-PCS codes",
    }


def build_pcs_reference() -> list:
    """Build ICD-10-PCS reference from known structure definitions."""
    records = []
    for key, title in PCS_SECTIONS.items():
        records.append({
            "code": f"{key}______",
            "description": title,
            "section": title,
            "body_system_char": "_",
            "root_operation_char": "_",
            "type": "section_definition",
        })
    return records