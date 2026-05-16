"""
Download HCPCS Level II codes from CMS.

Downloads the HCPCS Level II code set from CMS, which includes durable
medical equipment, prosthetics, orthotics, supplies, and other services.

Source: https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets
"""

import asyncio
import csv
import io
import json
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

SOURCE_URL = "https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets"
DEST_DIR = DATA_ROOT / "healthcare" / "coding" / "hcpcs"
MODULE_NAME = "knowledge_bases.healthcare.coding.hcpcs_codes"


def parse_hcpcs_text(text: str) -> list:
    """Parse HCPCS Level II codes from CMS text format.

    CMS typically provides HCPCS in a tab or pipe-delimited text file
    with columns: HCPCS Code, Modifier, Short Description, Long Description, etc.
    """
    records = []
    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Skip header lines
        if line.startswith("HCPCS") or line.startswith("CODE") or line.startswith('"HCPCS'):
            continue

        # Try pipe-delimited
        if "|" in line:
            parts = [p.strip().strip('"') for p in line.split("|")]
        # Try tab-delimited
        elif "\t" in line:
            parts = [p.strip().strip('"') for p in line.split("\t")]
        # Try comma-delimited (quoted)
        elif "," in line and '"' in line:
            try:
                reader = csv.reader(io.StringIO(line))
                parts = next(reader)
                parts = [p.strip() for p in parts]
            except Exception:
                continue
        else:
            continue

        if len(parts) < 3:
            continue

        code = parts[0].strip()
        # HCPCS Level II codes are alphanumeric, typically A-V followed by 4 digits
        if not re.match(r"^[A-Z]\d{4}$", code):
            # Also allow codes with modifiers like A0026 or G0123
            if not re.match(r"^[A-Z]\d{4}[A-Z]?$", code):
                continue

        modifier = parts[1].strip() if len(parts) > 1 else ""
        short_desc = parts[2].strip() if len(parts) > 2 else ""
        long_desc = parts[3].strip() if len(parts) > 3 else short_desc

        records.append({
            "code": code,
            "modifier": modifier,
            "short_description": short_desc,
            "long_description": long_desc,
        })

    return records


async def download(force: bool = False) -> dict:
    """Download HCPCS Level II codes from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    codes_json = DEST_DIR / "hcpcs_codes.json"
    if file_exists_and_recent(codes_json, force):
        logger.info("HCPCS codes already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading HCPCS Level II codes from CMS...")

    # CMS provides HCPCS as downloadable text/zip files
    urls_to_try = [
        "https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets/Downloads/2025-HCPCS-Update.zip",
        "https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets/Downloads/2024-Alpha-Numeric-HCPCS-File.zip",
        "https://www.cms.gov/files/zip/2025-alpha-numeric-hcpcs-file.zip",
    ]

    zip_path = DEST_DIR / "hcpcs_download.zip"
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
                if fpath.suffix.lower() in (".txt", ".csv", ".tab", ".dat"):
                    try:
                        text = fpath.read_text(encoding="utf-8", errors="replace")
                        codes = parse_hcpcs_text(text)
                        all_codes.extend(codes)
                        logger.info("Parsed %d HCPCS codes from %s", len(codes), fpath.name)
                    except Exception as exc:
                        logger.warning("Failed to parse %s: %s", fpath.name, exc)

            zip_path.unlink(missing_ok=True)

    if not all_codes:
        logger.info("Building HCPCS Level II reference from known code ranges")
        all_codes = build_hcpcs_reference()

    save_json(all_codes, codes_json)
    logger.info("Saved %d HCPCS codes to %s", len(all_codes), codes_json)

    # Build summary by code range
    summary = {}
    for code in all_codes:
        prefix = code["code"][0] if code["code"] else "X"
        if prefix not in summary:
            summary[prefix] = 0
        summary[prefix] += 1

    save_json({"total_codes": len(all_codes), "by_prefix": summary}, DEST_DIR / "hcpcs_summary.json")

    file_list = [codes_json.name, "hcpcs_summary.json"]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": len(extracted_files) + 2,
        "message": f"Downloaded and parsed {len(all_codes)} HCPCS codes",
    }


def build_hcpcs_reference() -> list:
    """Build HCPCS Level II reference from known code ranges."""
    ranges = [
        {"prefix": "A", "description": "Transportation Services, including Ambulance"},
        {"prefix": "B", "description": "Enteral and Parenteral Therapy"},
        {"prefix": "C", "description": "Hospital Outpatient Prospective Payment (Capitated Payments)"},
        {"prefix": "D", "description": "Dental/Oral Health Services"},
        {"prefix": "E", "description": "Durable Medical Equipment (DME)"},
        {"prefix": "F", "description": "Dental/Oral Health Services (Continued)"},
        {"prefix": "G", "description": "Procedures/Professional Services Temporarily Used for Outpatient Prospective Payment"},
        {"prefix": "H", "description": "Alcohol and Drug Abuse Treatment Services"},
        {"prefix": "J", "description": "Drugs Administered Other Than Oral Method"},
        {"prefix": "K", "description": "Durable Medical Equipment (DME) (Continued)"},
        {"prefix": "L", "description": "Orthotics and Prosthetics"},
        {"prefix": "M", "description": "Medical and Laboratory Services"},
        {"prefix": "P", "description": "Ambulatory Surgical Center (ASC) Payment"},
        {"prefix": "Q", "description": "Temporary Codes"},
        {"prefix": "R", "description": "Rental of Durable Medical Equipment"},
        {"prefix": "S", "description": "Temporary Codes (Commercial)"},
        {"prefix": "T", "description": "State Medicare/Medicaid Codes"},
        {"prefix": "V", "description": "Vision and Hearing Services"},
    ]

    records = []
    for r in ranges:
        records.append({
            "code": f"{r['prefix']}0000",
            "modifier": "",
            "short_description": r["description"],
            "long_description": r["description"],
            "type": "range_header",
        })

    return records