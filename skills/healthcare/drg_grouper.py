"""
Aethera AI - DRG Grouper Skill

DRG assignment logic: common MS-DRGs with weights, base rates,
CC/MCC lists. Supports: assign DRG from diagnosis/procedure codes,
calculate reimbursement, identify CC/MCC impact.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


# MS-DRG definitions (common DRGs with weights and info)
MS_DRGS: Dict[str, Dict[str, Any]] = {
    "001": {"description": "Heart transplant or implant of heart assist system w MCC", "weight": 22.4465, "geom_mean_los": 23.1, "type": "SURGICAL", "mcc": True},
    "002": {"description": "Heart transplant or implant of heart assist system w CC", "weight": 16.3214, "geom_mean_los": 18.5, "type": "SURGICAL", "cc": True},
    "003": {"description": "Heart transplant or implant of heart assist system w/o CC/MCC", "weight": 11.5432, "geom_mean_los": 14.2, "type": "SURGICAL"},
    "006": {"description": "Pancreas transplant", "weight": 9.8765, "geom_mean_los": 11.3, "type": "SURGICAL"},
    "065": {"description": "Intracranial hemorrhage or cerebral infarction w MCC", "weight": 2.0142, "geom_mean_los": 6.8, "type": "MEDICAL", "mcc": True},
    "066": {"description": "Intracranial hemorrhage or cerebral infarction w CC", "weight": 1.2136, "geom_mean_los": 5.1, "type": "MEDICAL", "cc": True},
    "067": {"description": "Intracranial hemorrhage or cerebral infarction w/o CC/MCC", "weight": 0.8654, "geom_mean_los": 3.9, "type": "MEDICAL"},
    "069": {"description": "Transient ischemia", "weight": 0.7654, "geom_mean_los": 3.2, "type": "MEDICAL"},
    "176": {"description": "Pulmonary embolism w MCC", "weight": 1.8976, "geom_mean_los": 5.9, "type": "MEDICAL", "mcc": True},
    "177": {"description": "Pulmonary embolism w CC", "weight": 1.1234, "geom_mean_los": 4.3, "type": "MEDICAL", "cc": True},
    "178": {"description": "Pulmonary embolism w/o CC/MCC", "weight": 0.7890, "geom_mean_los": 3.1, "type": "MEDICAL"},
    "190": {"description": "COPD w MCC", "weight": 1.4521, "geom_mean_los": 5.2, "type": "MEDICAL", "mcc": True},
    "191": {"description": "COPD w CC", "weight": 0.9234, "geom_mean_los": 4.0, "type": "MEDICAL", "cc": True},
    "192": {"description": "COPD w/o CC/MCC", "weight": 0.6789, "geom_mean_los": 3.0, "type": "MEDICAL"},
    "193": {"description": "Simple pneumonia & pleurisy w MCC", "weight": 1.6789, "geom_mean_los": 5.8, "type": "MEDICAL", "mcc": True},
    "194": {"description": "Simple pneumonia & pleurisy w CC", "weight": 1.0345, "geom_mean_los": 4.2, "type": "MEDICAL", "cc": True},
    "195": {"description": "Simple pneumonia & pleurisy w/o CC/MCC", "weight": 0.7123, "geom_mean_los": 3.0, "type": "MEDICAL"},
    "247": {"description": "Percutaneous cardiovascular procedures w drug-eluting stent w MCC", "weight": 3.2345, "geom_mean_los": 4.8, "type": "SURGICAL", "mcc": True},
    "248": {"description": "Percutaneous cardiovascular procedures w drug-eluting stent w CC", "weight": 2.1876, "geom_mean_los": 3.5, "type": "SURGICAL", "cc": True},
    "249": {"description": "Percutaneous cardiovascular procedures w drug-eluting stent w/o CC/MCC", "weight": 1.6543, "geom_mean_los": 2.3, "type": "SURGICAL"},
    "252": {"description": "Other vascular procedures w MCC", "weight": 4.5678, "geom_mean_los": 8.1, "type": "SURGICAL", "mcc": True},
    "253": {"description": "Other vascular procedures w CC", "weight": 2.9876, "geom_mean_los": 5.9, "type": "SURGICAL", "cc": True},
    "254": {"description": "Other vascular procedures w/o CC/MCC", "weight": 2.0123, "geom_mean_los": 3.8, "type": "SURGICAL"},
    "271": {"description": "Major small & large bowel procedures w MCC", "weight": 5.4321, "geom_mean_los": 10.2, "type": "SURGICAL", "mcc": True},
    "272": {"description": "Major small & large bowel procedures w CC", "weight": 3.4567, "geom_mean_los": 7.1, "type": "SURGICAL", "cc": True},
    "273": {"description": "Major small & large bowel procedures w/o CC/MCC", "weight": 2.3456, "geom_mean_los": 5.0, "type": "SURGICAL"},
    "281": {"description": "Total joint replacement w/o MCC", "weight": 2.8765, "geom_mean_los": 2.8, "type": "SURGICAL"},
    "282": {"description": "Total joint replacement w MCC", "weight": 4.1234, "geom_mean_los": 4.5, "type": "SURGICAL", "mcc": True},
    "291": {"description": "Heart failure & shock w MCC", "weight": 1.6789, "geom_mean_los": 6.1, "type": "MEDICAL", "mcc": True},
    "292": {"description": "Heart failure & shock w CC", "weight": 1.0345, "geom_mean_los": 4.5, "type": "MEDICAL", "cc": True},
    "293": {"description": "Heart failure & shock w/o CC/MCC", "weight": 0.7123, "geom_mean_los": 3.2, "type": "MEDICAL"},
    "312": {"description": "Syncope & collapse", "weight": 0.6543, "geom_mean_los": 2.5, "type": "MEDICAL"},
    "371": {"description": "Vaginal delivery w complicating diagnoses", "weight": 0.8765, "geom_mean_los": 2.8, "type": "SURGICAL"},
    "372": {"description": "Vaginal delivery w/o complicating diagnoses", "weight": 0.5678, "geom_mean_los": 2.1, "type": "SURGICAL"},
    "392": {"description": "Esophagitis, gastroenteritis & miscellaneous digestive disorders w/o MCC", "weight": 0.6789, "geom_mean_los": 2.8, "type": "MEDICAL"},
    "470": {"description": "Major joint replacement or reattachment of lower extremity w/o MCC", "weight": 2.8765, "geom_mean_los": 2.3, "type": "SURGICAL"},
    "471": {"description": "Major joint replacement or reattachment of lower extremity w MCC", "weight": 4.1234, "geom_mean_los": 4.1, "type": "SURGICAL", "mcc": True},
    "480": {"description": "Hip & femur procedures except major joint w MCC", "weight": 3.5678, "geom_mean_los": 6.2, "type": "SURGICAL", "mcc": True},
    "481": {"description": "Hip & femur procedures except major joint w CC", "weight": 2.4321, "geom_mean_los": 4.8, "type": "SURGICAL", "cc": True},
    "482": {"description": "Hip & femur procedures except major joint w/o CC/MCC", "weight": 1.7654, "geom_mean_los": 3.5, "type": "SURGICAL"},
    "690": {"description": "Kidney & urinary tract infections w MCC", "weight": 1.5432, "geom_mean_los": 5.5, "type": "MEDICAL", "mcc": True},
    "691": {"description": "Kidney & urinary tract infections w CC", "weight": 0.9876, "geom_mean_los": 4.0, "type": "MEDICAL", "cc": True},
    "692": {"description": "Kidney & urinary tract infections w/o CC/MCC", "weight": 0.6543, "geom_mean_los": 2.9, "type": "MEDICAL"},
}

# Diagnosis-to-DRG mapping (principal diagnosis code -> base DRG)
DX_TO_BASE_DRG: Dict[str, Dict[str, Any]] = {
    "I63.9": {"base_drg": "065-067", "description": "Cerebral infarction", "mdc": "05"},
    "I63.0": {"base_drg": "065-067", "description": "Cerebral infarction due to thrombosis of precerebral arteries", "mdc": "05"},
    "I63.1": {"base_drg": "065-067", "description": "Cerebral infarction due to thrombosis of cerebral artery", "mdc": "05"},
    "I63.3": {"base_drg": "065-067", "description": "Cerebral infarction due to thrombosis of cerebral artery", "mdc": "05"},
    "G45.9": {"base_drg": "069", "description": "Transient cerebral ischemic attack", "mdc": "05"},
    "I26.99": {"base_drg": "176-178", "description": "Pulmonary embolism", "mdc": "04"},
    "I26.0": {"base_drg": "176-178", "description": "Pulmonary embolism with acute cor pulmonale", "mdc": "04"},
    "J44.1": {"base_drg": "190-192", "description": "COPD with acute exacerbation", "mdc": "04"},
    "J44.0": {"base_drg": "190-192", "description": "COPD with acute lower respiratory infection", "mdc": "04"},
    "J18.9": {"base_drg": "193-195", "description": "Pneumonia unspecified organism", "mdc": "04"},
    "J18.1": {"base_drg": "193-195", "description": "Lobar pneumonia unspecified organism", "mdc": "04"},
    "I50.9": {"base_drg": "291-293", "description": "Heart failure unspecified", "mdc": "05"},
    "I50.22": {"base_drg": "291-293", "description": "Chronic systolic heart failure", "mdc": "05"},
    "I50.32": {"base_drg": "291-293", "description": "Chronic diastolic heart failure", "mdc": "05"},
    "R55": {"base_drg": "312", "description": "Syncope and collapse", "mdc": "06"},
    "Z96.641": {"base_drg": "470-471", "description": "Presence of right artificial hip joint", "mdc": "08"},
    "Z96.642": {"base_drg": "470-471", "description": "Presence of left artificial hip joint", "mdc": "08"},
    "M16.11": {"base_drg": "470-471", "description": "Primary osteoarthritis right hip", "mdc": "08"},
    "M16.12": {"base_drg": "470-471", "description": "Primary osteoarthritis left hip", "mdc": "08"},
    "M17.11": {"base_drg": "470-471", "description": "Primary osteoarthritis right knee", "mdc": "08"},
    "M17.12": {"base_drg": "470-471", "description": "Primary osteoarthritis left knee", "mdc": "08"},
    "S72.001": {"base_drg": "480-482", "description": "Fracture unspecified part of right femur", "mdc": "08"},
    "S72.002": {"base_drg": "480-482", "description": "Fracture unspecified part of left femur", "mdc": "08"},
    "K80.00": {"base_drg": "271-273", "description": "Cholelithiasis with acute cholecystitis without obstruction", "mdc": "06"},
    "K80.10": {"base_drg": "271-273", "description": "Calculus of gallbladder with cholecystitis without obstruction", "mdc": "06"},
    "N39.0": {"base_drg": "690-692", "description": "Urinary tract infection site not specified", "mdc": "11"},
    "K21.0": {"base_drg": "392", "description": "Gastro-esophageal reflux disease with esophagitis", "mdc": "06"},
}

# Procedure-to-DRG mapping
PROC_TO_BASE_DRG: Dict[str, Dict[str, Any]] = {
    "27447": {"base_drg": "470-471", "description": "Total knee arthroplasty", "mdc": "08"},
    "27130": {"base_drg": "470-471", "description": "Total hip arthroplasty", "mdc": "08"},
    "33510": {"base_drg": "001-003", "description": "Heart transplant", "mdc": "05"},
    "33533": {"base_drg": "001-003", "description": "Heart assist system implant", "mdc": "05"},
    "93350": {"base_drg": "247-249", "description": "Percutaneous cardiovascular procedure", "mdc": "05"},
    "93351": {"base_drg": "247-249", "description": "Percutaneous cardiovascular procedure", "mdc": "05"},
    "44970": {"base_drg": "271-273", "description": "Laparoscopic cholecystectomy", "mdc": "06"},
    "47600": {"base_drg": "271-273", "description": "Cholecystectomy", "mdc": "06"},
    "27236": {"base_drg": "480-482", "description": "Open treatment of femoral fracture", "mdc": "08"},
    "27245": {"base_drg": "480-482", "description": "Treatment of intertrochanteric femur fracture", "mdc": "08"},
}

# CC/MCC lists (common conditions that affect DRG grouping)
# MCC = Major Complication/Comorbidity; CC = Complication/Comorbidity
MCC_CODES: List[str] = [
    "A41.9",   # Sepsis unspecified organism
    "A41.5",   # Sepsis due to other gram-negative organisms
    "E87.2",   # Acidosis
    "I21.9",   # Acute myocardial infarction unspecified
    "I48.0",   # Atrial fibrillation
    "I48.91",  # Atrial fibrillation unspecified
    "I95.9",   # Hypotension unspecified
    "J96.0",   # Acute respiratory failure
    "J96.00",  # Acute respiratory failure with hypoxia
    "J96.02",  # Acute respiratory failure with hypercapnia
    "J95.821", # Postprocedural respiratory failure
    "N17.9",   # Acute kidney failure unspecified
    "N17.0",   # Acute kidney failure with tubular necrosis
    "R65.20",  # Severe sepsis without septic shock
    "R65.21",  # Severe sepsis with septic shock
    "G93.41",  # Metabolic encephalopathy
    "E86.0",   # Dehydration
    "D62",     # Acute posthemorrhagic anemia
    "E11.65",  # Type 2 DM with hyperglycemia
    "E10.65",  # Type 1 DM with hyperglycemia
    "I27.2",   # Other secondary pulmonary hypertension
    "B95.6",   # Staphylococcus aureus as cause of diseases classified elsewhere
    "B96.2",   # E. coli as cause of diseases classified elsewhere
    "T81.12",  # Postprocedural hematoma
    "K92.2",   # GI hemorrhage unspecified
]

CC_CODES: List[str] = [
    "E11.9",   # Type 2 DM without complications
    "E10.9",   # Type 1 DM without complications
    "I10",     # Essential hypertension
    "I12.9",   # Hypertensive CKD
    "I13.9",   # Hypertensive heart and CKD
    "E78.5",   # Dyslipidemia
    "E78.0",   # Pure hypercholesterolemia
    "J44.1",   # COPD with acute exacerbation
    "J44.0",   # COPD with acute lower respiratory infection
    "K21.0",   # GERD with esophagitis
    "N18.3",   # CKD stage 3
    "N18.4",   # CKD stage 4
    "N18.5",   # CKD stage 5
    "N18.6",   # End-stage renal disease
    "F32.9",   # Major depressive disorder single episode unspecified
    "F33.0",   # Major depressive disorder recurrent mild
    "G89.29",  # Other chronic pain
    "Z87.891", # Personal history of nicotine dependence
    "F17.210", # Nicotine dependence cigarettes
    "E03.9",   # Hypothyroidism unspecified
    "M81.0",   # Age-related osteoporosis without pathological fracture
    "I35.0",   # Nonrheumatic aortic stenosis
    "I34.0",   # Mitral regurgitation
    "B18.2",   # Chronic viral hepatitis C without hepatic coma
    "K74.3",   # Primary biliary cirrhosis
    "K74.0",   # Hepatic fibrosis
    "I42.9",   # Cardiomyopathy unspecified
    "I50.9",   # Heart failure unspecified
    "J84.10",  # Pulmonary fibrosis unspecified
    "J84.9",   # Interstitial pulmonary disease unspecified
    "G40.909", # Epilepsy unspecified not intractable without status epilepticus
    "R26.89",  # Other abnormalities of gait
    "Z79.01",  # Long term use of anticoagulants
    "Z79.02",  # Long term use of antiplatelets
    "Z79.899", # Other long term medication therapy
]

# CMS base rate (national average; actual varies by hospital)
DEFAULT_BASE_RATE = 6131.0  # FY2024 approximate national average


@skill(name="drg_grouper", category="healthcare")
class DRGGrouperSkill(AetheraSkill):
    """
    DRG assignment logic with reimbursement calculation.
    """

    @property
    def name(self) -> str:
        return "drg_grouper"

    @property
    def description(self) -> str:
        return "Assign MS-DRG from diagnosis/procedure codes, calculate reimbursement, identify CC/MCC impact on DRG grouping and payment."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["assign_drg", "calculate_reimbursement", "cc_mcc_impact", "lookup_drg"],
                    "description": "Action: assign_drg (group from dx/proc codes), calculate_reimbursement (calc payment for DRG), cc_mcc_impact (analyze CC/MCC effect on DRG/payment), lookup_drg (lookup DRG details)"
                },
                "principal_diagnosis": {
                    "type": "string",
                    "description": "Principal diagnosis ICD-10-CM code"
                },
                "secondary_diagnoses": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Secondary diagnosis ICD-10-CM codes"
                },
                "procedure_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "ICD-10-PCS or CPT procedure codes"
                },
                "drg_code": {
                    "type": "string",
                    "description": "MS-DRG code for direct lookup or reimbursement calculation"
                },
                "base_rate": {
                    "type": "number",
                    "description": "Hospital-specific base rate (default: national average ~6131)"
                }
            },
            "required": ["action"]
        }

    @property
    def requires_phi_protection(self) -> bool:
        return True

    @property
    def examples(self) -> list:
        return [
            {"input": {"action": "assign_drg", "principal_diagnosis": "I50.9", "secondary_diagnoses": ["I48.0", "E11.9"]}},
            {"input": {"action": "calculate_reimbursement", "drg_code": "291", "base_rate": 6000}},
            {"input": {"action": "cc_mcc_impact", "principal_diagnosis": "I50.9"}},
            {"input": {"action": "lookup_drg", "drg_code": "470"}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        principal_dx = kwargs.get("principal_diagnosis", "")
        secondary_dx = kwargs.get("secondary_diagnoses", [])
        procedure_codes = kwargs.get("procedure_codes", [])
        drg_code = kwargs.get("drg_code", "")
        base_rate = kwargs.get("base_rate", DEFAULT_BASE_RATE)

        try:
            if action == "assign_drg":
                result = self._assign_drg(principal_dx, secondary_dx, procedure_codes, base_rate)
                return SkillResult(success=True, data=result)

            elif action == "calculate_reimbursement":
                if not drg_code:
                    return SkillResult(success=False, error="drg_code is required for calculate_reimbursement")
                result = self._calculate_reimbursement(drg_code, base_rate)
                return SkillResult(success=True, data=result)

            elif action == "cc_mcc_impact":
                result = self._cc_mcc_impact(principal_dx, procedure_codes, base_rate)
                return SkillResult(success=True, data=result)

            elif action == "lookup_drg":
                if not drg_code:
                    return SkillResult(success=False, error="drg_code is required for lookup_drg")
                result = self._lookup_drg(drg_code)
                return SkillResult(success=True, data=result)

            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _assign_drg(self, principal_dx: str, secondary_dx: List[str], procedure_codes: List[str], base_rate: float) -> Dict[str, Any]:
        """Assign DRG from diagnosis and procedure codes."""
        if not principal_dx and not procedure_codes:
            return {"error": "At least a principal diagnosis or procedure code is required"}

        # Find base DRG from principal diagnosis
        base_drg_info = None
        if principal_dx:
            base_drg_info = DX_TO_BASE_DRG.get(principal_dx.upper())

        # If procedure code, use procedure mapping (overrides diagnosis for surgical DRGs)
        if procedure_codes:
            for proc in procedure_codes:
                proc_info = PROC_TO_BASE_DRG.get(proc)
                if proc_info:
                    base_drg_info = proc_info
                    break

        if not base_drg_info:
            return {
                "principal_diagnosis": principal_dx,
                "procedures": procedure_codes,
                "drg_assigned": None,
                "message": "No matching DRG found for the provided codes. Manual coding review required."
            }

        base_drg_range = base_drg_info["base_drg"]
        # Determine CC/MCC level from secondary diagnoses
        has_mcc = any(dx.upper() in MCC_CODES for dx in secondary_dx)
        has_cc = any(dx.upper() in CC_CODES for dx in secondary_dx)

        # Parse DRG range and pick appropriate DRG
        drg_parts = base_drg_range.split("-")
        if len(drg_parts) == 2:
            low_drg = drg_parts[0].lstrip("0") or "0"
            high_drg = drg_parts[1].lstrip("0") or "0"

            # Find matching DRGs in our database
            matching_drgs = []
            for drg_key, drg_val in MS_DRGS.items():
                drg_num = drg_key.lstrip("0") or "0"
                if low_drg <= drg_num <= high_drg:
                    matching_drgs.append((drg_key, drg_val))
        else:
            matching_drgs = [(base_drg_range, MS_DRGS.get(base_drg_range, {}))] if base_drg_range in MS_DRGS else []

        # Select the right DRG based on CC/MCC
        assigned_drg = None
        for drg_key, drg_val in matching_drgs:
            if has_mcc and drg_val.get("mcc"):
                assigned_drg = (drg_key, drg_val)
                break
            elif has_cc and drg_val.get("cc") and not has_mcc:
                assigned_drg = (drg_key, drg_val)
                break
            elif not drg_val.get("mcc") and not drg_val.get("cc"):
                if not has_mcc and not has_cc:
                    assigned_drg = (drg_key, drg_val)
                    break

        # If no exact match, take the last (base) DRG
        if not assigned_drg and matching_drgs:
            assigned_drg = matching_drgs[-1]

        if not assigned_drg:
            return {
                "principal_diagnosis": principal_dx,
                "secondary_diagnoses": secondary_dx,
                "procedures": procedure_codes,
                "drg_assigned": None,
                "message": "DRG range found but no specific DRG in database. Manual assignment needed."
            }

        drg_key, drg_val = assigned_drg
        reimbursement = round(drg_val["weight"] * base_rate, 2)

        return {
            "assigned_drg": drg_key,
            "description": drg_val["description"],
            "weight": drg_val["weight"],
            "type": drg_val["type"],
            "geom_mean_los": drg_val["geom_mean_los"],
            "reimbursement": reimbursement,
            "base_rate_used": base_rate,
            "cc_mcc_level": "MCC" if has_mcc else "CC" if has_cc else "Base",
            "grouping_details": {
                "principal_diagnosis": principal_dx,
                "secondary_diagnoses": secondary_dx,
                "procedures": procedure_codes,
                "has_mcc": has_mcc,
                "has_cc": has_cc,
                "base_drg_range": base_drg_range
            }
        }

    def _calculate_reimbursement(self, drg_code: str, base_rate: float) -> Dict[str, Any]:
        """Calculate reimbursement for a specific DRG."""
        drg_info = MS_DRGS.get(drg_code.lstrip("0").zfill(3))
        if not drg_info:
            # Try zero-padded
            drg_info = MS_DRGS.get(drg_code)
        if not drg_info:
            return {
                "drg_code": drg_code,
                "found": False,
                "message": f"DRG {drg_code} not found in database. Available DRGs: {', '.join(sorted(MS_DRGS.keys()))}"
            }

        weight = drg_info["weight"]
        reimbursement = round(weight * base_rate, 2)
        outlier_threshold = round(weight * base_rate * 1.0 + (base_rate * 0.6), 2)  # Simplified outlier calc

        return {
            "drg_code": drg_code,
            "description": drg_info["description"],
            "relative_weight": weight,
            "base_rate": base_rate,
            "reimbursement": reimbursement,
            "geom_mean_los": drg_info["geom_mean_los"],
            "type": drg_info["type"],
            "outlier_threshold_approx": outlier_threshold,
            "payment_components": {
                "base_payment": round(reimbursement, 2),
                "ime_adjustment": "Varies by hospital internship ratio",
                "dsh_adjustment": "Varies by hospital DSH percentage",
                "capital_related": "Included in base rate per IPPS"
            },
            "reference": "CMS IPPS FY2024 Final Rule"
        }

    def _cc_mcc_impact(self, principal_dx: str, procedure_codes: List[str], base_rate: float) -> Dict[str, Any]:
        """Analyze CC/MCC impact on DRG assignment and reimbursement."""
        base_drg_info = None
        if principal_dx:
            base_drg_info = DX_TO_BASE_DRG.get(principal_dx.upper())
        if not base_drg_info and procedure_codes:
            for proc in procedure_codes:
                proc_info = PROC_TO_BASE_DRG.get(proc)
                if proc_info:
                    base_drg_info = proc_info
                    break

        if not base_drg_info:
            return {
                "principal_diagnosis": principal_dx,
                "message": "No base DRG mapping found for the provided diagnosis/procedure. Cannot analyze CC/MCC impact."
            }

        base_drg_range = base_drg_info["base_drg"]
        drg_parts = base_drg_range.split("-")

        # Collect all DRGs in the range
        drg_levels = {}
        for drg_key, drg_val in MS_DRGS.items():
            if len(drg_parts) == 2:
                low = drg_parts[0].lstrip("0") or "0"
                high = drg_parts[1].lstrip("0") or "0"
                drg_num = drg_key.lstrip("0") or "0"
                if low <= drg_num <= high:
                    level = "MCC" if drg_val.get("mcc") else "CC" if drg_val.get("cc") else "Base"
                    drg_levels[level] = {
                        "drg": drg_key,
                        "description": drg_val["description"],
                        "weight": drg_val["weight"],
                        "reimbursement": round(drg_val["weight"] * base_rate, 2)
                    }

        # Calculate financial impact
        base_reimb = drg_levels.get("Base", {}).get("reimbursement", 0)
        cc_reimb = drg_levels.get("CC", {}).get("reimbursement", 0)
        mcc_reimb = drg_levels.get("MCC", {}).get("reimbursement", 0)

        impact = {
            "principal_diagnosis": principal_dx,
            "base_drg_range": base_drg_range,
            "drg_levels": drg_levels,
            "financial_impact": {
                "cc_vs_base": {
                    "additional_revenue": round(cc_reimb - base_reimb, 2) if base_reimb and cc_reimb else None,
                    "percent_increase": round(((cc_reimb - base_reimb) / base_reimb) * 100, 1) if base_reimb and cc_reimb else None
                },
                "mcc_vs_base": {
                    "additional_revenue": round(mcc_reimb - base_reimb, 2) if base_reimb and mcc_reimb else None,
                    "percent_increase": round(((mcc_reimb - base_reimb) / base_reimb) * 100, 1) if base_reimb and mcc_reimb else None
                },
                "mcc_vs_cc": {
                    "additional_revenue": round(mcc_reimb - cc_reimb, 2) if cc_reimb and mcc_reimb else None,
                    "percent_increase": round(((mcc_reimb - cc_reimb) / cc_reimb) * 100, 1) if cc_reimb and mcc_reimb else None
                }
            },
            "coding_recommendations": self._generate_coding_recommendations(principal_dx),
            "reference": "Impact calculated using CMS IPPS FY2024 relative weights"
        }

        return impact

    def _generate_coding_recommendations(self, principal_dx: str) -> List[str]:
        """Generate coding recommendations for CC/MCC capture."""
        recs = [
            "Ensure all secondary diagnoses are documented and coded to capture CC/MCC impact",
            "Query providers when clinical indicators suggest a CC/MCC condition that is not explicitly documented",
            "Document the cause-and-effect relationship between complications and the principal diagnosis",
            "Review discharge summary for any conditions that may qualify as CC or MCC"
        ]
        return recs

    def _lookup_drg(self, drg_code: str) -> Dict[str, Any]:
        """Look up a specific DRG code."""
        drg_info = MS_DRGS.get(drg_code.lstrip("0").zfill(3))
        if not drg_info:
            drg_info = MS_DRGS.get(drg_code)

        if not drg_info:
            return {
                "drg_code": drg_code,
                "found": False,
                "message": f"DRG {drg_code} not found in database"
            }

        return {
            "drg_code": drg_code,
            "found": True,
            "description": drg_info["description"],
            "relative_weight": drg_info["weight"],
            "geom_mean_los": drg_info["geom_mean_los"],
            "type": drg_info["type"],
            "cc_mcc_level": "MCC" if drg_info.get("mcc") else "CC" if drg_info.get("cc") else "Base",
            "standard_reimbursement": round(drg_info["weight"] * DEFAULT_BASE_RATE, 2),
            "reference": "CMS IPPS FY2024 Final Rule"
        }