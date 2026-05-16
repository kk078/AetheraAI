"""
Aethera AI - Denial Analyzer Skill

Analyze denial codes (CARC/RARC) and recommend actions.
"""

from typing import Dict, Any, List

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="denial_analyzer", category="healthcare")
class DenialAnalyzerSkill(AetheraSkill):
    """
    Analyze claim denial codes and recommend appeal actions.
    """

    @property
    def name(self) -> str:
        return "denial_analyzer"

    @property
    def description(self) -> str:
        return "Analyze CARC/RARC denial codes and recommend appeal actions"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "carc_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Claim Adjustment Reason Codes (e.g., CO-4, PR-1)"
                },
                "rarc_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Remittance Advice Remark Codes (e.g., N130, M21)"
                },
                "claim_amount": {
                    "type": "number",
                    "description": "Original claim amount"
                },
                "paid_amount": {
                    "type": "number",
                    "description": "Amount paid"
                },
                "payer": {
                    "type": "string",
                    "description": "Insurance payer name"
                }
            },
            "required": ["carc_codes"]
        }

    @property
    def requires_phi_protection(self) -> bool:
        return True  # Denials may contain patient info

    @property
    def examples(self) -> list:
        return [
            {"input": {"carc_codes": ["CO-4", "CO-11"]}},
            {"input": {"carc_codes": ["CO-50"], "rarc_codes": ["N130"]}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        carc_codes = kwargs.get("carc_codes", [])
        rarc_codes = kwargs.get("rarc_codes", [])
        claim_amount = kwargs.get("claim_amount")
        paid_amount = kwargs.get("paid_amount")
        payer = kwargs.get("payer", "Unknown")

        if not carc_codes:
            return SkillResult(success=False, error="At least one CARC code is required")

        try:
            analysis = self._analyze_denial(carc_codes, rarc_codes, claim_amount, paid_amount, payer)
            return SkillResult(success=True, data=analysis)
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _analyze_denial(
        self,
        carc_codes: List[str],
        rarc_codes: List[str],
        claim_amount: float,
        paid_amount: float,
        payer: str
    ) -> Dict[str, Any]:
        """Analyze denial and generate recommendations."""

        # Decode CARC codes
        decoded_carc = [self._decode_carc(code) for code in carc_codes]

        # Decode RARC codes
        decoded_rarc = [self._decode_rarc(code) for code in rarc_codes]

        # Determine denial category
        category = self._categorize_denial(carc_codes)

        # Generate appeal recommendation
        appeal_recommendation = self._generate_appeal_recommendation(carc_codes, rarc_codes)

        # Calculate financial impact
        adjusted_amount = claim_amount - paid_amount if claim_amount and paid_amount else 0

        return {
            "carc_codes": [
                {"code": c, "description": d} for c, d in zip(carc_codes, decoded_carc)
            ],
            "rarc_codes": [
                {"code": c, "description": d} for c, d in zip(rarc_codes, decoded_rarc)
            ],
            "category": category,
            "financial_impact": {
                "original_amount": claim_amount,
                "paid_amount": paid_amount,
                "adjusted_amount": adjusted_amount,
                "write_off": adjusted_amount if category["appeal_priority"] == "low" else 0
            },
            "appeal_recommendation": appeal_recommendation,
            "payer": payer
        }

    def _decode_carc(self, code: str) -> str:
        """Decode CARC code to description."""
        # Common CARC codes
        carc_descriptions = {
            "CO-4": "Procedure code inconsistent with modifier or missing modifier",
            "CO-11": "Diagnosis inconsistent with procedure",
            "CO-16": "Claim/service lacks information needed for adjudication",
            "CO-18": "Duplicate claim/service",
            "CO-22": "Coordination of benefits (this care may be covered by another payer)",
            "CO-27": "Expenses incurred after coverage terminated",
            "CO-29": "Time limit for filing has expired",
            "CO-45": "Charges exceed your contracted/legislated fee arrangement",
            "CO-50": "Not medically necessary",
            "CO-97": "Payment adjusted because already adjudicated (bundled)",
            "PR-1": "Deductible amount",
            "PR-2": "Coinsurance amount",
            "PR-3": "Copay amount",
            "OA-23": "Impact of prior payer adjudication",
        }
        code_upper = code.upper()
        return carc_descriptions.get(code_upper, f"Unknown CARC: {code}")

    def _decode_rarc(self, code: str) -> str:
        """Decode RARC code to description."""
        # Common RARC codes
        rarc_descriptions = {
            "N130": "Claim/service denied based on plan policy",
            "M21": "Missing/incomplete/invalid primary diagnosis code",
            "M87": "Missing/incomplete/invalid modifier",
            "N362": "Separate payment not allowed - bundled",
            "N539": "Prior authorization required",
            "W1": "Workers' Compensation jurisdiction",
        }
        code_upper = code.upper()
        return rarc_descriptions.get(code_upper, f"Unknown RARC: {code}")

    def _categorize_denial(self, carc_codes: List[str]) -> Dict[str, Any]:
        """Categorize denial by type and priority."""
        # Denial categories
        technical_denials = ["CO-4", "CO-11", "CO-16", "CO-18", "CO-29"]
        clinical_denials = ["CO-50"]
        contractual_denials = ["CO-45", "CO-97", "OA-23"]
        patient_responsibility = ["PR-1", "PR-2", "PR-3"]

        category = "unknown"
        appeal_priority = "medium"

        for code in carc_codes:
            code_upper = code.upper()
            if code_upper in technical_denials:
                category = "technical"
                appeal_priority = "high"  # Often fixable
                break
            elif code_upper in clinical_denials:
                category = "clinical"
                appeal_priority = "high"  # Needs clinical documentation
                break
            elif code_upper in contractual_denials:
                category = "contractual"
                appeal_priority = "medium"
            elif code_upper in patient_responsibility:
                category = "patient_responsibility"
                appeal_priority = "low"  # Cannot appeal

        return {
            "category": category,
            "appeal_priority": appeal_priority,
            "appealable": appeal_priority in ["high", "medium"]
        }

    def _generate_appeal_recommendation(
        self,
        carc_codes: List[str],
        rarc_codes: List[str]
    ) -> Dict[str, Any]:
        """Generate appeal recommendation."""
        recommendations = []
        required_documents = []
        timeline = "30 days"  # Standard appeal window

        for code in carc_codes:
            code_upper = code.upper()

            if code_upper == "CO-4":  # Modifier issue
                recommendations.append("Submit corrected claim with appropriate modifier")
                required_documents.append("Operative report supporting modifier use")

            elif code_upper == "CO-11":  # Diagnosis/procedure mismatch
                recommendations.append("Submit appeal with clinical documentation")
                required_documents.append("Medical records showing medical necessity")
                required_documents.append("Physician letter of medical necessity")

            elif code_upper == "CO-16":  # Missing information
                recommendations.append("Submit corrected claim with missing information")
                required_documents.append("Complete claim form with all required fields")

            elif code_upper == "CO-50":  # Medical necessity
                recommendations.append("File formal appeal with clinical evidence")
                required_documents.append("Complete medical records")
                required_documents.append("Peer-reviewed literature supporting treatment")
                required_documents.append("Physician statement of medical necessity")
                timeline = "120 days (Medicare)"

            elif code_upper == "CO-97":  # Bundled
                recommendations.append("Review NCCI edits and submit appeal if separately billable")
                required_documents.append("Documentation showing distinct procedure")

        if not recommendations:
            recommendations.append("Review denial reason and determine appeal viability")

        return {
            "recommendations": recommendations,
            "required_documents": required_documents,
            "appeal_timeline": timeline,
            "appeal_level": "Initial" if "CO-50" not in [c.upper() for c in carc_codes] else "Redetermination"
        }
