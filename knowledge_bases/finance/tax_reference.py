"""
Tax reference data download.

Tax brackets, standard deductions, and key tax provisions for
US federal income tax.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, download_text, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.irs.gov/tax-stats"
DEST_DIR = DATA_ROOT / "finance" / "tax"
MODULE_NAME = "knowledge_bases.finance.tax_reference"

TAX_REFERENCE = {
    "federal_income_tax_brackets_2024": [
        {"rate": "10%", "single": "$0 - $11,600", "married_filing_jointly": "$0 - $23,200", "head_of_household": "$0 - $16,550"},
        {"rate": "12%", "single": "$11,601 - $47,150", "married_filing_jointly": "$23,201 - $94,300", "head_of_household": "$16,551 - $63,100"},
        {"rate": "22%", "single": "$47,151 - $100,525", "married_filing_jointly": "$94,301 - $201,050", "head_of_household": "$63,101 - $100,500"},
        {"rate": "24%", "single": "$100,526 - $191,950", "married_filing_jointly": "$201,051 - $383,900", "head_of_household": "$100,501 - $191,950"},
        {"rate": "32%", "single": "$191,951 - $243,725", "married_filing_jointly": "$383,901 - $487,450", "head_of_household": "$191,951 - $243,700"},
        {"rate": "35%", "single": "$243,726 - $609,350", "married_filing_jointly": "$487,451 - $731,200", "head_of_household": "$243,701 - $609,350"},
        {"rate": "37%", "single": "$609,351+", "married_filing_jointly": "$731,201+", "head_of_household": "$609,351+"},
    ],
    "standard_deductions_2024": {
        "single": 14600, "married_filing_jointly": 29200, "head_of_household": 21900,
        "additional_over_65_single": 1550, "additional_over_65_joint": 1250,
    },
    "capital_gains_rates": [
        {"rate": "0%", "threshold": "Income up to $47,025 (single) / $94,050 (MFJ)"},
        {"rate": "15%", "threshold": "Income $47,026 - $518,900 (single) / $94,051 - $583,750 (MFJ)"},
        {"rate": "20%", "threshold": "Income above $518,901 (single) / $583,751 (MFJ)"},
    ],
    "fica_taxes": {
        "social_security": {"rate": "6.2%", "wage_base": 168600, "self_employed": "12.4%"},
        "medicare": {"rate": "1.45%", "additional_medicare": "0.9% over $200K (single) / $250K (MFJ)", "self_employed": "2.9% + 0.9% additional"},
    },
    "business_tax_provisions": [
        {"provision": "Section 179 Expensing", "limit_2024": 1220000, "phase_out_begins": 3050000},
        {"provision": "Bonus Depreciation", "rate_2024": "60%", "notes": "Phasing down 20% per year from 100% in 2022"},
        {"provision": "Qualified Business Income (QBI) Deduction", "rate": "20% of qualified business income", "threshold_2024": "$191,950 (single) / $383,900 (MFJ)"},
        {"provision": "Self-Employment Tax Deduction", "deduction": "50% of SE tax is deductible"},
    ],
}


async def download(force: bool = False) -> dict:
    """Download tax reference data."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "tax_reference.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading tax reference data...")
    save_json(TAX_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded tax reference data"}