"""
AetheraAI Knowledge Base Management CLI.

Provides a unified interface for downloading, indexing, and managing
knowledge base data.

Usage:
    python -m knowledge_bases.manage status
    python -m knowledge_bases.manage download [--category ...] [--force] [--dry-run]
    python -m knowledge_bases.manage index [--category ...] [--force] [--collection name]
    python -m knowledge_bases.manage update [--category ...]
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from knowledge_bases import CATEGORIES, DATA_ROOT

logger = logging.getLogger("knowledge_bases.manage")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def cmd_status(args):
    """Show status of downloaded knowledge bases."""
    data_root = Path(DATA_ROOT)
    if not data_root.exists():
        print(f"Data directory does not exist: {data_root}")
        print("Run 'download' to fetch knowledge base data.")
        return

    categories = args.category or CATEGORIES
    total_files = 0
    total_size = 0

    for category in categories:
        cat_path = data_root / category
        if not cat_path.exists():
            print(f"  {category}: NOT DOWNLOADED")
            continue

        cat_files = 0
        cat_size = 0
        manifests = 0

        for fpath in sorted(cat_path.rglob("*")):
            if fpath.is_file():
                cat_files += 1
                cat_size += fpath.stat().st_size
                if fpath.name == "manifest.json":
                    manifests += 1

        total_files += cat_files
        total_size += cat_size

        size_mb = cat_size / (1024 * 1024)
        print(f"  {category}: {cat_files} files, {manifests} manifests, {size_mb:.1f} MB")

    total_mb = total_size / (1024 * 1024)
    print(f"\n  Total: {total_files} files, {total_mb:.1f} MB")


def cmd_download(args):
    """Download knowledge base data."""
    from knowledge_bases.download_all import download_all
    reports = asyncio.run(download_all(
        categories=args.category,
        force=args.force,
        dry_run=args.dry_run,
    ))
    for report in reports:
        print(f"\n{report.category}: {report.successful} success, "
              f"{report.failed} failed, {report.skipped} skipped, "
              f"{report.total_files} files")


def cmd_index(args):
    """Index downloaded data into ChromaDB."""
    from knowledge_bases.index_all import index_all
    results = asyncio.run(index_all(
        categories=args.category,
        force=args.force,
        collection_name=args.collection,
    ))
    for result in results:
        print(f"\n{result['category']}: {result['total_files']} files, "
              f"{result['total_chunks']} chunks, "
              f"{result['total_indexed']} indexed, "
              f"{result['total_errors']} errors")


def cmd_update(args):
    """Check for updates and re-download changed data."""
    from knowledge_bases.update_all import update_all
    results = asyncio.run(update_all(categories=args.category))
    print(f"\nChecked: {results['checked']}")
    print(f"Needs update: {results['needs_update']}")
    print(f"Updated: {results['updated']}")
    print(f"Re-indexed: {results['re_indexed']}")
    print(f"Errors: {results['errors']}")


def main():
    parser = argparse.ArgumentParser(
        description="AetheraAI Knowledge Base Management CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status
    p_status = subparsers.add_parser("status", help="Show download status")
    p_status.add_argument("--category", action="append", choices=CATEGORIES,
                         help="Filter to specific categories")

    # download
    p_download = subparsers.add_parser("download", help="Download knowledge base data")
    p_download.add_argument("--category", action="append", choices=CATEGORIES,
                           help="Filter to specific categories")
    p_download.add_argument("--force", action="store_true",
                           help="Force re-download")
    p_download.add_argument("--dry-run", action="store_true",
                           help="Show what would be downloaded")

    # index
    p_index = subparsers.add_parser("index", help="Index data into ChromaDB")
    p_index.add_argument("--category", action="append", choices=CATEGORIES,
                        help="Filter to specific categories")
    p_index.add_argument("--force", action="store_true",
                        help="Force re-indexing")
    p_index.add_argument("--collection", type=str,
                        help="Override collection name")

    # update
    p_update = subparsers.add_parser("update", help="Check for updates")
    p_update.add_argument("--category", action="append", choices=CATEGORIES,
                         help="Filter to specific categories")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "status": cmd_status,
        "download": cmd_download,
        "index": cmd_index,
        "update": cmd_update,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()