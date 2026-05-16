"""
Revenue code descriptions.

Revenue codes are used on UB-04 claim forms to identify the department
or service area where services were rendered. Maintained by NUCC and
widely used in hospital billing.
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

SOURCE_URL = "https://www.nucc.org/index.php/code-sets-index/revenue-codes"
DEST_DIR = DATA_ROOT / "healthcare" / "coding" / "revenue_codes"
MODULE_NAME = "knowledge_bases.healthcare.coding.revenue_codes"

# Complete revenue code list
REVENUE_CODES = [
    {"code": "001x", "category": "Routine Services", "description": "Routine Services - General", "subcodes": [
        {"code": "0010", "description": "Routine Services - General Classification"},
        {"code": "0011", "description": "Routine Services - Semi-Private Room"},
        {"code": "0012", "description": "Routine Services - Private Room"},
        {"code": "0013", "description": "Routine Services - Ward"},
        {"code": "0014", "description": "Routine Services - Deluxe Room & Board"},
        {"code": "0015", "description": "Routine Services - Nursery"},
    ]},
    {"code": "002x", "category": "Routine Services", "description": "Routine Services - Skilled Nursing", "subcodes": [
        {"code": "0020", "description": "Routine Services - SNF General Classification"},
        {"code": "0021", "description": "Routine Services - SNF Semi-Private Room"},
        {"code": "0022", "description": "Routine Services - SNF Private Room"},
    ]},
    {"code": "003x", "category": "Routine Services", "description": "Routine Services - Subprovider", "subcodes": [
        {"code": "0030", "description": "Routine Services - Subprovider General Classification"},
    ]},
    {"code": "010x", "category": "Room and Board", "description": "Room and Board - Psychiatric", "subcodes": [
        {"code": "0100", "description": "Room and Board - Psych General Classification"},
        {"code": "0110", "description": "Room and Board - Accommodations"},
        {"code": "0111", "description": "Room and Board - Semi-Private Room"},
        {"code": "0112", "description": "Room and Board - Private Room"},
        {"code": "0113", "description": "Room and Board - Ward"},
    ]},
    {"code": "011x", "category": "Room and Board", "description": "Room and Board - Rehabilitation", "subcodes": [
        {"code": "0110", "description": "Room and Board - Rehab General Classification"},
        {"code": "0111", "description": "Room and Board - Rehab Semi-Private Room"},
        {"code": "0112", "description": "Room and Board - Rehab Private Room"},
    ]},
    {"code": "012x", "category": "Room and Board", "description": "Room and Board - Other", "subcodes": [
        {"code": "0120", "description": "Room and Board - Other General Classification"},
        {"code": "0121", "description": "Room and Board - Other Semi-Private Room"},
        {"code": "0122", "description": "Room and Board - Other Private Room"},
    ]},
    {"code": "020x", "category": "Intensive Care", "description": "Intensive Care", "subcodes": [
        {"code": "0200", "description": "Intensive Care - General Classification"},
        {"code": "0201", "description": "Intensive Care - Medical"},
        {"code": "0202", "description": "Intensive Care - Surgical"},
        {"code": "0203", "description": "Intensive Care - Pediatric"},
        {"code": "0204", "description": "Intensive Care - Psychiatric"},
        {"code": "0205", "description": "Intensive Care - Neonatal (NICU)"},
        {"code": "0206", "description": "Intensive Care - Coronary (CCU)"},
    ]},
    {"code": "021x", "category": "Intensive Care", "description": "Intensive Care - Special Charges", "subcodes": [
        {"code": "0210", "description": "Intensive Care - Special Charges General Classification"},
        {"code": "0211", "description": "Intensive Care - Special Charges - Medical"},
        {"code": "0212", "description": "Intensive Care - Special Charges - Surgical"},
        {"code": "0219", "description": "Intensive Care - Special Charges - Other"},
    ]},
    {"code": "030x", "category": "Ancillary Services", "description": "Laboratory", "subcodes": [
        {"code": "0300", "description": "Laboratory - General Classification"},
        {"code": "0301", "description": "Laboratory - General"},
        {"code": "0302", "description": "Laboratory - Blood Bank"},
        {"code": "0303", "description": "Laboratory - Chemistry"},
        {"code": "0304", "description": "Laboratory - Hematology"},
        {"code": "0305", "description": "Laboratory - Microbiology"},
        {"code": "0306", "description": "Laboratory - Immunology"},
        {"code": "0307", "description": "Laboratory - Urinalysis"},
        {"code": "0308", "description": "Laboratory - Cytology"},
        {"code": "0309", "description": "Laboratory - Other"},
    ]},
    {"code": "031x", "category": "Ancillary Services", "description": "Pathology", "subcodes": [
        {"code": "0310", "description": "Pathology - General Classification"},
        {"code": "0311", "description": "Pathology - General"},
        {"code": "0312", "description": "Pathology - Surgical Pathology"},
        {"code": "0313", "description": "Pathology - Cytology"},
        {"code": "0314", "description": "Pathology - Autopsy"},
    ]},
    {"code": "032x", "category": "Ancillary Services", "description": "Radiology - Diagnostic", "subcodes": [
        {"code": "0320", "description": "Radiology - Diagnostic General Classification"},
        {"code": "0321", "description": "Radiology - Diagnostic General"},
        {"code": "0322", "description": "Radiology - Diagnostic X-Ray"},
        {"code": "0323", "description": "Radiology - Diagnostic CT Scan"},
        {"code": "0324", "description": "Radiology - Diagnostic MRI"},
        {"code": "0325", "description": "Radiology - Diagnostic Ultrasound"},
        {"code": "0326", "description": "Radiology - Diagnostic Nuclear Medicine"},
        {"code": "0327", "description": "Radiology - Diagnostic PET Scan"},
    ]},
    {"code": "033x", "category": "Ancillary Services", "description": "Radiology - Therapeutic", "subcodes": [
        {"code": "0330", "description": "Radiology - Therapeutic General Classification"},
        {"code": "0331", "description": "Radiology - Therapeutic General"},
        {"code": "0332", "description": "Radiology - Therapeutic X-Ray"},
        {"code": "0333", "description": "Radiology - Therapeutic Nuclear Medicine"},
        {"code": "0334", "description": "Radiology - Radio Isotope"},
    ]},
    {"code": "034x", "category": "Ancillary Services", "description": "Radiology - Other", "subcodes": [
        {"code": "0340", "description": "Radiology - Other General Classification"},
        {"code": "0341", "description": "Radiology - Other - General"},
    ]},
    {"code": "035x", "category": "Ancillary Services", "description": "MRI", "subcodes": [
        {"code": "0350", "description": "MRI - General Classification"},
        {"code": "0351", "description": "MRI - Brain"},
        {"code": "0352", "description": "MRI - Other"},
    ]},
    {"code": "040x", "category": "Ancillary Services", "description": "Operating Room", "subcodes": [
        {"code": "0400", "description": "Operating Room - General Classification"},
        {"code": "0401", "description": "Operating Room - General"},
    ]},
    {"code": "041x", "category": "Ancillary Services", "description": "Recovery Room", "subcodes": [
        {"code": "0410", "description": "Recovery Room - General Classification"},
        {"code": "0411", "description": "Recovery Room - General"},
    ]},
    {"code": "042x", "category": "Ancillary Services", "description": "Delivery Room", "subcodes": [
        {"code": "0420", "description": "Delivery Room - General Classification"},
        {"code": "0421", "description": "Delivery Room - General"},
    ]},
    {"code": "044x", "category": "Ancillary Services", "description": "Anesthesia", "subcodes": [
        {"code": "0440", "description": "Anesthesia - General Classification"},
        {"code": "0441", "description": "Anesthesia - General"},
    ]},
    {"code": "045x", "category": "Ancillary Services", "description": "Emergency Room", "subcodes": [
        {"code": "0450", "description": "Emergency Room - General Classification"},
        {"code": "0451", "description": "Emergency Room - General"},
        {"code": "0452", "description": "Emergency Room - Level 1"},
        {"code": "0453", "description": "Emergency Room - Level 2"},
        {"code": "0454", "description": "Emergency Room - Level 3"},
        {"code": "0455", "description": "Emergency Room - Level 4"},
        {"code": "0456", "description": "Emergency Room - Level 5"},
        {"code": "0457", "description": "Emergency Room - Level 6"},
    ]},
    {"code": "051x", "category": "Ancillary Services", "description": "Respiratory Services", "subcodes": [
        {"code": "0510", "description": "Respiratory Services - General Classification"},
        {"code": "0511", "description": "Respiratory Services - General"},
        {"code": "0513", "description": "Respiratory Services - Inhalation Therapy"},
    ]},
    {"code": "060x", "category": "Ancillary Services", "description": "Pharmacy", "subcodes": [
        {"code": "0600", "description": "Pharmacy - General Classification"},
        {"code": "0601", "description": "Pharmacy - General"},
        {"code": "0602", "description": "Pharmacy - IV Solutions"},
        {"code": "0603", "description": "Pharmacy - Non-IV"},
        {"code": "0604", "description": "Pharmacy - Prescription"},
        {"code": "0605", "description": "Pharmacy - OTC"},
    ]},
    {"code": "061x", "category": "Ancillary Services", "description": "Medical/Surgical Supplies", "subcodes": [
        {"code": "0610", "description": "Medical/Surgical Supplies - General Classification"},
        {"code": "0611", "description": "Medical/Surgical Supplies - General"},
        {"code": "0612", "description": "Medical/Surgical Supplies - Operating Room"},
        {"code": "0613", "description": "Medical/Surgical Supplies - Recovery Room"},
        {"code": "0614", "description": "Medical/Surgical Supplies - Delivery Room"},
        {"code": "0615", "description": "Medical/Surgical Supplies - Emergency Room"},
        {"code": "0616", "description": "Medical/Surgical Supplies - Cath Lab"},
        {"code": "0617", "description": "Medical/Surgical Supplies - Pulmonary Lab"},
        {"code": "0618", "description": "Medical/Surgical Supplies - IV Therapy"},
        {"code": "0619", "description": "Medical/Surgical Supplies - Other"},
    ]},
    {"code": "070x", "category": "Ancillary Services", "description": "Physical Therapy", "subcodes": [
        {"code": "0700", "description": "Physical Therapy - General Classification"},
        {"code": "0701", "description": "Physical Therapy - General"},
    ]},
    {"code": "071x", "category": "Ancillary Services", "description": "Occupational Therapy", "subcodes": [
        {"code": "0710", "description": "Occupational Therapy - General Classification"},
        {"code": "0711", "description": "Occupational Therapy - General"},
    ]},
    {"code": "073x", "category": "Ancillary Services", "description": "Speech Therapy", "subcodes": [
        {"code": "0730", "description": "Speech Therapy - General Classification"},
        {"code": "0731", "description": "Speech Therapy - General"},
    ]},
    {"code": "074x", "category": "Ancillary Services", "description": "Cardiac Rehabilitation", "subcodes": [
        {"code": "0740", "description": "Cardiac Rehabilitation - General Classification"},
        {"code": "0741", "description": "Cardiac Rehabilitation - General"},
    ]},
    {"code": "080x", "category": "Ancillary Services", "description": "Dialysis", "subcodes": [
        {"code": "0800", "description": "Dialysis - General Classification"},
        {"code": "0801", "description": "Dialysis - General"},
        {"code": "0802", "description": "Dialysis - Hemodialysis"},
        {"code": "0803", "description": "Dialysis - Peritoneal"},
    ]},
    {"code": "090x", "category": "Ancillary Services", "description": "Supplies", "subcodes": [
        {"code": "0900", "description": "Supplies - General Classification"},
        {"code": "0901", "description": "Supplies - General"},
        {"code": "0902", "description": "Supplies - DME"},
        {"code": "0903", "description": "Supplies - Prosthetics/Orthotics"},
    ]},
    {"code": "100x", "category": "Ancillary Services", "description": "Organ Acquisition", "subcodes": [
        {"code": "1000", "description": "Organ Acquisition - General Classification"},
        {"code": "1001", "description": "Organ Acquisition - General"},
        {"code": "1002", "description": "Organ Acquisition - Kidney"},
        {"code": "1003", "description": "Organ Acquisition - Liver"},
        {"code": "1004", "description": "Organ Acquisition - Heart"},
        {"code": "1005", "description": "Organ Acquisition - Bone Marrow"},
        {"code": "1006", "description": "Organ Acquisition - Pancreas"},
        {"code": "1007", "description": "Organ Acquisition - Lung"},
    ]},
    {"code": "250x", "category": "Pharmacy", "description": "Pharmacy - General", "subcodes": [
        {"code": "2500", "description": "Pharmacy - General Classification"},
        {"code": "2501", "description": "Pharmacy - General"},
    ]},
    {"code": "260x", "category": "Pharmacy", "description": "IV Therapy", "subcodes": [
        {"code": "2600", "description": "IV Therapy - General Classification"},
        {"code": "2601", "description": "IV Therapy - General"},
    ]},
    {"code": "270x", "category": "Pharmacy", "description": "Drugs Requiring Specific Identification", "subcodes": [
        {"code": "2700", "description": "Drugs - General Classification"},
        {"code": "2701", "description": "Drugs - General"},
        {"code": "2702", "description": "Drugs - Chemotherapy"},
        {"code": "2703", "description": "Drugs - Blood Products"},
        {"code": "2704", "description": "Drugs - Immunosuppressive"},
        {"code": "2705", "description": "Drugs - Investigational"},
    ]},
    {"code": "300x", "category": "Laboratory", "description": "Laboratory - Outpatient", "subcodes": [
        {"code": "3000", "description": "Laboratory - Outpatient General Classification"},
        {"code": "3001", "description": "Laboratory - Outpatient General"},
    ]},
    {"code": "350x", "category": "Radiology", "description": "Radiology - Outpatient", "subcodes": [
        {"code": "3500", "description": "Radiology - Outpatient General Classification"},
    ]},
    {"code": "360x", "category": "Operating Room", "description": "Operating Room - Outpatient", "subcodes": [
        {"code": "3600", "description": "Operating Room - Outpatient General Classification"},
    ]},
    {"code": "400x", "category": "Ambulatory Services", "description": "Ambulatory Surgical Center", "subcodes": [
        {"code": "4000", "description": "ASC - General Classification"},
        {"code": "4001", "description": "ASC - General"},
    ]},
    {"code": "450x", "category": "Emergency Room", "description": "Emergency Room - Outpatient", "subcodes": [
        {"code": "4500", "description": "Emergency Room - Outpatient General Classification"},
        {"code": "4501", "description": "Emergency Room - Outpatient General"},
        {"code": "4502", "description": "Emergency Room - Outpatient Level 1"},
        {"code": "4503", "description": "Emergency Room - Outpatient Level 2"},
        {"code": "4504", "description": "Emergency Room - Outpatient Level 3"},
        {"code": "4505", "description": "Emergency Room - Outpatient Level 4"},
        {"code": "4506", "description": "Emergency Room - Outpatient Level 5"},
    ]},
    {"code": "510x", "category": "Clinic", "description": "Clinic - General", "subcodes": [
        {"code": "5100", "description": "Clinic - General Classification"},
        {"code": "5101", "description": "Clinic - General"},
        {"code": "5102", "description": "Clinic - Surgical"},
        {"code": "5103", "description": "Clinic - Medical"},
        {"code": "5104", "description": "Clinic - OB/GYN"},
        {"code": "5105", "description": "Clinic - Pediatric"},
        {"code": "5106", "description": "Clinic - Psychiatric"},
        {"code": "5107", "description": "Clinic - Rehabilitation"},
    ]},
    {"code": "610x", "category": "Dialysis", "description": "Dialysis - Outpatient", "subcodes": [
        {"code": "6100", "description": "Dialysis - Outpatient General Classification"},
        {"code": "6101", "description": "Dialysis - Outpatient General"},
    ]},
    {"code": "730x", "category": "E-Visit", "description": "E-Visit / Telehealth", "subcodes": [
        {"code": "7300", "description": "E-Visit / Telehealth - General Classification"},
    ]},
    {"code": "761x", "category": "Observation", "description": "Observation Services", "subcodes": [
        {"code": "7610", "description": "Observation - General Classification"},
        {"code": "7611", "description": "Observation - General"},
    ]},
    {"code": "910x", "category": "Other", "description": "Other Charges", "subcodes": [
        {"code": "9100", "description": "Other - General Classification"},
    ]},
]


async def download(force: bool = False) -> dict:
    """Create revenue code descriptions."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    codes_json = DEST_DIR / "revenue_codes.json"
    if file_exists_and_recent(codes_json, force):
        logger.info("Revenue codes already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Creating revenue code descriptions...")

    # Flatten for the main JSON file
    flat_codes = []
    for group in REVENUE_CODES:
        flat_codes.append({
            "code": group["code"],
            "category": group["category"],
            "description": group["description"],
            "type": "category_header",
        })
        for sub in group.get("subcodes", []):
            flat_codes.append({
                "code": sub["code"],
                "category": group["category"],
                "description": sub["description"],
                "type": "specific_code",
            })

    save_json(flat_codes, codes_json)
    save_json(REVENUE_CODES, DEST_DIR / "revenue_codes_hierarchical.json")

    file_list = [codes_json.name, "revenue_codes_hierarchical.json"]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    total = len(flat_codes)
    return {
        "files_downloaded": 2,
        "message": f"Created {total} revenue code descriptions",
    }