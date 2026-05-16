"""
Master download script for all AetheraAI knowledge bases.

Orchestrates individual category downloaders, tracks progress, and
produces a consolidated log of results. Supports category filtering,
force re-download, and dry-run mode.

Usage:
    python -m knowledge_bases.download_all [--category healthcare|finance|legal|technology] [--force] [--dry-run]
"""

import argparse
import asyncio
import importlib
import json
import logging
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from knowledge_bases import CATEGORIES, DATA_ROOT

logger = logging.getLogger("knowledge_bases.download_all")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Registry of all downloader modules organized by category and subcategory
DOWNLOADER_REGISTRY = {
    "healthcare": {
        "coding": [
            "knowledge_bases.healthcare.coding.icd10cm_codes",
            "knowledge_bases.healthcare.coding.icd10pcs_codes",
            "knowledge_bases.healthcare.coding.cpt_descriptions",
            "knowledge_bases.healthcare.coding.hcpcs_codes",
            "knowledge_bases.healthcare.coding.cdt_codes",
            "knowledge_bases.healthcare.coding.ndc_codes",
            "knowledge_bases.healthcare.coding.revenue_codes",
            "knowledge_bases.healthcare.coding.place_of_service",
            "knowledge_bases.healthcare.coding.modifier_list",
            "knowledge_bases.healthcare.coding.taxonomy_codes",
            "knowledge_bases.healthcare.coding.drg_weights",
        ],
        "claims": [
            "knowledge_bases.healthcare.claims.carc_rarc_codes",
            "knowledge_bases.healthcare.claims.claim_status_codes",
            "knowledge_bases.healthcare.claims.cci_edits",
            "knowledge_bases.healthcare.claims.mue_values",
            "knowledge_bases.healthcare.claims.ocm_edits",
            "knowledge_bases.healthcare.claims.edi_specs",
        ],
        "reimbursement": [
            "knowledge_bases.healthcare.reimbursement.mpfs",
            "knowledge_bases.healthcare.reimbursement.opps",
            "knowledge_bases.healthcare.reimbursement.ipps",
            "knowledge_bases.healthcare.reimbursement.asc_fee_schedule",
            "knowledge_bases.healthcare.reimbursement.dme_fee_schedule",
            "knowledge_bases.healthcare.reimbursement.clinical_lab_fee",
            "knowledge_bases.healthcare.reimbursement.snf_pps",
            "knowledge_bases.healthcare.reimbursement.hh_pps",
            "knowledge_bases.healthcare.reimbursement.irf_pps",
            "knowledge_bases.healthcare.reimbursement.ltch_pps",
            "knowledge_bases.healthcare.reimbursement.hospice_rates",
            "knowledge_bases.healthcare.reimbursement.esrd_pps",
            "knowledge_bases.healthcare.reimbursement.drug_pricing",
        ],
        "regulatory": [
            "knowledge_bases.healthcare.regulatory.cms_manuals",
            "knowledge_bases.healthcare.regulatory.claims_processing_manual",
            "knowledge_bases.healthcare.regulatory.program_integrity_manual",
            "knowledge_bases.healthcare.regulatory.mln_articles",
            "knowledge_bases.healthcare.regulatory.cms_transmittals",
            "knowledge_bases.healthcare.regulatory.hipaa_rules",
            "knowledge_bases.healthcare.regulatory.no_surprises_act",
            "knowledge_bases.healthcare.regulatory.price_transparency",
            "knowledge_bases.healthcare.regulatory.oig_work_plan",
            "knowledge_bases.healthcare.regulatory.stark_law",
            "knowledge_bases.healthcare.regulatory.anti_kickback",
            "knowledge_bases.healthcare.regulatory.false_claims_act",
            "knowledge_bases.healthcare.regulatory.emtala",
            "knowledge_bases.healthcare.regulatory.mental_health_parity",
            "knowledge_bases.healthcare.regulatory.telehealth_rules",
            "knowledge_bases.healthcare.regulatory.state_medicaid",
            "knowledge_bases.healthcare.regulatory.cms_final_rules",
        ],
        "quality": [
            "knowledge_bases.healthcare.quality.hedis_measures",
            "knowledge_bases.healthcare.quality.mips_measures",
            "knowledge_bases.healthcare.quality.star_ratings",
            "knowledge_bases.healthcare.quality.cahps",
            "knowledge_bases.healthcare.quality.core_measures",
            "knowledge_bases.healthcare.quality.value_based_programs",
        ],
        "clinical": [
            "knowledge_bases.healthcare.clinical.drug_database",
            "knowledge_bases.healthcare.clinical.lab_reference",
            "knowledge_bases.healthcare.clinical.screening_guidelines",
            "knowledge_bases.healthcare.clinical.clinical_guidelines",
            "knowledge_bases.healthcare.clinical.medical_calculators",
        ],
        "payer_specific": [
            "knowledge_bases.healthcare.payer_specific.medicare_parts",
            "knowledge_bases.healthcare.payer_specific.medicaid_rules",
            "knowledge_bases.healthcare.payer_specific.tricare",
            "knowledge_bases.healthcare.payer_specific.va_community_care",
            "knowledge_bases.healthcare.payer_specific.workers_comp",
            "knowledge_bases.healthcare.payer_specific.auto_nofault",
            "knowledge_bases.healthcare.payer_specific.commercial_basics",
        ],
    },
    "finance": {
        "tax": [
            "knowledge_bases.finance.tax_reference",
        ],
        "standards": [
            "knowledge_bases.finance.accounting_standards",
        ],
        "formulas": [
            "knowledge_bases.finance.financial_formulas",
        ],
    },
    "legal": {
        "contracts": [
            "knowledge_bases.legal.contract_templates",
        ],
        "licensing": [
            "knowledge_bases.legal.license_types",
        ],
        "privacy": [
            "knowledge_bases.legal.privacy_frameworks",
        ],
    },
    "technology": {
        "cloudflare": [
            "knowledge_bases.technology.cloudflare_docs",
        ],
        "security": [
            "knowledge_bases.technology.security_best_practices",
        ],
        "web": [
            "knowledge_bases.technology.web_standards",
        ],
    },
}


