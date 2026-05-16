"""
OpenFDA drug data download.

Downloads drug information from the FDA open data API including
drug labeling, adverse events, enforcement reports, and NDC directory.

Source: https://open.fda.gov/apis/drug/
"""

import asyncio
import json
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_text, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://open.fda.gov/apis/drug/"
DEST_DIR = DATA_ROOT / "healthcare" / "clinical" / "drug_database"
MODULE_NAME = "knowledge_bases.healthcare.clinical.drug_database"

OPENFDA_ENDPOINTS = {
    "drug_label": "https://api.fda.gov/drug/label.json?limit=100",
    "drug_ndc": "https://api.fda.gov/drug/ndc.json?limit=100",
    "drug_event": "https://api.fda.gov/drug/event.json?limit=100",
    "drug_enforcement": "https://api.fda.gov/drug/enforcement.json?limit=100",
    "drug_drugfda": "https://api.fda.gov/drug/drugfda.json?limit=100",
}


async def download(force: bool = False) -> dict:
    """Download drug data from OpenFDA API."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "drug_database.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading drug data from OpenFDA API...")
    all_data = {}

    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=120.0), follow_redirects=True) as client:
        for endpoint_name, url in OPENFDA_ENDPOINTS.items():
            try:
                text = await download_text(url, client)
                data = json.loads(text)
                results = data.get("results", [])
                all_data[endpoint_name] = {
                    "count": len(results),
                    "total_available": data.get("meta", {}).get("results", {}).get("total", 0),
                    "sample": results[:10] if results else [],
                }
                save_json(results, DEST_DIR / f"drug_{endpoint_name}.json")
                logger.info("Downloaded %d %s records", len(results), endpoint_name)
            except Exception as exc:
                logger.warning("Failed to download %s: %s", endpoint_name, exc)
                all_data[endpoint_name] = {"error": str(exc)}

    save_json(all_data, codes_json)
    file_list = [codes_json.name] + [f"drug_{k}.json" for k in OPENFDA_ENDPOINTS.keys()]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": len(file_list), "message": f"Downloaded drug data from {len(OPENFDA_ENDPOINTS)} OpenFDA endpoints"}