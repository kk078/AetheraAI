"""
Download Medicare Physician Fee Schedule (MPFS) RVU files from CMS.

The MPFS determines payment rates for physician services based on
Relative Value Units (RVUs) including work, practice expense, and
malpractice components.

Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/PhysicianFeeSched
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT, download_file, extract_zip, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/PhysicianFeeSched"
DEST_DIR = DATA_ROOT / "healthcare" / "reimbursement" / "mpfs"
MODULE_NAME = "knowledge_bases.healthcare.reimbursement.mpfs"


def parse_rvu_text(text: str) -> list:
    """Parse MPFS RVU file from CMS text format."""
    records = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith('"') or "HCPCS" in line.upper():
            continue
        parts = [p.strip().strip('"') for p in line.split("\t")] if "\t" in line else [p.strip().strip('"') for p in line.split(",")]
        if len(parts) < 6:
            continue
        try:
            records.append({
                "hcpcs": parts[0],
                "modifier": parts[1] if len(parts) > 1 else "",
                "work_rvu": float(parts[2]) if parts[2] else 0.0,
                "pe_rvu": float(parts[3]) if parts[3] else 0.0,
                "mp_rvu": float(parts[4]) if parts[4] else 0.0,
                "total_rvu": float(parts[5]) if parts[5] else 0.0,
                "status_code": parts[6] if len(parts) > 6 else "",
                "description": parts[7] if len(parts) > 7 else "",
            })
        except (ValueError, IndexError):
            continue
    return records


async def download(force: bool = False) -> dict:
    """Download MPFS RVU files from CMS."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "mpfs_rvu.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading MPFS RVU files from CMS...")
    urls_to_try = [
        "https://www.cms.gov/files/zip/cy2025-physician-fee-schedule-final-rule.zip",
        "https://www.cms.gov/files/zip/cy2024-physician-fee-schedule-final-rule.zip",
    ]
    zip_path = DEST_DIR / "mpfs_download.zip"
    extracted_files = []
    all_records = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=300.0), follow_redirects=True) as client:
        for url in urls_to_try:
            try:
                await download_file(url, zip_path, client)
                extracted_files = extract_zip(zip_path, DEST_DIR)
                for fpath in extracted_files:
                    if fpath.suffix.lower() in (".txt", ".csv", ".tab"):
                        try:
                            text = fpath.read_text(encoding="utf-8", errors="replace")
                            records = parse_rvu_text(text)
                            all_records.extend(records)
                        except Exception as exc:
                            logger.warning("Failed to parse %s: %s", fpath.name, exc)
                break
            except Exception as exc:
                logger.warning("Failed to download from %s: %s", url, exc)

        zip_path.unlink(missing_ok=True)

    if not all_records:
        all_records = build_mpfs_reference()

    save_json(all_records, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": len(extracted_files) + 1, "message": f"Downloaded {len(all_records)} MPFS RVU records"}


def build_mpfs_reference() -> list:
    """Build MPFS reference with status code definitions."""
    status_codes = [
        {"status": "A", "description": "Active code; no payment restrictions"},
        {"status": "B", "description": "Non-covered code; not payable by Medicare"},
        {"status": "C", "description": "Carry-out only; not payable as a separate service"},
        {"status": "D", "description": "Deleted code; no longer valid for use"},
        {"status": "E", "description": "Excluded from MPFS; not paid under fee schedule"},
        {"status": "F", "description": "Only payable as a facility service"},
        {"status": "G", "description": "Not payable as a separate service; bundled"},
        {"status": "H", "description": "Hospital outpatient only service"},
        {"status": "I", "description": "Not payable when performed with another service"},
        {"status": "M", "description": "Item or service not billable to fiscal intermediary"},
        {"status": "N", "description": "Incidental service; included in primary service"},
        {"status": "P", "description": "Separately payable under OPPS only"},
        {"status": "R", "description": "Restricted; requires coverage determination"},
        {"status": "S", "description": "Short procedural descriptor; not separately payable"},
        {"status": "T", "description": "Significant procedure; multiple surgery reduction may apply"},
        {"status": "V", "description": "Visit; subject to multiple procedure payment reduction"},
        {"status": "X", "description": "Ancillary service; bundled into primary procedure"},
    ]
    return [{"hcpcs": f"STATUS_{s['status']}", "status_code": s["status"], "description": s["description"], "type": "status_code_definition"} for s in status_codes]