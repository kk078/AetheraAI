"""
Place of Service (POS) code list from CMS.

POS codes identify where services were rendered. Used on both
professional (CMS-1500) and institutional (UB-04) claims.

Source: https://www.cms.gov/Medicare/Coding/Place-of-Service-Codes/Place-of-Service-Code-Set
"""

import asyncio
import logging
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT,
    download_file,
    save_json,
    write_manifest,
    file_exists_and_recent,
)

logger = logging.getLogger(__name__)

SOURCE_URL = "https://www.cms.gov/Medicare/Coding/Place-of-Service-Codes/Place-of-Service-Code-Set"
DEST_DIR = DATA_ROOT / "healthcare" / "coding" / "place_of_service"
MODULE_NAME = "knowledge_bases.healthcare.coding.place_of_service"

# Complete POS code list per CMS
POS_CODES = [
    {"code": "01", "description": "Pharmacy", "effective": "A facility where pharmacists provide medication and pharmacy services.", "status": "active"},
    {"code": "02", "description": "Telehealth", "effective": "The location where health services and care related to the diagnosis and treatment are provided via telecommunication systems.", "status": "active"},
    {"code": "03", "description": "School", "effective": "A facility whose primary purpose is education.", "status": "active"},
    {"code": "04", "description": "Homeless Shelter", "effective": "A facility or location whose primary purpose is to provide temporary housing.", "status": "active"},
    {"code": "05", "description": "Indian Health Service Facility", "effective": "A facility under the Indian Health Service program.", "status": "active"},
    {"code": "06", "description": "Indian Health Service Tribal Facility", "effective": "A tribal facility under the Indian Health Service program.", "status": "active"},
    {"code": "07", "description": "Tribal 638 Facility", "effective": "A tribal facility contracted under the Indian Self-Determination Act.", "status": "active"},
    {"code": "08", "description": "Patient Home", "effective": "Location, other than a hospital or other facility, where the patient receives care.", "status": "active"},
    {"code": "09", "description": "Prison/Correctional Facility", "effective": "A prison, jail, reformatory, or other correctional facility.", "status": "active"},
    {"code": "10", "description": "Unassigned", "effective": "Not assigned.", "status": "inactive"},
    {"code": "11", "description": "Office", "effective": "Location, other than a hospital, skilled nursing facility (SNF), military treatment facility, community health center, State or local public health clinic, or intermediate care facility (ICF), where the health professional routinely provides health examinations, diagnosis, and treatment of illness or injury on an ambulatory basis.", "status": "active"},
    {"code": "12", "description": "Patient Home", "effective": "Location, other than a hospital or other facility, where the patient receives care in a private residence.", "status": "active"},
    {"code": "13", "description": "Assisted Living Facility", "effective": "A facility providing supportive living arrangements.", "status": "active"},
    {"code": "14", "description": "Group Home", "effective": "A residence that provides room, board, and other personal care services.", "status": "active"},
    {"code": "15", "description": "Mobile Unit", "effective": "A facility or location that operates a mobile unit.", "status": "active"},
    {"code": "16", "description": "Temporary Lodging", "effective": "A short-term lodging facility.", "status": "active"},
    {"code": "17", "description": "Walk-in Retail Health Clinic", "effective": "A walk-in retail health clinic.", "status": "active"},
    {"code": "18", "description": "Place of Employment/Worksite", "effective": "A location at a worksite where health services are provided.", "status": "active"},
    {"code": "19", "description": "Off Campus-Outpatient Hospital", "effective": "A portion of an off-campus hospital provider which provides diagnostic, therapeutic, and other outpatient services.", "status": "active"},
    {"code": "20", "description": "Urgent Care Facility", "effective": "A location providing urgent care services.", "status": "active"},
    {"code": "21", "description": "Inpatient Hospital", "effective": "A facility, other than psychiatric, which primarily provides diagnostic, therapeutic, and rehabilitation services by or under the supervision of physicians.", "status": "active"},
    {"code": "22", "description": "On Campus-Outpatient Hospital", "effective": "A portion of a hospital's main campus which provides diagnostic, therapeutic, and other outpatient services.", "status": "active"},
    {"code": "23", "description": "Emergency Room - Hospital", "effective": "A portion of a hospital where emergency services are provided.", "status": "active"},
    {"code": "24", "description": "Ambulatory Surgical Center", "effective": "A freestanding facility, other than a physician's office, where surgical and diagnostic services are provided on an ambulatory basis.", "status": "active"},
    {"code": "25", "description": "Birthing Center", "effective": "A facility, other than a hospital's maternity facilities or a physician's office, which provides a setting for labor, delivery, and immediate postpartum care.", "status": "active"},
    {"code": "26", "description": "Military Treatment Facility", "effective": "A medical facility operated by the Department of Defense or Veterans Affairs.", "status": "active"},
    {"code": "27", "description": "Outreach Site/Street", "effective": "A location providing services in a non-permanent structure.", "status": "active"},
    {"code": "28", "description": "State or Local Public Health Clinic", "effective": "A facility maintained by state or local government.", "status": "active"},
    {"code": "29", "description": "Intermediate Care Facility/Mentally Retarded", "effective": "A facility providing intermediate-level care for the developmentally disabled.", "status": "active"},
    {"code": "30", "description": "Intermediate Care Facility/Mentally Retarded", "effective": "See code 29.", "status": "inactive"},
    {"code": "31", "description": "Skilled Nursing Facility", "effective": "A facility which primarily provides inpatient skilled nursing care and related services.", "status": "active"},
    {"code": "32", "description": "Nursing Facility", "effective": "A facility which primarily provides nursing and related services.", "status": "active"},
    {"code": "33", "description": "Custodial Care Facility", "effective": "A facility which provides room, board, and other personal assistance services.", "status": "active"},
    {"code": "34", "description": "Hospice", "effective": "A facility, other than a patient's home, where hospice care is provided.", "status": "active"},
    {"code": "35", "description": "Ambulance - Land", "effective": "A land ambulance provider.", "status": "active"},
    {"code": "36", "description": "Ambulance - Air or Water", "effective": "An air or water ambulance provider.", "status": "active"},
    {"code": "37", "description": "Ambulance - Air", "effective": "An air ambulance provider.", "status": "active"},
    {"code": "38", "description": "Ambulance - Water", "effective": "A water ambulance provider.", "status": "active"},
    {"code": "39", "description": "Ambulance - Land and Water", "effective": "A land and water ambulance provider.", "status": "active"},
    {"code": "40", "description": "Ambulance - Air and Water", "effective": "An air and water ambulance provider.", "status": "active"},
    {"code": "41", "description": "Ambulance - Land, Air, and Water", "effective": "A land, air, and water ambulance provider.", "status": "active"},
    {"code": "42", "description": "Ambulance - Land and Air", "effective": "A land and air ambulance provider.", "status": "active"},
    {"code": "49", "description": "Independent Clinic", "effective": "A facility operated by a physician or group of physicians.", "status": "active"},
    {"code": "50", "description": "Federally Qualified Health Center", "effective": "A facility receiving funds under the Section 330 program.", "status": "active"},
    {"code": "51", "description": "Inpatient Psychiatric Facility", "effective": "A facility providing inpatient psychiatric services.", "status": "active"},
    {"code": "52", "description": "Psychiatric Facility - Partial Hospitalization", "effective": "A facility providing partial hospitalization psychiatric services.", "status": "active"},
    {"code": "53", "description": "Community Mental Health Center", "effective": "A facility providing community mental health services.", "status": "active"},
    {"code": "54", "description": "Intermediate Care Facility/Mentally Retarded", "effective": "See code 29.", "status": "inactive"},
    {"code": "55", "description": "Residential Substance Abuse Treatment Facility", "effective": "A facility providing residential substance abuse treatment.", "status": "active"},
    {"code": "56", "description": "Psychiatric Residential Treatment Center", "effective": "A psychiatric residential treatment center for children and adolescents.", "status": "active"},
    {"code": "57", "description": "Non-Residential Substance Abuse Treatment Facility", "effective": "A non-residential substance abuse treatment facility.", "status": "active"},
    {"code": "60", "description": "Mass Immunization Center", "effective": "A location where mass immunizations are provided.", "status": "active"},
    {"code": "61", "description": "Comprehensive Inpatient Rehabilitation Facility", "effective": "A facility providing comprehensive inpatient rehabilitation.", "status": "active"},
    {"code": "62", "description": "Comprehensive Outpatient Rehabilitation Facility", "effective": "A facility providing comprehensive outpatient rehabilitation.", "status": "active"},
    {"code": "63", "description": "End-Stage Renal Disease Treatment Facility", "effective": "A facility providing ESRD treatment.", "status": "active"},
    {"code": "64", "description": "End-Stage Renal Disease Treatment Facility - Independent", "effective": "An independent ESRD treatment facility.", "status": "active"},
    {"code": "65", "description": "End-Stage Renal Disease Treatment Facility - Hospital-Based", "effective": "A hospital-based ESRD treatment facility.", "status": "active"},
    {"code": "66", "description": "End-Stage Renal Disease Treatment Facility - Home", "effective": "An ESRD treatment provided in the patient's home.", "status": "active"},
    {"code": "67", "description": "End-Stage Renal Disease Treatment Facility - Dialysis", "effective": "A dialysis facility for ESRD patients.", "status": "active"},
    {"code": "71", "description": "State or Local Public Health Clinic", "effective": "See code 28.", "status": "active"},
    {"code": "72", "description": "Rural Health Clinic", "effective": "A certified rural health clinic.", "status": "active"},
    {"code": "81", "description": "Independent Laboratory", "effective": "A laboratory independent of a hospital or physician office.", "status": "active"},
    {"code": "95", "description": "Telehealth (Non-Patient Home)", "effective": "The location where health services are provided through telecommunication technology.", "status": "active"},
    {"code": "96", "description": "Pharmacy", "effective": "See code 01.", "status": "inactive"},
    {"code": "97", "description": "Pharmacy", "effective": "See code 01.", "status": "inactive"},
    {"code": "98", "description": "Pharmacy", "effective": "See code 01.", "status": "inactive"},
    {"code": "99", "description": "Other Unlisted Facility", "effective": "Other place of service not listed above.", "status": "active"},
]


