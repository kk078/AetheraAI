"""
Aethera AI - APC Grouper Skill

APC assignment for outpatient services. Contains common APCs with status
indicators and payment rates. Supports: assign APC from CPT/HCPCS,
calculate OPPS payment, identify device-intensive procedures.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


# APC definitions with status indicators and payment rates
APC_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "0251": {"description": "Level 1 Eye Procedures", "status_indicator": "S", "payment_rate": 364.53, "weight": 0.562, "device_intensive": False},
    "0252": {"description": "Level 2 Eye Procedures", "status_indicator": "S", "payment_rate": 589.14, "weight": 0.908, "device_intensive": False},
    "0261": {"description": "Level 1 ENT Procedures", "status_indicator": "S", "payment_rate": 421.67, "weight": 0.650, "device_intensive": False},
    "0262": {"description": "Level 2 ENT Procedures", "status_indicator": "S", "payment_rate": 712.89, "weight": 1.099, "device_intensive": False},
    "0269": {"description": "Level 3 ENT Procedures", "status_indicator": "S", "payment_rate": 1123.45, "weight": 1.732, "device_intensive": False},
    "0301": {"description": "Level 1 Musculoskeletal Procedures", "status_indicator": "S", "payment_rate": 478.32, "weight": 0.737, "device_intensive": False},
    "0302": {"description": "Level 2 Musculoskeletal Procedures", "status_indicator": "S", "payment_rate": 867.45, "weight": 1.338, "device_intensive": False},
    "0303": {"description": "Level 3 Musculoskeletal Procedures", "status_indicator": "S", "payment_rate": 1456.78, "weight": 2.246, "device_intensive": False},
    "0304": {"description": "Level 4 Musculoskeletal Procedures", "status_indicator": "T", "payment_rate": 2345.67, "weight": 3.616, "device_intensive": True},
    "0305": {"description": "Level 5 Musculoskeletal Procedures", "status_indicator": "T", "payment_rate": 3456.78, "weight": 5.329, "device_intensive": True},
    "0401": {"description": "Level 1 Nervous System Procedures", "status_indicator": "S", "payment_rate": 534.21, "weight": 0.824, "device_intensive": False},
    "0402": {"description": "Level 2 Nervous System Procedures", "status_indicator": "S", "payment_rate": 987.65, "weight": 1.522, "device_intensive": False},
    "0403": {"description": "Level 3 Nervous System Procedures", "status_indicator": "T", "payment_rate": 2345.67, "weight": 3.616, "device_intensive": True},
    "0501": {"description": "Level 1 Cardiac Procedures", "status_indicator": "S", "payment_rate": 678.90, "weight": 1.046, "device_intensive": False},
    "0502": {"description": "Level 2 Cardiac Procedures", "status_indicator": "S", "payment_rate": 1456.78, "weight": 2.246, "device_intensive": False},
    "0503": {"description": "Level 3 Cardiac Procedures", "status_indicator": "T", "payment_rate": 3456.78, "weight": 5.329, "device_intensive": True},
    "0504": {"description": "Level 4 Cardiac Procedures", "status_indicator": "T", "payment_rate": 6789.12, "weight": 10.466, "device_intensive": True},
    "0601": {"description": "Level 1 GI Procedures", "status_indicator": "S", "payment_rate": 421.67, "weight": 0.650, "device_intensive": False},
    "0602": {"description": "Level 2 GI Procedures", "status_indicator": "S", "payment_rate": 867.45, "weight": 1.338, "device_intensive": False},
    "0603": {"description": "Level 3 GI Procedures", "status_indicator": "S", "payment_rate": 1456.78, "weight": 2.246, "device_intensive": False},
    "0604": {"description": "Level 4 GI Procedures", "status_indicator": "T", "payment_rate": 2345.67, "weight": 3.616, "device_intensive": True},
    "0801": {"description": "Level 1 Skin Procedures", "status_indicator": "S", "payment_rate": 364.53, "weight": 0.562, "device_intensive": False},
    "0802": {"description": "Level 2 Skin Procedures", "status_indicator": "S", "payment_rate": 712.89, "weight": 1.099, "device_intensive": False},
    "0803": {"description": "Level 3 Skin Procedures", "status_indicator": "S", "payment_rate": 1123.45, "weight": 1.732, "device_intensive": False},
    "0620": {"description": "Level 1 Imaging - MR", "status_indicator": "S", "payment_rate": 478.32, "weight": 0.737, "device_intensive": False},
    "0621": {"description": "Level 2 Imaging - MR", "status_indicator": "S", "payment_rate": 867.45, "weight": 1.338, "device_intensive": False},
    "0622": {"description": "Level 3 Imaging - MR", "status_indicator": "S", "payment_rate": 1456.78, "weight": 2.246, "device_intensive": False},
    "0700": {"description": "Level 1 Imaging - CT", "status_indicator": "S", "payment_rate": 364.53, "weight": 0.562, "device_intensive": False},
    "0701": {"description": "Level 2 Imaging - CT", "status_indicator": "S", "payment_rate": 534.21, "weight": 0.824, "device_intensive": False},
    "0710": {"description": "Level 1 Imaging - CT with contrast", "status_indicator": "S", "payment_rate": 478.32, "weight": 0.737, "device_intensive": False},
}

# CPT/HCPCS to APC mapping
CPT_TO_APC: Dict[str, Dict[str, Any]] = {
    # Eye procedures
    "65778": {"apc": "0251", "description": "Penetrating keratoplasty without removal of cornea"},
    "65779": {"apc": "0252", "description": "Penetrating keratoplasty with removal of cornea"},
    # ENT procedures
    "30120": {"apc": "0261", "description": "Excision or destruction of turbinate"},
    "31267": {"apc": "0262", "description": "Nasal/sinus endoscopy with frontal sinus exploration"},
    "43239": {"apc": "0602", "description": "Upper GI endoscopy with biopsy"},
    # Musculoskeletal
    "27447": {"apc": "0304", "description": "Total knee arthroplasty", "device_intensive": True},
    "27130": {"apc": "0304", "description": "Total hip arthroplasty", "device_intensive": True},
    "29881": {"apc": "0302", "description": "Knee arthroscopy with meniscectomy"},
    # Nervous system
    "62323": {"apc": "0401", "description": "Injection for lumbar transforaminal epidural"},
    "64483": {"apc": "0401", "description": "Injection anesthetic agent lumbar transforaminal epidural"},
    # Cardiac
    "93306": {"apc": "0501", "description": "Transthoracic echocardiography with spectral Doppler"},
    "93000": {"apc": "0501", "description": "ECG with interpretation and report"},
    # GI
    "43235": {"apc": "0601", "description": "Upper GI endoscopy diagnostic"},
    "43239": {"apc": "0602", "description": "Upper GI endoscopy with biopsy"},
    "45380": {"apc": "0602", "description": "Colonoscopy with biopsy"},
    "45378": {"apc": "0601", "description": "Colonoscopy diagnostic"},
    # Skin
    "11400": {"apc": "0801", "description": "Excision benign lesion trunk 0.6-1.0cm"},
    "11600": {"apc": "0801", "description": "Excision malignant lesion trunk 0.6-1.0cm"},
    "17000": {"apc": "0801", "description": "Destruction premalignant lesion first"},
    # Imaging
    "70553": {"apc": "0622", "description": "MRI brain with and without contrast"},
    "72148": {"apc": "0620", "description": "MRI lumbar spine without contrast"},
    "71045": {"apc": "0700", "description": "Chest X-ray 1 view"},
    "71046": {"apc": "0700", "description": "Chest X-ray 2 views"},
    # E/M and other common outpatient services
    "99211": {"apc": "0805", "description": "Office visit established patient low complexity", "si": "V"},
    "99212": {"apc": "0805", "description": "Office visit established patient low complexity", "si": "V"},
    "99213": {"apc": "0806", "description": "Office visit established patient low complexity", "si": "V"},
    "99214": {"apc": "0806", "description": "Office visit established patient moderate complexity", "si": "V"},
    "99215": {"apc": "0807", "description": "Office visit established patient high complexity", "si": "V"},
    # Labs and pathology
    "80053": {"apc": "0403", "description": "Comprehensive metabolic panel", "si": "Q1"},
    "85025": {"apc": "0403", "description": "CBC with auto differential", "si": "Q1"},
}

# Status indicator definitions
STATUS_INDICATORS: Dict[str, Dict[str, Any]] = {
    "S": {"description": "Significant procedure, not discounted when multiple", "payment": "APC rate. No discount for multiple procedures."},
    "T": {"description": "Significant procedure, multiple procedure reduction applies", "payment": "APC rate for highest paid; 50% for subsequent T procedures."},
    "V": {"description": "Visit services (clinic or emergency department visits)", "payment": "APC rate. Packaged services may apply."},
    "Q1": {"description": "Composite APC - packaged service", "payment": "Composite APC rate or packaged into primary service."},
    "Q2": {"description": "Composite APC - STVX packaged", "payment": "Composite rate; packaged with visit/procedure APC."},
    "Q3": {"description": "Composite APC - surgical packaged", "payment": "Surgical composite rate."},
    "N": {"description": "Items and services packaged into APC rates", "payment": "Payment packaged into associated service APC."},
    "J1": {"description": "Comprehensive APC - device-intensive procedure", "payment": "Single comprehensive APC rate includes all related services and devices."},
    "J2": {"description": "Comprehensive APC - device-intensive procedure", "payment": "Single comprehensive APC rate includes all related services and devices."},
    "R": {"description": "Blood and blood products", "payment": "Payment at APC rate; separate add-on for blood product costs."},
    "U": {"description": "New technology APC", "payment": "New technology APC rate. Temporary status pending reassignment."},
    "X": {"description": "Ancillary services", "payment": "Packaged into primary service APC."},
}

# Device-intensive procedure list (selected)
DEVICE_INTENSIVE_PROCEDURES: Dict[str, Dict[str, Any]] = {
    "27447": {"description": "Total knee arthroplasty", "device_category": "Implant - Knee", "offset_pct": 0.50},
    "27130": {"description": "Total hip arthroplasty", "device_category": "Implant - Hip", "offset_pct": 0.55},
    "33510": {"description": "Heart transplant", "device_category": "Transplant", "offset_pct": 0.0},
    "43239": {"description": "Upper GI endoscopy with biopsy", "device_category": "Endoscope", "offset_pct": 0.0},
    "22551": {"description": "Anterior interbody fusion lumbar", "device_category": "Implant - Spine", "offset_pct": 0.60},
}


@skill(name="apc_grouper", category="healthcare")
class APCGrouperSkill(AetheraSkill):
    """
    APC assignment for outpatient services under OPPS.
    """

    @property
    def name(self) -> str:
        return "apc_grouper"

    @property
    def description(self) -> str:
        return "Assign APC from CPT/HCPCS codes, calculate OPPS payment, identify device-intensive procedures and status indicators."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["assign_apc", "calculate_opps_payment", "lookup_apc", "device_intensive_check", "status_indicator_info"],
                    "description": "Action: assign_apc (assign APC from CPT), calculate_opps_payment (calc OPPS payment), lookup_apc (lookup APC details), device_intensive_check (check if device-intensive), status_indicator_info (explain status indicator)"
                },
                "cpt_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CPT/HCPCS codes to classify"
                },
                "apc_code": {
                    "type": "string",
                    "description": "APC code for direct lookup"
                },
                "status_indicator": {
                    "type": "string",
                    "description": "Status indicator code to look up (e.g., S, T, V, Q1, N)"
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
            {"input": {"action": "assign_apc", "cpt_codes": ["99213", "85025"]}},
            {"input": {"action": "calculate_opps_payment", "cpt_codes": ["93306", "93000"]}},
            {"input": {"action": "lookup_apc", "apc_code": "0602"}},
            {"input": {"action": "device_intensive_check", "cpt_codes": ["27447"]}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        cpt_codes = kwargs.get("cpt_codes", [])
        apc_code = kwargs.get("apc_code", "")
        status_indicator = kwargs.get("status_indicator", "")

        try:
            if action == "assign_apc":
                if not cpt_codes:
                    return SkillResult(success=False, error="cpt_codes is required for assign_apc")
                result = self._assign_apc(cpt_codes)
                return SkillResult(success=True, data=result)

            elif action == "calculate_opps_payment":
                if not cpt_codes:
                    return SkillResult(success=False, error="cpt_codes is required for calculate_opps_payment")
                result = self._calculate_opps_payment(cpt_codes)
                return SkillResult(success=True, data=result)

            elif action == "lookup_apc":
                if not apc_code:
                    return SkillResult(success=False, error="apc_code is required for lookup_apc")
                result = self._lookup_apc(apc_code)
                return SkillResult(success=True, data=result)

            elif action == "device_intensive_check":
                if not cpt_codes:
                    return SkillResult(success=False, error="cpt_codes is required for device_intensive_check")
                result = self._device_intensive_check(cpt_codes)
                return SkillResult(success=True, data=result)

            elif action == "status_indicator_info":
                result = self._status_indicator_info(status_indicator)
                return SkillResult(success=True, data=result)

            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _assign_apc(self, cpt_codes: List[str]) -> Dict[str, Any]:
        """Assign APC from CPT/HCPCS codes."""
        assignments = []
        for cpt in cpt_codes:
            cpt_info = CPT_TO_APC.get(cpt)
            if cpt_info:
                apc_code = cpt_info["apc"]
                apc_info = APC_DEFINITIONS.get(apc_code, {})
                assignments.append({
                    "cpt_code": cpt,
                    "apc_code": apc_code,
                    "apc_description": apc_info.get("description", ""),
                    "cpt_description": cpt_info.get("description", ""),
                    "status_indicator": apc_info.get("status_indicator", cpt_info.get("si", "S")),
                    "payment_rate": apc_info.get("payment_rate", 0),
                    "device_intensive": apc_info.get("device_intensive", False),
                    "found": True
                })
            else:
                assignments.append({
                    "cpt_code": cpt,
                    "found": False,
                    "message": f"CPT {cpt} not found in APC mapping database"
                })

        return {
            "assignments": assignments,
            "total_codes_submitted": len(cpt_codes),
            "codes_found": sum(1 for a in assignments if a.get("found")),
            "device_intensive_count": sum(1 for a in assignments if a.get("device_intensive"))
        }

    def _calculate_opps_payment(self, cpt_codes: List[str]) -> Dict[str, Any]:
        """Calculate OPPS payment for a set of CPT codes."""
        line_items = []
        total_payment = 0.0

        # Sort by payment rate descending for multiple procedure reduction
        sorted_codes = []
        for cpt in cpt_codes:
            cpt_info = CPT_TO_APC.get(cpt)
            if cpt_info:
                apc_code = cpt_info["apc"]
                apc_info = APC_DEFINITIONS.get(apc_code, {})
                sorted_codes.append((cpt, cpt_info, apc_code, apc_info))
            else:
                sorted_codes.append((cpt, None, None, None))

        # Apply multiple procedure reduction for T-status procedures
        t_procedures = [(c, ci, ac, ai) for c, ci, ac, ai in sorted_codes
                        if ai and ai.get("status_indicator") == "T"]
        other_procedures = [(c, ci, ac, ai) for c, ci, ac, ai in sorted_codes
                           if ai and ai.get("status_indicator") != "T"]

        # Sort T procedures by payment descending
        t_procedures.sort(key=lambda x: x[3].get("payment_rate", 0), reverse=True)

        for idx, (cpt, cpt_info, apc_code, apc_info) in enumerate(t_procedures):
            rate = apc_info.get("payment_rate", 0)
            if idx == 0:
                adjusted_rate = rate  # Highest paid at full rate
                discount_applied = False
            else:
                adjusted_rate = round(rate * 0.50, 2)  # 50% for subsequent T procedures
                discount_applied = True
            total_payment += adjusted_rate
            line_items.append({
                "cpt_code": cpt,
                "description": cpt_info.get("description", "") if cpt_info else "Unknown",
                "apc_code": apc_code,
                "apc_description": apc_info.get("description", "") if apc_info else "",
                "status_indicator": "T",
                "base_rate": rate,
                "adjusted_rate": adjusted_rate,
                "discount_applied": discount_applied,
                "discount_pct": 50 if discount_applied else 0,
                "device_intensive": apc_info.get("device_intensive", False) if apc_info else False
            })

        for cpt, cpt_info, apc_code, apc_info in other_procedures:
            if not cpt_info or not apc_info:
                line_items.append({
                    "cpt_code": cpt,
                    "found": False,
                    "message": f"CPT {cpt} not found in APC database"
                })
                continue
            rate = apc_info.get("payment_rate", 0)
            si = apc_info.get("status_indicator", cpt_info.get("si", "S"))
            total_payment += rate
            line_items.append({
                "cpt_code": cpt,
                "description": cpt_info.get("description", ""),
                "apc_code": apc_code,
                "apc_description": apc_info.get("description", ""),
                "status_indicator": si,
                "base_rate": rate,
                "adjusted_rate": rate,
                "discount_applied": False,
                "discount_pct": 0,
                "device_intensive": apc_info.get("device_intensive", False)
            })

        copay_pct = 0.20  # Standard 20% coinsurance for most OPPS services

        return {
            "line_items": line_items,
            "total_opps_payment": round(total_payment, 2),
            "copay_amount": round(total_payment * copay_pct, 2),
            "copay_pct": f"{int(copay_pct * 100)}%",
            "multiple_proc_reduction_applied": len(t_procedures) > 1,
            "notes": "Payment estimates based on national OPPS rates. Actual payments vary by hospital and region.",
            "reference": "CMS OPPS CY2024 Final Rule"
        }

    def _lookup_apc(self, apc_code: str) -> Dict[str, Any]:
        """Look up an APC by code."""
        apc_info = APC_DEFINITIONS.get(apc_code)
        if not apc_info:
            return {
                "apc_code": apc_code,
                "found": False,
                "message": f"APC {apc_code} not found in database"
            }

        # Find CPT codes mapped to this APC
        mapped_cpts = [
            {"cpt": cpt, "description": info.get("description", "")}
            for cpt, info in CPT_TO_APC.items()
            if info.get("apc") == apc_code
        ]

        si_code = apc_info.get("status_indicator", "")
        si_info = STATUS_INDICATORS.get(si_code, {})

        return {
            "apc_code": apc_code,
            "found": True,
            "description": apc_info["description"],
            "status_indicator": si_code,
            "status_indicator_description": si_info.get("description", ""),
            "payment_rate": apc_info["payment_rate"],
            "weight": apc_info["weight"],
            "device_intensive": apc_info["device_intensive"],
            "mapped_cpt_codes": mapped_cpts,
            "reference": "CMS OPPS CY2024 Final Rule"
        }

    def _device_intensive_check(self, cpt_codes: List[str]) -> Dict[str, Any]:
        """Check if CPT codes are device-intensive procedures."""
        results = []
        for cpt in cpt_codes:
            # Check CPT mapping for device-intensive flag
            cpt_info = CPT_TO_APC.get(cpt)
            if cpt_info:
                apc_code = cpt_info["apc"]
                apc_info = APC_DEFINITIONS.get(apc_code, {})
                is_device_intensive = apc_info.get("device_intensive", False) or cpt_info.get("device_intensive", False)
            else:
                is_device_intensive = False

            # Check device-intensive procedure list
            device_info = DEVICE_INTENSIVE_PROCEDURES.get(cpt)

            result_item = {
                "cpt_code": cpt,
                "is_device_intensive": is_device_intensive,
                "device_category": device_info.get("device_category", "") if device_info else "",
                "device_offset_pct": device_info.get("offset_pct", 0) if device_info else 0,
                "description": device_info.get("description", cpt_info.get("description", "")) if device_info or cpt_info else "Unknown"
            }
            results.append(result_item)

        device_intensive_count = sum(1 for r in results if r["is_device_intensive"])

        return {
            "results": results,
            "total_codes": len(cpt_codes),
            "device_intensive_count": device_intensive_count,
            "device_offset_note": "Device-intensive APCs include device cost in payment rate. Hospitals must report device credits (modifier FB/FC/FD) for refunded devices.",
            "reference": "CMS OPPS CY2024 Final Rule - Device-intensive procedures"
        }

    def _status_indicator_info(self, status_indicator: str) -> Dict[str, Any]:
        """Get information about a status indicator."""
        if status_indicator:
            si_info = STATUS_INDICATORS.get(status_indicator.upper())
            if si_info:
                return {
                    "status_indicator": status_indicator.upper(),
                    "description": si_info["description"],
                    "payment_rules": si_info["payment"],
                    "found": True
                }
            else:
                return {
                    "status_indicator": status_indicator,
                    "found": False,
                    "message": f"Unknown status indicator: {status_indicator}",
                    "available_indicators": list(STATUS_INDICATORS.keys())
                }
        else:
            return {
                "all_status_indicators": [
                    {"code": k, "description": v["description"], "payment": v["payment"]}
                    for k, v in STATUS_INDICATORS.items()
                ],
                "reference": "CMS OPPS CY2024 Final Rule"
            }