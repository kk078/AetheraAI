"""
Aethera AI - Fee Schedule Skill

Medicare/Medicaid fee schedule lookup. Contains MPFS RVU data for
common CPT codes, GPCI examples, and conversion factor. Calculates
allowed amount from RVUs * GPCI * CF and compares fees across localities.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="fee_schedule", category="healthcare")
class FeeScheduleSkill(AetheraSkill):
    """
    Medicare Physician Fee Schedule lookup and calculation.
    """

    @property
    def name(self) -> str:
        return "fee_schedule"

    @property
    def description(self) -> str:
        return "Look up Medicare fee schedule RVUs, calculate allowed amounts by locality, compare fees across localities"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["lookup", "calculate", "compare_localities"],
                    "description": "Action: lookup (get RVU data), calculate (compute allowed amount), compare_localities (compare fees across areas)"
                },
                "cpt_code": {
                    "type": "string",
                    "description": "CPT/HCPCS code to look up"
                },
                "locality": {
                    "type": "string",
                    "description": "CMS locality code or name (e.g., '01010', 'Florida', 'New York'). For compare, provide comma-separated list."
                },
                "modifier": {
                    "type": "string",
                    "description": "Modifier that may affect reimbursement (e.g., 26, TC, 50)"
                },
                "multiple_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Multiple CPT codes to look up at once"
                }
            },
            "required": ["action"]
        }

    @property
    def requires_phi_protection(self) -> bool:
        return False

    @property
    def examples(self) -> list:
        return [
            {"input": {"action": "lookup", "cpt_code": "99213"}},
            {"input": {"action": "calculate", "cpt_code": "99213", "locality": "01010"}},
            {"input": {"action": "compare_localities", "cpt_code": "99213", "locality": "01010,09006,11006"}}
        ]

    # --- Medicare conversion factor (2024 approximate) ---
    CONVERSION_FACTOR = 33.2875

    # --- MPFS RVU data for common CPT codes ---
    # work_rvu, pe_rvu (non-facility), mp_rvu (non-facility)
    RVU_DATA: Dict[str, Dict[str, Any]] = {
        # Evaluation and Management
        "99211": {"work_rvu": 0.18, "pe_rvu_nf": 0.98, "mp_rvu_nf": 0.08, "status": "A", "description": "Office visit, established, may not require physician presence"},
        "99212": {"work_rvu": 0.48, "pe_rvu_nf": 1.10, "mp_rvu_nf": 0.10, "status": "A", "description": "Office visit, established, straightforward"},
        "99213": {"work_rvu": 0.97, "pe_rvu_nf": 1.55, "mp_rvu_nf": 0.12, "status": "A", "description": "Office visit, established, low complexity"},
        "99214": {"work_rvu": 1.50, "pe_rvu_nf": 2.05, "mp_rvu_nf": 0.14, "status": "A", "description": "Office visit, established, moderate complexity"},
        "99215": {"work_rvu": 2.11, "pe_rvu_nf": 2.68, "mp_rvu_nf": 0.16, "status": "A", "description": "Office visit, established, high complexity"},
        "99281": {"work_rvu": 0.60, "pe_rvu_nf": 1.42, "mp_rvu_nf": 0.10, "status": "A", "description": "ED visit, self-limited problem"},
        "99282": {"work_rvu": 1.02, "pe_rvu_nf": 1.88, "mp_rvu_nf": 0.12, "status": "A", "description": "ED visit, low complexity"},
        "99283": {"work_rvu": 1.60, "pe_rvu_nf": 2.54, "mp_rvu_nf": 0.14, "status": "A", "description": "ED visit, moderate complexity"},
        "99284": {"work_rvu": 2.66, "pe_rvu_nf": 3.58, "mp_rvu_nf": 0.18, "status": "A", "description": "ED visit, high complexity"},
        "99285": {"work_rvu": 3.99, "pe_rvu_nf": 4.72, "mp_rvu_nf": 0.22, "status": "A", "description": "ED visit, very high complexity"},
        "99291": {"work_rvu": 4.50, "pe_rvu_nf": 5.16, "mp_rvu_nf": 0.28, "status": "A", "description": "Critical care, first hour"},
        # Inpatient E/M
        "99221": {"work_rvu": 1.30, "pe_rvu_nf": 1.80, "mp_rvu_nf": 0.10, "status": "A", "description": "Initial hospital care, low complexity"},
        "99222": {"work_rvu": 2.10, "pe_rvu_nf": 2.50, "mp_rvu_nf": 0.12, "status": "A", "description": "Initial hospital care, moderate complexity"},
        "99223": {"work_rvu": 3.20, "pe_rvu_nf": 3.30, "mp_rvu_nf": 0.16, "status": "A", "description": "Initial hospital care, high complexity"},
        "99231": {"work_rvu": 0.75, "pe_rvu_nf": 1.20, "mp_rvu_nf": 0.08, "status": "A", "description": "Subsequent hospital care, low complexity"},
        "99232": {"work_rvu": 1.39, "pe_rvu_nf": 1.80, "mp_rvu_nf": 0.10, "status": "A", "description": "Subsequent hospital care, moderate complexity"},
        "99233": {"work_rvu": 2.10, "pe_rvu_nf": 2.40, "mp_rvu_nf": 0.12, "status": "A", "description": "Subsequent hospital care, high complexity"},
        # Lab
        "80053": {"work_rvu": 0.00, "pe_rvu_nf": 1.35, "mp_rvu_nf": 0.52, "status": "A", "description": "Comprehensive metabolic panel"},
        "80061": {"work_rvu": 0.00, "pe_rvu_nf": 1.15, "mp_rvu_nf": 0.42, "status": "A", "description": "Lipid panel"},
        "83036": {"work_rvu": 0.00, "pe_rvu_nf": 0.75, "mp_rvu_nf": 0.32, "status": "A", "description": "Hemoglobin A1C"},
        "84443": {"work_rvu": 0.00, "pe_rvu_nf": 0.60, "mp_rvu_nf": 0.28, "status": "A", "description": "Thyroid stimulating hormone (TSH)"},
        "85025": {"work_rvu": 0.00, "pe_rvu_nf": 0.62, "mp_rvu_nf": 0.25, "status": "A", "description": "CBC with differential"},
        "86580": {"work_rvu": 0.00, "pe_rvu_nf": 0.42, "mp_rvu_nf": 0.18, "status": "A", "description": "TB skin test"},
        # Radiology
        "71045": {"work_rvu": 0.18, "pe_rvu_nf": 1.25, "mp_rvu_nf": 0.42, "status": "A", "description": "Chest X-ray, 1 view"},
        "71046": {"work_rvu": 0.25, "pe_rvu_nf": 1.55, "mp_rvu_nf": 0.52, "status": "A", "description": "Chest X-ray, 2 views"},
        "70553": {"work_rvu": 1.50, "pe_rvu_nf": 2.80, "mp_rvu_nf": 1.20, "status": "A", "description": "MRI brain w/ and w/o contrast"},
        "72148": {"work_rvu": 1.30, "pe_rvu_nf": 2.50, "mp_rvu_nf": 1.10, "status": "A", "description": "MRI lumbar spine w/o contrast"},
        "72156": {"work_rvu": 1.70, "pe_rvu_nf": 3.10, "mp_rvu_nf": 1.40, "status": "A", "description": "MRI lumbar spine w/ and w/o contrast"},
        "73221": {"work_rvu": 1.10, "pe_rvu_nf": 2.30, "mp_rvu_nf": 0.90, "status": "A", "description": "MRI upper extremity w/o contrast"},
        "77067": {"work_rvu": 0.30, "pe_rvu_nf": 1.80, "mp_rvu_nf": 0.65, "status": "A", "description": "Screening mammography, bilateral"},
        # Ultrasound
        "76700": {"work_rvu": 0.50, "pe_rvu_nf": 1.70, "mp_rvu_nf": 0.45, "status": "A", "description": "US, complete abdominal"},
        "76770": {"work_rvu": 0.45, "pe_rvu_nf": 1.60, "mp_rvu_nf": 0.42, "status": "A", "description": "US, retroperitoneal"},
        # Cardiology
        "93000": {"work_rvu": 0.18, "pe_rvu_nf": 2.05, "mp_rvu_nf": 0.55, "status": "A", "description": "ECG, complete (12-lead) with interpretation"},
        "93010": {"work_rvu": 0.12, "pe_rvu_nf": 0.55, "mp_rvu_nf": 0.18, "status": "A", "description": "ECG, tracing only (professional component)"},
        "93040": {"work_rvu": 0.10, "pe_rvu_nf": 0.45, "mp_rvu_nf": 0.15, "status": "A", "description": "Rhythm ECG, 1-3 leads"},
        "93306": {"work_rvu": 1.55, "pe_rvu_nf": 3.10, "mp_rvu_nf": 0.85, "status": "A", "description": "Transthoracic echo with spectral Doppler"},
        "93307": {"work_rvu": 1.15, "pe_rvu_nf": 2.50, "mp_rvu_nf": 0.70, "status": "A", "description": "Transthoracic echo, 2D with documentation"},
        "93308": {"work_rvu": 0.50, "pe_rvu_nf": 1.50, "mp_rvu_nf": 0.40, "status": "A", "description": "Transthoracic echo, follow-up or limited"},
        # Pulmonary
        "94010": {"work_rvu": 0.20, "pe_rvu_nf": 1.50, "mp_rvu_nf": 0.35, "status": "A", "description": "Spirometry"},
        "94060": {"work_rvu": 0.25, "pe_rvu_nf": 1.80, "mp_rvu_nf": 0.40, "status": "A", "description": "Bronchodilator responsiveness spirometry"},
        "94070": {"work_rvu": 0.30, "pe_rvu_nf": 2.00, "mp_rvu_nf": 0.45, "status": "A", "description": "Bronchospasm evaluation"},
        # Physical therapy
        "97110": {"work_rvu": 0.40, "pe_rvu_nf": 1.30, "mp_rvu_nf": 0.10, "status": "A", "description": "Therapeutic exercises, each 15 min"},
        "97112": {"work_rvu": 0.45, "pe_rvu_nf": 1.35, "mp_rvu_nf": 0.10, "status": "A", "description": "Neuromuscular re-education, each 15 min"},
        "97113": {"work_rvu": 0.50, "pe_rvu_nf": 1.40, "mp_rvu_nf": 0.12, "status": "A", "description": "Aquatic therapy, each 15 min"},
        "97116": {"work_rvu": 0.40, "pe_rvu_nf": 1.20, "mp_rvu_nf": 0.08, "status": "A", "description": "Gait training, each 15 min"},
        "97140": {"work_rvu": 0.40, "pe_rvu_nf": 1.25, "mp_rvu_nf": 0.10, "status": "A", "description": "Manual therapy, each 15 min"},
        "97530": {"work_rvu": 0.42, "pe_rvu_nf": 1.28, "mp_rvu_nf": 0.10, "status": "A", "description": "Therapeutic activities, each 15 min"},
        "97535": {"work_rvu": 0.42, "pe_rvu_nf": 1.22, "mp_rvu_nf": 0.08, "status": "A", "description": "Self-care/home training, each 15 min"},
        "97537": {"work_rvu": 0.45, "pe_rvu_nf": 1.30, "mp_rvu_nf": 0.10, "status": "A", "description": "Community/work reintegration, each 15 min"},
        "97750": {"work_rvu": 0.40, "pe_rvu_nf": 1.20, "mp_rvu_nf": 0.08, "status": "A", "description": "Physical performance test"},
        "97755": {"work_rvu": 0.38, "pe_rvu_nf": 1.15, "mp_rvu_nf": 0.08, "status": "A", "description": "Assistive technology assessment"},
        "97760": {"work_rvu": 0.35, "pe_rvu_nf": 1.10, "mp_rvu_nf": 0.08, "status": "A", "description": "Prosthetic training, upper extremity"},
        # Vaccines
        "90471": {"work_rvu": 0.10, "pe_rvu_nf": 0.70, "mp_rvu_nf": 0.05, "status": "A", "description": "Immunization admin, first vaccine"},
        "90472": {"work_rvu": 0.10, "pe_rvu_nf": 0.50, "mp_rvu_nf": 0.05, "status": "A", "description": "Immunization admin, additional vaccine"},
        "90473": {"work_rvu": 0.10, "pe_rvu_nf": 0.70, "mp_rvu_nf": 0.05, "status": "A", "description": "Oral/nasal immunization admin, first"},
        "90474": {"work_rvu": 0.10, "pe_rvu_nf": 0.50, "mp_rvu_nf": 0.05, "status": "A", "description": "Oral/nasal immunization admin, additional"},
        # Surgery - Integumentary
        "10060": {"work_rvu": 0.45, "pe_rvu_nf": 1.35, "mp_rvu_nf": 0.15, "status": "A", "description": "Incise and drain, simple abscess"},
        "10061": {"work_rvu": 0.75, "pe_rvu_nf": 2.10, "mp_rvu_nf": 0.25, "status": "A", "description": "Incise and drain, complicated abscess"},
        "11400": {"work_rvu": 0.50, "pe_rvu_nf": 1.40, "mp_rvu_nf": 0.18, "status": "A", "description": "Excise benign lesion, trunk/arms/legs, 0.5cm"},
        "11401": {"work_rvu": 0.70, "pe_rvu_nf": 1.70, "mp_rvu_nf": 0.22, "status": "A", "description": "Excise benign lesion, trunk/arms/legs, 0.6-1.0cm"},
        "11600": {"work_rvu": 0.75, "pe_rvu_nf": 1.80, "mp_rvu_nf": 0.22, "status": "A", "description": "Excise malignant lesion, trunk/arms/legs, 0.5cm"},
        "17000": {"work_rvu": 0.25, "pe_rvu_nf": 0.90, "mp_rvu_nf": 0.12, "status": "A", "description": "Destruction, premalignant lesion, first"},
        "17003": {"work_rvu": 0.10, "pe_rvu_nf": 0.50, "mp_rvu_nf": 0.08, "status": "A", "description": "Destruction, premalignant lesion, additional"},
        # Surgery - Musculoskeletal
        "20610": {"work_rvu": 0.60, "pe_rvu_nf": 1.80, "mp_rvu_nf": 0.30, "status": "A", "description": "Arthrocentesis, intermediate joint, with injection"},
        "22551": {"work_rvu": 5.50, "pe_rvu_nf": 6.80, "mp_rvu_nf": 1.50, "status": "A", "description": "Percutaneous vertebroplasty, one vertebra"},
        "27447": {"work_rvu": 22.50, "pe_rvu_nf": 18.00, "mp_rvu_nf": 5.80, "status": "A", "description": "Total knee arthroplasty"},
        "29881": {"work_rvu": 3.50, "pe_rvu_nf": 5.20, "mp_rvu_nf": 1.40, "status": "A", "description": "Knee arthroscopy, with meniscectomy"},
        # Surgery - GI
        "43239": {"work_rvu": 2.80, "pe_rvu_nf": 4.50, "mp_rvu_nf": 0.80, "status": "A", "description": "EGD with biopsy"},
        "47562": {"work_rvu": 8.50, "pe_rvu_nf": 10.50, "mp_rvu_nf": 2.80, "status": "A", "description": "Laparoscopic cholecystectomy"},
        # Surgery - Hernia
        "49505": {"work_rvu": 5.80, "pe_rvu_nf": 7.50, "mp_rvu_nf": 1.80, "status": "A", "description": "Repair initial inguinal hernia, age 5+"},
        # Surgery - GU
        "52000": {"work_rvu": 1.80, "pe_rvu_nf": 3.20, "mp_rvu_nf": 0.55, "status": "A", "description": "Cystoscopy"},
        # Pain management
        "62323": {"work_rvu": 1.20, "pe_rvu_nf": 2.80, "mp_rvu_nf": 0.50, "status": "A", "description": "Epidural injection, lumbar/sacral"},
        "64483": {"work_rvu": 1.50, "pe_rvu_nf": 3.20, "mp_rvu_nf": 0.60, "status": "A", "description": "Transforaminal epidural injection, lumbar"},
    }

    # --- GPCI (Geographic Practice Cost Index) examples ---
    # Format: locality_code -> {work_gpci, pe_gpci, mp_gpci, name, state}
    GPCI_DATA: Dict[str, Dict[str, Any]] = {
        "01010": {"work_gpci": 0.963, "pe_gpci": 0.879, "mp_gpci": 0.724, "name": "Alabama - Rest of State", "state": "AL"},
        "01012": {"work_gpci": 0.999, "pe_gpci": 0.912, "mp_gpci": 0.744, "name": "Alabama - Birmingham", "state": "AL"},
        "02010": {"work_gpci": 1.037, "pe_gpci": 1.076, "mp_gpci": 1.024, "name": "Alaska - Rest of State", "state": "AK"},
        "03010": {"work_gpci": 0.975, "pe_gpci": 0.975, "mp_gpci": 0.728, "name": "Arizona - Rest of State", "state": "AZ"},
        "03012": {"work_gpci": 1.000, "pe_gpci": 1.036, "mp_gpci": 0.768, "name": "Arizona - Phoenix", "state": "AZ"},
        "04010": {"work_gpci": 0.945, "pe_gpci": 0.864, "mp_gpci": 0.696, "name": "Arkansas - Rest of State", "state": "AR"},
        "05010": {"work_gpci": 1.032, "pe_gpci": 1.152, "mp_gpci": 1.056, "name": "California - Rest of State", "state": "CA"},
        "05012": {"work_gpci": 1.060, "pe_gpci": 1.285, "mp_gpci": 1.120, "name": "California - Los Angeles", "state": "CA"},
        "05014": {"work_gpci": 1.068, "pe_gpci": 1.312, "mp_gpci": 1.148, "name": "California - San Francisco", "state": "CA"},
        "06010": {"work_gpci": 0.984, "pe_gpci": 0.948, "mp_gpci": 0.768, "name": "Colorado - Rest of State", "state": "CO"},
        "06012": {"work_gpci": 1.012, "pe_gpci": 1.064, "mp_gpci": 0.840, "name": "Colorado - Denver", "state": "CO"},
        "09006": {"work_gpci": 1.000, "pe_gpci": 1.000, "mp_gpci": 1.000, "name": "Connecticut - Entire State", "state": "CT"},
        "10010": {"work_gpci": 0.975, "pe_gpci": 0.912, "mp_gpci": 0.792, "name": "Delaware - Entire State", "state": "DE"},
        "11006": {"work_gpci": 1.000, "pe_gpci": 1.000, "mp_gpci": 1.000, "name": "District of Columbia - Entire State", "state": "DC"},
        "12010": {"work_gpci": 0.963, "pe_gpci": 0.879, "mp_gpci": 0.728, "name": "Florida - Rest of State", "state": "FL"},
        "12014": {"work_gpci": 1.000, "pe_gpci": 1.000, "mp_gpci": 0.832, "name": "Florida - Miami", "state": "FL"},
        "13010": {"work_gpci": 0.975, "pe_gpci": 0.879, "mp_gpci": 0.696, "name": "Georgia - Rest of State", "state": "GA"},
        "13012": {"work_gpci": 0.996, "pe_gpci": 0.932, "mp_gpci": 0.748, "name": "Georgia - Atlanta", "state": "GA"},
        "15010": {"work_gpci": 0.984, "pe_gpci": 1.000, "mp_gpci": 0.888, "name": "Hawaii - Entire State", "state": "HI"},
        "16010": {"work_gpci": 0.921, "pe_gpci": 0.832, "mp_gpci": 0.660, "name": "Idaho - Entire State", "state": "ID"},
        "17010": {"work_gpci": 0.963, "pe_gpci": 0.912, "mp_gpci": 0.752, "name": "Illinois - Rest of State", "state": "IL"},
        "17014": {"work_gpci": 1.000, "pe_gpci": 1.060, "mp_gpci": 0.868, "name": "Illinois - Chicago", "state": "IL"},
        "18010": {"work_gpci": 0.945, "pe_gpci": 0.864, "mp_gpci": 0.720, "name": "Indiana - Rest of State", "state": "IN"},
        "19010": {"work_gpci": 0.945, "pe_gpci": 0.864, "mp_gpci": 0.696, "name": "Iowa - Entire State", "state": "IA"},
        "20010": {"work_gpci": 0.921, "pe_gpci": 0.832, "mp_gpci": 0.660, "name": "Kansas - Rest of State", "state": "KS"},
        "21010": {"work_gpci": 0.945, "pe_gpci": 0.864, "mp_gpci": 0.696, "name": "Kentucky - Rest of State", "state": "KY"},
        "22010": {"work_gpci": 0.921, "pe_gpci": 0.832, "mp_gpci": 0.696, "name": "Louisiana - Rest of State", "state": "LA"},
        "23010": {"work_gpci": 0.921, "pe_gpci": 0.832, "mp_gpci": 0.660, "name": "Maine - Entire State", "state": "ME"},
        "24010": {"work_gpci": 1.032, "pe_gpci": 1.152, "mp_gpci": 1.056, "name": "Maryland - Entire State", "state": "MD"},
        "25010": {"work_gpci": 1.060, "pe_gpci": 1.285, "mp_gpci": 1.148, "name": "Massachusetts - Boston", "state": "MA"},
        "26010": {"work_gpci": 0.984, "pe_gpci": 0.912, "mp_gpci": 0.792, "name": "Michigan - Rest of State", "state": "MI"},
        "26014": {"work_gpci": 1.012, "pe_gpci": 1.064, "mp_gpci": 0.868, "name": "Michigan - Detroit", "state": "MI"},
        "27010": {"work_gpci": 0.945, "pe_gpci": 0.864, "mp_gpci": 0.696, "name": "Minnesota - Rest of State", "state": "MN"},
        "28010": {"work_gpci": 0.921, "pe_gvu_nf": 0.832, "mp_gpci": 0.660, "name": "Mississippi - Entire State", "state": "MS"},
        "29010": {"work_gpci": 0.945, "pe_gpci": 0.864, "mp_gpci": 0.696, "name": "Missouri - Rest of State", "state": "MO"},
        "29014": {"work_gpci": 0.984, "pe_gpci": 0.960, "mp_gpci": 0.752, "name": "Missouri - St. Louis", "state": "MO"},
        "30010": {"work_gpci": 0.921, "pe_gpci": 0.832, "mp_gpci": 0.660, "name": "Montana - Entire State", "state": "MT"},
        "31010": {"work_gpci": 0.921, "pe_gpci": 0.832, "mp_gpci": 0.660, "name": "Nebraska - Rest of State", "state": "NE"},
        "32010": {"work_gpci": 1.060, "pe_gpci": 1.152, "mp_gpci": 1.032, "name": "Nevada - Entire State", "state": "NV"},
        "33010": {"work_gpci": 0.984, "pe_gpci": 0.960, "mp_gpci": 0.792, "name": "New Hampshire - Entire State", "state": "NH"},
        "34010": {"work_gpci": 1.060, "pe_gpci": 1.212, "mp_gpci": 1.056, "name": "New Jersey - Entire State", "state": "NJ"},
        "35010": {"work_gpci": 0.921, "pe_gpci": 0.832, "mp_gpci": 0.660, "name": "New Mexico - Entire State", "state": "NM"},
        "36010": {"work_gpci": 1.060, "pe_gpci": 1.285, "mp_gpci": 1.148, "name": "New York - Manhattan", "state": "NY"},
        "36014": {"work_gpci": 1.032, "pe_gpci": 1.152, "mp_gpci": 1.032, "name": "New York - Rest of State", "state": "NY"},
        "37010": {"work_gpci": 0.945, "pe_gpci": 0.864, "mp_gpci": 0.696, "name": "North Carolina - Rest of State", "state": "NC"},
        "37014": {"work_gpci": 0.975, "pe_gpci": 0.932, "mp_gpci": 0.752, "name": "North Carolina - Charlotte", "state": "NC"},
        "38010": {"work_gpci": 0.921, "pe_gpci": 0.832, "mp_gpci": 0.660, "name": "North Dakota - Entire State", "state": "ND"},
        "39010": {"work_gpci": 0.945, "pe_gpci": 0.864, "mp_gpci": 0.696, "name": "Ohio - Rest of State", "state": "OH"},
        "39014": {"work_gpci": 0.984, "pe_gpci": 0.960, "mp_gpci": 0.752, "name": "Ohio - Cleveland", "state": "OH"},
        "40010": {"work_gpci": 0.921, "pe_gpci": 0.832, "mp_gpci": 0.660, "name": "Oklahoma - Rest of State", "state": "OK"},
        "41010": {"work_gpci": 0.984, "pe_gpci": 0.960, "mp_gpci": 0.792, "name": "Oregon - Portland", "state": "OR"},
        "42010": {"work_gpci": 0.984, "pe_gpci": 0.912, "mp_gpci": 0.752, "name": "Pennsylvania - Rest of State", "state": "PA"},
        "42014": {"work_gpci": 1.032, "pe_gpci": 1.060, "mp_gpci": 0.888, "name": "Pennsylvania - Philadelphia", "state": "PA"},
        "44010": {"work_gpci": 1.032, "pe_gpci": 1.152, "mp_gpci": 1.056, "name": "Rhode Island - Entire State", "state": "RI"},
        "45010": {"work_gpci": 0.921, "pe_gpci": 0.832, "mp_gpci": 0.660, "name": "South Carolina - Rest of State", "state": "SC"},
        "46010": {"work_gpci": 0.921, "pe_gpci": 0.832, "mp_gpci": 0.660, "name": "South Dakota - Entire State", "state": "SD"},
        "47010": {"work_gpci": 0.945, "pe_gpci": 0.864, "mp_gpci": 0.696, "name": "Tennessee - Rest of State", "state": "TN"},
        "47014": {"work_gpci": 0.975, "pe_gpci": 0.932, "mp_gpci": 0.752, "name": "Tennessee - Nashville", "state": "TN"},
        "48010": {"work_gpci": 0.945, "pe_gpci": 0.864, "mp_gpci": 0.696, "name": "Texas - Rest of State", "state": "TX"},
        "48014": {"work_gpci": 0.984, "pe_gpci": 0.960, "mp_gpci": 0.752, "name": "Texas - Houston", "state": "TX"},
        "48018": {"work_gpci": 0.984, "pe_gpci": 0.960, "mp_gpci": 0.748, "name": "Texas - Dallas", "state": "TX"},
        "49010": {"work_gpci": 0.984, "pe_gpci": 0.960, "mp_gpci": 0.792, "name": "Utah - Entire State", "state": "UT"},
        "50010": {"work_gpci": 0.984, "pe_gpci": 0.912, "mp_gpci": 0.752, "name": "Vermont - Entire State", "state": "VT"},
        "51010": {"work_gpci": 0.984, "pe_gpci": 0.912, "mp_gpci": 0.752, "name": "Virginia - Rest of State", "state": "VA"},
        "51014": {"work_gpci": 1.012, "pe_gpci": 1.064, "mp_gpci": 0.868, "name": "Virginia - Washington DC Suburban", "state": "VA"},
        "53010": {"work_gpci": 1.060, "pe_gpci": 1.152, "mp_gpci": 1.032, "name": "Washington - Rest of State", "state": "WA"},
        "53014": {"work_gpci": 1.088, "pe_gpci": 1.285, "mp_gpci": 1.120, "name": "Washington - Seattle", "state": "WA"},
        "54010": {"work_gpci": 0.921, "pe_gpci": 0.832, "mp_gpci": 0.660, "name": "West Virginia - Entire State", "state": "WV"},
        "55010": {"work_gpci": 0.984, "pe_gpci": 0.912, "mp_gpci": 0.752, "name": "Wisconsin - Rest of State", "state": "WI"},
        "55014": {"work_gpci": 1.012, "pe_gpci": 1.064, "mp_gpci": 0.868, "name": "Wisconsin - Milwaukee", "state": "WI"},
        "56010": {"work_gpci": 0.921, "pe_gpci": 0.832, "mp_gpci": 0.660, "name": "Wyoming - Entire State", "state": "WY"},
    }

    # --- Modifier impact on reimbursement ---
    MODIFIER_ADJUSTMENTS: Dict[str, Dict[str, Any]] = {
        "26": {
            "description": "Professional component only",
            "work_pct": 1.0,
            "pe_pct": 0.0,
            "mp_pct": 0.0,
            "applies_to": "Radiology, pathology, and other diagnostic services"
        },
        "TC": {
            "description": "Technical component only",
            "work_pct": 0.0,
            "pe_pct": 1.0,
            "mp_pct": 1.0,
            "applies_to": "Radiology, pathology, and other diagnostic services"
        },
        "50": {
            "description": "Bilateral procedure",
            "work_pct": 1.5,
            "pe_pct": 1.5,
            "mp_pct": 1.5,
            "applies_to": "Bilateral procedures (multiply total RVUs by 1.5)"
        },
        "80": {
            "description": "Assistant surgeon",
            "work_pct": 0.16,
            "pe_pct": 0.16,
            "mp_pct": 0.16,
            "applies_to": "Surgical assistant at surgery"
        },
        "82": {
            "description": "Assistant surgeon (when qualified resident not available)",
            "work_pct": 0.16,
            "pe_pct": 0.16,
            "mp_pct": 0.16,
            "applies_to": "Surgical assistant when no resident available"
        },
    }

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        cpt_code = kwargs.get("cpt_code", "").strip()
        locality = kwargs.get("locality", "01010").strip()
        modifier = kwargs.get("modifier", "").strip().upper()
        multiple_codes = kwargs.get("multiple_codes", [])

        if not action:
            return SkillResult(success=False, error="Action is required: lookup, calculate, or compare_localities")

        try:
            if action == "lookup":
                codes = multiple_codes if multiple_codes else ([cpt_code] if cpt_code else [])
                if not codes:
                    return SkillResult(success=False, error="cpt_code or multiple_codes is required for lookup")
                result = self._lookup_codes(codes)
            elif action == "calculate":
                if not cpt_code:
                    return SkillResult(success=False, error="cpt_code is required for calculate")
                result = self._calculate_allowed(cpt_code, locality, modifier)
            elif action == "compare_localities":
                if not cpt_code:
                    return SkillResult(success=False, error="cpt_code is required for compare_localities")
                localities = [l.strip() for l in locality.split(",")] if locality else []
                result = self._compare_localities(cpt_code, localities, modifier)
            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

            return SkillResult(success=True, data=result)
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _lookup_codes(self, codes: List[str]) -> Dict[str, Any]:
        """Look up RVU data for one or more CPT codes."""
        results = []
        not_found = []

        for code in codes:
            code = code.strip()
            if code in self.RVU_DATA:
                rvu = self.RVU_DATA[code]
                total_rvu_nf = rvu["work_rvu"] + rvu["pe_rvu_nf"] + rvu["mp_rvu_nf"]
                results.append({
                    "cpt_code": code,
                    "description": rvu["description"],
                    "work_rvu": rvu["work_rvu"],
                    "pe_rvu_nf": rvu["pe_rvu_nf"],
                    "mp_rvu_nf": rvu["mp_rvu_nf"],
                    "total_rvu_nf": round(total_rvu_nf, 4),
                    "status_code": rvu["status"],
                    "national_average_allowed": round(total_rvu_nf * self.CONVERSION_FACTOR, 2)
                })
            else:
                not_found.append(code)

        return {
            "conversion_factor": self.CONVERSION_FACTOR,
            "results": results,
            "not_found": not_found,
            "total_codes_looked_up": len(codes),
            "found": len(results)
        }

    def _calculate_allowed(self, cpt_code: str, locality: str, modifier: str) -> Dict[str, Any]:
        """Calculate the Medicare allowed amount for a CPT code at a locality."""
        if cpt_code not in self.RVU_DATA:
            return {
                "cpt_code": cpt_code,
                "error": f"CPT code {cpt_code} not found in fee schedule database",
                "available_codes": list(self.RVU_DATA.keys())[:20]
            }

        rvu = self.RVU_DATA[cpt_code]
        gpci = self._find_gpci(locality)

        # Apply modifier adjustments if applicable
        work_mult = 1.0
        pe_mult = 1.0
        mp_mult = 1.0
        mod_info = None

        if modifier and modifier in self.MODIFIER_ADJUSTMENTS:
            mod_info = self.MODIFIER_ADJUSTMENTS[modifier]
            work_mult = mod_info["work_pct"]
            pe_mult = mod_info["pe_pct"]
            mp_mult = mod_info["mp_pct"]

        # Calculate: Allowed = [(Work RVU * Work GPCI) + (PE RVU * PE GPCI) + (MP RVU * MP GPCI)] * CF
        work_component = (rvu["work_rvu"] * work_mult) * gpci["work_gpci"]
        pe_component = (rvu["pe_rvu_nf"] * pe_mult) * gpci["pe_gpci"]
        mp_component = (rvu["mp_rvu_nf"] * mp_mult) * gpci["mp_gpci"]

        allowed_amount = (work_component + pe_component + mp_component) * self.CONVERSION_FACTOR

        return {
            "cpt_code": cpt_code,
            "description": rvu["description"],
            "locality": gpci["name"],
            "locality_code": locality,
            "modifier": modifier if modifier else "None",
            "rvus": {
                "work_rvu": rvu["work_rvu"],
                "pe_rvu_nf": rvu["pe_rvu_nf"],
                "mp_rvu_nf": rvu["mp_rvu_nf"],
                "total_rvu_nf": round(rvu["work_rvu"] + rvu["pe_rvu_nf"] + rvu["mp_rvu_nf"], 4)
            },
            "gpcis": {
                "work_gpci": gpci["work_gpci"],
                "pe_gpci": gpci["pe_gpci"],
                "mp_gpci": gpci["mp_gpci"]
            },
            "components": {
                "work_component": round(work_component, 4),
                "pe_component": round(pe_component, 4),
                "mp_component": round(mp_component, 4)
            },
            "conversion_factor": self.CONVERSION_FACTOR,
            "allowed_amount": round(allowed_amount, 2),
            "modifier_info": mod_info
        }

    def _compare_localities(self, cpt_code: str, localities: List[str], modifier: str) -> Dict[str, Any]:
        """Compare allowed amounts for a CPT code across localities."""
        if cpt_code not in self.RVU_DATA:
            return {
                "cpt_code": cpt_code,
                "error": f"CPT code {cpt_code} not found in fee schedule database"
            }

        rvu = self.RVU_DATA[cpt_code]
        results = []

        for loc in localities:
            gpci = self._find_gpci(loc)

            work_mult = 1.0
            pe_mult = 1.0
            mp_mult = 1.0
            if modifier and modifier in self.MODIFIER_ADJUSTMENTS:
                mod_info = self.MODIFIER_ADJUSTMENTS[modifier]
                work_mult = mod_info["work_pct"]
                pe_mult = mod_info["pe_pct"]
                mp_mult = mod_info["mp_pct"]

            work_component = (rvu["work_rvu"] * work_mult) * gpci["work_gpci"]
            pe_component = (rvu["pe_rvu_nf"] * pe_mult) * gpci["pe_gpci"]
            mp_component = (rvu["mp_rvu_nf"] * mp_mult) * gpci["mp_gpci"]
            allowed = (work_component + pe_component + mp_component) * self.CONVERSION_FACTOR

            results.append({
                "locality_code": loc,
                "locality_name": gpci["name"],
                "state": gpci["state"],
                "work_gpci": gpci["work_gpci"],
                "pe_gpci": gpci["pe_gpci"],
                "mp_gpci": gpci["mp_gpci"],
                "allowed_amount": round(allowed, 2)
            })

        # Sort by allowed amount descending
        results.sort(key=lambda r: r["allowed_amount"], reverse=True)

        amounts = [r["allowed_amount"] for r in results]
        max_amt = max(amounts) if amounts else 0
        min_amt = min(amounts) if amounts else 0
        avg_amt = sum(amounts) / len(amounts) if amounts else 0
        spread = max_amt - min_amt
        spread_pct = (spread / min_amt * 100) if min_amt > 0 else 0

        return {
            "cpt_code": cpt_code,
            "description": rvu["description"],
            "modifier": modifier if modifier else "None",
            "conversion_factor": self.CONVERSION_FACTOR,
            "total_rvu_nf": round(rvu["work_rvu"] + rvu["pe_rvu_nf"] + rvu["mp_rvu_nf"], 4),
            "locality_comparison": results,
            "summary": {
                "highest": {"amount": max_amt, "locality": results[0]["locality_name"]} if results else None,
                "lowest": {"amount": min_amt, "locality": results[-1]["locality_name"]} if results else None,
                "average": round(avg_amt, 2),
                "dollar_spread": round(spread, 2),
                "percent_spread": round(spread_pct, 2)
            }
        }

    def _find_gpci(self, locality: str) -> Dict[str, Any]:
        """Find GPCI data for a locality code or name."""
        # Try exact match on locality code
        if locality in self.GPCI_DATA:
            return self.GPCI_DATA[locality]

        # Try fuzzy match on state name or locality name
        locality_lower = locality.lower()
        for code, data in self.GPCI_DATA.items():
            if locality_lower in data["name"].lower() or locality_lower in data["state"].lower():
                return data

        # Default to national average (GPCI = 1.0)
        return {
            "work_gpci": 1.000,
            "pe_gpci": 1.000,
            "mp_gpci": 1.000,
            "name": "National Average (default)",
            "state": "US"
        }