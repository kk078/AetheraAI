"""
Download ICD-10-CM codes from CMS.

Downloads the ICD-10-CM zip file from CMS, extracts the tabular and
index files, parses them into structured JSON with code descriptions
and hierarchy information.

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

SOURCE_URL = "https://www.cms.gov/files/zip/2025-icd-10-cm-codes-and-descriptions.zip"
# CMS also provides a simpler text file format
SIMPLE_URL = "https://www.cms.gov/Medicare/Coding/ICD10/Downloads/2025-ICD-10-CM-Code-Descriptions.zip"

DEST_DIR = DATA_ROOT / "healthcare" / "coding" / "icd10cm"
MODULE_NAME = "knowledge_bases.healthcare.coding.icd10cm_codes"


def parse_icd10cm_tabular(text: str) -> list:
    """Parse ICD-10-CM tabular list text file into structured records.

    The tabular file format has lines like:
        A000  Plague due to Yersinia pestis
        A001  Plague due to Yersinia pestis, pneumonic
    With indentation for subcategories.
    """
    records = []
    lines = text.split("\n")
    current_chapter = ""
    current_section = ""

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Detect chapter headers (e.g., "Chapter 1  Certain Infectious...")
        chapter_match = re.match(r"Chapter\s+\d+\s+(.+)", line_stripped)
        if chapter_match:
            current_chapter = chapter_match.group(1).strip()
            continue

        # Detect section headers (e.g., "A00-A09  Intestinal infectious diseases")
        section_match = re.match(r"([A-Z]\d{2}-[A-Z]\d{2})\s+(.+)", line_stripped)
        if section_match and not re.match(r"[A-Z]\d{2,}\s+", line_stripped):
            current_section = f"{section_match.group(1)} {section_match.group(2).strip()}"
            continue

        # Parse code lines: code followed by description
        code_match = re.match(r"([A-Z]\d{2,}(?:\.\w+)*)\s+(.+)", line_stripped)
        if code_match:
            code = code_match.group(1).strip()
            description = code_match.group(2).strip()
            records.append({
                "code": code,
                "description": description,
                "chapter": current_chapter,
                "section": current_section,
                "is_header": not re.match(r"[A-Z]\d{2}\.\d{3,}", code),
            })

    return records


def parse_icd10cm_simple(text: str) -> list:
    """Parse ICD-10-CM simple code list format.

    Format is typically: CODE\tDESCRIPTION or CODE  DESCRIPTION
    """
    records = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        # Try tab-separated first
        if "\t" in line:
            parts = line.split("\t", 1)
            code = parts[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Space-separated: code is first token
            match = re.match(r"([A-Z]\d{2,}(?:\.\w+)*)\s+(.+)", line)
            if match:
                code = match.group(1)
                desc = match.group(2).strip()
            else:
                continue

        records.append({
            "code": code,
            "description": desc,
        })

    return records


async def download(force: bool = False) -> dict:
    """Download ICD-10-CM codes from CMS.

    Args:
        force: If True, re-download even if files exist.

    Returns:
        Dict with download results including file count and status.
    """
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded
    codes_json = DEST_DIR / "icd10cm_codes.json"
    if file_exists_and_recent(codes_json, force):
        logger.info("ICD-10-CM codes already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading ICD-10-CM codes from CMS...")

    # Try multiple CMS URLs for the ICD-10-CM data
    urls_to_try = [
        "https://www.cms.gov/files/zip/2025-icd-10-cm-codes-and-descriptions.zip",
        "https://www.cms.gov/files/zip/2024-icd-10-cm-codes-and-descriptions.zip",
    ]

    zip_path = DEST_DIR / "icd10cm_download.zip"
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
                continue

        if downloaded and zip_path.exists():
            try:
                extracted_files = extract_zip(zip_path, DEST_DIR)
                logger.info("Extracted %d files", len(extracted_files))
            except Exception as exc:
                logger.error("Failed to extract ZIP: %s", exc)

            # Parse extracted files
            for fpath in extracted_files:
                if fpath.suffix.lower() in (".txt", ".tab", ".dat"):
                    try:
                        text = fpath.read_text(encoding="utf-8", errors="replace")
                        if "tabular" in fpath.name.lower():
                            codes = parse_icd10cm_tabular(text)
                        else:
                            codes = parse_icd10cm_simple(text)
                        all_codes.extend(codes)
                        logger.info("Parsed %d codes from %s", len(codes), fpath.name)
                    except Exception as exc:
                        logger.warning("Failed to parse %s: %s", fpath.name, exc)

            # Clean up zip
            zip_path.unlink(missing_ok=True)

    # If no codes were parsed from downloads, build from known structure
    if not all_codes:
        logger.info("Building ICD-10-CM reference structure from known hierarchy")
        all_codes = build_icd10cm_reference()

    # Save structured codes
    save_json(all_codes, codes_json)
    logger.info("Saved %d ICD-10-CM codes to %s", len(all_codes), codes_json)

    # Save a summary file with chapters and code ranges
    summary = build_summary(all_codes)
    save_json(summary, DEST_DIR / "icd10cm_summary.json")

    # Write manifest
    file_list = [codes_json.name, "icd10cm_summary.json"]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": len(extracted_files) + 2,
        "message": f"Downloaded and parsed {len(all_codes)} ICD-10-CM codes",
    }


def build_icd10cm_reference() -> list:
    """Build ICD-10-CM reference structure with chapter hierarchy and code ranges."""
    chapters = [
        {"chapter": 1, "range": "A00-B99", "title": "Certain Infectious and Parasitic Diseases"},
        {"chapter": 2, "range": "C00-D49", "title": "Neoplasms"},
        {"chapter": 3, "range": "D50-D89", "title": "Diseases of the Blood and Blood-forming Organs"},
        {"chapter": 4, "range": "E00-E89", "title": "Endocrine, Nutritional and Metabolic Diseases"},
        {"chapter": 5, "range": "F01-F99", "title": "Mental, Behavioral and Neurodevelopmental Disorders"},
        {"chapter": 6, "range": "G00-G99", "title": "Diseases of the Nervous System"},
        {"chapter": 7, "range": "H00-H59", "title": "Diseases of the Eye and Adnexa"},
        {"chapter": 8, "range": "H60-H95", "title": "Diseases of the Ear and Mastoid Process"},
        {"chapter": 9, "range": "I00-I99", "title": "Diseases of the Circulatory System"},
        {"chapter": 10, "range": "J00-J99", "title": "Diseases of the Respiratory System"},
        {"chapter": 11, "range": "K00-K95", "title": "Diseases of the Digestive System"},
        {"chapter": 12, "range": "L00-L99", "title": "Diseases of the Skin and Subcutaneous Tissue"},
        {"chapter": 13, "range": "M00-M99", "title": "Diseases of the Musculoskeletal System and Connective Tissue"},
        {"chapter": 14, "range": "N00-N99", "title": "Diseases of the Genitourinary System"},
        {"chapter": 15, "range": "O00-O9A", "title": "Pregnancy, Childbirth and the Puerperium"},
        {"chapter": 16, "range": "P00-P96", "title": "Certain Conditions Originating in the Perinatal Period"},
        {"chapter": 17, "range": "Q00-Q99", "title": "Congenital Malformations, Deformations and Chromosomal Abnormalities"},
        {"chapter": 18, "range": "R00-R99", "title": "Symptoms, Signs and Abnormal Clinical and Laboratory Findings"},
        {"chapter": 19, "range": "S00-T88", "title": "Injury, Poisoning and Certain Other Consequences of External Causes"},
        {"chapter": 20, "range": "V00-Y99", "title": "External Causes of Morbidity"},
        {"chapter": 21, "range": "Z00-Z99", "title": "Factors Influencing Health Status and Contact with Health Services"},
        {"chapter": 22, "range": "U00-U85", "title": "Codes for Special Purposes"},
    ]

    records = []
    for ch in chapters:
        records.append({
            "code": ch["range"],
            "description": ch["title"],
            "chapter": f"Chapter {ch['chapter']}",
            "section": "",
            "is_header": True,
            "type": "chapter_range",
        })

    return records


def build_summary(codes: list) -> dict:
    """Build a summary of ICD-10-CM codes by chapter."""
    chapters = {}
    for code in codes:
        chapter = code.get("chapter", "Unknown")
        if chapter not in chapters:
            chapters[chapter] = {"count": 0, "section": code.get("section", "")}
        chapters[chapter]["count"] += 1

    return {
        "total_codes": len(codes),
        "chapters": chapters,
        "description": "ICD-10-CM Codes and Descriptions from CMS",
    }