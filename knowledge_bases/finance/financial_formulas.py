"""
Financial formulas reference.

Common financial formulas and calculations used in healthcare
finance, revenue cycle management, and business analytics.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.investopedia.com/financial-analysis-4689809"
DEST_DIR = DATA_ROOT / "finance" / "financial_formulas"
MODULE_NAME = "knowledge_bases.finance.financial_formulas"

FINANCIAL_FORMULAS = {
    "revenue_cycle_kpis": [
        {"name": "Days in A/R", "formula": "(Net Patient A/R / Net Patient Revenue) * Days in Period", "benchmark": "<50 days", "description": "Average number of days to collect payment for services"},
        {"name": "Clean Claim Rate", "formula": "(Claims Accepted on First Submission / Total Claims Submitted) * 100", "benchmark": ">95%", "description": "Percentage of claims accepted without need for correction"},
        {"name": "Denial Rate", "formula": "(Denied Claims / Total Claims Submitted) * 100", "benchmark": "<5%", "description": "Percentage of claims denied by payers"},
        {"name": "First Pass Resolution Rate", "formula": "(Claims Paid on First Submission / Total Claims) * 100", "benchmark": ">90%", "description": "Claims resolved without rework or appeal"},
        {"name": "Net Collection Rate", "formula": "(Payments / (Charges - Contractual Adjustments)) * 100", "benchmark": ">95%", "description": "Effectiveness of collecting what is contractually owed"},
        {"name": "Gross Collection Rate", "formula": "(Total Payments / Total Charges) * 100", "benchmark": "Varies", "description": "Total payments received as percentage of gross charges"},
        {"name": "Cost to Collect", "formula": "(Total RCM Costs / Total Collections) * 100", "benchmark": "<5%", "description": "Cost of billing operations as percentage of collections"},
        {"name": "A/R > 120 Days", "formula": "(A/R older than 120 days / Total A/R) * 100", "benchmark": "<15%", "description": "Percentage of receivables older than 120 days"},
    ],
    "profitability_ratios": [
        {"name": "Operating Margin", "formula": "(Operating Income / Total Revenue) * 100", "description": "Operating profitability as percentage of revenue"},
        {"name": "Net Margin", "formula": "(Net Income / Total Revenue) * 100", "description": "Bottom line profitability"},
        {"name": "Return on Assets (ROA)", "formula": "Net Income / Total Assets", "description": "How efficiently assets generate profit"},
        {"name": "Return on Equity (ROE)", "formula": "Net Income / Shareholders' Equity", "description": "Return generated for equity holders"},
    ],
    "liquidity_ratios": [
        {"name": "Current Ratio", "formula": "Current Assets / Current Liabilities", "benchmark": ">1.5", "description": "Ability to pay short-term obligations"},
        {"name": "Quick Ratio", "formula": "(Current Assets - Inventory) / Current Liabilities", "benchmark": ">1.0", "description": "Liquidity excluding inventory"},
        {"name": "Days Cash on Hand", "formula": "(Cash + Investments) / (Operating Expenses / 365)", "benchmark": ">180 days", "description": "Days of operations covered by available cash"},
    ],
    "efficiency_ratios": [
        {"name": "Asset Turnover", "formula": "Total Revenue / Total Assets", "description": "Revenue generated per dollar of assets"},
        {"name": "Revenue per Employee", "formula": "Total Revenue / FTE Count", "description": "Revenue productivity per employee"},
        {"name": "Cost per Discharge", "formula": "Total Operating Costs / Total Discharges", "description": "Average cost to treat an inpatient"},
    ],
    "healthcare_specific": [
        {"name": "Case Mix Index (CMI)", "formula": "Sum(DRG relative weights) / Total cases", "description": "Average relative weight of all cases; indicates severity/acuity"},
        {"name": "Occupancy Rate", "formula": "(Patient Days / (Beds * Days in Period)) * 100", "description": "Hospital bed utilization rate"},
        {"name": "Average Length of Stay (ALOS)", "formula": "Total Patient Days / Total Discharges", "description": "Average number of days per inpatient stay"},
        {"name": "Revenue per Adjusted Discharge", "formula": "Total Net Revenue / Adjusted Discharges", "description": "Revenue per case adjusted for outpatient activity"},
        {"name": "Outpatient Revenue %", "formula": "(Outpatient Revenue / Total Revenue) * 100", "description": "Proportion of revenue from outpatient services"},
    ],
    "time_value_of_money": [
        {"name": "Future Value", "formula": "PV * (1 + r)^n", "description": "Future value of present amount at interest rate r for n periods"},
        {"name": "Present Value", "formula": "FV / (1 + r)^n", "description": "Present value of future amount discounted at rate r"},
        {"name": "Net Present Value (NPV)", "formula": "Sum(CF_t / (1+r)^t) for t=0..n", "description": "Present value of all cash flows including initial investment"},
        {"name": "Internal Rate of Return (IRR)", "formula": "Rate where NPV = 0", "description": "Discount rate that makes NPV of all cash flows equal to zero"},
    ],
}


async def download(force: bool = False) -> dict:
    """Download financial formulas reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "financial_formulas.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading financial formulas reference...")
    save_json(FINANCIAL_FORMULAS, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded financial formulas reference"}