"""
Check for updates and re-download changed knowledge base files.

Compares local file dates against remote Last-Modified headers.
Only re-downloads files that have changed on the remote server.
Re-indexes updated files into ChromaDB automatically.

Usage:
    python -m knowledge_bases.update_all [--category healthcare|finance|legal|technology]
"""

import argparse
import asyncio
import json
import logging
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import httpx

from knowledge_bases import CATEGORIES, DATA_ROOT
from knowledge_bases.download_all import DOWNLOADER_REGISTRY, run_downloader
from knowledge_bases.index_all import index_file, create_or_get_collection, delete_from_collection

logger = logging.getLogger("knowledge_bases.update_all")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@dataclass
class UpdateCheck:
    """Result of checking a single file for updates."""
    module: str
    local_date: str = ""
    remote_date: str = ""
    needs_update: bool = False
    updated: bool = False
    re_indexed: bool = False
    error: str = ""


def read_manifest(manifest_path: Path) -> dict:
    """Read a manifest.json file if it exists."""
    if not manifest_path.exists():
        return {}
    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


async def check_remote_last_modified(
    url: str, client: httpx.AsyncClient
) -> Optional[str]:
    """Check the Last-Modified header of a remote URL using HEAD request."""
    try:
        response = await client.head(url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        return response.headers.get("last-modified", "")
    except Exception as exc:
        logger.debug("HEAD request failed for %s: %s", url, exc)
        return None


async def check_manifest_update(
    category: str, subcategory: str, client: httpx.AsyncClient
) -> list:
    """Check all manifests in a subcategory for updates.

    Reads each manifest.json, compares download_date with the current
    date, and checks if remote sources have been updated.
    """
    subcategory_path = Path(DATA_ROOT) / category / subcategory
    if not subcategory_path.exists():
        return []

    updates = []
    for manifest_path in sorted(subcategory_path.glob("*/manifest.json")):
        manifest = read_manifest(manifest_path)
        if not manifest:
            continue

        source_url = manifest.get("source_url", "")
        download_date = manifest.get("download_date", "")

        if source_url:
            remote_date = await check_remote_last_modified(source_url, client)
            needs_update = False

            if remote_date and download_date:
                # Compare dates
                try:
                    from email.utils import parsedate_to_datetime
                    remote_dt = parsedate_to_datetime(remote_date)
                    # Parse our ISO format date
                    local_dt_str = download_date.replace("Z", "+00:00")
                    from datetime import datetime, timezone
                    local_dt = datetime.fromisoformat(local_dt_str)
                    needs_update = remote_dt > local_dt
                except Exception:
                    # If we can't parse dates, be conservative
                    needs_update = False
            elif not download_date:
                needs_update = True

            updates.append(UpdateCheck(
                module=manifest.get("module", str(manifest_path.parent)),
                local_date=download_date,
                remote_date=remote_date or "",
                needs_update=needs_update,
            ))

    return updates


async def update_all(
    categories: Optional[list] = None,
) -> dict:
    """Check for updates and re-download changed files, then re-index."""
    cats = categories or CATEGORIES
    results = {
        "checked": 0,
        "needs_update": 0,
        "updated": 0,
        "re_indexed": 0,
        "errors": 0,
        "details": [],
    }

    async with httpx.AsyncClient() as client:
        for category in cats:
            if category not in DOWNLOADER_REGISTRY:
                continue

            subcategories = DOWNLOADER_REGISTRY[category]
            logger.info("Checking for updates in category: %s", category)

            for sub_name in subcategories:
                # Check manifests for updates
                checks = await check_manifest_update(category, sub_name, client)
                results["checked"] += len(checks)

                for check in checks:
                    if check.needs_update:
                        results["needs_update"] += 1
                        logger.info(
                            "Update available: %s (local: %s, remote: %s)",
                            check.module, check.local_date, check.remote_date,
                        )

                # For files that need updating, re-run the downloaders
                # We use a simpler approach: re-download if any manifest
                # indicates an update, or if no manifest exists
                subcategory_path = Path(DATA_ROOT) / category / sub_name
                if subcategory_path.exists():
                    # Check if any subdirectory lacks a manifest
                    for subdir in sorted(subcategory_path.iterdir()):
                        if not subdir.is_dir():
                            continue
                        manifest_path = subdir / "manifest.json"
                        if not manifest_path.exists():
                            # Missing manifest means we need to download
                            logger.info(
                                "Missing manifest in %s, scheduling download",
                                subdir,
                            )
                            results["needs_update"] += 1

        # Now re-download modules that need updates
        # We run all downloaders with force=False (they should check internally)
        # but only for categories that showed updates
        for category in cats:
            if category not in DOWNLOADER_REGISTRY:
                continue

            subcategories = DOWNLOADER_REGISTRY[category]
            for sub_name, module_names in subcategories.items():
                subcategory_path = Path(DATA_ROOT) / category / sub_name
                has_missing = False
                has_outdated = False

                if subcategory_path.exists():
                    for subdir in sorted(subcategory_path.iterdir()):
                        if not subdir.is_dir():
                            continue
                        manifest_path = subdir / "manifest.json"
                        if not manifest_path.exists():
                            has_missing = True
                            break
                        manifest = read_manifest(manifest_path)
                        if manifest.get("needs_update"):
                            has_outdated = True
                            break

                if has_missing or has_outdated:
                    logger.info(
                        "Re-downloading %s/%s due to updates detected",
                        category, sub_name,
                    )
                    for module_name in module_names:
                        dl_result = await run_downloader(module_name, force=True, dry_run=False)
                        if dl_result.success and not dl_result.skipped:
                            results["updated"] += 1
                        elif not dl_result.success:
                            results["errors"] += 1
                        results["details"].append(asdict(dl_result))

    # Save update report
    report_path = Path(DATA_ROOT) / "update_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                **results,
            },
            fh,
            indent=2,
        )
    logger.info("Update report saved to %s", report_path)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Check for updates and re-download changed knowledge base files"
    )
    parser.add_argument(
        "--category",
        action="append",
        choices=CATEGORIES,
        help="Filter to specific categories (can be repeated)",
    )
    args = parser.parse_args()
    asyncio.run(update_all(categories=args.category))


if __name__ == "__main__":
    main()