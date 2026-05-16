"""
Claim status category codes.

Claim status codes indicate the status of a claim in the adjudication
process. Used in X12 276/277 claim status inquiry and response
transactions.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT,
    save_json,
    write_manifest,
    file_exists_and_recent,
)

logger = logging.getLogger(__name__)

SOURCE_URL = "https://x12.org/codes/claim-status-category-codes"
DEST_DIR = DATA_ROOT / "healthcare" / "claims" / "claim_status"
MODULE_NAME = "knowledge_bases.healthcare.claims.claim_status_codes"

CLAIM_STATUS_CODES = [
    {"code": "1", "category": "Received", "description": "Claim received by the payer, initial processing has not started"},
    {"code": "2", "category": "Received", "description": "Claim received and entered into the payer's adjudication system"},
    {"code": "3", "category": "Received", "description": "Claim received and is pending review"},
    {"code": "4", "category": "Received", "description": "Claim received, pending review of additional information"},
    {"code": "5", "category": "Received", "description": "Claim received, under investigation or review"},
    {"code": "6", "category": "Received", "description": "Claim received and is being processed"},
    {"code": "7", "category": "Received", "description": "Claim received, but the payer has not yet responded to the provider's request for a status"},
    {"code": "10", "category": "Received", "description": "Claim received, but processing has been delayed"},
    {"code": "11", "category": "Received", "description": "Claim received, but the provider was not certified at the time of service"},
    {"code": "12", "category": "Received", "description": "Claim received, additional information requested from the provider"},
    {"code": "13", "category": "Received", "description": "Claim received, additional information requested from the patient/subscriber"},
    {"code": "14", "category": "Received", "description": "Claim received, additional information requested from another source"},
    {"code": "15", "category": "Received", "description": "Claim received, additional information received, processing resumed"},
    {"code": "16", "category": "Received", "description": "Claim received, additional information requested but not received"},
    {"code": "17", "category": "Received", "description": "Claim received, additional information received but insufficient, further information required"},
    {"code": "18", "category": "Received", "description": "Claim received, under review for duplicate"},
    {"code": "19", "category": "Received", "description": "Claim received, under review for coordination of benefits"},
    {"code": "20", "category": "Accepted", "description": "Claim accepted for processing"},
    {"code": "21", "category": "Accepted", "description": "Claim accepted, waiting for payment"},
    {"code": "22", "category": "Accepted", "description": "Claim accepted, payment pending review"},
    {"code": "23", "category": "Accepted", "description": "Claim accepted, pending secondary payer processing"},
    {"code": "24", "category": "Accepted", "description": "Claim accepted, pending prior payer adjudication"},
    {"code": "25", "category": "Accepted", "description": "Claim accepted, pending completion of pre-existing review"},
    {"code": "26", "category": "Accepted", "description": "Claim accepted, pending authorization review"},
    {"code": "27", "category": "Accepted", "description": "Claim accepted, pending patient eligibility verification"},
    {"code": "F1", "category": "Finalized", "description": "Finalized - Payment made"},
    {"code": "F2", "category": "Finalized", "description": "Finalized - Partial payment made"},
    {"code": "F3", "category": "Finalized", "description": "Finalized - Denied"},
    {"code": "F4", "category": "Finalized", "description": "Finalized - Denied, appealed by provider"},
    {"code": "F5", "category": "Finalized", "description": "Finalized - Denied, appealed by patient"},
    {"code": "F6", "category": "Finalized", "description": "Finalized - Denied, under review"},
    {"code": "F7", "category": "Finalized", "description": "Finalized - Reversed during prior payer adjudication"},
    {"code": "F8", "category": "Finalized", "description": "Finalized - Reversed to patient responsibility"},
    {"code": "F9", "category": "Finalized", "description": "Finalized - Reversed to provider responsibility"},
    {"code": "A0", "category": "Accepted", "description": "Accepted - In review"},
    {"code": "A1", "category": "Accepted", "description": "Accepted - Reconsideration requested"},
    {"code": "A2", "category": "Accepted", "description": "Accepted - Reopened"},
    {"code": "A3", "category": "Accepted", "description": "Accepted - Adjusted"},
    {"code": "A4", "category": "Accepted", "description": "Accepted - Appeal received"},
    {"code": "A5", "category": "Accepted", "description": "Accepted - Appeal under review"},
    {"code": "A6", "category": "Accepted", "description": "Accepted - Second appeal received"},
    {"code": "A7", "category": "Accepted", "description": "Accepted - Second appeal under review"},
    {"code": "A8", "category": "Accepted", "description": "Accepted - External review requested"},
    {"code": "A9", "category": "Accepted", "description": "Accepted - External review under review"},
    {"code": "P0", "category": "Pending", "description": "Pending - Adjudication in progress"},
    {"code": "P1", "category": "Pending", "description": "Pending - Primary payer processing"},
    {"code": "P2", "category": "Pending", "description": "Pending - Secondary payer processing"},
    {"code": "P3", "category": "Pending", "description": "Pending - Tertiary payer processing"},
    {"code": "P4", "category": "Pending", "description": "Pending - Coordination of benefits processing"},
    {"code": "P5", "category": "Pending", "description": "Pending - Payment processing"},
    {"code": "P6", "category": "Pending", "description": "Pending - Additional review required"},
    {"code": "P7", "category": "Pending", "description": "Pending - Medical review required"},
    {"code": "P8", "category": "Pending", "description": "Pending - Utilization review required"},
    {"code": "P9", "category": "Pending", "description": "Pending - Prior authorization required"},
    {"code": "P10", "category": "Pending", "description": "Pending - Referral required"},
    {"code": "P11", "category": "Pending", "description": "Pending - Information requested from provider"},
    {"code": "P12", "category": "Pending", "description": "Pending - Information requested from patient"},
    {"code": "P13", "category": "Pending", "description": "Pending - Information requested from other source"},
    {"code": "P14", "category": "Pending", "description": "Pending - Information received, processing resumed"},
    {"code": "P15", "category": "Pending", "description": "Pending - Information requested but not received"},
    {"code": "P16", "category": "Pending", "description": "Pending - Waiting for filing deadline"},
    {"code": "P17", "category": "Pending", "description": "Pending - Waiting for prior payer payment"},
    {"code": "P18", "category": "Pending", "description": "Pending - Waiting for prior payer adjudication"},
    {"code": "P19", "category": "Pending", "description": "Pending - Waiting for patient eligibility determination"},
    {"code": "P20", "category": "Pending", "description": "Pending - Waiting for benefit determination"},
    {"code": "P21", "category": "Pending", "description": "Pending - Waiting for pre-certification/authorization"},
    {"code": "P22", "category": "Pending", "description": "Pending - Waiting for referral"},
    {"code": "P23", "category": "Pending", "description": "Pending - Waiting for documentation"},
    {"code": "P24", "category": "Pending", "description": "Pending - Waiting for itemized bill"},
    {"code": "P25", "category": "Pending", "description": "Pending - Waiting for operative report"},
    {"code": "P26", "category": "Pending", "description": "Pending - Waiting for medical records"},
    {"code": "P27", "category": "Pending", "description": "Pending - Waiting for itemization of charges"},
    {"code": "R0", "category": "Rejected", "description": "Rejected - Claim not processable"},
    {"code": "R1", "category": "Rejected", "description": "Rejected - Invalid claim data"},
    {"code": "R2", "category": "Rejected", "description": "Rejected - Missing required data"},
    {"code": "R3", "category": "Rejected", "description": "Rejected - Duplicate claim"},
    {"code": "R4", "category": "Rejected", "description": "Rejected - Filing deadline expired"},
    {"code": "R5", "category": "Rejected", "description": "Rejected - Invalid provider"},
    {"code": "R6", "category": "Rejected", "description": "Rejected - Invalid patient"},
    {"code": "R7", "category": "Rejected", "description": "Rejected - Invalid subscriber"},
    {"code": "R8", "category": "Rejected", "description": "Rejected - Invalid payer"},
    {"code": "R9", "category": "Rejected", "description": "Rejected - Invalid diagnosis"},
    {"code": "R10", "category": "Rejected", "description": "Rejected - Invalid procedure"},
    {"code": "R11", "category": "Rejected", "description": "Rejected - Invalid date"},
    {"code": "R12", "category": "Rejected", "description": "Rejected - Invalid amount"},
    {"code": "R13", "category": "Rejected", "description": "Rejected - Invalid format"},
    {"code": "R14", "category": "Rejected", "description": "Rejected - Invalid attachment"},
    {"code": "R15", "category": "Rejected", "description": "Rejected - Invalid resubmission"},
    {"code": "R16", "category": "Rejected", "description": "Rejected - Invalid crossover"},
    {"code": "R17", "category": "Rejected", "description": "Rejected - Invalid authorization"},
    {"code": "R18", "category": "Rejected", "description": "Rejected - Invalid referral"},
    {"code": "R19", "category": "Rejected", "description": "Rejected - Invalid NPI"},
    {"code": "R20", "category": "Rejected", "description": "Rejected - Invalid tax ID"},
    {"code": "S1", "category": "Suspended", "description": "Suspended - Pending review"},
    {"code": "S2", "category": "Suspended", "description": "Suspended - Pending investigation"},
    {"code": "S3", "category": "Suspended", "description": "Suspended - Pending audit"},
    {"code": "S4", "category": "Suspended", "description": "Suspended - Pending litigation"},
    {"code": "S5", "category": "Suspended", "description": "Suspended - Pending fraud investigation"},
    {"code": "S6", "category": "Suspended", "description": "Suspended - Pending abuse investigation"},
    {"code": "S7", "category": "Suspended", "description": "Suspended - Pending compliance review"},
]


async def download(force: bool = False) -> dict:
    """Create claim status category codes."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    codes_json = DEST_DIR / "claim_status_codes.json"
    if file_exists_and_recent(codes_json, force):
        logger.info("Claim status codes already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Creating claim status category codes...")

    save_json(CLAIM_STATUS_CODES, codes_json)

    # Group by category
    by_category = {}
    for code in CLAIM_STATUS_CODES:
        cat = code["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(code)
    save_json(by_category, DEST_DIR / "claim_status_by_category.json")

    file_list = [codes_json.name, "claim_status_by_category.json"]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": 2,
        "message": f"Created {len(CLAIM_STATUS_CODES)} claim status codes",
    }