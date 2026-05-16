"""
Aethera AI - Contract Analyzer Skill

Extract and compare payer contract terms, calculate reimbursement.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


# Common contract term types with standard fields
CONTRACT_TERM_TYPES: Dict[str, Dict[str, Any]] = {
    "fee_schedule_methodology": {
        "name": "Fee Schedule Methodology",
        "description": "Method used to determine reimbursement rates for services",
        "common_types": [
            {
                "type": "Medicare Percentage",
                "description": "Reimbursement calculated as a percentage of Medicare allowable amount",
                "typical_range": "100%-150% of Medicare",
                "example_formula": "Medicare Allowed Amount * Contract Percentage = Reimbursement",
                "pros": ["Transparent and verifiable", "Updates with Medicare changes"],
                "cons": ["Subject to Medicare rate cuts", "May not reflect actual cost to provide service"]
            },
            {
                "type": "Fee-for-Service Schedule",
                "description": "Fixed fee schedule with specific reimbursement per CPT code",
                "typical_range": "Varies by payer and region",
                "example_formula": "Lookup CPT in fee schedule -> Fixed dollar amount",
                "pros": ["Predictable reimbursement", "Easy to verify payments"],
                "cons": ["May not keep pace with cost increases", "Negotiated rates may be below market"]
            },
            {
                "type": "RBRVS-based",
                "description": "Resource-Based Relative Value Scale (RBRVS) based reimbursement with conversion factor",
                "typical_range": "Varies; conversion factor typically $30-$80 per RVU",
                "example_formula": "RVU * Conversion Factor * Geographic Adjustment = Reimbursement",
                "pros": ["Reflects relative work and practice expense", "Widely used standard"],
                "cons": ["Complex calculation", "Subject to annual RVU updates"]
            },
            {
                "type": "DRG-based",
                "description": "Diagnosis-Related Group flat rate per admission for hospital services",
                "typical_range": "Varies by DRG weight and base rate",
                "example_formula": "DRG Weight * Base Rate = Reimbursement",
                "pros": ["Predictable per-case payment", "Encourages efficiency"],
                "cons": ["May not cover high-acuity outliers", "Complex classification system"]
            },
            {
                "type": "Percentage of Billed Charges",
                "description": "Reimbursement as a percentage of provider's billed charges",
                "typical_range": "50%-80% of charges",
                "example_formula": "Billed Charges * Contract Percentage = Reimbursement",
                "pros": ["Simple calculation"],
                "cons": ["Dependent on charge master rates", "May not reflect actual cost"]
            }
        ]
    },
    "timely_filing": {
        "name": "Timely Filing Requirements",
        "description": "Time limits for submitting initial claims and appeals",
        "common_terms": [
            {
                "payer_type": "Medicare",
                "initial_claim_filing_days": 365,
                "appeal_filing_days": 120,
                "redetermination_days": 120,
                "reconsideration_days": 180,
                "notes": "Initial claim must be filed within 1 year of date of service. Redetermination appeal within 120 days of initial determination."
            },
            {
                "payer_type": "Medicaid",
                "initial_claim_filing_days": 90,
                "appeal_filing_days": 30,
                "redetermination_days": 30,
                "reconsideration_days": 60,
                "notes": "Varies by state; many states use 90-day initial filing with 30-day appeal window."
            },
            {
                "payer_type": "Commercial (Standard)",
                "initial_claim_filing_days": 90,
                "appeal_filing_days": 60,
                "redetermination_days": 60,
                "reconsideration_days": 90,
                "notes": "Most commercial payers use 90-day initial filing, 60-day appeal. Always verify specific contract terms."
            },
            {
                "payer_type": "UHC",
                "initial_claim_filing_days": 90,
                "appeal_filing_days": 60,
                "redetermination_days": 60,
                "reconsideration_days": 90,
                "notes": "UHC standard: 90 days initial, 60 days appeal. Community/state plans may vary."
            },
            {
                "payer_type": "Aetna",
                "initial_claim_filing_days": 90,
                "appeal_filing_days": 60,
                "redetermination_days": 60,
                "reconsideration_days": 90,
                "notes": "Aetna standard: 90 days initial filing, 60 days for appeals."
            },
            {
                "payer_type": "Cigna",
                "initial_claim_filing_days": 90,
                "appeal_filing_days": 60,
                "redetermination_days": 60,
                "reconsideration_days": 90,
                "notes": "Cigna standard: 90 days initial filing, 60 days for appeals."
            },
            {
                "payer_type": "BCBS",
                "initial_claim_filing_days": 90,
                "appeal_filing_days": 60,
                "redetermination_days": 60,
                "reconsideration_days": 90,
                "notes": "BCBS plans vary by state/local plan. Common: 90 days initial, 60 days appeal."
            },
            {
                "payer_type": "Humana",
                "initial_claim_filing_days": 90,
                "appeal_filing_days": 60,
                "redetermination_days": 60,
                "reconsideration_days": 90,
                "notes": "Humana standard: 90 days initial filing, 60 days for appeals."
            }
        ]
    },
    "appeal_rights": {
        "name": "Appeal Rights and Process",
        "description": "Rights and procedures for appealing claim denials and payment decisions",
        "common_terms": [
            {
                "appeal_level": "Initial/First Level",
                "description": "First appeal of a denied or underpaid claim submitted to the payer",
                "typical_timeline_days": 30,
                "typical_response_days": 30,
                "required_elements": [
                    "Written appeal letter citing contract terms",
                    "Copy of original claim and EOB/RA",
                    "Supporting clinical documentation",
                    "Relevant contract language"
                ]
            },
            {
                "appeal_level": "Second Level/Reconsideration",
                "description": "Second appeal if first level is denied; typically reviewed by different reviewer",
                "typical_timeline_days": 60,
                "typical_response_days": 30,
                "required_elements": [
                    "First-level appeal denial letter",
                    "Additional supporting documentation",
                    "Revised appeal letter addressing first-level denial reasons"
                ]
            },
            {
                "appeal_level": "External Review/Independent Review Organization (IRO)",
                "description": "Independent external review for medical necessity denials (ACA requirement for commercial plans)",
                "typical_timeline_days": 120,
                "typical_response_days": 45,
                "required_elements": [
                    "Exhausted internal appeals",
                    "Request for external review within 4 months of final internal denial",
                    "All prior appeal documentation"
                ]
            },
            {
                "appeal_level": "Medicare Redetermination",
                "description": "Medicare-specific first level appeal (QIC review)",
                "typical_timeline_days": 120,
                "typical_response_days": 60,
                "required_elements": [
                    "Redetermination request (CMS-20033 or written request)",
                    "Copy of MSN or RA",
                    "Supporting medical documentation"
                ]
            },
            {
                "appeal_level": "Medicare QIC Reconsideration",
                "description": "Medicare second-level appeal to Qualified Independent Contractor",
                "typical_timeline_days": 180,
                "typical_response_days": 90,
                "required_elements": [
                    "Reconsideration request",
                    "Redetermination dismissal/denial letter",
                    "Additional evidence not previously submitted"
                ]
            },
            {
                "appeal_level": "Medicare ALJ Hearing",
                "description": "Medicare third-level appeal to Administrative Law Judge",
                "typical_timeline_days": 540,
                "typical_response_days": 90,
                "required_elements": [
                    "ALJ hearing request",
                    "QIC reconsideration dismissal/denial",
                    "All prior evidence and new evidence",
                    "Amount in controversy must meet minimum threshold"
                ]
            }
        ]
    },
    "termination_clause": {
        "name": "Termination Clauses",
        "description": "Terms governing contract termination by either party",
        "common_terms": [
            {
                "type": "Without Cause Termination",
                "description": "Either party may terminate the contract without stating a specific reason",
                "typical_notice_period_days": 90,
                "typical_range": "60-180 days written notice",
                "post_termination_obligations": [
                    "Continued service for existing patients for transition period",
                    "Final claims adjudication for services rendered before termination date",
                    "Return or destruction of confidential information",
                    "Ongoing confidentiality obligations"
                ]
            },
            {
                "type": "With Cause Termination",
                "description": "Termination due to material breach or specific cause",
                "typical_notice_period_days": 30,
                "cure_period_days": 30,
                "typical_causes": [
                    "Material breach of contract terms",
                    "Failure to maintain required credentials or licensure",
                    "Fraud or misrepresentation",
                    "Failure to meet quality standards",
                    "Non-payment of obligations",
                    "Violation of regulatory requirements"
                ]
            },
            {
                "type": "Automatic Termination",
                "description": "Contract terminates automatically upon certain events",
                "trigger_events": [
                    "Provider loses medical license",
                    "Provider loses malpractice insurance",
                    "Provider becomes excluded from Medicare/Medicaid",
                    "Provider files for bankruptcy",
                    "Payer becomes insolvent",
                    "Change of ownership without consent"
                ]
            },
            {
                "type": "Run-out Provision",
                "description": "Post-termination period during which claims for services rendered before termination are still adjudicated under contract terms",
                "typical_runout_period_days": 90,
                "typical_range": "60-180 days",
                "notes": "Critical for ensuring payment for services rendered before contract end date"
            }
        ]
    },
    "payment_terms": {
        "name": "Payment Terms",
        "description": "Terms governing timing and method of payment",
        "common_terms": [
            {
                "type": "Clean Claim Payment Timeline",
                "description": "Required timeline for payer to pay clean (complete) claims",
                "standard_days": 30,
                "typical_range": "15-45 days",
                "interest_penalty": "Varies by state; typically 1%-1.5% per month for late payment",
                "notes": "Many states have prompt payment laws requiring payment within 15-30 days for clean claims"
            },
            {
                "type": "Payment Method",
                "description": "Method by which the payer remits payment",
                "common_methods": [
                    "EFT/ACH (Electronic Funds Transfer)",
                    "Check (paper)",
                    "Virtual credit card (VCC)"
                ],
                "notes": "Providers can typically require EFT payment per CMS regulations"
            },
            {
                "type": "Holdback/Withhold",
                "description": "Percentage of payment withheld pending quality or performance metrics",
                "typical_range": "0%-10%",
                "release_criteria": [
                    "Quality metric achievement",
                    "Patient satisfaction scores",
                    "Utilization targets",
                    "Reporting compliance"
                ],
                "notes": "Common in value-based contracts; verify release terms and timelines"
            }
        ]
    },
    "other_key_terms": {
        "name": "Other Key Contract Terms",
        "description": "Additional important contract provisions",
        "common_terms": [
            {
                "type": "Most Favored Nation (MFN) Clause",
                "description": "Guarantees the provider reimbursement at least as favorable as any other payer contract",
                "notes": "Rare but important; ensures competitive rates"
            },
            {
                "type": "Annual Rate Escalator",
                "description": "Automatic annual rate increase built into the contract",
                "typical_range": "1%-5% per year",
                "notes": "Helps keep pace with inflation; verify CPI or fixed percentage basis"
            },
            {
                "type": "Stop-Loss/Outlier Protection",
                "description": "Additional payment for cases exceeding cost thresholds",
                "typical_threshold": "2-3 standard deviations above DRG mean or specific dollar threshold",
                "notes": "Critical for hospitals to avoid catastrophic losses on high-cost cases"
            },
            {
                "type": "Carve-out Provisions",
                "description": "Specific services excluded from capitation or global payment, paid fee-for-service instead",
                "common_carveouts": [
                    "Behavioral health services",
                    "Prescription drugs",
                    "Transplants",
                    "Specialty oncology drugs",
                    "Durable medical equipment"
                ]
            },
            {
                "type": "Non-Compete/Exclusivity",
                "description": "Restrictions on provider contracting with other payers or practicing at competing facilities",
                "notes": "Review carefully; may limit provider's ability to serve patients with other insurance"
            },
            {
                "type": "Gag Clause Prohibition",
                "description": "Provisions preventing payer from restricting provider communication with patients",
                "notes": "Most contracts now include gag clause prohibition per patient protection laws; verify compliance"
            }
        ]
    }
}

# Sample fee schedule for reimbursement calculation (CPT -> Medicare RVU data, illustrative)
SAMPLE_FEE_SCHEDULE: Dict[str, Dict[str, Any]] = {
    "99213": {"description": "E/M Established Low", "work_rvu": 0.97, "pe_rvu": 1.10, "mp_rvu": 0.39, "total_rvu": 2.46, "medicare_allowed": 115.48},
    "99214": {"description": "E/M Established Moderate", "work_rvu": 1.50, "pe_rvu": 1.46, "mp_rvu": 0.50, "total_rvu": 3.46, "medicare_allowed": 162.44},
    "99215": {"description": "E/M Established High", "work_rvu": 2.11, "pe_rvu": 1.79, "mp_rvu": 0.60, "total_rvu": 4.50, "medicare_allowed": 211.27},
    "99203": {"description": "E/M New Low", "work_rvu": 1.60, "pe_rvu": 1.64, "mp_rvu": 0.48, "total_rvu": 3.72, "medicare_allowed": 174.71},
    "99204": {"description": "E/M New Moderate", "work_rvu": 2.60, "pe_rvu": 2.27, "mp_rvu": 0.63, "total_rvu": 5.50, "medicare_allowed": 258.22},
    "99205": {"description": "E/M New High", "work_rvu": 3.50, "pe_rvu": 2.69, "mp_rvu": 0.75, "total_rvu": 6.94, "medicare_allowed": 325.90},
    "27447": {"description": "Total Knee Arthroplasty", "work_rvu": 21.07, "pe_rvu": 32.89, "mp_rvu": 8.24, "total_rvu": 62.20, "medicare_allowed": 2918.65},
    "43239": {"description": "EGD with Biopsy", "work_rvu": 4.06, "pe_rvu": 5.56, "mp_rvu": 1.11, "total_rvu": 10.73, "medicare_allowed": 503.16},
    "70553": {"description": "MRI Brain w/ & w/o Contrast", "work_rvu": 1.45, "pe_rvu": 12.67, "mp_rvu": 3.28, "total_rvu": 17.40, "medicare_allowed": 816.17},
    "90837": {"description": "Psychotherapy 60 min", "work_rvu": 1.50, "pe_rvu": 0.92, "mp_rvu": 0.32, "total_rvu": 2.74, "medicare_allowed": 128.56},
}


@skill(name="contract_analyzer", category="healthcare")
class ContractAnalyzerSkill(AetheraSkill):
    """
    Extract and compare payer contract terms, calculate reimbursement.
    """

    @property
    def name(self) -> str:
        return "contract_analyzer"

    @property
    def description(self) -> str:
        return "Extract payer contract terms, compare contracts, calculate reimbursement rates"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["extract_terms", "compare_contracts", "calculate_reimbursement", "get_term_type", "list_term_types"],
                    "description": "Action: extract_terms, compare_contracts, calculate_reimbursement, get_term_type, list_term_types"
                },
                "term_type": {
                    "type": "string",
                    "description": "Contract term type (fee_schedule_methodology, timely_filing, appeal_rights, termination_clause, payment_terms, other_key_terms)"
                },
                "payer": {
                    "type": "string",
                    "description": "Payer name for term extraction"
                },
                "cpt_code": {
                    "type": "string",
                    "description": "CPT code for reimbursement calculation"
                },
                "contract_percentage": {
                    "type": "number",
                    "description": "Contract percentage of Medicare (e.g., 120 for 120% of Medicare)"
                },
                "compare_payers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of payers to compare"
                },
                "compare_term_type": {
                    "type": "string",
                    "description": "Term type to compare across payers"
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
            {"input": {"action": "extract_terms", "term_type": "timely_filing", "payer": "Medicare"}},
            {"input": {"action": "calculate_reimbursement", "cpt_code": "99214", "contract_percentage": 120}},
            {"input": {"action": "compare_contracts", "compare_payers": ["Medicare", "UHC", "Aetna"], "compare_term_type": "timely_filing"}},
            {"input": {"action": "list_term_types"}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "extract_terms")

        try:
            if action == "extract_terms":
                term_type = kwargs.get("term_type", "")
                payer = kwargs.get("payer", "")
                if not term_type:
                    return SkillResult(success=False, error="Term type is required for extract_terms action")
                result = self._extract_terms(term_type, payer)

            elif action == "compare_contracts":
                compare_payers = kwargs.get("compare_payers", [])
                compare_term_type = kwargs.get("compare_term_type", "timely_filing")
                if not compare_payers or len(compare_payers) < 2:
                    return SkillResult(success=False, error="At least 2 payers required for comparison")
                result = self._compare_contracts(compare_payers, compare_term_type)

            elif action == "calculate_reimbursement":
                cpt_code = kwargs.get("cpt_code", "")
                contract_percentage = kwargs.get("contract_percentage", 100)
                if not cpt_code:
                    return SkillResult(success=False, error="CPT code is required for calculate_reimbursement action")
                result = self._calculate_reimbursement(cpt_code, contract_percentage)

            elif action == "get_term_type":
                term_type = kwargs.get("term_type", "")
                if not term_type:
                    return SkillResult(success=False, error="Term type is required")
                result = self._get_term_type(term_type)

            elif action == "list_term_types":
                result = self._list_term_types()

            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

            return SkillResult(success=True, data=result)

        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _extract_terms(self, term_type: str, payer: str) -> Dict[str, Any]:
        """Extract contract terms for a specific term type and payer."""
        term_data = CONTRACT_TERM_TYPES.get(term_type)
        if not term_data:
            available = ", ".join(CONTRACT_TERM_TYPES.keys())
            return {"error": f"Unknown term type. Available: {available}"}

        result = {
            "term_type": term_type,
            "term_name": term_data["name"],
            "description": term_data["description"]
        }

        if term_type == "timely_filing" and payer:
            payer_lower = payer.lower().strip()
            for term in term_data["common_terms"]:
                if term["payer_type"].lower() == payer_lower:
                    result["payer"] = payer
                    result["terms"] = term
                    return result
            result["payer"] = payer
            result["message"] = f"No specific terms found for {payer}. Showing standard commercial terms."
            for term in term_data["common_terms"]:
                if term["payer_type"].lower() == "commercial (standard)":
                    result["terms"] = term
                    return result
            result["all_terms"] = term_data["common_terms"]
            return result

        result["terms"] = term_data.get("common_terms", term_data.get("common_types", []))
        return result

    def _compare_contracts(self, payers: List[str], term_type: str) -> Dict[str, Any]:
        """Compare contract terms across payers."""
        term_data = CONTRACT_TERM_TYPES.get(term_type)
        if not term_data:
            available = ", ".join(CONTRACT_TERM_TYPES.keys())
            return {"error": f"Unknown term type. Available: {available}"}

        comparison = {
            "term_type": term_type,
            "term_name": term_data["name"],
            "payers_compared": payers,
            "comparison": {},
            "differences": []
        }

        if term_type == "timely_filing":
            payer_data = {}
            for payer in payers:
                payer_lower = payer.lower().strip()
                for term in term_data["common_terms"]:
                    if term["payer_type"].lower() == payer_lower:
                        payer_data[payer] = term
                        break

            comparison["comparison"] = payer_data

            # Identify differences
            if len(payer_data) >= 2:
                values = {payer: data.get("initial_claim_filing_days") for payer, data in payer_data.items()}
                if len(set(values.values())) > 1:
                    comparison["differences"].append({
                        "field": "initial_claim_filing_days",
                        "values": values,
                        "note": "Filing deadlines differ across payers"
                    })

                appeal_values = {payer: data.get("appeal_filing_days") for payer, data in payer_data.items()}
                if len(set(appeal_values.values())) > 1:
                    comparison["differences"].append({
                        "field": "appeal_filing_days",
                        "values": appeal_values,
                        "note": "Appeal deadlines differ across payers"
                    })

        elif term_type == "fee_schedule_methodology":
            comparison["comparison"] = {
                "available_methodologies": term_data["common_types"],
                "recommendation": "Compare specific percentage of Medicare or dollar amounts in each contract"
            }

        elif term_type == "appeal_rights":
            comparison["comparison"] = {
                "appeal_levels": term_data["common_terms"],
                "note": "Appeal rights and timelines vary by payer type (Medicare vs commercial)"
            }

        else:
            comparison["comparison"] = term_data.get("common_terms", term_data.get("common_types", []))

        return comparison

    def _calculate_reimbursement(self, cpt_code: str, contract_percentage: float) -> Dict[str, Any]:
        """Calculate reimbursement for a CPT code based on contract percentage of Medicare."""
        cpt_upper = cpt_code.upper().strip()
        fee_data = SAMPLE_FEE_SCHEDULE.get(cpt_upper)

        if not fee_data:
            return {
                "cpt_code": cpt_upper,
                "error": f"CPT code {cpt_upper} not found in fee schedule",
                "available_codes": list(SAMPLE_FEE_SCHEDULE.keys())
            }

        medicare_allowed = fee_data["medicare_allowed"]
        contract_rate = round(medicare_allowed * (contract_percentage / 100), 2)
        difference_from_medicare = round(contract_rate - medicare_allowed, 2)

        return {
            "cpt_code": cpt_upper,
            "description": fee_data["description"],
            "rvu_breakdown": {
                "work_rvu": fee_data["work_rvu"],
                "pe_rvu": fee_data["pe_rvu"],
                "mp_rvu": fee_data["mp_rvu"],
                "total_rvu": fee_data["total_rvu"]
            },
            "medicare_allowed": medicare_allowed,
            "contract_percentage": f"{contract_percentage}%",
            "contract_reimbursement": contract_rate,
            "difference_from_medicare": difference_from_medicare,
            "annual_impact_per_100_claims": round(difference_from_medicare * 100, 2)
        }

    def _get_term_type(self, term_type: str) -> Dict[str, Any]:
        """Get detailed information about a contract term type."""
        term_data = CONTRACT_TERM_TYPES.get(term_type)
        if not term_data:
            available = ", ".join(CONTRACT_TERM_TYPES.keys())
            return {"error": f"Unknown term type. Available: {available}"}

        return {
            "term_type": term_type,
            "name": term_data["name"],
            "description": term_data["description"],
            "terms": term_data.get("common_terms", term_data.get("common_types", []))
        }

    def _list_term_types(self) -> Dict[str, Any]:
        """List all available contract term types."""
        term_types = []
        for key, data in CONTRACT_TERM_TYPES.items():
            term_types.append({
                "key": key,
                "name": data["name"],
                "description": data["description"]
            })

        return {
            "total_term_types": len(term_types),
            "term_types": term_types
        }