@dataclass
class DownloadResult:
    """Result of a single downloader execution."""
    module: str
    success: bool
    message: str = ""
    files_downloaded: int = 0
    duration_seconds: float = 0.0
    skipped: bool = False


@dataclass
class DownloadReport:
    """Consolidated report of all download operations."""
    category: str
    total_downloaders: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    total_files: int = 0
    total_duration: float = 0.0
    results: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "total_downloaders": self.total_downloaders,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "total_files": self.total_files,
            "total_duration": round(self.total_duration, 2),
            "results": [asdict(r) for r in self.results],
        }


async def run_downloader(
    module_name: str, force: bool, dry_run: bool
) -> DownloadResult:
    """Import and execute a single downloader module."""
    start = time.monotonic()
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        duration = time.monotonic() - start
        logger.error("Failed to import %s: %s", module_name, exc)
        return DownloadResult(
            module=module_name,
            success=False,
            message=f"Import error: {exc}",
            duration_seconds=duration,
        )

    if dry_run:
        duration = time.monotonic() - start
        logger.info("[DRY-RUN] Would download: %s", module_name)
        return DownloadResult(
            module=module_name,
            success=True,
            message="Dry run - skipped",
            duration_seconds=duration,
            skipped=True,
        )

    try:
        result = await module.download(force=force)
        duration = time.monotonic() - start
        files_count = result.get("files_downloaded", 0) if isinstance(result, dict) else 0
        msg = result.get("message", "OK") if isinstance(result, dict) else "OK"
        return DownloadResult(
            module=module_name,
            success=True,
            message=msg,
            files_downloaded=files_count,
            duration_seconds=duration,
        )
    except Exception as exc:
        duration = time.monotonic() - start
        logger.error("Download failed for %s: %s", module_name, exc)
        return DownloadResult(
            module=module_name,
            success=False,
            message=str(exc),
            duration_seconds=duration,
        )


async def download_category(
    category: str, subcategories: dict, force: bool, dry_run: bool
) -> DownloadReport:
    """Run all downloaders for a given category."""
    report = DownloadReport(category=category)
    total_modules = sum(len(mods) for mods in subcategories.values())
    report.total_downloaders = total_modules

    completed = 0
    for sub_name, module_names in subcategories.items():
        logger.info(
            "[%s] Starting subcategory: %s (%d downloaders)",
            category, sub_name, len(module_names),
        )
        for module_name in module_names:
            completed += 1
            progress = f"[{completed}/{total_modules}]"
            logger.info("%s Downloading: %s", progress, module_name)
            result = await run_downloader(module_name, force, dry_run)
            report.results.append(result)
            report.total_files += result.files_downloaded
            report.total_duration += result.duration_seconds

            if result.skipped:
                report.skipped += 1
            elif result.success:
                report.successful += 1
                logger.info(
                    "%s Completed: %s (%d files, %.1fs)",
                    progress, module_name, result.files_downloaded, result.duration_seconds,
                )
            else:
                report.failed += 1
                logger.error(
                    "%s Failed: %s - %s", progress, module_name, result.message,
                )

    return report


async def download_all(
    categories: Optional[list] = None,
    force: bool = False,
    dry_run: bool = False,
) -> list:
    """Download all knowledge bases, optionally filtered by category."""
    cats = categories or CATEGORIES
    reports = []

    for category in cats:
        if category not in DOWNLOADER_REGISTRY:
            logger.warning("Unknown category: %s, skipping", category)
            continue
        subcategories = DOWNLOADER_REGISTRY[category]
        logger.info("=" * 60)
        logger.info("Starting downloads for category: %s", category)
        logger.info("=" * 60)
        report = await download_category(category, subcategories, force, dry_run)
        reports.append(report)
        logger.info(
            "[%s] Complete: %d success, %d failed, %d skipped, %d files, %.1fs",
            category,
            report.successful,
            report.failed,
            report.skipped,
            report.total_files,
            report.total_duration,
        )

    # Save consolidated report
    report_path = Path(DATA_ROOT) / "download_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "categories": [r.to_dict() for r in reports],
            },
            fh,
            indent=2,
        )
    logger.info("Download report saved to %s", report_path)
    return reports


def main():
    parser = argparse.ArgumentParser(
        description="Download all AetheraAI knowledge bases"
    )
    parser.add_argument(
        "--category",
        action="append",
        choices=CATEGORIES,
        help="Filter to specific categories (can be repeated)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if files exist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )
    args = parser.parse_args()
    asyncio.run(download_all(
        categories=args.category,
        force=args.force,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()