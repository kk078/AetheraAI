"""
Aethera AI - Claim Status Skill

Interpret 276/277 claim status category codes and their meanings.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


# Claim Status Category Codes (277)
# Based on ANSI ASC X12 277 Health Care Claim Status Response
CLAIM_STATUS_CODES: Dict[str, Dict[str, Any]] = {
    "P0": {
        "category": "P0",
        "short_description": "Pre-authorization required",
        "full_description": "The claim requires prior authorization before adjudication can proceed",
        "status_type": "pending",
        "action_needed": "Submit prior authorization request to payer before or concurrent with claim submission",
        "is_final": False,
        "next_steps": [
            "Verify PA requirement with payer",
            "Submit PA request with required clinical documentation",
            "Track PA approval and resubmit claim"
        ],
        "typical_resolution_days": 14
    },
    "P1": {
        "category": "P1",
        "short_description": "Pre-authorization in process",
        "full_description": "Prior authorization request has been received and is being reviewed by the payer",
        "status_type": "pending",
        "action_needed": "Monitor PA status; await payer determination on authorization request",
        "is_final": False,
        "next_steps": [
            "Track PA request with payer",
            "Ensure all required documentation has been submitted",
            "Contact payer if no decision within expected timeframe"
        ],
        "typical_resolution_days": 14
    },
    "P2": {
        "category": "P2",
        "short_description": "Pre-authorization approved",
        "full_description": "Prior authorization has been approved; claim may proceed to adjudication",
        "status_type": "pending",
        "action_needed": "Resubmit claim with PA approval number if not already submitted",
        "is_final": False,
        "next_steps": [
            "Verify PA approval number and effective dates",
            "Submit claim with PA number referenced",
            "Monitor claim for payment"
        ],
        "typical_resolution_days": 7
    },
    "P3": {
        "category": "P3",
        "short_description": "Pre-authorization denied",
        "full_description": "Prior authorization request has been denied by the payer",
        "status_type": "denied",
        "action_needed": "Review denial reason; consider appeal with additional clinical documentation or explore alternative treatments",
        "is_final": True,
        "next_steps": [
            "Review PA denial reason and RARC codes",
            "Gather additional clinical documentation",
            "File PA appeal or peer-to-peer review request",
            "Consider alternative treatment options"
        ],
        "typical_resolution_days": 30
    },
    "P5": {
        "category": "P5",
        "short_description": "Adjudication in process",
        "full_description": "Claim has been received and is being processed for payment determination",
        "status_type": "pending",
        "action_needed": "No action required; claim is being processed",
        "is_final": False,
        "next_steps": [
            "Monitor claim status",
            "No action required unless status does not change within expected timeframe"
        ],
        "typical_resolution_days": 14
    },
    "P6": {
        "category": "P6",
        "short_description": "Adjudication in process - additional information requested",
        "full_description": "Claim adjudication is pending receipt of additional information from the provider",
        "status_type": "pending",
        "action_needed": "Submit the requested additional information to the payer within the specified timeframe",
        "is_final": False,
        "next_steps": [
            "Identify specific information requested by payer",
            "Gather and submit requested documentation promptly",
            "Track submission and confirm receipt by payer"
        ],
        "typical_resolution_days": 7
    },
    "P7": {
        "category": "P7",
        "short_description": "Adjudication in process - under medical review",
        "full_description": "Claim is being reviewed for medical necessity or clinical appropriateness",
        "status_type": "pending",
        "action_needed": "Prepare clinical documentation supporting medical necessity in case of denial",
        "is_final": False,
        "next_steps": [
            "Prepare clinical documentation and medical necessity letter",
            "Monitor for potential denial",
            "Be ready to appeal with clinical evidence if denied"
        ],
        "typical_resolution_days": 21
    },
    "P8": {
        "category": "P8",
        "short_description": "Adjudication in process - under payment review",
        "full_description": "Claim is being reviewed for correct payment amount or pricing",
        "status_type": "pending",
        "action_needed": "No action required; payment review is standard processing",
        "is_final": False,
        "next_steps": [
            "Monitor claim for payment",
            "Review payment amount when received"
        ],
        "typical_resolution_days": 14
    },
    "A0": {
        "category": "A0",
        "short_description": "Payment remitted",
        "full_description": "Claim has been processed and payment has been remitted to the provider",
        "status_type": "paid",
        "action_needed": "Verify payment amount matches expected reimbursement; post payment to patient account",
        "is_final": True,
        "next_steps": [
            "Verify payment amount against expected reimbursement",
            "Post payment to patient account",
            "Identify and appeal any underpayments"
        ],
        "typical_resolution_days": 0
    },
    "A1": {
        "category": "A1",
        "short_description": "Payment remitted - with adjustment",
        "full_description": "Claim has been processed and payment remitted, but includes an adjustment (contractual, etc.)",
        "status_type": "paid",
        "action_needed": "Review adjustment reason codes; determine if adjustment is contractual or appealable",
        "is_final": True,
        "next_steps": [
            "Review CARC/RARC codes for adjustment reasons",
            "Verify adjustment is per contract terms",
            "Appeal if adjustment appears incorrect or non-contractual",
            "Post payment and adjustment to patient account"
        ],
        "typical_resolution_days": 0
    },
    "A2": {
        "category": "A2",
        "short_description": "Denied",
        "full_description": "Claim has been denied by the payer",
        "status_type": "denied",
        "action_needed": "Review denial reason codes; determine appealability and file timely appeal if warranted",
        "is_final": True,
        "next_steps": [
            "Review CARC/RARC codes for specific denial reasons",
            "Determine if denial is appealable",
            "Gather supporting documentation",
            "File appeal within payer's timely filing window"
        ],
        "typical_resolution_days": 30
    },
    "A3": {
        "category": "A3",
        "short_description": "Denied - not covered by payer",
        "full_description": "Claim denied because the service is not a covered benefit under the patient's plan",
        "status_type": "denied",
        "action_needed": "Verify coverage with payer; determine if alternate billing or payer is appropriate",
        "is_final": True,
        "next_steps": [
            "Verify patient benefits and coverage for the service",
            "Check if another payer is responsible (COB)",
            "Consider billing patient if service is truly non-covered",
            "File appeal if coverage denial appears incorrect"
        ],
        "typical_resolution_days": 30
    },
    "A4": {
        "category": "A4",
        "short_description": "Denied - patient responsibility",
        "full_description": "Claim denied or adjusted as patient responsibility (deductible, coinsurance, copay)",
        "status_type": "patient_responsibility",
        "action_needed": "Bill patient for responsibility amount; verify if secondary insurance should be billed",
        "is_final": True,
        "next_steps": [
            "Bill patient for owed amount",
            "Check for secondary insurance coverage",
            "Post adjustment to patient account",
            "Follow up on patient balance collection"
        ],
        "typical_resolution_days": 0
    },
    "A5": {
        "category": "A5",
        "short_description": "Denied - duplicate claim",
        "full_description": "Claim denied as a duplicate of a previously submitted claim",
        "status_type": "denied",
        "action_needed": "Verify if original claim was paid; if not paid, resubmit with documentation showing this is not a duplicate",
        "is_final": True,
        "next_steps": [
            "Check claim history to verify if original claim exists",
            "If not a duplicate, resubmit with supporting documentation",
            "If original was paid, no further action needed",
            "If original was denied, review denial reasons and correct"
        ],
        "typical_resolution_days": 14
    },
    "A6": {
        "category": "A6",
        "short_description": "Denied - timely filing limit exceeded",
        "full_description": "Claim denied because it was submitted after the payer's timely filing deadline",
        "status_type": "denied",
        "action_needed": "File appeal with proof of timely filing (initial submission date, prior payer EOB, etc.)",
        "is_final": True,
        "next_steps": [
            "Gather proof of timely filing (clearinghouse reports, prior submission records)",
            "File appeal with documentation of original submission date",
            "If initial submission was timely, provide proof to payer",
            "For Medicare, file as redetermination with proof of timely filing"
        ],
        "typical_resolution_days": 30
    },
    "A7": {
        "category": "A7",
        "short_description": "Denied - coordination of benefits",
        "full_description": "Claim denied due to coordination of benefits issues; another payer may be primary",
        "status_type": "denied",
        "action_needed": "Verify correct primary payer per COB rules; submit to correct payer",
        "is_final": True,
        "next_steps": [
            "Verify COB information with patient",
            "Determine correct order of payer responsibility",
            "Submit claim to correct primary payer",
            "After primary payment, resubmit to secondary with EOB"
        ],
        "typical_resolution_days": 30
    },
    "A8": {
        "category": "A8",
        "short_description": "Reversed - previous payment recouped",
        "full_description": "A previous payment on this claim has been reversed/recouped by the payer",
        "status_type": "reversal",
        "action_needed": "Determine reason for reversal; appeal if reversal is incorrect",
        "is_final": True,
        "next_steps": [
            "Identify reason for payment reversal",
            "Review recoupment notice for specific reason codes",
            "File appeal if reversal appears incorrect",
            "If reversal is correct, adjust accounting records"
        ],
        "typical_resolution_days": 30
    },
    "R0": {
        "category": "R0",
        "short_description": "Received - not yet processed",
        "full_description": "Claim has been received by the payer but has not yet entered adjudication",
        "status_type": "received",
        "action_needed": "No action needed; allow standard processing time before follow-up",
        "is_final": False,
        "next_steps": [
            "Monitor claim status",
            "Follow up if claim remains in this status beyond expected processing time",
            "Verify claim was received by contacting payer if needed"
        ],
        "typical_resolution_days": 14
    },
    "R1": {
        "category": "R1",
        "short_description": "Received - pending review",
        "full_description": "Claim received and pending initial review for completeness and eligibility",
        "status_type": "received",
        "action_needed": "No action needed; claim is in initial review queue",
        "is_final": False,
        "next_steps": [
            "Monitor claim status",
            "Be prepared to respond to any information requests"
        ],
        "typical_resolution_days": 7
    },
    "R2": {
        "category": "R2",
        "short_description": "Received - returned as unprocessable",
        "full_description": "Claim received but returned as unprocessable due to errors or missing information",
        "status_type": "returned",
        "action_needed": "Review errors, correct claim, and resubmit",
        "is_final": True,
        "next_steps": [
            "Review rejection reason codes",
            "Correct claim errors (missing/invalid data)",
            "Resubmit corrected claim as a new submission",
            "Track resubmission for processing"
        ],
        "typical_resolution_days": 7
    },
}


# Entity type codes used in 277
ENTITY_TYPE_CODES: Dict[str, str] = {
    "1P": "Rendering Provider",
    "85": "Billing Provider",
    "IL": "Insured/Subscriber",
    "QC": "Patient",
    "PR": "Payer",
    "TT": "Transfer To",
    "OF": "Other Furnishing",
}

# Claim status type classification for quick filtering
STATUS_TYPE_GROUPS: Dict[str, List[str]] = {
    "pending": ["P0", "P1", "P2", "P5", "P6", "P7", "P8", "R0", "R1"],
    "final_paid": ["A0", "A1"],
    "final_denied": ["A2", "A3", "A5", "A6", "A7", "P3"],
    "patient_responsibility": ["A4"],
    "reversal": ["A8"],
    "action_needed": ["R2", "P0", "P6", "A2", "A3", "A5", "A6", "A7", "A8"],
}


@skill(name="claim_status", category="healthcare")
class ClaimStatusSkill(AetheraSkill):
    """
    Interpret 276/277 claim status codes and their meanings.
    """

    @property
    def name(self) -> str:
        return "claim_status"

    @property
    def description(self) -> str:
        return "Interpret 276/277 claim status category codes, get action needed, check if status is final"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["interpret_status", "get_action", "check_final", "list_by_type", "full_status"],
                    "description": "Action: interpret_status, get_action, check_final, list_by_type, full_status"
                },
                "status_code": {
                    "type": "string",
                    "description": "Claim status category code (e.g., P0, A2, R2)"
                },
                "status_type": {
                    "type": "string",
                    "description": "Filter by status type (pending, final_paid, final_denied, patient_responsibility, reversal, action_needed)"
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
            {"input": {"action": "interpret_status", "status_code": "A2"}},
            {"input": {"action": "get_action", "status_code": "P6"}},
            {"input": {"action": "check_final", "status_code": "P5"}},
            {"input": {"action": "list_by_type", "status_type": "pending"}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "interpret_status")
        status_code = kwargs.get("status_code", "")
        status_type = kwargs.get("status_type", "")

        try:
            if action == "interpret_status":
                if not status_code:
                    return SkillResult(success=False, error="Status code is required for interpret_status action")
                result = self._interpret_status(status_code)

            elif action == "get_action":
                if not status_code:
                    return SkillResult(success=False, error="Status code is required for get_action action")
                result = self._get_action(status_code)

            elif action == "check_final":
                if not status_code:
                    return SkillResult(success=False, error="Status code is required for check_final action")
                result = self._check_final(status_code)

            elif action == "list_by_type":
                if not status_type:
                    return SkillResult(success=False, error="Status type is required for list_by_type action")
                result = self._list_by_type(status_type)

            elif action == "full_status":
                if not status_code:
                    return SkillResult(success=False, error="Status code is required for full_status action")
                result = self._full_status(status_code)

            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

            return SkillResult(success=True, data=result)

        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _interpret_status(self, code: str) -> Dict[str, Any]:
        """Interpret a claim status category code."""
        code_upper = code.upper().strip()
        status_info = CLAIM_STATUS_CODES.get(code_upper)

        if not status_info:
            return {
                "code": code_upper,
                "description": f"Unknown claim status code: {code_upper}",
                "status_type": "unknown",
                "is_final": False,
                "recommendation": "Contact payer for status clarification"
            }

        return {
            "code": code_upper,
            "short_description": status_info["short_description"],
            "full_description": status_info["full_description"],
            "status_type": status_info["status_type"]
        }

    def _get_action(self, code: str) -> Dict[str, Any]:
        """Get action needed for a claim status code."""
        code_upper = code.upper().strip()
        status_info = CLAIM_STATUS_CODES.get(code_upper)

        if not status_info:
            return {
                "code": code_upper,
                "action_needed": "Contact payer for status clarification",
                "next_steps": ["Call payer provider services line", "Verify claim status through payer portal"],
                "typical_resolution_days": None
            }

        return {
            "code": code_upper,
            "status_type": status_info["status_type"],
            "action_needed": status_info["action_needed"],
            "next_steps": status_info["next_steps"],
            "typical_resolution_days": status_info["typical_resolution_days"],
            "is_final": status_info["is_final"]
        }

    def _check_final(self, code: str) -> Dict[str, Any]:
        """Check if a claim status code represents a final disposition."""
        code_upper = code.upper().strip()
        status_info = CLAIM_STATUS_CODES.get(code_upper)

        if not status_info:
            return {
                "code": code_upper,
                "is_final": False,
                "status_type": "unknown",
                "message": "Unknown status code; cannot determine if final"
            }

        return {
            "code": code_upper,
            "is_final": status_info["is_final"],
            "status_type": status_info["status_type"],
            "short_description": status_info["short_description"],
            "message": "This is a final status; no further processing expected." if status_info["is_final"]
                       else "This is not a final status; claim is still being processed."
        }

    def _list_by_type(self, status_type: str) -> Dict[str, Any]:
        """List all status codes of a given type."""
        type_lower = status_type.lower().strip()
        codes = STATUS_TYPE_GROUPS.get(type_lower, [])

        if not codes:
            available = ", ".join(STATUS_TYPE_GROUPS.keys())
            return {
                "status_type": type_lower,
                "codes": [],
                "message": f"Unknown status type. Available types: {available}"
            }

        result_codes = []
        for code in codes:
            info = CLAIM_STATUS_CODES.get(code, {})
            result_codes.append({
                "code": code,
                "short_description": info.get("short_description", "Unknown"),
                "full_description": info.get("full_description", ""),
                "is_final": info.get("is_final", False),
                "action_needed": info.get("action_needed", "")
            })

        return {
            "status_type": type_lower,
            "total_codes": len(result_codes),
            "codes": result_codes
        }

    def _full_status(self, code: str) -> Dict[str, Any]:
        """Return full information for a claim status code."""
        code_upper = code.upper().strip()
        status_info = CLAIM_STATUS_CODES.get(code_upper)

        if not status_info:
            return {
                "code": code_upper,
                "description": f"Unknown claim status code: {code_upper}",
                "status_type": "unknown",
                "is_final": False,
                "action_needed": "Contact payer for status clarification",
                "next_steps": ["Call payer provider services line"],
                "typical_resolution_days": None
            }

        return {
            "code": code_upper,
            "short_description": status_info["short_description"],
            "full_description": status_info["full_description"],
            "status_type": status_info["status_type"],
            "is_final": status_info["is_final"],
            "action_needed": status_info["action_needed"],
            "next_steps": status_info["next_steps"],
            "typical_resolution_days": status_info["typical_resolution_days"]
        }