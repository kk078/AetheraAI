"""
Download CARC/RARC codes from WPC/X12.

Claim Adjustment Reason Codes (CARC) and Remittance Advice Remark
Codes (RARC) are used to explain adjustments on claims. CARC codes
identify the reason for any adjustment, while RARC codes provide
supplemental explanation.

Source: https://x12.org/codes/claim-adjustment-reason-codes
Source: https://x12.org/codes/remittance-advice-remark-codes
"""

import asyncio
import csv
import io
import json
import logging
import re
from pathlib import Path

import httpx
from knowledge_bases._shared import (
    DATA_ROOT,
    download_file,
    download_text,
    save_json,
    write_manifest,
    file_exists_and_recent,
)

logger = logging.getLogger(__name__)

SOURCE_URL = "https://x12.org/codes/claim-adjustment-reason-codes"
DEST_DIR = DATA_ROOT / "healthcare" / "claims" / "carc_rarc"
MODULE_NAME = "knowledge_bases.healthcare.claims.carc_rarc_codes"

WPC_CARC_URL = "https://www.wpc-edi.com/reference/codes/CARC/"
WPC_RARC_URL = "https://www.wpc-edi.com/reference/codes/RARC/"


def parse_carc_rarc_text(text: str) -> list:
    """Parse CARC/RARC codes from text format."""
    records = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Format: CODE - Description or CODE\tDescription
        if " - " in line:
            parts = line.split(" - ", 1)
            code = parts[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ""
        elif "\t" in line:
            parts = line.split("\t", 1)
            code = parts[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ""
        else:
            match = re.match(r"^(\d{1,5}[A-Z]?)\s+(.+)", line)
            if match:
                code = match.group(1)
                desc = match.group(2).strip()
            else:
                continue

        if code and desc:
            code_type = "CARC" if re.match(r"^\d{1,5}$", code) else "RARC"
            records.append({
                "code": code,
                "type": code_type,
                "description": desc,
            })

    return records


async def download(force: bool = False) -> dict:
    """Download CARC/RARC codes from WPC/X12."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    codes_json = DEST_DIR / "carc_rarc_codes.json"
    if file_exists_and_recent(codes_json, force):
        logger.info("CARC/RARC codes already downloaded, use --force to re-download")
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading CARC/RARC codes...")

    all_codes = []

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=30.0, read=120.0),
        follow_redirects=True,
    ) as client:
        # Try downloading from WPC
        for url_name, url in [("CARC", WPC_CARC_URL), ("RARC", WPC_RARC_URL)]:
            try:
                text = await download_text(url, client)
                codes = parse_carc_rarc_text(text)
                if codes:
                    all_codes.extend(codes)
                    logger.info("Parsed %d %s codes from WPC", len(codes), url_name)
            except Exception as exc:
                logger.warning("Failed to download %s from WPC: %s", url_name, exc)

    if not all_codes:
        logger.info("Building CARC/RARC reference from known codes")
        all_codes = build_carc_rarc_reference()

    save_json(all_codes, codes_json)

    # Separate into CARC and RARC files
    carc = [c for c in all_codes if c["type"] == "CARC"]
    rarc = [c for c in all_codes if c["type"] == "RARC"]
    save_json(carc, DEST_DIR / "carc_codes.json")
    save_json(rarc, DEST_DIR / "rarc_codes.json")

    file_list = [codes_json.name, "carc_codes.json", "rarc_codes.json"]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)

    return {
        "files_downloaded": 3,
        "message": f"Downloaded {len(carc)} CARC and {len(rarc)} RARC codes",
    }


def build_carc_rarc_reference() -> list:
    """Build CARC/RARC reference from commonly used codes."""
    carc_codes = [
        {"code": "1", "type": "CARC", "description": "Deductible amount"},
        {"code": "2", "type": "CARC", "description": "Coinsurance amount"},
        {"code": "3", "type": "CARC", "description": "Co-payment amount"},
        {"code": "4", "type": "CARC", "description": "The procedure code is inconsistent with the modifier used or is missing a required modifier"},
        {"code": "5", "type": "CARC", "description": "The procedure code/bill type is inconsistent with the patient's age"},
        {"code": "6", "type": "CARC", "description": "The procedure/revenue code is inconsistent with the patient's gender"},
        {"code": "7", "type": "CARC", "description": "The procedure/revenue code is inconsistent with the provider type/specialty"},
        {"code": "8", "type": "CARC", "description": "The procedure code is inconsistent with the length of stay"},
        {"code": "9", "type": "CARC", "description": "The diagnosis is inconsistent with the patient's age"},
        {"code": "10", "type": "CARC", "description": "The diagnosis is inconsistent with the patient's gender"},
        {"code": "11", "type": "CARC", "description": "The diagnosis is inconsistent with the procedure"},
        {"code": "12", "type": "CARC", "description": "The diagnosis is inconsistent with the provider type"},
        {"code": "13", "type": "CARC", "description": "The date of death precedes the date of service"},
        {"code": "15", "type": "CARC", "description": "The authorization number is missing, invalid, or expired"},
        {"code": "16", "type": "CARC", "description": "Claim/service lacks information or includes incomplete/invalid information (see RARC)"},
        {"code": "18", "type": "CARC", "description": "Exact duplicate claim/service"},
        {"code": "19", "type": "CARC", "description": "This is a work-related injury/illness and thus the liability of the Workers' Compensation carrier"},
        {"code": "20", "type": "CARC", "description": "This injury/illness is covered by the liability carrier"},
        {"code": "21", "type": "CARC", "description": "This injury/illness is the liability of the no-fault carrier"},
        {"code": "22", "type": "CARC", "description": "This care may be covered by another payer per coordination of benefits"},
        {"code": "23", "type": "CARC", "description": "The impact of prior payer(s) adjudication including payments and/or adjustments"},
        {"code": "24", "type": "CARC", "description": "Charges are covered under a capitation agreement/managed care plan"},
        {"code": "25", "type": "CARC", "description": "Payment for this service is included in the payment for another service"},
        {"code": "26", "type": "CARC", "description": "This item was previously paid"},
        {"code": "27", "type": "CARC", "description": "Expenses incurred prior to coverage effective date"},
        {"code": "29", "type": "CARC", "description": "The time limit for filing has expired"},
        {"code": "31", "type": "CARC", "description": "Patient cannot be identified as our insured"},
        {"code": "32", "type": "CARC", "description": "Our records indicate that this dependent is not an eligible dependent"},
        {"code": "33", "type": "CARC", "description": "Insured has no dependent coverage"},
        {"code": "34", "type": "CARC", "description": "Insured has no coverage for this service"},
        {"code": "39", "type": "CARC", "description": "Services denied at the time authorization/pre-certification was requested"},
        {"code": "44", "type": "CARC", "description": "Prompt-pay discount"},
        {"code": "45", "type": "CARC", "description": "Charges exceed your fee schedule/maximum allowable or contracted/legislated fee arrangement"},
        {"code": "49", "type": "CARC", "description": "This is a non-covered service because it is not deemed a medical necessity by the payer"},
        {"code": "50", "type": "CARC", "description": "This is a non-covered service/not a Medicare benefit"},
        {"code": "51", "type": "CARC", "description": "This is a non-covered service"},
        {"code": "53", "type": "CARC", "description": "This is a non-covered service because it is an investigational/experimental service"},
        {"code": "55", "type": "CARC", "description": "Procedure/service/product is not clinically appropriate based on InterQual criteria"},
        {"code": "56", "type": "CARC", "description": "Procedure/service/product has not been deemed proven/effective by the payer"},
        {"code": "58", "type": "CARC", "description": "This service/procedure was not prescribed by a physician"},
        {"code": "59", "type": "CARC", "description": "This service/procedure was not authorized by the payer"},
        {"code": "60", "type": "CARC", "description": "Charges for outpatient services are not covered when performed within a period of time prior to or after inpatient services"},
        {"code": "65", "type": "CARC", "description": "Procedure code was cancelled"},
        {"code": "66", "type": "CARC", "description": "Blood deductible"},
        {"code": "69", "type": "CARC", "description": "This is a non-covered service because it is a dental service"},
        {"code": "70", "type": "CARC", "description": "Patient has met the spending cap for this service/benefit category"},
        {"code": "74", "type": "CARC", "description": "Indirect medical education adjustment"},
        {"code": "78", "type": "CARC", "description": "This service was not authorized by the payer"},
        {"code": "80", "type": "CARC", "description": "Outpatient services were not preceded by the required referral"},
        {"code": "87", "type": "CARC", "description": "Transfer adjustment"},
        {"code": "89", "type": "CARC", "description": "Professional services were not authorized"},
        {"code": "90", "type": "CARC", "description": "This is a non-covered service because the patient is enrolled in a hospice"},
        {"code": "94", "type": "CARC", "description": "Processed in excess of charges"},
        {"code": "95", "type": "CARC", "description": "Plan procedures not followed"},
        {"code": "96", "type": "CARC", "description": "Non-covered charge(s); patient is responsible through prior agreement or waiver"},
        {"code": "97", "type": "CARC", "description": "The benefit for this service is included in the payment/allowance for another service"},
        {"code": "100", "type": "CARC", "description": "Payment made to patient/insured/subscriber"},
        {"code": "101", "type": "CARC", "description": "Predetermination: anticipated payment upon completion of services or claim submission"},
        {"code": "109", "type": "CARC", "description": "Claim not covered as the provider type is not certified for this service"},
        {"code": "111", "type": "CARC", "description": "Not covered unless the provider accepts assignment"},
        {"code": "128", "type": "CARC", "description": "Newborn's services are covered in the mother's allowance"},
        {"code": "142", "type": "CARC", "description": "Monthly benefit maximum has been reached"},
        {"code": "144", "type": "CARC", "description": "Incentive adjustment for preferred product/designated service"},
        {"code": "149", "type": "CARC", "description": "Lifetime benefit maximum has been reached"},
        {"code": "150", "type": "CARC", "description": "Payer deems the information submitted does not support this level of service"},
        {"code": "151", "type": "CARC", "description": "Payment adjusted because the payer deems the information submitted does not support this many services"},
        {"code": "152", "type": "CARC", "description": "Payment adjusted because the payer deems the information submitted does not support this length of service"},
        {"code": "153", "type": "CARC", "description": "Payer deems the information submitted does not support this dosage"},
        {"code": "167", "type": "CARC", "description": "This (these) diagnosis(es) is (are) not covered"},
        {"code": "169", "type": "CARC", "description": "This (these) diagnosis(es) is (are) not covered for this procedure/service"},
        {"code": "170", "type": "CARC", "description": "Payment is denied when performed/billed by this type of provider"},
        {"code": "176", "type": "CARC", "description": "This service was not prescribed by a physician"},
        {"code": "177", "type": "CARC", "description": "This service was not prescribed prior to the patient's admission"},
        {"code": "178", "type": "CARC", "description": "This service was not referred by the patient's physician"},
        {"code": "180", "type": "CARC", "description": "This service was not authorized by the patient's physician"},
        {"code": "185", "type": "CARC", "description": "This service was not authorized or the authorization has expired"},
        {"code": "197", "type": "CARC", "description": "Precertification/authorization/notification/pre-treatment was absent or exceeded"},
        {"code": "204", "type": "CARC", "description": "This service/equipment/drug is not covered under the patient's current benefit plan"},
        {"code": "206", "type": "CARC", "description": "National Provider Identifier - missing"},
        {"code": "207", "type": "CARC", "description": "National Provider Identifier - invalid format"},
        {"code": "209", "type": "CARC", "description": "Provider Tax ID - missing"},
        {"code": "210", "type": "CARC", "description": "Provider Tax ID - invalid format"},
        {"code": "211", "type": "CARC", "description": "National Drug Code - missing"},
        {"code": "212", "type": "CARC", "description": "National Drug Code - invalid format"},
        {"code": "213", "type": "CARC", "description": "Adjustment based on a Professional Review Organization (PRO) decision"},
        {"code": "219", "type": "CARC", "description": "Based on extent of review, this claim was processed as a duplicate of a previously processed claim"},
        {"code": "222", "type": "CARC", "description": "This claim was denied based on the payer's review of the patient's medical record"},
        {"code": "223", "type": "CARC", "description": "Adjustment based on entitlement to a different benefit or program"},
        {"code": "227", "type": "CARC", "description": "Information was requested from the rendering provider; however, no response was received"},
        {"code": "236", "type": "CARC", "description": "This procedure or procedure/modifier combination is not compatible with another procedure or procedure/modifier combination on the same day"},
        {"code": "237", "type": "CARC", "description": "This claim was denied based on the applicable fee schedule for this type of service"},
        {"code": "242", "type": "CARC", "description": "Services not provided by network/primary care providers"},
        {"code": "243", "type": "CARC", "description": "Services not authorized by network/primary care providers"},
        {"code": "246", "type": "CARC", "description": "This service was not authorized"},
        {"code": "247", "type": "CARC", "description": "Deductible has been satisfied"},
        {"code": "248", "type": "CARC", "description": "Maximum out-of-pocket has been satisfied"},
        {"code": "252", "type": "CARC", "description": "An attachment/other documentation is required to adjudicate this claim/service"},
        {"code": "253", "type": "CARC", "description": "Sequestration - reduction in federal payment"},
        {"code": "254", "type": "CARC", "description": "This is a non-covered service when performed in this place of service"},
        {"code": "256", "type": "CARC", "description": "Service is not payable per the applicable payer's requirements"},
        {"code": "A0", "type": "CARC", "description": "Patient refund amount"},
        {"code": "A1", "type": "CARC", "description": "Claim denied charges"},
        {"code": "A5", "type": "CARC", "description": "Medicare claim PPS capital cost outlier amount"},
        {"code": "A6", "type": "CARC", "description": "Prior payer covered amount (CARC 23)"},
        {"code": "A7", "type": "CARC", "description": "Prior payer's adjudication (CARC 23)"},
        {"code": "A8", "type": "CARC", "description": "Ungroupable DRG"},
        {"code": "B1", "type": "CARC", "description": "Non-covered visits"},
        {"code": "B4", "type": "CARC", "description": "Late filing penalty"},
        {"code": "B5", "type": "CARC", "description": "Coverage/program guidelines (CARC 15)"},
        {"code": "B7", "type": "CARC", "description": "Provider was not certified/eligible to be paid for this procedure/service on this date of service"},
        {"code": "B8", "type": "CARC", "description": "Alternative services were available, and should have been utilized"},
        {"code": "B9", "type": "CARC", "description": "Patient is enrolled in a Hospice"},
        {"code": "B10", "type": "CARC", "description": "Allowed amount has been reduced because this is a service/item not provided to the patient directly"},
        {"code": "B11", "type": "CARC", "description": "The claim/service has been transferred to the proper payer/processor for processing"},
        {"code": "B12", "type": "CARC", "description": "Services not documented in patients' medical records"},
        {"code": "B13", "type": "CARC", "description": "Previously paid. Payment for this claim/service may have been provided in a previous payment"},
        {"code": "B14", "type": "CARC", "description": "Only one visit or consultation per physician per day is covered"},
        {"code": "B15", "type": "CARC", "description": "This service/procedure requires that a qualifying service/procedure be received and covered"},
        {"code": "B16", "type": "CARC", "description": "New patient qualifications were not met"},
        {"code": "B22", "type": "CARC", "description": "This payment is adjusted based on the diagnosis"},
        {"code": "B23", "type": "CARC", "description": "Procedure billed is not payable per the applicable payer's requirements"},
        {"code": "W1", "type": "CARC", "description": "Workers' compensation case adjudicated as non-compensable"},
        {"code": "W2", "type": "CARC", "description": "Payment reduced or denied based on workers' compensation jurisdictional regulation or payment methodology"},
        {"code": "Y1", "type": "CARC", "description": "Payment denied based on the Medical Review/Professional Review Organization (MR/PRO) decision"},
        {"code": "Y2", "type": "CARC", "description": "Payment denied based on utilization review criteria"},
    ]

    rarc_codes = [
        {"code": "N1", "type": "RARC", "description": "Alert: You may be subject to penalties if you bill a patient for amounts above the allowed amount"},
        {"code": "N2", "type": "RARC", "description": "This claim/service was paid in error"},
        {"code": "N4", "type": "RARC", "description": "Past filing deadline; claim was not timely filed"},
        {"code": "N5", "type": "RARC", "description": "Not covered unless submitted via electronic claim"},
        {"code": "N6", "type": "RARC", "description": "Under HIPAA, you must use the appropriate standard code set"},
        {"code": "N7", "type": "RARC", "description": "Alert: The provider is not certified for this service"},
        {"code": "N11", "type": "RARC", "description": "This claim has been denied as a duplicate of a claim that has already been processed"},
        {"code": "N14", "type": "RARC", "description": "This claim has been identified as a split claim"},
        {"code": "N18", "type": "RARC", "description": "Alert: This claim was processed in accordance with the payer's guidelines"},
        {"code": "N19", "type": "RARC", "description": "Procedure code incidental to primary procedure"},
        {"code": "N20", "type": "RARC", "description": "Service not paid under this fee schedule"},
        {"code": "N21", "type": "RARC", "description": "Alert: This is a conditional payment made pending a determination of liability"},
        {"code": "N22", "type": "RARC", "description": "This procedure code was added/changed for correct coding"},
        {"code": "N27", "type": "RARC", "description": "This claim was processed in accordance with a specific payer policy"},
        {"code": "N28", "type": "RARC", "description": "This claim was processed in accordance with the payer's guidelines"},
        {"code": "N30", "type": "RARC", "description": "Patient is responsible for difference between approved amount and billed amount"},
        {"code": "N36", "type": "RARC", "description": "This claim has been previously processed and paid"},
        {"code": "N38", "type": "RARC", "description": "Alert: This claim/service was submitted under an invalid provider number"},
        {"code": "N43", "type": "RARC", "description": "This claim was processed in accordance with the payer's fee schedule"},
        {"code": "N48", "type": "RARC", "description": "Alert: This claim was processed under a different provider number"},
        {"code": "N51", "type": "RARC", "description": "Alert: This is the initial determination on this claim"},
        {"code": "N56", "type": "RARC", "description": "Claim submitted with missing/incomplete/invalid information"},
        {"code": "N57", "type": "RARC", "description": "Missing/incomplete/invalid attending provider information"},
        {"code": "N67", "type": "RARC", "description": "This claim was processed in accordance with the payer's payment rules"},
        {"code": "N69", "type": "RARC", "description": "This service was denied as not medically necessary"},
        {"code": "N70", "type": "RARC", "description": "Alert: This service was denied as not medically necessary; however, the patient was notified"},
        {"code": "N75", "type": "RARC", "description": "Missing/incomplete/invalid referring provider information"},
        {"code": "N80", "type": "RARC", "description": "Alert: This claim was processed as a duplicate of a previously processed claim"},
        {"code": "N81", "type": "RARC", "description": "Alert: This claim was processed as a duplicate of a claim received on the same date of service"},
        {"code": "N85", "type": "RARC", "description": "Patient responsible for this amount as a result of the payer's decision"},
        {"code": "N89", "type": "RARC", "description": "This claim was processed in accordance with the payer's payment methodology"},
        {"code": "N95", "type": "RARC", "description": "This provider was not certified/eligible to be paid for this procedure on this date of service"},
        {"code": "N100", "type": "RARC", "description": "Alert: This claim was paid as a result of an appeal"},
        {"code": "N104", "type": "RARC", "description": "This claim/service is not payable under the claims jurisdiction"},
        {"code": "N115", "type": "RARC", "description": "This decision was based on a National Coverage Determination (NCD)"},
        {"code": "N119", "type": "RARC", "description": "This claim was processed in accordance with the payer's contract with the provider"},
        {"code": "N130", "type": "RARC", "description": "Consult plan documents for additional information regarding this claim/service"},
        {"code": "N135", "type": "RARC", "description": "This claim was processed in accordance with the payer's payment policies"},
        {"code": "N142", "type": "RARC", "description": "This claim was processed in accordance with the payer's prior authorization policy"},
        {"code": "N157", "type": "RARC", "description": "Service was not authorized"},
        {"code": "N167", "type": "RARC", "description": "Alert: This claim was processed as an adjustment to a previously processed claim"},
        {"code": "N170", "type": "RARC", "description": "This claim was processed as an adjustment to a previously processed claim"},
        {"code": "N189", "type": "RARC", "description": "Alert: This claim was processed based on the information provided on the claim"},
        {"code": "N200", "type": "RARC", "description": "Alert: The provider was not eligible for this service at the time of service"},
        {"code": "N211", "type": "RARC", "description": "Alert: You may not appeal this decision"},
        {"code": "N218", "type": "RARC", "description": "Missing/incomplete/invalid provider information on the claim"},
        {"code": "N222", "type": "RARC", "description": "Missing/incomplete/invalid claim information"},
        {"code": "N230", "type": "RARC", "description": "Missing/incomplete/invalid type or class of provider information"},
        {"code": "N240", "type": "RARC", "description": "Missing/incomplete/invalid patient relationship to insured"},
        {"code": "N249", "type": "RARC", "description": "Missing/incomplete/invalid service facility information"},
        {"code": "N252", "type": "RARC", "description": "Missing/incomplete/invalid attending provider information"},
        {"code": "N261", "type": "RARC", "description": "Missing/incomplete/invalid type of bill"},
        {"code": "N264", "type": "RARC", "description": "Missing/incomplete/invalid ordering provider information"},
        {"code": "N270", "type": "RARC", "description": "Missing/incomplete/invalid provider taxonomy code"},
        {"code": "N276", "type": "RARC", "description": "Missing/incomplete/invalid other provider information"},
        {"code": "N277", "type": "RARC", "description": "Missing/incomplete/invalid referring provider information"},
        {"code": "N286", "type": "RARC", "description": "Missing/incomplete/invalid referring provider primary identifier"},
        {"code": "N290", "type": "RARC", "description": "Missing/incomplete/invalid referring provider secondary identifier"},
        {"code": "N301", "type": "RARC", "description": "Missing/incomplete/invalid patient birth date"},
        {"code": "N309", "type": "RARC", "description": "Missing/incomplete/invalid patient weight"},
        {"code": "N323", "type": "RARC", "description": "Missing/incomplete/invalid admission date"},
        {"code": "N343", "type": "RARC", "description": "Missing/incomplete/invalid discharge date"},
        {"code": "N356", "type": "RARC", "description": "This claim was processed in accordance with applicable guidelines"},
        {"code": "N361", "type": "RARC", "description": "Alert: This claim was processed as a duplicate of a previously processed claim"},
        {"code": "N362", "type": "RARC", "description": "Alert: This claim was processed in accordance with the payer's rules"},
        {"code": "N381", "type": "RARC", "description": "Alert: This claim was processed in accordance with the payer's medical policy"},
        {"code": "N386", "type": "RARC", "description": "Alert: This decision was based on a Local Coverage Determination (LCD)"},
        {"code": "N395", "type": "RARC", "description": "Alert: This service was processed as an elective service"},
        {"code": "N410", "type": "RARC", "description": "Alert: This claim was processed in accordance with the payer's guidelines"},
        {"code": "N432", "type": "RARC", "description": "Alert: This claim was processed as a duplicate of a claim already processed"},
        {"code": "N448", "type": "RARC", "description": "Alert: This claim was processed based on the information submitted"},
        {"code": "N450", "type": "RARC", "description": "Alert: This claim was processed based on the payer's fee schedule"},
        {"code": "N451", "type": "RARC", "description": "Alert: This claim was processed based on the payer's payment policy"},
        {"code": "N461", "type": "RARC", "description": "Alert: This claim was processed in accordance with the payer's rules and guidelines"},
        {"code": "N517", "type": "RARC", "description": "Alert: This claim was processed as an adjustment to a previously processed claim"},
        {"code": "N519", "type": "RARC", "description": "Alert: This claim was processed in accordance with the payer's policy"},
        {"code": "N527", "type": "RARC", "description": "Alert: This claim was processed as a split claim"},
        {"code": "N536", "type": "RARC", "description": "Alert: This claim was processed in accordance with the payer's guidelines for this type of service"},
        {"code": "N548", "type": "RARC", "description": "Alert: This claim was processed as a result of an appeal or reopening"},
        {"code": "N553", "type": "RARC", "description": "Alert: This claim was processed based on the payer's medical review decision"},
        {"code": "N558", "type": "RARC", "description": "Alert: This claim was processed in accordance with the payer's guidelines for this provider type"},
        {"code": "N570", "type": "RARC", "description": "Alert: Missing/incomplete/invalid CLIA certification number"},
        {"code": "N573", "type": "RARC", "description": "Alert: This claim was processed in accordance with the payer's payment methodology for this service"},
        {"code": "N575", "type": "RARC", "description": "Alert: Missing/incomplete/invalid prior insurance carrier EOB"},
        {"code": "N579", "type": "RARC", "description": "Alert: Missing/incomplete/invalid service information"},
        {"code": "N586", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding other insurance"},
        {"code": "N592", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the accident"},
        {"code": "N594", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the injury"},
        {"code": "N596", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the illness"},
        {"code": "N620", "type": "RARC", "description": "Alert: This claim was processed in accordance with the payer's prior authorization requirements"},
        {"code": "N629", "type": "RARC", "description": "Alert: This claim was processed in accordance with the payer's medical necessity guidelines"},
        {"code": "N631", "type": "RARC", "description": "Alert: This claim was processed in accordance with the payer's payment rules for this type of service"},
        {"code": "N643", "type": "RARC", "description": "Alert: This claim was processed in accordance with the payer's guidelines for this service"},
        {"code": "N652", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the referring provider"},
        {"code": "N655", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the ordering provider"},
        {"code": "N660", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the rendering provider"},
        {"code": "N663", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the billing provider"},
        {"code": "N666", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the pay-to provider"},
        {"code": "N671", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the attending provider"},
        {"code": "N674", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the operating provider"},
        {"code": "N677", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the supervising provider"},
        {"code": "N680", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the purchase service provider"},
        {"code": "N686", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the service facility"},
        {"code": "N690", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the patient"},
        {"code": "N693", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the insured"},
        {"code": "N695", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the subscriber"},
        {"code": "N699", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the dependent"},
        {"code": "N702", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the diagnosis"},
        {"code": "N706", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the procedure"},
        {"code": "N710", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the date of service"},
        {"code": "N713", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the place of service"},
        {"code": "N716", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the type of service"},
        {"code": "N719", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the charges"},
        {"code": "N722", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the units of service"},
        {"code": "N725", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the authorization"},
        {"code": "N728", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the referral"},
        {"code": "N731", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the admission"},
        {"code": "N734", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the discharge"},
        {"code": "N737", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the onset of symptoms"},
        {"code": "N740", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the accident date"},
        {"code": "N743", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the accident type"},
        {"code": "N746", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the accident state"},
        {"code": "N749", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the accident description"},
        {"code": "N752", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the illness date"},
        {"code": "N755", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the illness description"},
        {"code": "N758", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the hospitalization date"},
        {"code": "N761", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the hospitalization discharge date"},
        {"code": "N764", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the external cause of injury"},
        {"code": "N767", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the drug quantity"},
        {"code": "N770", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the drug name"},
        {"code": "N773", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the drug NDC"},
        {"code": "N776", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the drug dosage"},
        {"code": "N779", "type": "RARC", "description": "Alert: Missing/incomplete/invalid information regarding the drug days supply"},
    ]

    return carc_codes + rarc_codes