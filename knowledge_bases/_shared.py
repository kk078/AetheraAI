"""
Shared utilities for knowledge base downloaders.

Provides common download, extraction, manifest, and retry logic
used by all individual downloader modules.
"""

import asyncio
import io
import json
import logging
import os
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("knowledge_bases.shared")

DATA_ROOT = Path(os.environ.get("AETHERA_DATA_ROOT", "/data/knowledge"))
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
CONNECT_TIMEOUT = 30.0
READ_TIMEOUT = 300.0


async def download_file(
    url: str,
    dest_path: Path,
    client: Optional[httpx.AsyncClient] = None,
    retries: int = MAX_RETRIES,
) -> Path:
    """Download a file from URL to dest_path with retries.

    Args:
        url: Remote URL to download from.
        dest_path: Local path to save the file.
        client: Optional httpx client to reuse.
        retries: Maximum number of retry attempts.

    Returns:
        Path to the downloaded file.

    Raises:
        httpx.HTTPError: If all retries fail.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=CONNECT_TIMEOUT, read=READ_TIMEOUT),
            follow_redirects=True,
        )

    try:
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                logger.debug("Downloading %s (attempt %d/%d)", url, attempt, retries)
                response = await client.get(url)
                response.raise_for_status()
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, "wb") as fh:
                    fh.write(response.content)
                logger.debug("Downloaded %s -> %s (%d bytes)", url, dest_path, len(response.content))
                return dest_path
            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as exc:
                last_error = exc
                if attempt < retries:
                    delay = RETRY_DELAY_SECONDS * attempt
                    logger.warning(
                        "Download attempt %d/%d failed for %s: %s. Retrying in %ds...",
                        attempt, retries, url, exc, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("All %d download attempts failed for %s: %s", retries, url, exc)
        raise last_error  # type: ignore[misc]
    finally:
        if own_client:
            await client.aclose()


async def download_text(
    url: str,
    client: Optional[httpx.AsyncClient] = None,
    retries: int = MAX_RETRIES,
    encoding: str = "utf-8",
) -> str:
    """Download a text file from URL and return its content as string."""
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=CONNECT_TIMEOUT, read=READ_TIMEOUT),
            follow_redirects=True,
        )

    try:
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as exc:
                last_error = exc
                if attempt < retries:
                    delay = RETRY_DELAY_SECONDS * attempt
                    await asyncio.sleep(delay)
        raise last_error  # type: ignore[misc]
    finally:
        if own_client:
            await client.aclose()


def extract_zip(zip_path: Path, dest_dir: Path) -> list:
    """Extract a ZIP file and return list of extracted file paths.

    Args:
        zip_path: Path to the ZIP file.
        dest_dir: Directory to extract files into.

    Returns:
        List of paths to extracted files.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    extracted_files = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            # Skip directories and __MACOSX junk
            if info.is_dir():
                continue
            if "__MACOSX" in info.filename or info.filename.startswith("."):
                continue
            # Sanitize the filename to prevent path traversal
            safe_name = Path(info.filename).name
            if not safe_name:
                continue
            target = dest_dir / safe_name
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted_files.append(target)

    return extracted_files


def save_json(data, dest_path: Path) -> Path:
    """Save structured data as JSON."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    return dest_path


def save_text(text: str, dest_path: Path) -> Path:
    """Save text content to a file."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return dest_path


def write_manifest(
    dest_dir: Path,
    module_name: str,
    source_url: str,
    file_list: list,
    extra: Optional[dict] = None,
) -> Path:
    """Write a manifest.json file for a downloaded dataset.

    Args:
        dest_dir: Directory where the manifest should be written.
        module_name: Name of the downloader module.
        source_url: URL the data was downloaded from.
        file_list: List of filenames in the dataset.
        extra: Additional metadata to include.

    Returns:
        Path to the manifest file.
    """
    manifest = {
        "module": module_name,
        "source_url": source_url,
        "download_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "file_list": [str(f) if isinstance(f, Path) else f for f in file_list],
    }
    if extra:
        manifest.update(extra)

    dest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = dest_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    return manifest_path


def write_placeholder(
    dest_dir: Path,
    module_name: str,
    dataset_name: str,
    instructions: str,
    source_url: str,
) -> Path:
    """Write a placeholder JSON with instructions for obtaining licensed data.

    Args:
        dest_dir: Directory for the placeholder.
        module_name: Downloader module name.
        dataset_name: Name of the licensed dataset.
        instructions: How to obtain the data.
        source_url: Where to get the data.

    Returns:
        Path to the placeholder file.
    """
    placeholder = {
        "licensed_content": True,
        "module": module_name,
        "dataset_name": dataset_name,
        "instructions": instructions,
        "source_url": source_url,
        "message": (
            f"This dataset ({dataset_name}) requires a license agreement. "
            f"Follow the instructions below to obtain the data, then place "
            f"the files in this directory and re-run the download to generate "
            f"the structured JSON."
        ),
    }
    dest_dir.mkdir(parents=True, exist_ok=True)
    placeholder_path = dest_dir / "LICENSED_DATA_INSTRUCTIONS.json"
    save_json(placeholder, placeholder_path)
    write_manifest(
        dest_dir, module_name, source_url,
        file_list=[placeholder_path.name],
        extra={"licensed": True, "placeholder": True},
    )
    return placeholder_path


def parse_tab_separated(text: str, has_header: bool = True) -> list:
    """Parse tab-separated text into a list of dicts (if header) or list of lists."""
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    if not lines:
        return []

    if has_header:
        headers = lines[0].split("\t")
        records = []
        for line in lines[1:]:
            values = line.split("\t")
            record = {}
            for i, header in enumerate(headers):
                record[header.strip()] = values[i].strip() if i < len(values) else ""
            records.append(record)
        return records
    else:
        return [line.split("\t") for line in lines]


def parse_csv_text(text: str, has_header: bool = True) -> list:
    """Parse CSV text into a list of dicts (if header) or list of lists.

    Handles quoted fields and commas within quotes.
    """
    import csv as csv_mod
    reader = csv_mod.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []

    if has_header:
        headers = [h.strip() for h in rows[0]]
        records = []
        for row in rows[1:]:
            record = {}
            for i, header in enumerate(headers):
                record[header] = row[i].strip() if i < len(row) else ""
            records.append(record)
        return records
    else:
        return rows


def file_exists_and_recent(dest_path: Path, force: bool = False) -> bool:
    """Check if a file exists and is recent enough to skip download.

    If force is True, always returns False (always re-download).
    """
    if force:
        return False
    return dest_path.exists() and dest_path.stat().st_size > 0