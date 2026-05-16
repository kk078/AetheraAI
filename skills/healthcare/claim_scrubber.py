"""
Aethera AI - Claim Scrubber Skill

Pre-submission claim validation: ICD-10 format, CPT format, CCI edits,
MUE limits, diagnosis-procedure consistency, modifier rules, place of service.
Returns a risk score and list of issues.
"""

import re
from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="claim_scrubber", category="healthcare")
class ClaimScrubberSkill(AetheraSkill):
    """
    Pre-submission claim validation and scrubbing.
    Checks coding accuracy, CCI edits, MUE limits, and consistency.
    """

    @property
    def name(self) -> str:
        return "claim_scrubber"

    @property
    def description(self) -> str:
        return "Pre-submission claim validation: ICD-10/CPT format, CCI edits, MUE limits, diagnosis-procedure consistency, modifier rules, POS consistency. Returns risk score and issue list."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "diagnosis_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "ICD-10-CM diagnosis codes on the claim"
                },
                "procedure_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CPT/HCPCS procedure codes on the claim"
                },
                "modifiers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Modifiers paired 1:1 with procedure_codes (use '' for none)"
                },
                "place_of_service": {
                    "type": "string",
                    "description": "Place of service code (e.g., 11, 21, 22)"
                },
                "units": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Units for each procedure code"
                },
                "payer": {
                    "type": "string",
                    "description": "Payer name for payer-specific rules"
                }
            },
            "required": ["diagnosis_codes", "procedure_codes"]
        }

    @property
    def requires_phi_protection(self) -> bool:
        return True

    @property
    def examples(self) -> list:
        return [
            {
                "input": {
                    "diagnosis_codes": ["E11.9", "I10"],
                    "procedure_codes": ["99213", "85025"],
                    "modifiers": ["", ""],
                    "place_of_service": "11"
                }
            },
            {
                "input": {
                    "diagnosis_codes": ["M54.5"],
                    "procedure_codes": ["99214", "97110", "97110"],
                    "modifiers": ["", "", "76"],
                    "place_of_service": "11"
                }
            }
        ]

    # --- ICD-10-CM format: A00-Z99, letter + 2 digits [. 1-4 alphanum] ---
    ICD10_PATTERN = re.compile(
        r"^[A-Z]\d{2}(\.[A-Z0-9]{1,4})?$"
    )

    # --- CPT format: 5 digits, first digit 0-9, no alpha in Category I ---
    CPT_PATTERN = re.compile(
        r"^\d{5}[A-Z]?$"
    )

    # --- MUE limits per CPT (CMS Medically Unlikely Edits) ---
    MUE_LIMITS: Dict[str, int] = {
        "99211": 4, "99212": 4, "99213": 4, "99214": 4, "99215": 4,
        "99281": 3, "99282": 3, "99283": 3, "99284": 3, "99285": 3,
        "99291": 1, "99292": 1,
        "36415": 1, "36416": 1,
        "85025": 1, "85027": 1,
        "80053": 1, "80061": 1,
        "83036": 1,
        "84443": 1,
        "86580": 1,
        "90471": 1, "90472": 1, "90473": 1, "90474": 1,
        "90480": 1,
        "90734": 1,
        "90735": 1,
        "93000": 1, "93010": 1, "93040": 1,
        "93306": 1, "93307": 1, "93308": 1,
        "94010": 2,
        "94060": 1,
        "94070": 1,
        "94726": 1, "94727": 1, "94729": 1,
        "95816": 1, "95819": 1,
        "97110": 1, "97112": 1, "97113": 1, "97116": 1,
        "97140": 1,
        "97150": 1,
        "97530": 1,
        "97535": 1,
        "97537": 1,
        "97750": 1, "97755": 1, "97760": 1,
        "10060": 1, "10061": 1,
        "11400": 1, "11401": 1, "11402": 1, "11403": 1,
        "11600": 1, "11601": 1, "11602": 1,
        "11900": 1,
        "12001": 1, "12002": 1,
        "15780": 1,
        "17000": 1, "17003": 1,
        "19000": 1,
        "20610": 1,
        "22551": 1,
        "27447": 1,
        "29881": 1,
        "43239": 1,
        "47562": 1,
        "49505": 1,
        "52000": 1,
        "62323": 1,
        "64483": 1,
        "70553": 1,
        "71045": 1, "71046": 1,
        "72148": 1,
        "73221": 1,
        "76700": 1,
        "77067": 1,
    }

    # --- CCI edit pairs (column 1, column 2, modifier indicator) ---
    # modifier_indicator: 0 = never allowed together, 1 = allowed with modifier, 9 = not applicable
    CCI_EDITS: List[Dict[str, Any]] = [
        {"col1": "99213", "col2": "99214", "modifier_indicator": 0},
        {"col1": "99214", "col2": "99215", "modifier_indicator": 0},
        {"col1": "99213", "col2": "99215", "modifier_indicator": 0},
        {"col1": "99211", "col2": "99213", "modifier_indicator": 0},
        {"col1": "93000", "col2": "93010", "modifier_indicator": 0},
        {"col1": "93000", "col2": "93040", "modifier_indicator": 0},
        {"col1": "93306", "col2": "93307", "modifier_indicator": 0},
        {"col1": "93306", "col2": "93308", "modifier_indicator": 0},
        {"col1": "94010", "col2": "94060", "modifier_indicator": 1},
        {"col1": "94010", "col2": "94070", "modifier_indicator": 1},
        {"col1": "97110", "col2": "97112", "modifier_indicator": 1},
        {"col1": "97110", "col2": "97113", "modifier_indicator": 1},
        {"col1": "97110", "col2": "97116", "modifier_indicator": 1},
        {"col1": "97112", "col2": "97113", "modifier_indicator": 1},
        {"col1": "97110", "col2": "97530", "modifier_indicator": 1},
        {"col1": "97110", "col2": "97140", "modifier_indicator": 1},
        {"col1": "97112", "col2": "97140", "modifier_indicator": 1},
        {"col1": "97113", "col2": "97140", "modifier_indicator": 1},
        {"col1": "97140", "col2": "97530", "modifier_indicator": 1},
        {"col1": "97140", "col2": "97535", "modifier_indicator": 1},
        {"col1": "97530", "col2": "97535", "modifier_indicator": 1},
        {"col1": "97530", "col2": "97537", "modifier_indicator": 1},
        {"col1": "97535", "col2": "97537", "modifier_indicator": 1},
        {"col1": "71045", "col2": "71046", "modifier_indicator": 0},
        {"col1": "70553", "col2": "70551", "modifier_indicator": 0},
        {"col1": "72148", "col2": "72156", "modifier_indicator": 0},
        {"col1": "73221", "col2": "73225", "modifier_indicator": 0},
        {"col1": "76700", "col2": "76770", "modifier_indicator": 0},
        {"col1": "80053", "col2": "80061", "modifier_indicator": 0},
        {"col1": "80053", "col2": "83036", "modifier_indicator": 0},
        {"col1": "84443", "col2": "84439", "modifier_indicator": 0},
        {"col1": "85025", "col2": "85027", "modifier_indicator": 0},
        {"col1": "90471", "col2": "90472", "modifier_indicator": 1},
        {"col1": "90473", "col2": "90474", "modifier_indicator": 1},
        {"col1": "11400", "col2": "11401", "modifier_indicator": 0},
        {"col1": "11401", "col2": "11402", "modifier_indicator": 0},
        {"col1": "11600", "col2": "11601", "modifier_indicator": 0},
        {"col1": "10060", "col2": "10061", "modifier_indicator": 0},
        {"col1": "12001", "col2": "12002", "modifier_indicator": 0},
        {"col1": "17000", "col2": "17003", "modifier_indicator": 0},
        {"col1": "29881", "col2": "29880", "modifier_indicator": 0},
        {"col1": "27447", "col2": "27486", "modifier_indicator": 0},
        {"col1": "22551", "col2": "22612", "modifier_indicator": 1},
        {"col1": "62323", "col2": "62327", "modifier_indicator": 0},
        {"col1": "64483", "col2": "64484", "modifier_indicator": 0},
        {"col1": "52000", "col2": "51701", "modifier_indicator": 1},
        {"col1": "43239", "col2": "43235", "modifier_indicator": 0},
        {"col1": "47562", "col2": "47563", "modifier_indicator": 0},
        {"col1": "49505", "col2": "49507", "modifier_indicator": 0},
        {"col1": "20610", "col2": "20600", "modifier_indicator": 0},
    ]

    # --- Diagnosis-Procedure consistency matrix ---
    # Maps CPT category -> typical ICD-10 chapter prefixes
    DIAG_PROC_CONSISTENCY: Dict[str, List[str]] = {
        # E/M visits: any diagnosis is plausible
        "992": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
                "N", "O", "P", "Q", "R", "S", "T", "V", "W", "X", "Y", "Z"],
        # EKG
        "930": ["I", "R", "Z"],
        # Echocardiography
        "933": ["I", "Q", "R", "Z"],
        # Pulmonary function
        "940": ["J", "R", "Z"],
        # PT/OT
        "971": ["M", "G", "S", "R"],
        "975": ["M", "G", "S", "R"],
        "977": ["M", "G", "S", "R"],
        # Radiology
        "710": ["J", "R", "Z", "S"],
        "705": ["G", "H", "M", "R", "Z"],
        "721": ["M", "R", "S", "Z"],
        "732": ["M", "S", "Z"],
        # Ultrasound
        "767": ["K", "N", "R", "Z"],
        # Mammography
        "770": ["C", "N", "R", "Z"],
        # Lab
        "800": ["A", "B", "C", "D", "E", "G", "I", "J", "K", "N", "R", "Z"],
        "830": ["D", "E", "N", "R", "Z"],
        "844": ["D", "E", "G", "N", "R", "Z"],
        "850": ["D", "D", "N", "R", "Z"],
        "865": ["A", "B", "R", "Z"],
        # Vaccines
        "904": ["B", "U", "Z"],
        "907": ["B", "U", "Z"],
        # Surgery integumentary
        "100": ["C", "L", "S", "T", "Z"],
        "114": ["C", "D", "L", "S", "T", "Z"],
        "116": ["C", "D", "L", "S", "T", "Z"],
        "119": ["C", "L", "S", "Z"],
        "120": ["S", "T", "W", "Z"],
        "157": ["L", "S", "Z"],
        "170": ["C", "D", "L", "S", "Z"],
        # Musculoskeletal surgery
        "206": ["M", "S", "Z"],
        "225": ["M", "S", "Z"],
        "274": ["M", "S", "Z"],
        "298": ["M", "S", "Z"],
        # GI
        "432": ["K", "C", "R", "Z"],
        "475": ["K", "C", "R", "Z"],
        "495": ["K", "C", "R", "Z"],
        # GU
        "520": ["N", "R", "Z"],
        "623": ["G", "M", "R", "S", "Z"],
        "644": ["G", "M", "R", "S", "Z"],
    }

    # --- Modifier rules ---
    MODIFIER_RULES: Dict[str, Dict[str, Any]] = {
        "25": {
            "description": "Significant, separately identifiable E/M service",
            "requires": "Must have separate diagnosis or documentation",
            "valid_with": ["99211", "99212", "99213", "99214", "99215",
                           "99281", "99282", "99283", "99284", "99285",
                           "99291", "99292"],
            "invalid_with": []
        },
        "59": {
            "description": "Distinct procedural service",
            "requires": "Procedures must be distinct (different site, session, etc.)",
            "valid_with": "any_procedure",
            "invalid_with": []
        },
        "76": {
            "description": "Repeat procedure by same physician",
            "requires": "Same procedure repeated on same day",
            "valid_with": "any_procedure",
            "invalid_with": []
        },
        "77": {
            "description": "Repeat procedure by different physician",
            "requires": "Same procedure repeated by different provider",
            "valid_with": "any_procedure",
            "invalid_with": []
        },
        "26": {
            "description": "Professional component",
            "requires": "Radiology/pathology procedure with separate professional component",
            "valid_with": ["71045", "71046", "70553", "72148", "73221", "76700",
                           "77067", "93000", "93010", "93040", "94010",
                           "80053", "80061", "85025", "83036", "84443", "86580"],
            "invalid_with": ["99211", "99212", "99213", "99214", "99215"]
        },
        "TC": {
            "description": "Technical component",
            "requires": "Radiology/pathology procedure with separate technical component",
            "valid_with": ["71045", "71046", "70553", "72148", "73221", "76700",
                           "77067", "93000", "93010", "93040", "94010",
                           "80053", "80061", "85025", "83036", "84443", "86580"],
            "invalid_with": ["99211", "99212", "99213", "99214", "99215"]
        },
        "LT": {
            "description": "Left side",
            "requires": "Procedure performed on left side of body",
            "valid_with": "any_procedure",
            "invalid_with": []
        },
        "RT": {
            "description": "Right side",
            "requires": "Procedure performed on right side of body",
            "valid_with": "any_procedure",
            "invalid_with": []
        },
        "50": {
            "description": "Bilateral procedure",
            "requires": "Same procedure performed on both sides",
            "valid_with": "any_procedure",
            "invalid_with": []
        },
    }

    # --- Place of service consistency ---
    # Maps POS code -> allowed CPT prefixes
    POS_CONSISTENCY: Dict[str, Dict[str, Any]] = {
        "11": {
            "description": "Office",
            "typical_cpt_prefixes": ["992", "9921", "99211", "99212", "99213",
                                     "99214", "99215", "9938", "9939",
                                     "364", "850", "800", "830", "844",
                                     "904", "907", "170", "100",
                                     "971", "975", "977",
                                     "930", "933", "940"],
            "invalid_cpt_prefixes": ["99281", "99282", "99283", "99284", "99285", "99291"]
        },
        "19": {
            "description": "Off campus-outpatient hospital",
            "typical_cpt_prefixes": ["992", "9921", "99281", "99282", "99283", "99284",
                                     "930", "933", "940", "710", "705", "721", "732",
                                     "767", "770"],
            "invalid_cpt_prefixes": []
        },
        "21": {
            "description": "Inpatient hospital",
            "typical_cpt_prefixes": ["99221", "99222", "99223", "99231", "99232",
                                     "99233", "99238", "99239", "99251", "99252",
                                     "99253", "99254", "99255", "99281", "99282",
                                     "99283", "99284", "99285", "99291", "99292",
                                     "930", "933", "940"],
            "invalid_cpt_prefixes": ["99211", "99212", "99213", "99214", "99215",
                                     "99381", "99382", "99383", "99384", "99385",
                                     "99391", "99392", "99393", "99394", "99395"]
        },
        "22": {
            "description": "Outpatient hospital",
            "typical_cpt_prefixes": ["992", "99281", "99282", "99283", "99284",
                                     "99285", "99291", "930", "933", "940",
                                     "710", "705", "721", "732", "767", "770"],
            "invalid_cpt_prefixes": []
        },
        "23": {
            "description": "Emergency room - hospital",
            "typical_cpt_prefixes": ["99281", "99282", "99283", "99284", "99285",
                                     "99291", "930", "933", "940"],
            "invalid_cpt_prefixes": ["99211", "99212", "99213", "99214", "99215",
                                     "9938", "9939"]
        },
        "24": {
            "description": "Ambulatory surgical center",
            "typical_cpt_prefixes": ["100", "114", "116", "119", "120", "157",
                                     "170", "190", "206", "225", "274", "298",
                                     "432", "475", "495", "520", "623", "644"],
            "invalid_cpt_prefixes": ["99221", "99222", "99223", "99231", "99232",
                                     "99233", "99291", "99292"]
        },
    }

    async def execute(self, **kwargs) -> SkillResult:
        diagnosis_codes = kwargs.get("diagnosis_codes", [])
        procedure_codes = kwargs.get("procedure_codes", [])
        modifiers = kwargs.get("modifiers", [])
        place_of_service = kwargs.get("place_of_service", "")
        units = kwargs.get("units", [])
        payer = kwargs.get("payer", "")

        if not diagnosis_codes and not procedure_codes:
            return SkillResult(success=False, error="Diagnosis codes and/or procedure codes are required")

        issues: List[Dict[str, Any]] = []

        # Pad modifiers and units lists to match procedure_codes length
        while len(modifiers) < len(procedure_codes):
            modifiers.append("")
        while len(units) < len(procedure_codes):
            units.append(1)

        # 1. Validate ICD-10-CM format
        for dx in diagnosis_codes:
            fmt_issue = self._validate_icd10(dx)
            if fmt_issue:
                issues.append(fmt_issue)

        # 2. Validate CPT format
        for proc in procedure_codes:
            fmt_issue = self._validate_cpt(proc)
            if fmt_issue:
                issues.append(fmt_issue)

        # 3. CCI edit pair checks
        cci_issues = self._check_cci_edits(procedure_codes, modifiers)
        issues.extend(cci_issues)

        # 4. MUE limit checks
        mue_issues = self._check_mue_limits(procedure_codes, units)
        issues.extend(mue_issues)

        # 5. Diagnosis-procedure consistency
        diag_proc_issues = self._check_diag_proc_consistency(diagnosis_codes, procedure_codes)
        issues.extend(diag_proc_issues)

        # 6. Modifier rules
        modifier_issues = self._check_modifier_rules(procedure_codes, modifiers)
        issues.extend(modifier_issues)

        # 7. Place of service consistency
        if place_of_service:
            pos_issues = self._check_pos_consistency(place_of_service, procedure_codes)
            issues.extend(pos_issues)

        # Calculate risk score (0-100)
        risk_score = self._calculate_risk_score(issues)

        # Classify risk level
        if risk_score >= 70:
            risk_level = "high"
        elif risk_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        return SkillResult(success=True, data={
            "risk_score": risk_score,
            "risk_level": risk_level,
            "total_issues": len(issues),
            "issues": issues,
            "claim_summary": {
                "diagnosis_codes": diagnosis_codes,
                "procedure_codes": procedure_codes,
                "modifiers": modifiers,
                "place_of_service": place_of_service,
                "units": units,
                "payer": payer
            },
            "recommendation": self._generate_recommendation(issues, risk_score)
        })

    def _validate_icd10(self, code: str) -> Optional[Dict[str, Any]]:
        """Validate ICD-10-CM code format."""
        code = code.strip().upper()
        if not code:
            return None
        if not self.ICD10_PATTERN.match(code):
            return {
                "severity": "critical",
                "category": "icd10_format",
                "code": code,
                "message": f"Invalid ICD-10-CM format: '{code}'. Expected format: Letter + 2 digits + optional .alphanum (e.g., E11.9, M54.5)",
                "action": "Correct the ICD-10-CM code before submission"
            }
        return None

    def _validate_cpt(self, code: str) -> Optional[Dict[str, Any]]:
        """Validate CPT code format."""
        code = code.strip()
        if not code:
            return None
        if not self.CPT_PATTERN.match(code):
            return {
                "severity": "critical",
                "category": "cpt_format",
                "code": code,
                "message": f"Invalid CPT format: '{code}'. Expected format: 5 digits with optional alpha suffix (e.g., 99213, 99213F)",
                "action": "Correct the CPT code before submission"
            }
        return None

    def _check_cci_edits(self, procedure_codes: List[str], modifiers: List[str]) -> List[Dict[str, Any]]:
        """Check CCI edit pair violations."""
        issues = []
        unique_procs = [p.strip() for p in procedure_codes if p.strip()]

        for i in range(len(unique_procs)):
            for j in range(i + 1, len(unique_procs)):
                code_a = unique_procs[i]
                code_b = unique_procs[j]
                for edit in self.CCI_EDITS:
                    col1, col2 = edit["col1"], edit["col2"]
                    mi = edit["modifier_indicator"]

                    pair_match = (code_a == col1 and code_b == col2) or \
                                 (code_a == col2 and code_b == col1)
                    if not pair_match:
                        continue

                    if mi == 0:
                        issues.append({
                            "severity": "critical",
                            "category": "cci_edit",
                            "code": f"{col1}/{col2}",
                            "message": f"CCI edit violation: {col1} and {col2} cannot be billed together (modifier indicator 0 - not allowed)",
                            "action": f"Remove one of the codes or bill on separate days"
                        })
                    elif mi == 1:
                        # Check if an appropriate modifier is present
                        mod_a = modifiers[i] if i < len(modifiers) else ""
                        mod_b = modifiers[j] if j < len(modifiers) else ""
                        has_distinct = mod_a in ("59", "XE", "XS", "XP", "XU") or \
                                       mod_b in ("59", "XE", "XS", "XP", "XU")
                        if not has_distinct:
                            issues.append({
                                "severity": "warning",
                                "category": "cci_edit",
                                "code": f"{col1}/{col2}",
                                "message": f"CCI edit: {col1} and {col2} require modifier 59/XE/XS/XP/XU to bill together (modifier indicator 1)",
                                "action": f"Append modifier 59 or appropriate X-modifier if services are distinct"
                            })
        return issues

    def _check_mue_limits(self, procedure_codes: List[str], units: List[int]) -> List[Dict[str, Any]]:
        """Check Medically Unlikely Edit limits."""
        issues = []
        # Aggregate units per CPT
        proc_units: Dict[str, int] = {}
        for i, proc in enumerate(procedure_codes):
            proc = proc.strip()
            if proc not in proc_units:
                proc_units[proc] = 0
            unit_val = units[i] if i < len(units) else 1
            proc_units[proc] += unit_val

        for proc, total_units in proc_units.items():
            if proc in self.MUE_LIMITS:
                limit = self.MUE_LIMITS[proc]
                if total_units > limit:
                    issues.append({
                        "severity": "critical",
                        "category": "mue_limit",
                        "code": proc,
                        "message": f"MUE limit exceeded for {proc}: billed {total_units} units, maximum allowed is {limit}",
                        "action": f"Reduce units to {limit} or append modifier if clinically justified with documentation"
                    })
        return issues

    def _check_diag_proc_consistency(self, diagnosis_codes: List[str], procedure_codes: List[str]) -> List[Dict[str, Any]]:
        """Check that diagnosis codes are consistent with procedure codes."""
        issues = []
        dx_prefixes = set()
        for dx in diagnosis_codes:
            dx = dx.strip().upper()
            if dx and dx[0].isalpha():
                dx_prefixes.add(dx[0])

        if not dx_prefixes:
            return issues

        for proc in procedure_codes:
            proc = proc.strip()
            if not proc or len(proc) < 3:
                continue
            prefix = proc[:3]
            if prefix in self.DIAG_PROC_CONSISTENCY:
                allowed_chapters = self.DIAG_PROC_CONSISTENCY[prefix]
                # Check if at least one diagnosis falls in allowed chapters
                has_match = any(ch in allowed_chapters for ch in dx_prefixes)
                if not has_match and allowed_chapters:
                    issues.append({
                        "severity": "warning",
                        "category": "diag_proc_consistency",
                        "code": proc,
                        "message": f"Procedure {proc} may not be clinically consistent with the submitted diagnosis codes. Expected diagnoses starting with: {', '.join(allowed_chapters[:5])}...",
                        "action": "Verify that the diagnosis supports medical necessity for this procedure"
                    })
        return issues

    def _check_modifier_rules(self, procedure_codes: List[str], modifiers: List[str]) -> List[Dict[str, Any]]:
        """Check modifier usage rules."""
        issues = []
        for i, (proc, mod) in enumerate(zip(procedure_codes, modifiers)):
            proc = proc.strip()
            mod = mod.strip().upper()
            if not mod:
                continue

            if mod in self.MODIFIER_RULES:
                rule = self.MODIFIER_RULES[mod]
                invalid_with = rule.get("invalid_with", [])
                if isinstance(invalid_with, list) and proc in invalid_with:
                    issues.append({
                        "severity": "critical",
                        "category": "modifier_rule",
                        "code": f"{proc}-{mod}",
                        "message": f"Modifier {mod} is not valid with procedure {proc}: {rule['description']}",
                        "action": f"Remove modifier {mod} or select a different procedure code"
                    })

                # Modifier 25 requires supporting documentation note
                if mod == "25" and proc.startswith("992"):
                    issues.append({
                        "severity": "info",
                        "category": "modifier_rule",
                        "code": f"{proc}-{mod}",
                        "message": f"Modifier 25 on E/M code {proc}: ensure documentation supports a separately identifiable service",
                        "action": "Verify separate note documents the E/M service beyond the procedure"
                    })
        return issues

    def _check_pos_consistency(self, pos: str, procedure_codes: List[str]) -> List[Dict[str, Any]]:
        """Check place of service consistency with procedure codes."""
        issues = []
        if pos not in self.POS_CONSISTENCY:
            issues.append({
                "severity": "warning",
                "category": "pos_consistency",
                "code": pos,
                "message": f"Unknown place of service code: {pos}",
                "action": "Verify the place of service code is valid"
            })
            return issues

        pos_info = self.POS_CONSISTENCY[pos]
        invalid_prefixes = pos_info.get("invalid_cpt_prefixes", [])

        for proc in procedure_codes:
            proc = proc.strip()
            for inv_prefix in invalid_prefixes:
                if proc.startswith(inv_prefix) and len(inv_prefix) >= 3:
                    issues.append({
                        "severity": "warning",
                        "category": "pos_consistency",
                        "code": proc,
                        "message": f"Procedure {proc} may not be appropriate for POS {pos} ({pos_info['description']})",
                        "action": f"Verify place of service or procedure code accuracy"
                    })
                    break
        return issues

    def _calculate_risk_score(self, issues: List[Dict[str, Any]]) -> int:
        """Calculate claim risk score 0-100."""
        if not issues:
            return 0

        weights = {"critical": 30, "warning": 10, "info": 2}
        raw = sum(weights.get(issue.get("severity", "warning"), 10) for issue in issues)
        # Cap at 100
        return min(raw, 100)

    def _generate_recommendation(self, issues: List[Dict[str, Any]], risk_score: int) -> str:
        """Generate a recommendation based on issues."""
        critical_count = sum(1 for i in issues if i.get("severity") == "critical")
        warning_count = sum(1 for i in issues if i.get("severity") == "warning")

        if critical_count > 0:
            return (f"DO NOT SUBMIT: {critical_count} critical issue(s) found. "
                    f"Resolve all critical issues before claim submission. "
                    f"Also review {warning_count} warning(s).")
        elif warning_count > 0:
            return (f"REVIEW BEFORE SUBMIT: {warning_count} warning(s) found. "
                    f"Review each warning and correct if applicable before submission.")
        else:
            return "PASS: No significant issues found. Claim appears ready for submission."