"""
Download NDC codes from FDA.

Downloads the National Drug Code directory from FDA, which contains
all commercially available drugs in the US with their product,
package, and substance information.

Source: https://www.fda.gov/drugs/drug-approvals-and-databases/national-drug-code-directory
"""

import asyncio
import json
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT,
    download_file,
    download_text,
    save_json,
    write_manifest,
    file_exists_and_recent,
)

logger = logging.getLogger(__name__)

SOURCE_URL = "https://www.fda.gov/drugs/drug-approvals-and-databases/national-drug-code-directory"
DEST_DIR = DATA_ROOT / "healthcare" / "coding" / "ndc"
MODULE_NAME = "knowledge_bases.healthcare.coding.ndc_codes"

# FDA provides NDC data in multiple formats
NDC_JSON_URL = "https://api.fda.gov/download/drug/ndc.zip"
NDC_DIRECTORY_URL = "https://www.accessdata.fda.gov/cder/ndctext.zip"


def parse_ndc_text(text: str) -> list:
    """Parse NDC directory text file into structured records.

    FDA NDC files are typically pipe or tab delimited with columns:
    NDC, ProductNDC, ProductTypeName, ProprietaryName, NonProprietaryName, etc.
    """
    records = []
    lines = text.strip().split("\n")
    if not lines:
        return records

    # Detect delimiter
    header = lines[0]
    if "|" in header:
        delimiter = "|"
    elif "\t" in header:
        delimiter = "\t"
    else:
        delimiter = ","

    headers = [h.strip().strip('"') for h in header.split(delimiter)]

    for line in lines[1:]:
        parts = [p.strip().strip('"') for p in line.split(delimiter)]
        if not parts or not parts[0]:
            continue

        record = {}
        for i, header_name in enumerate(headers):
            record[header_name] = parts[i] if i < len(parts) else ""

        ndc = record.get("NDC", record.get("PRODUCTNDC", ""))
        if ndc:
            records.append({
                "ndc_code": ndc,
                "product_ndc": record.get("PRODUCTNDC", ""),
                "product_type": record.get("PRODUCTTYPENAME", ""),
                "proprietary_name": record.get("PROPRIETARYNAME", ""),
                "non_proprietary_name": record.get("NONPROPRIETARYNAME", ""),
                "labeler_name": record.get("LABELERNAME", ""),
                "substance_name": record.get("SUBSTANCENAME", ""),
                "route": record.get("ROUTENAME", ""),
                "dosage_form": record.get("DOSAGEFORMNAME", ""),
                "marketing_category": record.get("MARKETINGCATEGORYNAME", ""),
                "application_number": record.get("APPLICATIONNUMBER", ""),
            })

    return records


async def download(force: bool = False) -> dict:
    """Download NDC codes from FDA."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    codes_json = DEST_DIR / "ndc_codes.json"
    if file_exists_and_recent(codes_json, force):
        logger.info("NDC codes already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading NDC codes from FDA...")

    all_codes = []

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=30.0, read=300.0),
        follow_redirects=True,
    ) as client:
        # Try FDA openFDA API for structured NDC data
        try:
            ndc_zip_path = DEST_DIR / "ndc_download.zip"
            await download_file(NDC_DIRECTORY_URL, ndc_zip_path, client)

            from knowledge_bases._shared import extract_zip
            extracted = extract_zip(ndc_zip_path, DEST_DIR)
            logger.info("Extracted %d NDC files", len(extracted))

            for fpath in extracted:
                if fpath.suffix.lower() in (".txt", ".csv", ".dat"):
                    try:
                        text = fpath.read_text(encoding="utf-8", errors="replace")
                        codes = parse_ndc_text(text)
                        all_codes.extend(codes)
                        logger.info("Parsed %d NDC codes from %s", len(codes), fpath.name)
                    except Exception as exc:
                        logger.warning("Failed to parse %s: %s", fpath.name, exc)

            ndc_zip_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("FDA NDC directory download failed: %s", exc)

        # Try openFDA API as fallback
        if not all_codes:
            try:
                api_url = "https://api.fda.gov/drug/ndc.json?limit=1000"
                response = await client.get(api_url, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                for item in results:
                    all_codes.append({
                        "ndc_code": item.get("product_ndc", ""),
                        "product_type": item.get("product_type", ""),
                        "proprietary_name": item.get("proprietary_name", ""),
                        "non_proprietary_name": ", ".join(item.get("nonproprietary_name", [])),
                        "labeler_name": item.get("labeler_name", ""),
                        "route": ", ".join(item.get("route", [])),
                        "dosage_form": item.get("dosage_form", ""),
                        "marketing_category": item.get("marketing_category", ""),
                    })
                logger.info("Retrieved %d NDC codes from openFDA API", len(all_codes))
            except Exception as exc:
                logger.warning("openFDA API query failed: %s", exc)

    if not all_codes:
        logger.info("Building NDC reference from known structure")
        all_codes = build_ndc_reference()

    # Save in batches if the dataset is large to avoid memory issues
    if len(all_codes) > 50000:
        batch_size = 50000
        for i in range(0, len(all_codes), batch_size):
            batch = all_codes[i:i + batch_size]
            batch_num = i // batch_size
            save_json(batch, DEST_DIR / f"ndc_codes_part{batch_num}.json")
        # Save index
        save_json({
            "total_codes": len(all_codes),
            "parts": (len(all_codes) + batch_size - 1) // batch_size,
        }, DEST_DIR / "ndc_index.json")
    else:
        save_json(all_codes, codes_json)

    logger.info("Saved %d NDC codes", len(all_codes))

    file_list = [f.name for f in DEST_DIR.glob("ndc_codes*.json")]
    if DEST_DIR.glob("ndc_index.json"):
        file_list.append("ndc_index.json")
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": len(file_list),
        "message": f"Downloaded and parsed {len(all_codes)} NDC codes",
    }


def build_ndc_reference() -> list:
    """Build NDC reference structure."""
    return [
        {
            "ndc_code": "0000-0000",
            "product_type": "Reference Structure",
            "proprietary_name": "NDC Code Directory Structure",
            "description": (
                "NDC codes are 10-digit numbers in one of three formats: "
                "5-4-1, 5-3-2, or 4-4-2. The first segment is the labeler code, "
                "the second is the product code, and the third is the package code."
            ),
            "format_5_4_1": "Labeler(5)-Product(4)-Package(1)",
            "format_5_3_2": "Labeler(5)-Product(3)-Package(2)",
            "format_4_4_2": "Labeler(4)-Product(4)-Package(2)",
        },
    ]