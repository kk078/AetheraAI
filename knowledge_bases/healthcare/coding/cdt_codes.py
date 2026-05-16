"""
CDT dental codes (public descriptions from ADA).

CDT (Current Dental Terminology) codes are maintained by the American
Dental Association. Full code descriptions require an ADA license.
This module provides publicly available category descriptions and a
placeholder for obtaining full licensed data.

Source: https://www.ada.org/publications/cdt
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT,
    save_json,
    write_placeholder,
    write_manifest,
    file_exists_and_recent,
)

logger = logging.getLogger(__name__)

SOURCE_URL = "https://www.ada.org/publications/cdt"
DEST_DIR = DATA_ROOT / "healthcare" / "coding" / "cdt"
MODULE_NAME = "knowledge_bases.healthcare.coding.cdt_codes"

# Publicly available CDT code categories
CDT_CATEGORIES = [
    {
        "range": "D0100-D1999",
        "category": "Diagnostic",
        "description": "Diagnostic services including examinations, radiographs, and diagnostic casts",
    },
    {
        "range": "D2000-D2999",
        "category": "Preventive",
        "description": "Preventive services including prophylaxis, fluoride treatments, and sealants",
    },
    {
        "range": "D3000-D3999",
        "category": "Endodontics",
        "description": "Endodontic services including root canal therapy and periradicular surgery",
    },
    {
        "range": "D4000-D4999",
        "category": "Periodontics",
        "description": "Periodontal services including scaling, root planing, and periodontal surgery",
    },
    {
        "range": "D5000-D5999",
        "category": "Prosthodontics",
        "description": "Prosthodontic services including crowns, bridges, dentures, and implants",
        "subcategories": [
            {"range": "D5100-D5200", "category": "Removable Prosthodontics - Maxillary"},
            {"range": "D5210-D5299", "category": "Removable Prosthodontics - Mandibular"},
            {"range": "D5500-D5899", "category": "Removable Prosthodontics - Repairs/Adjustments"},
            {"range": "D6000-D6199", "category": "Implant Services"},
            {"range": "D6200-D6999", "category": "Fixed Prosthodontics"},
        ],
    },
    {
        "range": "D7000-D7999",
        "category": "Oral and Maxillofacial Surgery",
        "description": "Surgical services including extractions, surgical adjuncts, and bone grafting",
    },
    {
        "range": "D8000-D8999",
        "category": "Orthodontics",
        "description": "Orthodontic services including diagnosis, active treatment, and retention",
    },
    {
        "range": "D9000-D9999",
        "category": "Adjunctive General Services",
        "description": "Adjunctive services including sedation, anesthesia, and behavioral management",
    },
]


async def download(force: bool = False) -> dict:
    """Create CDT category descriptions and licensed content placeholder."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    categories_json = DEST_DIR / "cdt_categories.json"
    if file_exists_and_recent(categories_json, force):
        logger.info("CDT codes already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Creating CDT dental code categories and license placeholder...")

    save_json(CDT_CATEGORIES, categories_json)

    write_placeholder(
        DEST_DIR,
        MODULE_NAME,
        "CDT Code Descriptions (Full)",
        (
            "CDT (Current Dental Terminology) code descriptions are copyrighted by the "
            "American Dental Association (ADA). To obtain CDT data:\n\n"
            "1. Visit https://www.ada.org/publications/cdt\n"
            "2. Purchase the CDT reference manual or digital code set\n"
            "3. Download the code file (typically CSV format)\n"
            "4. Place the file in this directory as 'cdt_codes_full.csv'\n"
            "5. Re-run the download to generate structured JSON\n\n"
            "Note: CDT codes are updated annually. Ensure you have the current year's codes.\n"
            "Some dental insurance carriers provide CDT code lookups in their provider portals."
        ),
        SOURCE_URL,
    )

    file_list = [categories_json.name, "LICENSED_DATA_INSTRUCTIONS.json"]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": 2,
        "message": "Created CDT categories and licensed content placeholder",
    }