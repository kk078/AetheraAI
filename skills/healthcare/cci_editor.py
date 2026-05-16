"""
Aethera AI - CCI Editor Skill

NCCI (National Correct Coding Initiative) edit pair checking.
Contains common CCI edit pairs, modifier indicators, and supports
pair checking, modifier checks, and listing edits for a code.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="cci_editor", category="healthcare")
class CCIEditorSkill(AetheraSkill):
    """
    NCCI edit pair checking with modifier indicator support.
    """

    @property
    def name(self) -> str:
        return "cci_editor"

    @property
    def description(self) -> str:
        return "Check NCCI edit pairs: verify if procedure codes can be billed together, check modifier allowance, list edits for a code"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["check_pair", "check_with_modifier", "list_edits"],
                    "description": "Action to perform: check_pair (are two codes billable together), check_with_modifier (can modifier override the edit), list_edits (list all edits for a code)"
                },
                "code1": {
                    "type": "string",
                    "description": "First CPT/HCPCS code (column 1 / comprehensive code)"
                },
                "code2": {
                    "type": "string",
                    "description": "Second CPT/HCPCS code (column 2 / component code)"
                },
                "modifier": {
                    "type": "string",
                    "description": "Modifier to check (e.g., 59, XE, XS, XP, XU)"
                },
                "code": {
                    "type": "string",
                    "description": "Single CPT/HCPCS code to list all edits for"
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
            {"input": {"action": "check_pair", "code1": "99213", "code2": "99214"}},
            {"input": {"action": "check_with_modifier", "code1": "97110", "code2": "97112", "modifier": "59"}},
            {"input": {"action": "list_edits", "code": "97110"}}
        ]

    # --- CCI edit pairs database ---
    # modifier_indicator: 0 = not allowed (cannot override with modifier)
    #                     1 = allowed with appropriate modifier
    #                     9 = not applicable / edit deleted
    # effective_date and deletion_date in YYYY-MM-DD format
    CCI_EDITS: List[Dict[str, Any]] = [
        # E/M code bundling
        {"col1": "99211", "col2": "99212", "modifier_indicator": 0, "edit_rationale": "E/M codes are mutually exclusive within same encounter"},
        {"col1": "99211", "col2": "99213", "modifier_indicator": 0, "edit_rationale": "E/M codes are mutually exclusive within same encounter"},
        {"col1": "99211", "col2": "99214", "modifier_indicator": 0, "edit_rationale": "E/M codes are mutually exclusive within same encounter"},
        {"col1": "99211", "col2": "99215", "modifier_indicator": 0, "edit_rationale": "E/M codes are mutually exclusive within same encounter"},
        {"col1": "99212", "col2": "99213", "modifier_indicator": 0, "edit_rationale": "E/M codes are mutually exclusive within same encounter"},
        {"col1": "99212", "col2": "99214", "modifier_indicator": 0, "edit_rationale": "E/M codes are mutually exclusive within same encounter"},
        {"col1": "99212", "col2": "99215", "modifier_indicator": 0, "edit_rationale": "E/M codes are mutually exclusive within same encounter"},
        {"col1": "99213", "col2": "99214", "modifier_indicator": 0, "edit_rationale": "E/M codes are mutually exclusive within same encounter"},
        {"col1": "99213", "col2": "99215", "modifier_indicator": 0, "edit_rationale": "E/M codes are mutually exclusive within same encounter"},
        {"col1": "99214", "col2": "99215", "modifier_indicator": 0, "edit_rationale": "E/M codes are mutually exclusive within same encounter"},
        # E/M with procedure
        {"col1": "99213", "col2": "36415", "modifier_indicator": 1, "edit_rationale": "Blood draw is component of E/M; modifier 25 on E/M allows separate billing"},
        {"col1": "99214", "col2": "36415", "modifier_indicator": 1, "edit_rationale": "Blood draw is component of E/M; modifier 25 on E/M allows separate billing"},
        {"col1": "99215", "col2": "36415", "modifier_indicator": 1, "edit_rationale": "Blood draw is component of E/M; modifier 25 on E/M allows separate billing"},
        # EKG bundling
        {"col1": "93000", "col2": "93010", "modifier_indicator": 0, "edit_rationale": "93000 includes both professional and technical components; 93010 is a component"},
        {"col1": "93000", "col2": "93040", "modifier_indicator": 0, "edit_rationale": "93000 includes rhythm EKG; 93040 is component"},
        {"col1": "93010", "col2": "93040", "modifier_indicator": 0, "edit_rationale": "93010 is professional component of 93000; 93040 is separate but bundled with complete EKG"},
        # Echocardiography bundling
        {"col1": "93306", "col2": "93307", "modifier_indicator": 0, "edit_rationale": "93306 includes spectral Doppler; 93307 is component of 93306"},
        {"col1": "93306", "col2": "93308", "modifier_indicator": 0, "edit_rationale": "93308 is component of 93306"},
        {"col1": "93307", "col2": "93308", "modifier_indicator": 0, "edit_rationale": "93308 is component of 93307"},
        # Pulmonary function bundling
        {"col1": "94010", "col2": "94060", "modifier_indicator": 1, "edit_rationale": "Bronchodilator response is add-on to spirometry; modifier allowed if distinct service"},
        {"col1": "94010", "col2": "94070", "modifier_indicator": 1, "edit_rationale": "Bronchospasm evaluation is add-on; modifier allowed if distinct service"},
        {"col1": "94060", "col2": "94070", "modifier_indicator": 0, "edit_rationale": "94060 and 94070 are mutually exclusive"},
        # Physical therapy bundling
        {"col1": "97110", "col2": "97112", "modifier_indicator": 1, "edit_rationale": "Therapeutic exercise and neuromuscular re-ed are separate but often bundled; modifier 59/X-modifier allowed for distinct services"},
        {"col1": "97110", "col2": "97113", "modifier_indicator": 1, "edit_rationale": "Aquatic therapy includes therapeutic exercise; modifier allowed if distinct"},
        {"col1": "97110", "col2": "97116", "modifier_indicator": 1, "edit_rationale": "Gait training includes therapeutic exercise component; modifier allowed for distinct services"},
        {"col1": "97112", "col2": "97113", "modifier_indicator": 1, "edit_rationale": "Neuromuscular re-ed and aquatic therapy overlap; modifier allowed for distinct services"},
        {"col1": "97110", "col2": "97530", "modifier_indicator": 1, "edit_rationale": "Therapeutic activities includes exercise component; modifier allowed if distinct"},
        {"col1": "97112", "col2": "97530", "modifier_indicator": 1, "edit_rationale": "Therapeutic activities includes neuromuscular component; modifier allowed if distinct"},
        {"col1": "97110", "col2": "97140", "modifier_indicator": 1, "edit_rationale": "Manual therapy often includes exercise; modifier allowed for distinct services"},
        {"col1": "97112", "col2": "97140", "modifier_indicator": 1, "edit_rationale": "Manual therapy overlaps neuromuscular re-ed; modifier allowed for distinct services"},
        {"col1": "97113", "col2": "97140", "modifier_indicator": 1, "edit_rationale": "Manual therapy overlaps aquatic therapy; modifier allowed for distinct services"},
        {"col1": "97140", "col2": "97530", "modifier_indicator": 1, "edit_rationale": "Manual therapy overlaps therapeutic activities; modifier allowed for distinct services"},
        {"col1": "97140", "col2": "97535", "modifier_indicator": 1, "edit_rationale": "Manual therapy overlaps self-care training; modifier allowed for distinct services"},
        {"col1": "97530", "col2": "97535", "modifier_indicator": 1, "edit_rationale": "Therapeutic activities and self-care training overlap; modifier allowed for distinct services"},
        {"col1": "97530", "col2": "97537", "modifier_indicator": 1, "edit_rationale": "Therapeutic activities and community/work integration overlap; modifier allowed"},
        {"col1": "97535", "col2": "97537", "modifier_indicator": 1, "edit_rationale": "Self-care and community/work integration overlap; modifier allowed"},
        # Radiology bundling
        {"col1": "71045", "col2": "71046", "modifier_indicator": 0, "edit_rationale": "71046 (2-view) includes 71045 (1-view); mutually exclusive"},
        {"col1": "70553", "col2": "70551", "modifier_indicator": 0, "edit_rationale": "MRI brain w/ and w/o contrast includes without contrast"},
        {"col1": "70553", "col2": "70552", "modifier_indicator": 0, "edit_rationale": "MRI brain w/ and w/o contrast includes with contrast"},
        {"col1": "72148", "col2": "72156", "modifier_indicator": 0, "edit_rationale": "Lumbar MRI w/ and w/o contrast includes without contrast"},
        {"col1": "72148", "col2": "72158", "modifier_indicator": 0, "edit_rationale": "72158 includes 72148 component"},
        {"col1": "73221", "col2": "73225", "modifier_indicator": 0, "edit_rationale": "Upper extremity MRA includes MRI component"},
        # Ultrasound bundling
        {"col1": "76700", "col2": "76770", "modifier_indicator": 0, "edit_rationale": "Complete abdominal US includes retroperitoneal component"},
        {"col1": "76705", "col2": "76700", "modifier_indicator": 0, "edit_rationale": "Limited abdominal US is component of complete abdominal US"},
        # Lab bundling
        {"col1": "80053", "col2": "80061", "modifier_indicator": 0, "edit_rationale": "CMP includes lipid panel components; organ panel bundling"},
        {"col1": "80053", "col2": "83036", "modifier_indicator": 0, "edit_rationale": "CMP and HbA1c may overlap in reimbursement; panel bundling"},
        {"col1": "84443", "col2": "84439", "modifier_indicator": 0, "edit_rationale": "TSH includes reflex T4; billed together is duplicate"},
        {"col1": "85025", "col2": "85027", "modifier_indicator": 0, "edit_rationale": "CBC with differential includes CBC without differential"},
        # Vaccine administration
        {"col1": "90471", "col2": "90472", "modifier_indicator": 1, "edit_rationale": "First vaccine admin and additional admin; modifier allowed if different vaccines on same date"},
        {"col1": "90473", "col2": "90474", "modifier_indicator": 1, "edit_rationale": "Oral/nasal first and additional admin; modifier allowed if different vaccines"},
        # Surgery - Integumentary
        {"col1": "10060", "col2": "10061", "modifier_indicator": 0, "edit_rationale": "Incise and drain simple vs. complicated; mutually exclusive"},
        {"col1": "11400", "col2": "11401", "modifier_indicator": 0, "edit_rationale": "Excision benign lesion by size; larger includes smaller"},
        {"col1": "11401", "col2": "11402", "modifier_indicator": 0, "edit_rationale": "Size-based excision bundling; larger includes smaller"},
        {"col1": "11402", "col2": "11403", "modifier_indicator": 0, "edit_rationale": "Size-based excision bundling; larger includes smaller"},
        {"col1": "11403", "col2": "11404", "modifier_indicator": 0, "edit_rationale": "Size-based excision bundling; larger includes smaller"},
        {"col1": "11600", "col2": "11601", "modifier_indicator": 0, "edit_rationale": "Excision malignant lesion by size; larger includes smaller"},
        {"col1": "11601", "col2": "11602", "modifier_indicator": 0, "edit_rationale": "Size-based malignant excision bundling"},
        {"col1": "11602", "col2": "11603", "modifier_indicator": 0, "edit_rationale": "Size-based malignant excision bundling"},
        {"col1": "11900", "col2": "11901", "modifier_indicator": 0, "edit_rationale": "Injection by number of lesions; larger includes smaller"},
        {"col1": "12001", "col2": "12002", "modifier_indicator": 0, "edit_rationale": "Simple repair by size; larger includes smaller"},
        {"col1": "12002", "col2": "12005", "modifier_indicator": 0, "edit_rationale": "Simple repair bundling by size"},
        {"col1": "15780", "col2": "15786", "modifier_indicator": 0, "edit_rationale": "Dermabrasion levels are mutually exclusive"},
        {"col1": "17000", "col2": "17003", "modifier_indicator": 0, "edit_rationale": "Destruction premalignant lesion; first lesion includes additional"},
        # Surgery - Musculoskeletal
        {"col1": "20600", "col2": "20610", "modifier_indicator": 0, "edit_rationale": "Arthrocentesis small vs. intermediate joint; mutually exclusive per joint"},
        {"col1": "20610", "col2": "20611", "modifier_indicator": 1, "edit_rationale": "Arthrocentesis with vs without ultrasound guidance; modifier allowed if distinct"},
        {"col1": "22551", "col2": "22612", "modifier_indicator": 1, "edit_rationale": "Vertebroplasty and posterior arthrodesis; modifier allowed if distinct approaches"},
        {"col1": "27447", "col2": "27486", "modifier_indicator": 0, "edit_rationale": "Total knee arthroplasty includes revision component"},
        {"col1": "29881", "col2": "29880", "modifier_indicator": 0, "edit_rationale": "Knee arthroscopy with meniscectomy includes diagnostic scope"},
        # Surgery - GI
        {"col1": "43235", "col2": "43239", "modifier_indicator": 0, "edit_rationale": "Diagnostic EGD is component of EGD with biopsy"},
        {"col1": "43239", "col2": "43235", "modifier_indicator": 0, "edit_rationale": "EGD with biopsy includes diagnostic component"},
        {"col1": "47562", "col2": "47563", "modifier_indicator": 0, "edit_rationale": "Laparoscopic cholecystectomy without vs with cholangiography"},
        {"col1": "49505", "col2": "49507", "modifier_indicator": 0, "edit_rationale": "Initial hernia repair includes reduction"},
        # Surgery - GU
        {"col1": "52000", "col2": "51701", "modifier_indicator": 1, "edit_rationale": "Cystoscopy and bladder irrigation; modifier allowed if distinct services"},
        # Pain management
        {"col1": "62323", "col2": "62327", "modifier_indicator": 0, "edit_rationale": "Lumbar epidural injection levels are bundled"},
        {"col1": "64483", "col2": "64484", "modifier_indicator": 0, "edit_rationale": "Transforaminal epidural injection levels are bundled"},
        {"col1": "64493", "col2": "64494", "modifier_indicator": 1, "edit_rationale": "Lumbar facet injection levels; modifier allowed if distinct levels"},
        {"col1": "64494", "col2": "64495", "modifier_indicator": 1, "edit_rationale": "Third level facet injection; modifier allowed for additional level"},
    ]

    # --- Modifier definitions for CCI override ---
    MODIFIER_DEFINITIONS: Dict[str, Dict[str, Any]] = {
        "59": {
            "description": "Distinct procedural service",
            "use_criteria": "Used to indicate that a procedure is not part of another service. Must document: different session, different procedure, different site, separate incision, or separate organ.",
            "replaces": None,
            "replaced_by": ["XE", "XS", "XP", "XU"]
        },
        "XE": {
            "description": "Separate encounter",
            "use_criteria": "Service is distinct because it occurred during a separate encounter/session on the same day.",
            "replaces": "59 (when applicable)",
            "replaced_by": None
        },
        "XS": {
            "description": "Separate structure",
            "use_criteria": "Service is distinct because it was performed on a separate organ/structure.",
            "replaces": "59 (when applicable)",
            "replaced_by": None
        },
        "XP": {
            "description": "Distinct practitioner",
            "use_criteria": "Service is distinct because it was performed by a different practitioner.",
            "replaces": "59 (when applicable)",
            "replaced_by": None
        },
        "XU": {
            "description": "Unusual non-overlapping service",
            "use_criteria": "Service is distinct because it does not overlap usual components of the main service.",
            "replaces": "59 (when applicable)",
            "replaced_by": None
        }
    }

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        code1 = kwargs.get("code1", "").strip()
        code2 = kwargs.get("code2", "").strip()
        modifier = kwargs.get("modifier", "").strip().upper()
        code = kwargs.get("code", "").strip()

        if not action:
            return SkillResult(success=False, error="Action is required: check_pair, check_with_modifier, or list_edits")

        try:
            if action == "check_pair":
                if not code1 or not code2:
                    return SkillResult(success=False, error="Both code1 and code2 are required for check_pair")
                result = self._check_pair(code1, code2)
            elif action == "check_with_modifier":
                if not code1 or not code2:
                    return SkillResult(success=False, error="Both code1 and code2 are required for check_with_modifier")
                result = self._check_with_modifier(code1, code2, modifier)
            elif action == "list_edits":
                target = code or code1
                if not target:
                    return SkillResult(success=False, error="Code is required for list_edits")
                result = self._list_edits(target)
            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

            return SkillResult(success=True, data=result)
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _find_edit(self, code1: str, code2: str) -> Optional[Dict[str, Any]]:
        """Find a CCI edit pair (check both directions)."""
        for edit in self.CCI_EDITS:
            if (edit["col1"] == code1 and edit["col2"] == code2) or \
               (edit["col1"] == code2 and edit["col2"] == code1):
                return edit
        return None

    def _check_pair(self, code1: str, code2: str) -> Dict[str, Any]:
        """Check if two codes have a CCI edit."""
        edit = self._find_edit(code1, code2)

        if edit is None:
            return {
                "code1": code1,
                "code2": code2,
                "edit_found": False,
                "can_bill_together": True,
                "modifier_indicator": None,
                "message": f"No CCI edit found between {code1} and {code2}. These codes can generally be billed together without restriction.",
                "recommendation": "No CCI edit restriction applies. Submit both codes per standard billing guidelines."
            }

        mi = edit["modifier_indicator"]
        if mi == 0:
            can_bill = False
            message = f"CCI edit: {edit['col1']} and {edit['col2']} CANNOT be billed together (modifier indicator 0). Rationale: {edit['edit_rationale']}"
            recommendation = "Remove one of the codes or bill on separate dates of service. No modifier can override this edit."
        elif mi == 1:
            can_bill = True
            message = f"CCI edit: {edit['col1']} and {edit['col2']} can be billed together ONLY with an appropriate modifier (modifier indicator 1). Rationale: {edit['edit_rationale']}"
            recommendation = "Append modifier 59, XE, XS, XP, or XU to the column 2 code to indicate distinct procedural service. Ensure documentation supports the modifier."
        elif mi == 9:
            can_bill = True
            message = f"CCI edit previously existed but has been deleted (modifier indicator 9). These codes can now be billed together."
            recommendation = "Submit both codes per standard billing guidelines. No modifier required."
        else:
            can_bill = True
            message = f"Unknown modifier indicator ({mi}) for edit between {code1} and {code2}."
            recommendation = "Consult the current CMS NCCI policy manual for guidance."

        return {
            "code1": code1,
            "code2": code2,
            "edit_found": True,
            "can_bill_together": can_bill,
            "modifier_indicator": mi,
            "modifier_indicator_description": self._describe_modifier_indicator(mi),
            "edit_rationale": edit.get("edit_rationale", ""),
            "column_1_code": edit["col1"],
            "column_2_code": edit["col2"],
            "message": message,
            "recommendation": recommendation
        }

    def _check_with_modifier(self, code1: str, code2: str, modifier: str) -> Dict[str, Any]:
        """Check if a modifier can override the CCI edit."""
        edit = self._find_edit(code1, code2)

        if edit is None:
            return {
                "code1": code1,
                "code2": code2,
                "edit_found": False,
                "modifier_applicable": False,
                "message": f"No CCI edit found between {code1} and {code2}. No modifier needed.",
                "recommendation": "Submit both codes per standard billing guidelines."
            }

        mi = edit["modifier_indicator"]

        if mi == 0:
            return {
                "code1": code1,
                "code2": code2,
                "edit_found": True,
                "modifier_applicable": False,
                "modifier_indicator": 0,
                "modifier_checked": modifier,
                "message": f"Modifier {modifier} CANNOT override this CCI edit. The modifier indicator is 0, meaning no modifier can allow these codes to be billed together.",
                "recommendation": "Remove one of the codes or bill on separate dates of service. The CCI edit with modifier indicator 0 cannot be overridden."
            }

        if mi == 1:
            valid_modifiers = ["59", "XE", "XS", "XP", "XU"]
            if modifier in valid_modifiers:
                mod_info = self.MODIFIER_DEFINITIONS.get(modifier, {})
                return {
                    "code1": code1,
                    "code2": code2,
                    "edit_found": True,
                    "modifier_applicable": True,
                    "modifier_indicator": 1,
                    "modifier_checked": modifier,
                    "modifier_valid": True,
                    "modifier_description": mod_info.get("description", ""),
                    "use_criteria": mod_info.get("use_criteria", ""),
                    "message": f"Modifier {modifier} CAN override this CCI edit. The modifier indicator is 1, meaning an appropriate modifier is allowed.",
                    "recommendation": f"Append modifier {modifier} to the column 2 code ({edit['col2']}). {mod_info.get('use_criteria', 'Ensure documentation supports the distinct nature of the service.')}",
                    "column_2_code_receives_modifier": edit["col2"]
                }
            else:
                return {
                    "code1": code1,
                    "code2": code2,
                    "edit_found": True,
                    "modifier_applicable": True,
                    "modifier_indicator": 1,
                    "modifier_checked": modifier,
                    "modifier_valid": False,
                    "valid_modifiers": valid_modifiers,
                    "message": f"Modifier {modifier} is not a recognized CCI override modifier. Valid override modifiers are: {', '.join(valid_modifiers)}.",
                    "recommendation": f"Use one of the following modifiers instead: 59 (Distinct procedural service), XE (Separate encounter), XS (Separate structure), XP (Distinct practitioner), XU (Unusual non-overlapping service)."
                }

        if mi == 9:
            return {
                "code1": code1,
                "code2": code2,
                "edit_found": True,
                "modifier_applicable": False,
                "modifier_indicator": 9,
                "modifier_checked": modifier,
                "message": "This CCI edit has been deleted (modifier indicator 9). No modifier needed; codes can be billed together.",
                "recommendation": "Submit both codes per standard billing guidelines."
            }

        return {
            "code1": code1,
            "code2": code2,
            "edit_found": True,
            "modifier_applicable": False,
            "modifier_indicator": mi,
            "message": f"Unknown modifier indicator ({mi}). Consult CMS NCCI policy manual.",
            "recommendation": "Verify current NCCI edit status with CMS."
        }

    def _list_edits(self, code: str) -> Dict[str, Any]:
        """List all CCI edits involving a given code."""
        edits_as_col1 = []
        edits_as_col2 = []

        for edit in self.CCI_EDITS:
            if edit["col1"] == code:
                edits_as_col1.append({
                    "paired_code": edit["col2"],
                    "paired_as": "column_2",
                    "modifier_indicator": edit["modifier_indicator"],
                    "modifier_indicator_description": self._describe_modifier_indicator(edit["modifier_indicator"]),
                    "edit_rationale": edit.get("edit_rationale", "")
                })
            if edit["col2"] == code:
                edits_as_col2.append({
                    "paired_code": edit["col1"],
                    "paired_as": "column_1",
                    "modifier_indicator": edit["modifier_indicator"],
                    "modifier_indicator_description": self._describe_modifier_indicator(edit["modifier_indicator"]),
                    "edit_rationale": edit.get("edit_rationale", "")
                })

        total_edits = len(edits_as_col1) + len(edits_as_col2)

        if total_edits == 0:
            return {
                "code": code,
                "total_edits": 0,
                "edits_as_column_1": [],
                "edits_as_column_2": [],
                "message": f"No CCI edits found involving code {code}. This code has no known bundling restrictions in the current database.",
                "recommendation": "Bill per standard guidelines. Verify against the current CMS NCCI files for any recently added edits."
            }

        return {
            "code": code,
            "total_edits": total_edits,
            "edits_as_column_1": edits_as_col1,
            "edits_as_column_2": edits_as_col2,
            "summary": {
                "cannot_bill_with": [
                    e["paired_code"] for e in edits_as_col1 + edits_as_col2
                    if e["modifier_indicator"] == 0
                ],
                "can_bill_with_modifier": [
                    e["paired_code"] for e in edits_as_col1 + edits_as_col2
                    if e["modifier_indicator"] == 1
                ],
                "deleted_edits": [
                    e["paired_code"] for e in edits_as_col1 + edits_as_col2
                    if e["modifier_indicator"] == 9
                ]
            },
            "message": f"Found {total_edits} CCI edit(s) involving code {code}. Review the edit details for billing guidance.",
            "recommendation": self._generate_list_recommendation(code, edits_as_col1, edits_as_col2)
        }

    def _describe_modifier_indicator(self, mi: int) -> str:
        """Return human-readable description of modifier indicator."""
        descriptions = {
            0: "Not allowed - no modifier can override this edit",
            1: "Allowed with modifier - appropriate modifier (59/XE/XS/XP/XU) can override",
            9: "Not applicable - edit has been deleted or is not effective"
        }
        return descriptions.get(mi, f"Unknown modifier indicator ({mi})")

    def _generate_list_recommendation(self, code: str, col1_edits: List[Dict], col2_edits: List[Dict]) -> str:
        """Generate a recommendation summary for list_edits results."""
        cannot_bill = [e["paired_code"] for e in col1_edits + col2_edits if e["modifier_indicator"] == 0]
        needs_modifier = [e["paired_code"] for e in col1_edits + col2_edits if e["modifier_indicator"] == 1]

        parts = []
        if cannot_bill:
            parts.append(f"Cannot bill {code} with: {', '.join(cannot_bill)} (no modifier override allowed).")
        if needs_modifier:
            parts.append(f"Can bill {code} with: {', '.join(needs_modifier)} only if modifier 59/XE/XS/XP/XU is appended and documented.")
        if not parts:
            parts.append(f"No CCI restrictions found for {code}.")

        return " ".join(parts)