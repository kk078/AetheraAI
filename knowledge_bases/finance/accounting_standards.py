"""
Accounting standards reference.

Key accounting standards and principles reference including GAAP,
IFRS, and industry-specific guidance relevant to healthcare.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.fasb.org/"
DEST_DIR = DATA_ROOT / "finance" / "accounting_standards"
MODULE_NAME = "knowledge_bases.finance.accounting_standards"

ACCOUNTING_REFERENCE = {
    "gaap_principles": [
        {"principle": "Revenue Recognition (ASC 606)", "description": "5-step model: identify contract, identify performance obligations, determine transaction price, allocate price, recognize revenue when/as obligation satisfied", "healthcare_application": "Patient service revenue, capitation, risk-sharing arrangements"},
        {"principle": "Lease Accounting (ASC 842)", "description": "Lessee records right-of-use asset and lease liability for leases >12 months", "healthcare_application": "Medical equipment leases, facility leases"},
        {"principle": "Credit Losses (ASC 326)", "description": "Expected credit loss model replaces incurred loss model", "healthcare_application": "Patient receivable reserves, bad debt estimation"},
        {"principle": "Goodwill and Intangibles (ASC 350)", "description": "Goodwill not amortized; tested for impairment annually", "healthcare_application": "Hospital acquisitions, medical practice valuations"},
        {"principle": "Consolidation (ASC 810)", "description": "Variable interest entity (VIE) model for consolidation", "healthcare_application": "Joint ventures, physician practice affiliations"},
    ],
    "healthcare_specific_guidance": [
        {"topic": "ASC 954", "name": "Health Care Entities", "description": "Industry-specific guidance for health care entities including revenue classification (patient service, capitation, etc.)"},
        {"topic": "ASC 605", "name": "Revenue Recognition (Legacy)", "description": "Legacy healthcare revenue recognition; being replaced by ASC 606"},
        {"topic": "Charity Care", "description": "Charity care and unconditional courtesy adjustments are not reported as revenue; only reported in footnotes"},
        {"topic": "Contractual Adjustments", "description": "Difference between gross charges and amounts expected from third-party payers; reported as revenue deduction"},
        {"topic": "Capitation Revenue", "description": "Prepaid amounts received per member per month; recognized as services are provided"},
    ],
    "financial_statements": [
        {"statement": "Balance Sheet", "key_line_items": ["Patient receivables (net)", "Property and equipment", "Goodwill", "Long-term debt", "Net assets (restricted and unrestricted)"]},
        {"statement": "Income Statement", "key_line_items": ["Patient service revenue (net of contractuals)", "Premium revenue (for health plans)", "Operating expenses", "Excess of revenue over expenses"]},
        {"statement": "Cash Flow Statement", "key_line_items": ["Operating cash flows", "Capital expenditures", "Borrowing/debt payments", "Investment activity"]},
    ],
}


async def download(force: bool = False) -> dict:
    """Download accounting standards reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "accounting_standards.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading accounting standards reference...")
    save_json(ACCOUNTING_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded accounting standards reference"}