"""
CPT category descriptions (public portions only).

CPT codes are copyrighted by the American Medical Association (AMA).
Full CPT code descriptions require a license from AMA. This module
creates a placeholder file with instructions on how to obtain licensed
CPT data, along with publicly available category-level descriptions.

Source: https://www.ama-assn.org/practice-management/cpt-codes
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT,
    save_json,
    write_placeholder,
    write_manifest,
    file_exists_and_recent,
)

logger = logging.getLogger(__name__)

SOURCE_URL = "https://www.ama-assn.org/practice-management/cpt-codes"
DEST_DIR = DATA_ROOT / "healthcare" / "coding" / "cpt"
MODULE_NAME = "knowledge_bases.healthcare.coding.cpt_descriptions"

# Publicly available CPT category structure
CPT_CATEGORIES = [
    {
        "range": "00100-01999",
        "category": "Anesthesia",
        "description": "Anesthesia services including general, regional, and local anesthesia administration",
    },
    {
        "range": "0200F-0620F",
        "category": "Category II - Performance Measurement",
        "description": "Supplemental tracking codes for performance measurement and quality reporting",
    },
    {
        "range": "0700T-0999T",
        "category": "Category III - Emerging Technology",
        "description": "Temporary codes for emerging technology, services, and procedures",
    },
    {
        "range": "10004-19499",
        "category": "Integumentary System",
        "description": "Procedures on the skin, subcutaneous tissue, and accessory structures",
    },
    {
        "range": "20005-22899",
        "category": "Musculoskeletal System",
        "description": "Procedures on the musculoskeletal system including bones, joints, and muscles",
    },
    {
        "range": "23000-23999",
        "category": "Musculoskeletal System - General",
        "description": "General musculoskeletal procedures",
    },
    {
        "range": "24000-29999",
        "category": "Musculoskeletal System - Extremities",
        "description": "Musculoskeletal procedures on extremities",
    },
    {
        "range": "30000-32999",
        "category": "Respiratory System",
        "description": "Procedures on the respiratory system",
    },
    {
        "range": "33000-37799",
        "category": "Cardiovascular System",
        "description": "Procedures on the cardiovascular system including heart and blood vessels",
    },
    {
        "range": "38000-38999",
        "category": "Hemic and Lymphatic Systems",
        "description": "Procedures on the hemic and lymphatic systems",
    },
    {
        "range": "39000-39599",
        "category": "Mediastinum and Diaphragm",
        "description": "Procedures on the mediastinum and diaphragm",
    },
    {
        "range": "40490-49999",
        "category": "Digestive System",
        "description": "Procedures on the digestive system including GI tract and accessory organs",
    },
    {
        "range": "50010-53899",
        "category": "Urinary System",
        "description": "Procedures on the urinary system",
    },
    {
        "range": "54000-58000",
        "category": "Male Reproductive System",
        "description": "Procedures on the male reproductive system",
    },
    {
        "range": "58100-60000",
        "category": "Female Reproductive System",
        "description": "Procedures on the female reproductive system",
    },
    {
        "range": "60000-60699",
        "category": "Endocrine System",
        "description": "Procedures on the endocrine system",
    },
    {
        "range": "61000-64999",
        "category": "Nervous System",
        "description": "Procedures on the nervous system including brain and spinal procedures",
    },
    {
        "range": "65000-69990",
        "category": "Eye and Ocular Adnexa",
        "description": "Procedures on the eye and ocular adnexa",
    },
    {
        "range": "69801-69999",
        "category": "Auditory System",
        "description": "Procedures on the auditory system",
    },
    {
        "range": "70000-79999",
        "category": "Radiology",
        "description": "Radiology procedures including diagnostic imaging and radiation therapy",
    },
    {
        "range": "80047-89398",
        "category": "Pathology and Laboratory",
        "description": "Pathology and laboratory procedures and tests",
    },
    {
        "range": "90281-99607",
        "category": "Medicine",
        "description": "Medicine services including immunizations, infusions, and psychiatric services",
    },
    {
        "range": "99202-99499",
        "category": "Evaluation and Management",
        "description": "Office and outpatient visits, consultations, hospital care, and other E/M services",
    },
    {
        "range": "99001-99607",
        "category": "Medicine - Special Services",
        "description": "Special medicine services and procedures",
    },
]

# CPT modifier reference (publicly available)
CPT_MODIFIERS = [
    {"modifier": "-22", "description": "Increased procedural services"},
    {"modifier": "-23", "description": "Unusual anesthesia"},
    {"modifier": "-25", "description": "Significant, separately identifiable evaluation and management service"},
    {"modifier": "-26", "description": "Professional component"},
    {"modifier": "-32", "description": "Services mandated by a third-party payer"},
    {"modifier": "-47", "description": "Anesthesia by surgeon"},
    {"modifier": "-50", "description": "Bilateral procedure"},
    {"modifier": "-51", "description": "Multiple procedures"},
    {"modifier": "-52", "description": "Reduced services"},
    {"modifier": "-53", "description": "Discontinued procedure"},
    {"modifier": "-54", "description": "Surgical care only"},
    {"modifier": "-55", "description": "Postoperative management only"},
    {"modifier": "-56", "description": "Preoperative management only"},
    {"modifier": "-57", "description": "Decision for surgery"},
    {"modifier": "-58", "description": "Staged or related procedure"},
    {"modifier": "-59", "description": "Distinct procedural service"},
    {"modifier": "-62", "description": "Two surgeons"},
    {"modifier": "-63", "description": "Procedure performed on infants less than 4 kg"},
    {"modifier": "-66", "description": "Surgical team"},
    {"modifier": "-76", "description": "Repeat procedure by same physician"},
    {"modifier": "-77", "description": "Repeat procedure by different physician"},
    {"modifier": "-78", "description": "Unplanned return to operating room"},
    {"modifier": "-79", "description": "Unrelated procedure during postoperative period"},
    {"modifier": "-80", "description": "Assistant surgeon"},
    {"modifier": "-81", "description": "Minimum assistant surgeon"},
    {"modifier": "-82", "description": "Assistant surgeon when qualified resident not available"},
    {"modifier": "-90", "description": "Reference (outside) laboratory"},
    {"modifier": "-91", "description": "Repeat clinical laboratory test"},
    {"modifier": "-92", "description": "Alternative laboratory platform testing"},
    {"modifier": "-95", "description": "Synchronous telemedicine service rendered via real-time interactive audio and video"},
    {"modifier": "-96", "description": "Non-urgent transport"},
    {"modifier": "-97", "description": "Rehabilitative services"},
    {"modifier": "-99", "description": "Multiple modifiers"},
]


async def download(force: bool = False) -> dict:
    """Create CPT category descriptions and licensed content placeholder."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    categories_json = DEST_DIR / "cpt_categories.json"
    modifiers_json = DEST_DIR / "cpt_modifiers.json"

    if file_exists_and_recent(categories_json, force):
        logger.info("CPT descriptions already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Creating CPT category descriptions and license placeholder...")

    # Save publicly available category structure
    save_json(CPT_CATEGORIES, categories_json)
    save_json(CPT_MODIFIERS, modifiers_json)

    # Create placeholder for licensed content
    write_placeholder(
        DEST_DIR,
        MODULE_NAME,
        "CPT Code Descriptions (Full)",
        (
            "Full CPT code descriptions are copyrighted by the American Medical Association (AMA). "
            "To obtain CPT data:\n"
            "1. Visit https://www.ama-assn.org/practice-management/cpt-codes\n"
            "2. Purchase a CPT license or subscription from AMA\n"
            "3. Download the CPT code file (typically in CSV or text format)\n"
            "4. Place the file in this directory as 'cpt_codes_full.csv'\n"
            "5. Re-run the download to generate structured JSON from the full data\n\n"
            "Alternative sources:\n"
            "- AMA CPT Net: https://cptnet.ama-assn.org/\n"
            "- CMS CPT files (limited): https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets\n"
            "- Your clearinghouse or EHR vendor may provide licensed CPT data"
        ),
        SOURCE_URL,
    )

    file_list = [categories_json.name, modifiers_json.name, "LICENSED_DATA_INSTRUCTIONS.json"]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": 3,
        "message": "Created CPT categories, modifiers, and licensed content placeholder",
    }