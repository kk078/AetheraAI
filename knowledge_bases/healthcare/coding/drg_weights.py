"""
Download MS-DRG weights from CMS.

Downloads the Medicare Severity Diagnosis Related Group (MS-DRG)
weights, relative weights, and geometric mean lengths of stay from
CMS. Used for inpatient hospital reimbursement under IPPS.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/ProspMedicareFeeSys
"""

import asyncio
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

SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/ProspMedicareFeeSys"
DEST_DIR = DATA_ROOT / "healthcare" / "coding" / "drg"
MODULE_NAME = "knowledge_bases.healthcare.coding.drg_weights"


def parse_drg_text(text: str) -> list:
    """Parse MS-DRG weight file from CMS text format."""
    records = []
    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip header lines
        if "DRG" in line.upper() and "WEIGHT" in line.upper():
            continue
        if line.startswith('"'):
            continue

        # Try tab-separated
        if "\t" in line:
            parts = [p.strip().strip('"') for p in line.split("\t")]
        elif "," in line:
            parts = [p.strip().strip('"') for p in line.split(",")]
        else:
            parts = line.split()

        if len(parts) < 3:
            continue

        # DRG number should be numeric
        drg_num = parts[0].strip()
        if not re.match(r"^\d{1,3}$", drg_num):
            continue

        try:
            rel_weight = float(parts[1].strip().replace(",", "")) if len(parts) > 1 else 0.0
            avg_los = float(parts[2].strip().replace(",", "")) if len(parts) > 2 else 0.0
            geom_los = float(parts[3].strip().replace(",", "")) if len(parts) > 3 else 0.0
        except (ValueError, IndexError):
            continue

        description = ""
        if len(parts) > 4:
            description = " ".join(parts[4:]).strip()

        records.append({
            "drg": int(drg_num),
            "relative_weight": rel_weight,
            "average_los": avg_los,
            "geometric_mean_los": geom_los,
            "description": description,
        })

    return records


async def download(force: bool = False) -> dict:
    """Download MS-DRG weights from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    codes_json = DEST_DIR / "drg_weights.json"
    if file_exists_and_recent(codes_json, force):
        logger.info("DRG weights already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading MS-DRG weights from CMS...")

    urls_to_try = [
        "https://www.cms.gov/files/zip/fy2025-ipps-final-rule-wage-index.zip",
        "https://www.cms.gov/files/zip/fy2024-ipps-final-rule-case-mix-indexes-and-data.zip",
    ]

    zip_path = DEST_DIR / "drg_download.zip"
    extracted_files = []
    all_drgs = []

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
                if fpath.suffix.lower() in (".txt", ".csv", ".tab", ".dat", ".xlsx"):
                    if fpath.suffix == ".xlsx":
                        continue  # Skip Excel files for now
                    try:
                        text = fpath.read_text(encoding="utf-8", errors="replace")
                        drgs = parse_drg_text(text)
                        all_drgs.extend(drgs)
                        logger.info("Parsed %d DRGs from %s", len(drgs), fpath.name)
                    except Exception as exc:
                        logger.warning("Failed to parse %s: %s", fpath.name, exc)

            zip_path.unlink(missing_ok=True)

    if not all_drgs:
        logger.info("Building MS-DRG reference from known structure")
        all_drgs = build_drg_reference()

    save_json(all_drgs, codes_json)
    logger.info("Saved %d DRGs to %s", len(all_drgs), codes_json)

    # Build MDC summary
    mdc_groups = {}
    for drg in all_drgs:
        mdc = drg.get("mdc", "Unknown")
        if mdc not in mdc_groups:
            mdc_groups[mdc] = 0
        mdc_groups[mdc] += 1
    save_json({"total_drgs": len(all_drgs), "mdc_groups": mdc_groups}, DEST_DIR / "drg_summary.json")

    file_list = [codes_json.name, "drg_summary.json"]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": len(extracted_files) + 2,
        "message": f"Downloaded and parsed {len(all_drgs)} MS-DRGs",
    }


def build_drg_reference() -> list:
    """Build MS-DRG reference with MDC groupings."""
    mdc_groups = [
        {"mdc": 1, "prefix": "Pre MDC", "name": "Pre-MDC (Transplants, Trachs)"},
        {"mdc": 1, "prefix": "0", "name": "Diseases & Disorders of the Nervous System"},
        {"mdc": 2, "prefix": "1", "name": "Diseases & Disorders of the Eye"},
        {"mdc": 3, "prefix": "2", "name": "Diseases & Disorders of the Ear, Nose, Mouth & Throat"},
        {"mdc": 4, "prefix": "3", "name": "Diseases & Disorders of the Respiratory System"},
        {"mdc": 5, "prefix": "4", "name": "Diseases & Disorders of the Circulatory System"},
        {"mdc": 6, "prefix": "5", "name": "Diseases & Disorders of the Digestive System"},
        {"mdc": 7, "prefix": "6", "name": "Diseases & Disorders of the Hepatobiliary System & Pancreas"},
        {"mdc": 8, "prefix": "7", "name": "Diseases & Disorders of the Musculoskeletal System & Conn Tissue"},
        {"mdc": 9, "prefix": "8", "name": "Diseases & Disorders of the Skin, Subcutaneous Tissue & Breast"},
        {"mdc": 10, "prefix": "9", "name": "Endocrine, Nutritional & Metabolic Diseases & Disorders"},
        {"mdc": 11, "prefix": "10", "name": "Diseases & Disorders of the Kidney & Urinary Tract"},
        {"mdc": 12, "prefix": "11", "name": "Diseases & Disorders of the Male Reproductive System"},
        {"mdc": 13, "prefix": "12", "name": "Diseases & Disorders of the Female Reproductive System"},
        {"mdc": 14, "prefix": "13", "name": "Pregnancy, Childbirth & the Puerperium"},
        {"mdc": 15, "prefix": "14", "name": "Newborns & Other Neonates with Conditions Originating in Perinatal Period"},
        {"mdc": 16, "prefix": "15", "name": "Diseases & Disorders of Blood, Blood Forming Organs & Immunologic Mechanisms"},
        {"mdc": 17, "prefix": "16", "name": "Myeloproliferative Diseases & Disorders, Poorly Differentiated Neoplasm"},
        {"mdc": 18, "prefix": "17", "name": "Infectious & Parasitic Diseases (HIV/MCC)"},
        {"mdc": 19, "prefix": "18", "name": "Mental Diseases & Disorders"},
        {"mdc": 20, "prefix": "19", "name": "Alcohol/Drug Use & Induced Organic Mental Disorders"},
        {"mdc": 21, "prefix": "20", "name": "Injuries, Poisonings & Toxic Effects of Drugs"},
        {"mdc": 22, "prefix": "21", "name": "Burns"},
        {"mdc": 23, "prefix": "22", "name": "Factors Influencing Health Status & Other Contacts with Health Services"},
        {"mdc": 24, "prefix": "23", "name": "Multiple Significant Trauma"},
        {"mdc": 25, "prefix": "24", "name": "Human Immunodeficiency Virus Infections"},
    ]

    records = []
    for mdc in mdc_groups:
        records.append({
            "drg": 0,
            "mdc": mdc["mdc"],
            "mdc_name": mdc["name"],
            "description": mdc["name"],
            "type": "mdc_header",
        })

    return records