async def download(force: bool = False) -> dict:
    """Download Place of Service codes."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    codes_json = DEST_DIR / "pos_codes.json"
    if file_exists_and_recent(codes_json, force):
        logger.info("POS codes already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading Place of Service codes from CMS...")

    # Try to download the latest POS code file from CMS
    pos_csv_url = "https://www.cms.gov/Medicare/Coding/Place-of-Service-Codes/Downloads/POS-Code-List.xlsx"
    downloaded_from_cms = False

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=30.0, read=120.0),
        follow_redirects=True,
    ) as client:
        try:
            xlsx_path = DEST_DIR / "pos_codes_download.xlsx"
            await download_file(pos_csv_url, xlsx_path, client)
            downloaded_from_cms = True
            logger.info("Downloaded POS codes from CMS")
        except Exception as exc:
            logger.warning("Could not download POS codes from CMS: %s", exc)

    # Save the comprehensive built-in list
    active_codes = [c for c in POS_CODES if c["status"] == "active"]
    save_json(POS_CODES, codes_json)
    save_json(active_codes, DEST_DIR / "pos_codes_active.json")

    file_list = [codes_json.name, "pos_codes_active.json"]
    if downloaded_from_cms:
        file_list.append("pos_codes_download.xlsx")
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": len(file_list),
        "message": f"Downloaded {len(POS_CODES)} POS codes ({len(active_codes)} active)",
    }