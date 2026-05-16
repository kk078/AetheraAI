"""
X12 EDI transaction specification references.

Provides reference information about X12 Electronic Data Interchange
transaction sets used in healthcare, including 837 (claims), 835
(remittance), 270/271 (eligibility), 276/277 (claim status), and
278 (authorization).
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

SOURCE_URL = "https://x12.org/products/transaction-sets"
DEST_DIR = DATA_ROOT / "healthcare" / "claims" / "edi_specs"
MODULE_NAME = "knowledge_bases.healthcare.claims.edi_specs"

EDI_TRANSACTIONS = [
    {
        "transaction": "837",
        "type": "Health Care Claim",
        "versions": ["005010X222A1", "005010X223A2", "005010X224A2", "005010X231A1"],
        "description": "Health Care Claim transaction used to submit health care claims to payers",
        "sub_types": [
            {"id": "837P", "name": "Professional", "form": "CMS-1500", "usage": "Physician and professional claims"},
            {"id": "837I", "name": "Institutional", "form": "UB-04", "usage": "Hospital and facility claims"},
            {"id": "837D", "name": "Dental", "form": "ADA Dental Claim Form", "usage": "Dental claims"},
        ],
        "key_segments": [
            {"segment": "ISA", "name": "Interchange Control Header", "level": "interchange"},
            {"segment": "GS", "name": "Functional Group Header", "level": "group"},
            {"segment": "ST", "name": "Transaction Set Header", "level": "transaction"},
            {"segment": "BHT", "name": "Beginning of Hierarchical Transaction", "level": "transaction"},
            {"segment": "NM1", "name": "Name", "level": "hierarchical"},
            {"segment": "HL", "name": "Hierarchical Level", "level": "hierarchical"},
            {"segment": "CLM", "name": "Claim Information", "level": "claim"},
            {"segment": "SV1", "name": "Professional Service", "level": "service_line"},
            {"segment": "SV2", "name": "Institutional Service", "level": "service_line"},
            {"segment": "SV3", "name": "Dental Service", "level": "service_line"},
            {"segment": "LX", "name": "Service Line Loop", "level": "service_line"},
            {"segment": "REF", "name": "Reference Identification", "level": "various"},
            {"segment": "DTP", "name": "Date/Time Period", "level": "various"},
            {"segment": "DI", "name": "Diagnosis", "level": "claim"},
            {"segment": "HI", "name": "Health Care Diagnosis", "level": "claim"},
            {"segment": "SE", "name": "Transaction Set Trailer", "level": "transaction"},
            {"segment": "GE", "name": "Functional Group Trailer", "level": "group"},
            {"segment": "IEA", "name": "Interchange Control Trailer", "level": "interchange"},
        ],
    },
    {
        "transaction": "835",
        "type": "Health Care Remittance Advice",
        "versions": ["005010X221A1"],
        "description": "Health Care Remittance Advice used to communicate claim payment information",
        "key_segments": [
            {"segment": "ISA", "name": "Interchange Control Header", "level": "interchange"},
            {"segment": "GS", "name": "Functional Group Header", "level": "group"},
            {"segment": "ST", "name": "Transaction Set Header", "level": "transaction"},
            {"segment": "BPR", "name": "Financial Information", "level": "transaction"},
            {"segment": "TRN", "name": "Trace Number", "level": "transaction"},
            {"segment": "LX", "name": "Service Line Loop", "level": "service_line"},
            {"segment": "CLP", "name": "Claim Level Data", "level": "claim"},
            {"segment": "SVC", "name": "Service Payment Information", "level": "service_line"},
            {"segment": "CAS", "name": "Claim Adjustments", "level": "various"},
            {"segment": "AMT", "name": "Monetary Amount", "level": "various"},
            {"segment": "LQ", "name": "Code List Qualifier", "level": "various"},
            {"segment": "PLB", "name": "Provider Level Adjustment", "level": "provider"},
            {"segment": "SE", "name": "Transaction Set Trailer", "level": "transaction"},
        ],
    },
    {
        "transaction": "270",
        "type": "Eligibility Inquiry",
        "versions": ["005010X279A1"],
        "description": "Health Care Eligibility Benefit Inquiry used to request patient eligibility and benefit information",
        "key_segments": [
            {"segment": "ISA", "name": "Interchange Control Header", "level": "interchange"},
            {"segment": "BHT", "name": "Beginning of Hierarchical Transaction", "level": "transaction"},
            {"segment": "HL", "name": "Hierarchical Level", "level": "hierarchical"},
            {"segment": "NM1", "name": "Name", "level": "hierarchical"},
            {"segment": "TRN", "name": "Trace Number", "level": "transaction"},
            {"segment": "DMG", "name": "Demographic Information", "level": "hierarchical"},
            {"segment": "INS", "name": "Insured Benefit", "level": "hierarchical"},
            {"segment": "EQ", "name": "Eligibility Inquiry", "level": "inquiry"},
        ],
    },
    {
        "transaction": "271",
        "type": "Eligibility Response",
        "versions": ["005010X279A1"],
        "description": "Health Care Eligibility Benefit Response used to return eligibility and benefit information",
        "key_segments": [
            {"segment": "ISA", "name": "Interchange Control Header", "level": "interchange"},
            {"segment": "BHT", "name": "Beginning of Hierarchical Transaction", "level": "transaction"},
            {"segment": "HL", "name": "Hierarchical Level", "level": "hierarchical"},
            {"segment": "NM1", "name": "Name", "level": "hierarchical"},
            {"segment": "EB", "name": "Eligibility Benefit", "level": "benefit"},
            {"segment": "LS", "name": "Loop Header", "level": "loop"},
            {"segment": "LE", "name": "Loop Trailer", "level": "loop"},
        ],
    },
    {
        "transaction": "276",
        "type": "Claim Status Inquiry",
        "versions": ["005010X212A1"],
        "description": "Health Care Claim Status Request used to inquire about the status of a submitted claim",
        "key_segments": [
            {"segment": "ISA", "name": "Interchange Control Header", "level": "interchange"},
            {"segment": "BHT", "name": "Beginning of Hierarchical Transaction", "level": "transaction"},
            {"segment": "HL", "name": "Hierarchical Level", "level": "hierarchical"},
            {"segment": "NM1", "name": "Name", "level": "hierarchical"},
            {"segment": "TRN", "name": "Trace Number", "level": "transaction"},
            {"segment": "REF", "name": "Reference Identification", "level": "various"},
            {"segment": "DTP", "name": "Date/Time Period", "level": "various"},
        ],
    },
    {
        "transaction": "277",
        "type": "Claim Status Response",
        "versions": ["005010X212A1"],
        "description": "Health Care Claim Status Notification used to report the status of submitted claims",
        "key_segments": [
            {"segment": "ISA", "name": "Interchange Control Header", "level": "interchange"},
            {"segment": "BHT", "name": "Beginning of Hierarchical Transaction", "level": "transaction"},
            {"segment": "HL", "name": "Hierarchical Level", "level": "hierarchical"},
            {"segment": "NM1", "name": "Name", "level": "hierarchical"},
            {"segment": "STC", "name": "Claim Status Information", "level": "claim"},
            {"segment": "REF", "name": "Reference Identification", "level": "various"},
            {"segment": "DTP", "name": "Date/Time Period", "level": "various"},
        ],
    },
    {
        "transaction": "278",
        "type": "Authorization",
        "versions": ["005010X217A1"],
        "description": "Health Care Services Review Authorization used for prior authorization requests and responses",
        "sub_types": [
            {"id": "278A1", "name": "Request", "usage": "Authorization request from provider to payer"},
            {"id": "278A3", "name": "Response", "usage": "Authorization response from payer to provider"},
        ],
        "key_segments": [
            {"segment": "ISA", "name": "Interchange Control Header", "level": "interchange"},
            {"segment": "BHT", "name": "Beginning of Hierarchical Transaction", "level": "transaction"},
            {"segment": "HL", "name": "Hierarchical Level", "level": "hierarchical"},
            {"segment": "NM1", "name": "Name", "level": "hierarchical"},
            {"segment": "SV1", "name": "Professional Service", "level": "service"},
            {"segment": "HSD", "name": "Health Care Services Review", "level": "review"},
        ],
    },
]


async def download(force: bool = False) -> dict:
    """Create X12 EDI transaction specification references."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    codes_json = DEST_DIR / "edi_specs.json"
    if file_exists_and_recent(codes_json, force):
        logger.info("EDI specs already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Creating X12 EDI transaction specification references...")

    save_json(EDI_TRANSACTIONS, codes_json)

    # Save individual transaction specs
    for txn in EDI_TRANSACTIONS:
        txn_id = txn["transaction"]
        save_json(txn, DEST_DIR / f"edi_{txn_id}_spec.json")

    file_list = [codes_json.name] + [f"edi_{t['transaction']}_spec.json" for t in EDI_TRANSACTIONS]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": len(file_list),
        "message": f"Created {len(EDI_TRANSACTIONS)} EDI transaction specifications",
    }