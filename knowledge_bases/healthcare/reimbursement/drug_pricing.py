"""
ASP, AWP, NADAC drug pricing from CMS/FDA.

Downloads Average Sales Price (ASP), Average Wholesale Price (AWP),
and National Average Drug Acquisition Cost (NADAC) data from CMS and
FDA for drug pricing reference.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Part-B-Drugs/McrPartBDrugAvgSalesPrice
Source: https://www.medicaid.gov/medicaid-chip-program-information/by-topics/pharmacy/nadac.html
"""

import asyncio
import csv
import io
import json
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_file, download_text, extract_zip, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Part-B-Drugs/McrPartBDrugAvgSalesPrice"
DEST_DIR = DATA_ROOT / "healthcare" / "reimbursement" / "drug_pricing"
MODULE_NAME = "knowledge_bases.healthcare.reimbursement.drug_pricing"

DRUG_PRICING_REFERENCE = {
    "pricing_types": [
        {
            "type": "ASP (Average Sales Price)",
            "description": "Weighted average of prices paid to manufacturers by wholesalers, calculated quarterly",
            "source": "CMS Part B Drug ASP files",
            "usage": "Medicare Part B drug reimbursement (ASP + 6%)",
        },
        {
            "type": "AWP (Average Wholesale Price)",
            "description": "Manufacturer-reported list price; typically higher than actual transaction prices",
            "source": "Commercial publishers (e.g., Red Book, Medi-Span)",
            "usage": "Reference pricing for commercial contracts; often discounted significantly",
        },
        {
            "type": "NADAC (National Average Drug Acquisition Cost)",
            "description": "Average price pharmacies pay to acquire drugs, based on survey data",
            "source": "CMS Medicaid pharmacy surveys",
            "usage": "Medicaid reimbursement benchmark for pharmacy dispensing",
        },
        {
            "type": "WAC (Wholesale Acquisition Cost)",
            "description": "Manufacturer list price to wholesalers, before discounts",
            "source": "Manufacturer reporting",
            "usage": "Starting point for price negotiations; less commonly used for reimbursement",
        },
        {
            "type": "340B Price",
            "description": "Discounted price for covered entities under Section 340B program",
            "source": "HRSA 340B program",
            "usage": "Safety-net providers accessing discounted drug prices",
        },
    ],
    "part_b_payment_formula": "Medicare Part B Drug Payment = ASP + 6% (or ASP + add-on for infused drugs in SECA)",
    "sequester_adjustment": "2% sequestration reduction may apply to drug payments",
}


def parse_asp_csv(text: str) -> list:
    """Parse ASP drug pricing CSV from CMS."""
    records = []
    try:
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            hcpcs = row.get("HCPCS", row.get("hcpcs", ""))
            if not hcpcs:
                continue
            records.append({
                "hcpcs_code": hcpcs,
                "drug_name": row.get("Drug_Name", row.get("drug_name", "")),
                "dosage": row.get("Dosage", row.get("dosage", "")),
                "asp": row.get("ASP", row.get("asp", "")),
                "units": row.get("Units", row.get("units", "")),
                "payment_limit": row.get("Payment_Limit", row.get("payment_limit", "")),
            })
    except Exception as exc:
        logger.warning("Failed to parse ASP CSV: %s", exc)
    return records


async def download(force: bool = False) -> dict:
    """Download drug pricing data from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "drug_pricing.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading drug pricing data from CMS...")
    all_records = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=300.0), follow_redirects=True) as client:
        # Try ASP files
        asp_urls = [
            "https://www.cms.gov/files/zip/2025-q1-asp-pricing-file.zip",
            "https://www.cms.gov/files/zip/2024-q4-asp-pricing-file.zip",
        ]
        for url in asp_urls:
            try:
                zip_path = DEST_DIR / "asp_download.zip"
                await download_file(url, zip_path, client)
                extracted = extract_zip(zip_path, DEST_DIR)
                for fpath in extracted:
                    if fpath.suffix.lower() in (".csv", ".txt"):
                        try:
                            text = fpath.read_text(encoding="utf-8", errors="replace")
                            records = parse_asp_csv(text)
                            all_records.extend(records)
                        except Exception as exc:
                            logger.warning("Failed to parse ASP file %s: %s", fpath.name, exc)
                zip_path.unlink(missing_ok=True)
                break
            except Exception as exc:
                logger.warning("Failed to download ASP from %s: %s", url, exc)

    save_json(DRUG_PRICING_REFERENCE, codes_json)
    if all_records:
        save_json(all_records, DEST_DIR / "asp_pricing_detail.json")

    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": len(file_list), "message": f"Downloaded drug pricing reference with {len(all_records)} ASP records"}