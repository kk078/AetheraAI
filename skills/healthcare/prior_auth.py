"""
Aethera AI - Prior Authorization Skill

Check prior authorization requirements by payer and procedure.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


# Prior authorization requirement database
# Structure: PA_REQUIREMENTS[payer][procedure_code] = requirement details
PA_REQUIREMENTS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "medicare": {
        "27447": {
            "description": "Total knee arthroplasty",
            "pa_required": True,
            "criteria": [
                "Failed conservative treatment for at least 3 months (NSAIDs, PT, injections)",
                "Radiographic evidence of joint degeneration",
                "Functional limitation documented (e.g., cannot walk 2 blocks without assistive device)",
                "BMI documentation (some MACs require BMI < 40 or documented weight-loss attempt)"
            ],
            "required_documentation": [
                "Operative report",
                "Radiology reports (X-ray, MRI if applicable)",
                "Physical therapy records showing failed conservative treatment",
                "Pain and functional assessment scores",
                "Progress notes documenting conservative treatment duration"
            ],
            "timeline": {
                "standard_days": 14,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "Medicare requires PA via MAC-specific LCD/NCD. Check local MAC requirements."
        },
        "27130": {
            "description": "Total hip arthroplasty",
            "pa_required": True,
            "criteria": [
                "Failed conservative treatment for at least 3 months",
                "Radiographic evidence of hip joint degeneration",
                "Functional limitation documented",
                "No active infection"
            ],
            "required_documentation": [
                "Operative report",
                "Radiology reports",
                "Physical therapy records",
                "Pain assessment documentation",
                "Progress notes"
            ],
            "timeline": {
                "standard_days": 14,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "Medicare PA via MAC-specific LCD."
        },
        "43239": {
            "description": "Upper GI endoscopy with biopsy",
            "pa_required": True,
            "criteria": [
                "Persistent symptoms despite appropriate medical management",
                "Suspected malignancy or Barrett's esophagus surveillance",
                "Iron deficiency anemia of unclear etiology",
                "GI bleeding"
            ],
            "required_documentation": [
                "History and physical",
                "Prior conservative treatment documentation",
                "Lab results (CBC, H. pylori if applicable)",
                "Prior imaging results"
            ],
            "timeline": {
                "standard_days": 14,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "NCD 100.3 covers diagnostic and screening endoscopy criteria."
        },
        "70553": {
            "description": "MRI brain with and without contrast",
            "pa_required": True,
            "criteria": [
                "Clinical indication supporting medical necessity",
                "Failed or contraindicated CT when appropriate",
                "Suspected CNS pathology (tumor, MS, stroke, infection)"
            ],
            "required_documentation": [
                "Clinical notes with specific indication",
                "Prior imaging reports if applicable",
                "Neurological exam findings"
            ],
            "timeline": {
                "standard_days": 14,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "NCD 220.2.1 outlines MRI coverage criteria."
        },
        "99213": {
            "description": "Office visit established patient low complexity",
            "pa_required": False,
            "criteria": [],
            "required_documentation": [],
            "timeline": {
                "standard_days": 0,
                "expedited_days": 0,
                "retroactive_allowed": True
            },
            "notes": "E/M services do not require prior authorization under Medicare."
        },
    },
    "medicaid": {
        "27447": {
            "description": "Total knee arthroplasty",
            "pa_required": True,
            "criteria": [
                "Failed conservative treatment for at least 6 months",
                "Radiographic evidence of advanced degenerative joint disease",
                "Pain score of 6 or higher on standardized scale",
                "Functional limitation impacting activities of daily living",
                "BMI screening documented"
            ],
            "required_documentation": [
                "Operative report",
                "Radiology reports demonstrating joint damage",
                "6 months of conservative treatment records (PT, medications, injections)",
                "Pain and functional assessment documentation",
                "Primary care physician referral"
            ],
            "timeline": {
                "standard_days": 30,
                "expedited_days": 5,
                "retroactive_allowed": False
            },
            "notes": "State Medicaid programs vary; check state-specific requirements."
        },
        "43239": {
            "description": "Upper GI endoscopy with biopsy",
            "pa_required": True,
            "criteria": [
                "Symptoms persisting > 4 weeks despite treatment",
                "Suspected malignancy",
                "GI hemorrhage",
                "Iron deficiency anemia workup"
            ],
            "required_documentation": [
                "History and physical",
                "Treatment trial documentation",
                "Lab results",
                "Referral from PCP"
            ],
            "timeline": {
                "standard_days": 21,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "State-specific criteria apply."
        },
        "90837": {
            "description": "Psychotherapy 60 minutes",
            "pa_required": True,
            "criteria": [
                "Documented mental health diagnosis",
                "Medical necessity for 60-minute session vs 45-minute (90834)",
                "Treatment plan showing need for extended sessions"
            ],
            "required_documentation": [
                "Psychiatric evaluation with diagnosis",
                "Treatment plan",
                "Progress notes from prior sessions",
                "Justification for 60-minute session length"
            ],
            "timeline": {
                "standard_days": 14,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "Many states limit 90837 sessions; 90834 may be preferred."
        },
        "70553": {
            "description": "MRI brain with and without contrast",
            "pa_required": True,
            "criteria": [
                "Clinical indication with specific neurological symptoms",
                "Suspected pathology requiring MRI specifically",
                "CT not sufficient or contraindicated"
            ],
            "required_documentation": [
                "Clinical notes with neurological findings",
                "Prior imaging if available",
                "PCP or specialist referral"
            ],
            "timeline": {
                "standard_days": 21,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "State Medicaid requirements vary."
        },
        "99213": {
            "description": "Office visit established patient low complexity",
            "pa_required": False,
            "criteria": [],
            "required_documentation": [],
            "timeline": {
                "standard_days": 0,
                "expedited_days": 0,
                "retroactive_allowed": True
            },
            "notes": "E/M visits generally do not require PA under Medicaid."
        },
    },
    "uhc": {
        "27447": {
            "description": "Total knee arthroplasty",
            "pa_required": True,
            "criteria": [
                "Radiographic evidence of moderate to severe osteoarthritis (Kellgren-Lawrence Grade 3 or 4)",
                "Failed non-surgical treatment for at least 12 weeks including PT and NSAIDs",
                "Pain and functional limitation documented",
                "No contraindications to surgery"
            ],
            "required_documentation": [
                "UHC prior authorization form",
                "Radiology reports with grading",
                "Physical therapy records",
                "Pain and functional assessment",
                "Surgeon's clinical notes"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "UHC uses OptumInsight clinical guidelines. Submit via UnitedHealthcare Provider Portal."
        },
        "43239": {
            "description": "Upper GI endoscopy with biopsy",
            "pa_required": True,
            "criteria": [
                "Persistent GERD symptoms despite PPI therapy for 8+ weeks",
                "Dysphagia or odynophagia",
                "Unexplained weight loss with GI symptoms",
                "Suspected Barrett's esophagus surveillance per guidelines",
                "Iron deficiency anemia"
            ],
            "required_documentation": [
                "UHC prior authorization form",
                "History documenting symptom duration and prior treatment",
                "PPI trial records",
                "Lab results"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "UHC follows ASGE guidelines for endoscopy appropriateness."
        },
        "70553": {
            "description": "MRI brain with and without contrast",
            "pa_required": True,
            "criteria": [
                "Specific neurological indication (seizures, focal deficits, suspected tumor)",
                "Failed or insufficient CT for the clinical question",
                "Documented clinical necessity"
            ],
            "required_documentation": [
                "UHC prior authorization form",
                "Clinical notes with specific indication",
                "Prior imaging results",
                "Neurological examination findings"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "Submit via UnitedHealthcare Provider Portal or call."
        },
        "90837": {
            "description": "Psychotherapy 60 minutes",
            "pa_required": True,
            "criteria": [
                "Documented mental health diagnosis",
                "Medical necessity for 60-minute vs 45-minute session",
                "Complex presentation requiring extended session time"
            ],
            "required_documentation": [
                "UHC prior authorization form",
                "Psychiatric evaluation",
                "Treatment plan",
                "Progress notes"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "UHC limits 90837; 90834 or 90832 preferred when clinically appropriate."
        },
        "64483": {
            "description": "Injection anesthetic agent lumbar transforaminal epidural",
            "pa_required": True,
            "criteria": [
                "Radicular pain with correlating imaging findings",
                "Failed conservative treatment for at least 6 weeks",
                "No prior successful epidural within last 6 months",
                "Limited to 3 epidural injections per 6-month period"
            ],
            "required_documentation": [
                "UHC prior authorization form",
                "MRI or CT showing radiculopathy",
                "Conservative treatment records",
                "Pain assessment documentation"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "UHC limits frequency of epidural injections."
        },
    },
    "aetna": {
        "27447": {
            "description": "Total knee arthroplasty",
            "pa_required": True,
            "criteria": [
                "Radiographic evidence of moderate to severe OA",
                "Failed conservative treatment (PT, NSAIDs, injections) for at least 3 months",
                "Functional impairment documented",
                "No active infection or contraindication"
            ],
            "required_documentation": [
                "Aetna precertification form",
                "X-ray reports showing joint degeneration",
                "Conservative treatment records",
                "Functional assessment"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "Submit via Aetna Provider Portal or Availity."
        },
        "43239": {
            "description": "Upper GI endoscopy with biopsy",
            "pa_required": True,
            "criteria": [
                "GERD symptoms unresponsive to 8+ weeks of PPI therapy",
                "Alarm symptoms (weight loss, dysphagia, GI bleeding)",
                "Barrett's surveillance per ACG guidelines",
                "Unexplained iron deficiency anemia"
            ],
            "required_documentation": [
                "Aetna precertification form",
                "Symptom documentation with duration",
                "PPI trial records",
                "Relevant lab work"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "Aetna follows ASGE/ACG guidelines."
        },
        "70553": {
            "description": "MRI brain with and without contrast",
            "pa_required": True,
            "criteria": [
                "Documented neurological symptoms requiring MRI evaluation",
                "CT insufficient or contraindicated for the clinical indication",
                "Suspected CNS pathology"
            ],
            "required_documentation": [
                "Aetna precertification form",
                "Clinical notes with neurological findings",
                "Prior imaging if performed",
                "Referral documentation"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "Aetna uses Clinical Policy Bulletins (CPBs) for MRI criteria."
        },
        "90837": {
            "description": "Psychotherapy 60 minutes",
            "pa_required": True,
            "criteria": [
                "Documented psychiatric diagnosis",
                "Clinical necessity for 60-minute session",
                "Complexity justifies extended time"
            ],
            "required_documentation": [
                "Aetna precertification form",
                "Psychiatric evaluation with diagnosis",
                "Treatment plan",
                "Progress notes"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "Aetna typically prefers 90834 (45 min) unless 90837 is justified."
        },
        "22551": {
            "description": "Anterior interbody fusion lumbar",
            "pa_required": True,
            "criteria": [
                "Degenerative disc disease with objective evidence on imaging",
                "Failed conservative treatment for at least 6 months",
                "Neurological deficit or severe radicular symptoms",
                "Single or two-level disease preferred"
            ],
            "required_documentation": [
                "Aetna precertification form",
                "MRI/CT demonstrating pathology",
                "6 months of conservative treatment records",
                "Pain and functional assessments",
                "Surgeon's clinical notes"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "Aetna CPB 069 covers spinal fusion criteria."
        },
    },
    "cigna": {
        "27447": {
            "description": "Total knee arthroplasty",
            "pa_required": True,
            "criteria": [
                "Severe OA confirmed by imaging (Kellgren-Lawrence Grade 3-4)",
                "Conservative treatment failure of at least 12 weeks",
                "Significant functional limitation",
                "No active infection"
            ],
            "required_documentation": [
                "Cigna precertification request",
                "Imaging reports",
                "Conservative treatment documentation",
                "Functional assessment"
            ],
            "timeline": {
                "standard_days": 10,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "Submit via Cigna Provider Portal or call Cigna precertification line."
        },
        "43239": {
            "description": "Upper GI endoscopy with biopsy",
            "pa_required": True,
            "criteria": [
                "Refractory GERD despite adequate PPI trial",
                "Alarm symptoms present",
                "Barrett's surveillance per guidelines",
                "GI bleeding or iron deficiency anemia"
            ],
            "required_documentation": [
                "Cigna precertification request",
                "Clinical documentation of symptoms and prior treatment",
                "PPI trial records",
                "Lab results"
            ],
            "timeline": {
                "standard_days": 10,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "Cigna uses evidence-based coverage guidelines."
        },
        "70553": {
            "description": "MRI brain with and without contrast",
            "pa_required": True,
            "criteria": [
                "Clinical indication with specific neurological symptoms",
                "Imaging necessary for diagnosis or treatment planning",
                "CT insufficient for the clinical question"
            ],
            "required_documentation": [
                "Cigna precertification request",
                "Clinical notes",
                "Prior imaging reports",
                "Neurological exam"
            ],
            "timeline": {
                "standard_days": 10,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "Cigna coverage guidelines specify MRI criteria."
        },
        "90837": {
            "description": "Psychotherapy 60 minutes",
            "pa_required": True,
            "criteria": [
                "Mental health diagnosis documented",
                "Extended session clinically justified",
                "Complexity requires 60-minute session"
            ],
            "required_documentation": [
                "Cigna precertification request",
                "Psychiatric evaluation",
                "Treatment plan",
                "Clinical justification for 60-minute session"
            ],
            "timeline": {
                "standard_days": 10,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "Cigna may limit 90837; documentation must justify extended time."
        },
        "64483": {
            "description": "Injection anesthetic agent lumbar transforaminal epidural",
            "pa_required": True,
            "criteria": [
                "Radiculopathy confirmed by clinical exam and imaging",
                "Failed conservative treatment of at least 6 weeks",
                "Maximum 2 epidural steroid injections per year preferred",
                "Functional improvement documented after prior injection"
            ],
            "required_documentation": [
                "Cigna precertification request",
                "MRI/CT confirming radiculopathy",
                "Conservative treatment records",
                "Pain and functional assessments"
            ],
            "timeline": {
                "standard_days": 10,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "Cigna limits epidural injection frequency per coverage guidelines."
        },
    },
    "bcbs": {
        "27447": {
            "description": "Total knee arthroplasty",
            "pa_required": True,
            "criteria": [
                "Advanced osteoarthritis on imaging",
                "Failed conservative treatment for minimum 3-6 months",
                "Pain and functional limitation documented",
                "No active infection"
            ],
            "required_documentation": [
                "BCBS precertification form (plan-specific)",
                "X-ray/MRI reports",
                "Conservative treatment documentation",
                "Functional assessment"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "BCBS plans vary by state/plan; check specific plan requirements."
        },
        "43239": {
            "description": "Upper GI endoscopy with biopsy",
            "pa_required": True,
            "criteria": [
                "Chronic GERD unresponsive to treatment",
                "Alarm symptoms (dysphagia, weight loss, bleeding)",
                "Surveillance per guidelines",
                "Unexplained anemia"
            ],
            "required_documentation": [
                "BCBS precertification form",
                "Symptom documentation",
                "Treatment trial records",
                "Lab results"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "BCBS follows specialty society guidelines."
        },
        "70553": {
            "description": "MRI brain with and without contrast",
            "pa_required": True,
            "criteria": [
                "Specific neurological indication",
                "CT insufficient for clinical question",
                "Documented clinical necessity"
            ],
            "required_documentation": [
                "BCBS precertification form",
                "Clinical notes",
                "Neurological exam findings",
                "Prior imaging if available"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "BCBS uses InterQual or MCG criteria depending on plan."
        },
        "90837": {
            "description": "Psychotherapy 60 minutes",
            "pa_required": True,
            "criteria": [
                "Mental health diagnosis documented",
                "60-minute session clinically justified",
                "Complexity warrants extended time"
            ],
            "required_documentation": [
                "BCBS precertification form",
                "Psychiatric evaluation",
                "Treatment plan",
                "Clinical justification"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "BCBS plans may limit 90837; documentation must support medical necessity."
        },
        "22551": {
            "description": "Anterior interbody fusion lumbar",
            "pa_required": True,
            "criteria": [
                "Degenerative disc disease with imaging confirmation",
                "Failed at least 6 months of conservative treatment",
                "Neurological deficit or severe symptoms",
                "Fusion limited to 1-2 levels preferred"
            ],
            "required_documentation": [
                "BCBS precertification form",
                "MRI/CT imaging reports",
                "Conservative treatment records",
                "Functional assessment",
                "Surgeon clinical notes"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "BCBS medical policy varies by plan for spinal fusion."
        },
    },
    "humana": {
        "27447": {
            "description": "Total knee arthroplasty",
            "pa_required": True,
            "criteria": [
                "Advanced OA on imaging",
                "Conservative treatment failure of at least 12 weeks",
                "Functional limitation documented"
            ],
            "required_documentation": [
                "Humana precertification form",
                "Imaging reports",
                "Conservative treatment records",
                "Functional assessment"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "Humana uses Availity for PA submission."
        },
        "43239": {
            "description": "Upper GI endoscopy with biopsy",
            "pa_required": True,
            "criteria": [
                "Refractory GERD despite adequate PPI trial",
                "Alarm symptoms",
                "Surveillance per guidelines"
            ],
            "required_documentation": [
                "Humana precertification form",
                "Symptom documentation",
                "PPI trial records",
                "Lab results"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "Humana follows specialty society guidelines for endoscopy."
        },
        "70553": {
            "description": "MRI brain with and without contrast",
            "pa_required": True,
            "criteria": [
                "Neurological indication documented",
                "CT insufficient for clinical question",
                "Clinical necessity established"
            ],
            "required_documentation": [
                "Humana precertification form",
                "Clinical notes",
                "Neurological exam findings",
                "Prior imaging if available"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "Humana uses MCG/InterQual criteria for imaging."
        },
        "90837": {
            "description": "Psychotherapy 60 minutes",
            "pa_required": True,
            "criteria": [
                "Mental health diagnosis documented",
                "Clinical justification for 60-minute session",
                "Complexity supports extended time"
            ],
            "required_documentation": [
                "Humana precertification form",
                "Psychiatric evaluation",
                "Treatment plan",
                "Clinical justification"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 3,
                "retroactive_allowed": False
            },
            "notes": "Humana typically limits 90837."
        },
        "64483": {
            "description": "Injection anesthetic agent lumbar transforaminal epidural",
            "pa_required": True,
            "criteria": [
                "Radiculopathy with imaging correlation",
                "Conservative treatment failure of at least 6 weeks",
                "Frequency limits apply"
            ],
            "required_documentation": [
                "Humana precertification form",
                "Imaging reports",
                "Conservative treatment records",
                "Pain assessment"
            ],
            "timeline": {
                "standard_days": 15,
                "expedited_days": 2,
                "retroactive_allowed": False
            },
            "notes": "Humana limits epidural steroid injection frequency."
        },
    }
}

# Payer name normalization
PAYER_ALIASES: Dict[str, str] = {
    "medicare": "medicare",
    "medicare advantage": "medicare",
    "medicare part c": "medicare",
    "medicaid": "medicaid",
    "medicaid managed care": "medicaid",
    "uhc": "uhc",
    "united": "uhc",
    "unitedhealthcare": "uhc",
    "united health": "uhc",
    "united healthcare": "uhc",
    "aetna": "aetna",
    "cigna": "cigna",
    "bcbs": "bcbs",
    "blue cross": "bcbs",
    "blue shield": "bcbs",
    "blue cross blue shield": "bcbs",
    "humana": "humana",
}


@skill(name="prior_auth", category="healthcare")
class PriorAuthSkill(AetheraSkill):
    """
    Check prior authorization requirements by payer and procedure.
    """

    @property
    def name(self) -> str:
        return "prior_auth"

    @property
    def description(self) -> str:
        return "Check prior authorization requirements by payer and procedure code"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["check_pa", "get_criteria", "get_docs", "get_timeline", "full_lookup"],
                    "description": "Action to perform: check_pa (is PA needed?), get_criteria, get_docs, get_timeline, full_lookup (all info)"
                },
                "payer": {
                    "type": "string",
                    "description": "Insurance payer name (e.g., Medicare, UHC, Aetna, BCBS, Cigna, Humana, Medicaid)"
                },
                "procedure_code": {
                    "type": "string",
                    "description": "CPT/HCPCS procedure code (e.g., 27447, 43239, 70553)"
                }
            },
            "required": ["action", "payer", "procedure_code"]
        }

    @property
    def requires_phi_protection(self) -> bool:
        return True

    @property
    def examples(self) -> list:
        return [
            {"input": {"action": "check_pa", "payer": "Medicare", "procedure_code": "27447"}},
            {"input": {"action": "full_lookup", "payer": "UHC", "procedure_code": "43239"}},
            {"input": {"action": "get_criteria", "payer": "Aetna", "procedure_code": "70553"}},
            {"input": {"action": "get_docs", "payer": "BCBS", "procedure_code": "90837"}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "full_lookup")
        payer = kwargs.get("payer", "")
        procedure_code = kwargs.get("procedure_code", "")

        if not payer:
            return SkillResult(success=False, error="Payer name is required")

        if not procedure_code:
            return SkillResult(success=False, error="Procedure code is required")

        try:
            normalized_payer = self._normalize_payer(payer)
            if not normalized_payer:
                return SkillResult(
                    success=False,
                    error=f"Unknown payer: {payer}. Supported payers: {', '.join(sorted(set(PAYER_ALIASES.values())))}"
                )

            pa_data = self._lookup_pa(normalized_payer, procedure_code)
            if not pa_data:
                return SkillResult(
                    success=True,
                    data={
                        "payer": normalized_payer,
                        "procedure_code": procedure_code,
                        "pa_required": None,
                        "message": f"No PA data found for procedure {procedure_code} under {normalized_payer}. Contact payer directly to verify PA requirements."
                    }
                )

            result = self._format_result(action, normalized_payer, procedure_code, pa_data)
            return SkillResult(success=True, data=result)

        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _normalize_payer(self, payer: str) -> Optional[str]:
        """Normalize payer name to standard key."""
        normalized = payer.lower().strip()
        return PAYER_ALIASES.get(normalized)

    def _lookup_pa(self, payer: str, procedure_code: str) -> Optional[Dict[str, Any]]:
        """Look up PA requirement for payer and procedure."""
        payer_data = PA_REQUIREMENTS.get(payer, {})
        return payer_data.get(procedure_code)

    def _format_result(self, action: str, payer: str, procedure_code: str, pa_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format result based on requested action."""
        base = {
            "payer": payer,
            "procedure_code": procedure_code,
            "description": pa_data["description"],
            "pa_required": pa_data["pa_required"],
        }

        if action == "check_pa":
            base["pa_required"] = pa_data["pa_required"]
            return base

        elif action == "get_criteria":
            base["criteria"] = pa_data["criteria"]
            base["notes"] = pa_data.get("notes", "")
            return base

        elif action == "get_docs":
            base["required_documentation"] = pa_data["required_documentation"]
            return base

        elif action == "get_timeline":
            base["timeline"] = pa_data["timeline"]
            return base

        elif action == "full_lookup":
            base["criteria"] = pa_data["criteria"]
            base["required_documentation"] = pa_data["required_documentation"]
            base["timeline"] = pa_data["timeline"]
            base["notes"] = pa_data.get("notes", "")
            return base

        return base