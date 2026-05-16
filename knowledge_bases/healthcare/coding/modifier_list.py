"""
CPT/HCPCS modifier descriptions.

Modifiers provide additional information about a service without
changing its definition. Used on both professional and institutional claims.
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

SOURCE_URL = "https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets"
DEST_DIR = DATA_ROOT / "healthcare" / "coding" / "modifiers"
MODULE_NAME = "knowledge_bases.healthcare.coding.modifier_list"

# Complete modifier list
MODIFIERS = [
    # CPT Modifiers
    {"code": "22", "type": "CPT", "description": "Increased procedural services", "usage": "When the service provided is substantially greater than usually required"},
    {"code": "23", "type": "CPT", "description": "Unusual anesthesia", "usage": "When a procedure that normally does not require anesthesia must be performed under anesthesia"},
    {"code": "25", "type": "CPT", "description": "Significant, separately identifiable evaluation and management service", "usage": "When a separate E/M service is provided on the same day as a procedure"},
    {"code": "26", "type": "CPT", "description": "Professional component", "usage": "When only the professional component of a service is provided"},
    {"code": "32", "type": "CPT", "description": "Services mandated by a third-party payer", "usage": "When a service is required by a third-party payer"},
    {"code": "47", "type": "CPT", "description": "Anesthesia by surgeon", "usage": "When the surgeon administers anesthesia"},
    {"code": "50", "type": "CPT", "description": "Bilateral procedure", "usage": "When a procedure is performed bilaterally"},
    {"code": "51", "type": "CPT", "description": "Multiple procedures", "usage": "When multiple procedures are performed at the same session"},
    {"code": "52", "type": "CPT", "description": "Reduced services", "usage": "When a service is partially reduced"},
    {"code": "53", "type": "CPT", "description": "Discontinued procedure", "usage": "When a procedure is discontinued"},
    {"code": "54", "type": "CPT", "description": "Surgical care only", "usage": "When only surgical care is provided"},
    {"code": "55", "type": "CPT", "description": "Postoperative management only", "usage": "When only postoperative management is provided"},
    {"code": "56", "type": "CPT", "description": "Preoperative management only", "usage": "When only preoperative management is provided"},
    {"code": "57", "type": "CPT", "description": "Decision for surgery", "usage": "When an E/M service results in the decision for surgery"},
    {"code": "58", "type": "CPT", "description": "Staged or related procedure by the same physician", "usage": "When a staged or related procedure is performed during the postoperative period"},
    {"code": "59", "type": "CPT", "description": "Distinct procedural service", "usage": "When a procedure is distinct from another service on the same day"},
    {"code": "62", "type": "CPT", "description": "Two surgeons", "usage": "When two surgeons work together as primary surgeons"},
    {"code": "63", "type": "CPT", "description": "Procedure performed on infants less than 4 kg", "usage": "When a procedure is performed on a small infant"},
    {"code": "66", "type": "CPT", "description": "Surgical team", "usage": "When a team of surgeons performs a complex procedure"},
    {"code": "73", "type": "CPT", "description": "Discontinued procedure - outpatient", "usage": "When an outpatient procedure is discontinued due to extenuating circumstances"},
    {"code": "74", "type": "CPT", "description": "Discontinued procedure - inpatient", "usage": "When an inpatient procedure is discontinued due to extenuating circumstances"},
    {"code": "76", "type": "CPT", "description": "Repeat procedure by same physician", "usage": "When the same physician repeats a procedure"},
    {"code": "77", "type": "CPT", "description": "Repeat procedure by different physician", "usage": "When a different physician repeats a procedure"},
    {"code": "78", "type": "CPT", "description": "Unplanned return to operating/procedure room", "usage": "When an unplanned return to the OR is related to the initial procedure"},
    {"code": "79", "type": "CPT", "description": "Unrelated procedure during postoperative period", "usage": "When an unrelated procedure is performed during the postoperative period"},
    {"code": "80", "type": "CPT", "description": "Assistant surgeon", "usage": "When an assistant surgeon provides assistance"},
    {"code": "81", "type": "CPT", "description": "Minimum assistant surgeon", "usage": "When a minimum assistant surgeon provides assistance"},
    {"code": "82", "type": "CPT", "description": "Assistant surgeon when qualified resident not available", "usage": "When an assistant surgeon is needed because no qualified resident is available"},
    {"code": "90", "type": "CPT", "description": "Reference (outside) laboratory", "usage": "When a laboratory service is performed by an outside lab"},
    {"code": "91", "type": "CPT", "description": "Repeat clinical laboratory test", "usage": "When a lab test is repeated for medical necessity"},
    {"code": "92", "type": "CPT", "description": "Alternative laboratory platform testing", "usage": "When testing is performed on an alternative platform"},
    {"code": "95", "type": "CPT", "description": "Synchronous telemedicine service", "usage": "When a service is provided via real-time audio/video"},
    {"code": "96", "type": "CPT", "description": "Non-urgent transport", "usage": "For non-emergency medical transportation"},
    {"code": "97", "type": "CPT", "description": "Rehabilitative services", "usage": "For rehabilitative therapy services"},
    {"code": "99", "type": "CPT", "description": "Multiple modifiers", "usage": "When two or more modifiers apply"},
    # HCPCS Level II Modifiers
    {"code": "1P", "type": "HCPCS", "description": "Performance measure exclusion - patient", "usage": "When a patient reason prevents performance measure compliance"},
    {"code": "2P", "type": "HCPCS", "description": "Performance measure exclusion - provider", "usage": "When a provider reason prevents performance measure compliance"},
    {"code": "3P", "type": "HCPCS", "description": "Performance measure exclusion - system", "usage": "When a system reason prevents performance measure compliance"},
    {"code": "8P", "type": "HCPCS", "description": "Performance measure exclusion - other", "usage": "When performance measure action was not performed"},
    {"code": "GA", "type": "HCPCS", "description": "Waiver of liability statement issued", "usage": "When an ABN/Waiver of Liability is on file"},
    {"code": "GB", "type": "HCPCS", "description": "Claim being re-submitted", "usage": "When a claim is being re-submitted with an ABN"},
    {"code": "GC", "type": "HCPCS", "description": "Teaching physician service", "usage": "When a teaching physician is involved"},
    {"code": "GD", "type": "HCPCS", "description": "Service performed by resident without teaching physician", "usage": "When a resident performs a service without a teaching physician present"},
    {"code": "GE", "type": "HCPCS", "description": "Service performed by resident under teaching physician", "usage": "When a resident performs a service under teaching physician supervision"},
    {"code": "GF", "type": "HCPCS", "description": "Service performed by resident without teaching physician - non-physician", "usage": "Similar to GD for non-physician providers"},
    {"code": "GG", "type": "HCPCS", "description": "Functional limitation reporting", "usage": "When functional limitation reporting is applicable"},
    {"code": "GH", "type": "HCPCS", "description": "Service provided by a home health aide", "usage": "When a home health aide provides the service"},
    {"code": "GJ", "type": "HCPCS", "description": "Opt out physician or practitioner emergency or urgent", "usage": "When an opt-out provider renders emergency services"},
    {"code": "GK", "type": "HCPCS", "description": "Reasonable and necessary - not covered by Medicare", "usage": "When a service is reasonable and necessary but not covered"},
    {"code": "GL", "type": "HCPCS", "description": "Services provided under a clinical trial", "usage": "When a service is part of a clinical trial"},
    {"code": "GM", "type": "HCPCS", "description": "Service performed by a resident without teaching physician", "usage": "When a resident performs without teaching physician present"},
    {"code": "GN", "type": "HCPCS", "description": "Services delivered under a plan of care", "usage": "When services are delivered under an established plan of care"},
    {"code": "GO", "type": "HCPCS", "description": "Service delivered in an outpatient setting", "usage": "When a service is provided in an outpatient setting"},
    {"code": "GP", "type": "HCPCS", "description": "Service delivered by a physical therapist", "usage": "When a PT delivers the service"},
    {"code": "GQ", "type": "HCPCS", "description": "Service delivered via telecommunication", "usage": "When a service is delivered via telecommunications"},
    {"code": "GR", "type": "HCPCS", "description": "Service delivered in a rural area", "usage": "When a service is delivered in a rural health setting"},
    {"code": "GS", "type": "HCPCS", "description": "Service performed by a certified nurse midwife", "usage": "When a CNM performs the service"},
    {"code": "GT", "type": "HCPCS", "description": "Telehealth service delivered via interactive audio/video", "usage": "When telehealth is delivered via interactive audio and video"},
    {"code": "GU", "type": "HCPCS", "description": "Service performed by a certified registered nurse anesthetist", "usage": "When a CRNA performs the service"},
    {"code": "GV", "type": "HCPCS", "description": "Service performed by a physician who does not accept assignment", "usage": "When a non-participating physician performs the service"},
    {"code": "GW", "type": "HCPCS", "description": "Service not related to terminal illness", "usage": "When a hospice service is not related to the terminal illness"},
    {"code": "GX", "type": "HCPCS", "description": "Service not covered by Medicare - patient notified", "usage": "When a non-covered service is provided and patient is notified"},
    {"code": "GY", "type": "HCPCS", "description": "Service not covered by Medicare", "usage": "When a service is not a Medicare benefit"},
    {"code": "GZ", "type": "HCPCS", "description": "Service not reasonable and necessary", "usage": "When a service is not reasonable and necessary"},
    {"code": "KX", "type": "HCPCS", "description": "Requirements specified in policy met", "usage": "When coverage requirements are met"},
    {"code": "KS", "type": "HCPCS", "description": "Service performed by a licensed social worker", "usage": "When an LSW performs the service"},
    {"code": "KY", "type": "HCPCS", "description": "Service performed by a licensed psychologist", "usage": "When a licensed psychologist performs the service"},
    {"code": "LB", "type": "HCPCS", "description": "Service performed by a licensed baccalaureate social worker", "usage": "When an LBSW performs the service"},
    {"code": "LC", "type": "HCPCS", "description": "Left circumflex coronary artery", "usage": "Anatomical modifier for cardiac procedures"},
    {"code": "LD", "type": "HCPCS", "description": "Left anterior descending coronary artery", "usage": "Anatomical modifier for cardiac procedures"},
    {"code": "LT", "type": "HCPCS", "description": "Left side", "usage": "When a procedure is performed on the left side"},
    {"code": "RC", "type": "HCPCS", "description": "Right coronary artery", "usage": "Anatomical modifier for cardiac procedures"},
    {"code": "RI", "type": "HCPCS", "description": "Ramus intermedius coronary artery", "usage": "Anatomical modifier for cardiac procedures"},
    {"code": "RT", "type": "HCPCS", "description": "Right side", "usage": "When a procedure is performed on the right side"},
    {"code": "SA", "type": "HCPCS", "description": "Service performed by a nurse practitioner", "usage": "When an NP performs the service"},
    {"code": "SB", "type": "HCPCS", "description": "Service performed by a clinical nurse specialist", "usage": "When a CNS performs the service"},
    {"code": "SC", "type": "HCPCS", "description": "Service performed by a certified nurse midwife", "usage": "When a CNM performs the service"},
    {"code": "SD", "type": "HCPCS", "description": "Service performed by a certified registered nurse anesthetist", "usage": "When a CRNA performs the service"},
    {"code": "SG", "type": "HCPCS", "description": "Ambulatory surgical center", "usage": "When an ASC facility service is billed"},
    {"code": "SH", "type": "HCPCS", "description": "Service performed by a certified nurse practitioner", "usage": "When a CNP performs the service"},
    {"code": "SK", "type": "HCPCS", "description": "Service performed by a certified clinical nurse specialist", "usage": "When a CCNS performs the service"},
    {"code": "SL", "type": "HCPCS", "description": "State lymphedema program", "usage": "When service is under a state lymphedema program"},
    {"code": "SN", "type": "HCPCS", "description": "Service performed by a certified nurse midwife", "usage": "When a CNM performs the service under state program"},
    {"code": "SQ", "type": "HCPCS", "description": "Service performed in a sub-provider", "usage": "When a sub-provider performs the service"},
    {"code": "SS", "type": "HCPCS", "description": "Service performed by a certified nurse practitioner", "usage": "When a CNP performs the service"},
    {"code": "TC", "type": "HCPCS", "description": "Technical component", "usage": "When only the technical component is provided"},
    {"code": "TQ", "type": "HCPCS", "description": "Service performed by a licensed clinical social worker", "usage": "When an LCSW performs the service"},
    {"code": "U1", "type": "HCPCS", "description": "Medicare mandated demonstration project", "usage": "For Medicare demonstration project services"},
    {"code": "U2", "type": "HCPCS", "description": "Medicare mandated demonstration project", "usage": "For Medicare demonstration project services"},
    {"code": "U3", "type": "HCPCS", "description": "Medicare mandated demonstration project", "usage": "For Medicare demonstration project services"},
    {"code": "XE", "type": "HCPCS", "description": "Separate encounter", "usage": "When a service is distinct because it occurred in a separate encounter"},
    {"code": "XS", "type": "HCPCS", "description": "Separate structure", "usage": "When a service is distinct because it was performed on a separate organ/structure"},
    {"code": "XP", "type": "HCPCS", "description": "Separate practitioner", "usage": "When a service is distinct because it was performed by a different practitioner"},
    {"code": "XU", "type": "HCPCS", "description": "Unusual non-overlapping service", "usage": "When a service is distinct because it does not overlap usual components"},
    {"code": "XA", "type": "HCPCS", "description": "Separate encounter", "usage": "Alternate modifier for separate encounter"},
    {"code": "XB", "type": "HCPCS", "description": "Separate structure", "usage": "Alternate modifier for separate organ/structure"},
    {"code": "XC", "type": "HCPCS", "description": "Separate practitioner", "usage": "Alternate modifier for separate practitioner"},
    {"code": "XD", "type": "HCPCS", "description": "Unusual non-overlapping service", "usage": "Alternate modifier for unusual non-overlapping service"},
]


async def download(force: bool = False) -> dict:
    """Create modifier descriptions."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    codes_json = DEST_DIR / "modifier_list.json"
    if file_exists_and_recent(codes_json, force):
        logger.info("Modifiers already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Creating CPT/HCPCS modifier descriptions...")

    save_json(MODIFIERS, codes_json)

    # Separate by type for easier lookup
    cpt_mods = [m for m in MODIFIERS if m["type"] == "CPT"]
    hcpcs_mods = [m for m in MODIFIERS if m["type"] == "HCPCS"]
    save_json(cpt_mods, DEST_DIR / "cpt_modifiers.json")
    save_json(hcpcs_mods, DEST_DIR / "hcpcs_modifiers.json")

    file_list = [codes_json.name, "cpt_modifiers.json", "hcpcs_modifiers.json"]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": 3,
        "message": f"Created {len(MODIFIERS)} modifier descriptions",
    }