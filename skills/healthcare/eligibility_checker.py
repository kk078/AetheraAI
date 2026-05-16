"""
Aethera AI - Eligibility Checker Skill

Interpret benefits and eligibility, calculate patient responsibility.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


# Benefit structure database by plan type
BENEFIT_STRUCTURES: Dict[str, Dict[str, Any]] = {
    "medicare_a": {
        "name": "Medicare Part A (Hospital Insurance)",
        "description": "Covers inpatient hospital care, skilled nursing facility, hospice, home health services",
        "covered_services": [
            "Inpatient hospital care",
            "Skilled nursing facility care (after 3-day hospital stay)",
            "Hospice care",
            "Home health services",
            "Religious non-medical health care institution services",
            "Blood (after first 3 pints per year)"
        ],
        "cost_sharing": {
            "hospital_deductible": 1632.00,
            "hospital_deductible_period": "per benefit period",
            "hospital_coinsurance_days_61_90": 408.00,
            "hospital_coinsurance_period_days_61_90": "per day",
            "hospital_lifetime_reserve_days_91_60": 816.00,
            "hospital_lifetime_reserve_period": "per day",
            "snf_coinsurance_days_21_100": 204.00,
            "snf_coinsurance_period_days_21_100": "per day",
            "snf_days_1_20": 0.00,
            "hospice_copay": "5% of respite care",
            "home_health_copay": 0.00,
            "blood_deductible": "First 3 pints per year"
        },
        "coverage_limits": {
            "hospital_days_per_benefit_period": 90,
            "lifetime_reserve_days": 60,
            "snf_days_per_benefit_period": 100,
            "home_health_visits": "Reasonable and necessary",
            "hospice": "Unlimited if criteria met"
        },
        "eligibility_requirements": [
            "Age 65 or older and entitled to Social Security",
            "Under 65 with qualifying disability and receiving SSDI for 24 months",
            "ESRD requiring dialysis or kidney transplant",
            "ALS (Lou Gehrig's disease)"
        ]
    },
    "medicare_b": {
        "name": "Medicare Part B (Medical Insurance)",
        "description": "Covers outpatient medical care, doctor services, preventive services, durable medical equipment",
        "covered_services": [
            "Doctor services (outpatient)",
            "Outpatient hospital services",
            "Preventive services (screenings, vaccinations)",
            "Durable medical equipment (DME)",
            "Mental health services (outpatient)",
            "Ambulance services",
            "Clinical laboratory services",
            "Outpatient prescription drugs (limited, e.g., injectable)",
            "Radiology and pathology services"
        ],
        "cost_sharing": {
            "standard_monthly_premium": 174.70,
            "annual_deductible": 240.00,
            "coinsurance": 0.20,
            "preventive_services_copay": 0.00,
            "mental_health_outpatient_coinsurance": 0.20,
            "outpatient_hospital_coinsurance": "Varies by service",
            "clinical_lab_copay": 0.00,
            "dme_coinsurance": 0.20,
            "ambulance_coinsurance": 0.20,
            "physical_therapy_coinsurance": 0.20,
            "high_income_premium_surcharge": {
                "threshold_single": 103000,
                "threshold_married": 206000,
                "tiers": [
                    {"income_single": 103000, "income_married": 206000, "surcharge": 69.90},
                    {"income_single": 129000, "income_married": 258000, "surcharge": 278.20},
                    {"income_single": 161000, "income_married": 322000, "surcharge": 486.50},
                    {"income_single": 193000, "income_married": 386000, "surcharge": 694.80},
                    {"income_single": 500000, "income_married": 750000, "surcharge": 764.00}
                ]
            }
        },
        "coverage_limits": {
            "therapy_cap": "No cap (exceptions process removed 2018)",
            "dme_purchase_threshold": "Varies by item",
            "outpatient_hospital": "No dollar limit per se, subject to medical necessity"
        },
        "eligibility_requirements": [
            "Enrolled in Medicare Part A or eligible for Part A",
            "US citizen or lawfully present resident",
            "Voluntary enrollment (automatic if receiving Social Security)"
        ]
    },
    "medicare_c": {
        "name": "Medicare Part C (Medicare Advantage)",
        "description": "Private plan alternative to Original Medicare combining Part A, B, and usually D benefits",
        "covered_services": [
            "All services covered by Original Medicare (Part A and B)",
            "May include additional benefits: vision, dental, hearing, wellness programs",
            "May include Part D prescription drug coverage"
        ],
        "cost_sharing": {
            "monthly_premium": "Varies by plan ($0 to $200+)",
            "deductible": "Varies by plan",
            "copay_primary_care": "Varies (typically $0-$30)",
            "copay_specialist": "Varies (typically $10-$50)",
            "coinsurance": "Varies (typically 0%-20%)",
            "out_of_pocket_maximum": 8850.00,
            "out_of_pocket_maximum_network_only": True,
            "emergency_copay": "Varies (typically $50-$150)",
            "inpatient_hospital_copay": "Varies (typically $200-$400 per admission)"
        },
        "coverage_limits": {
            "out_of_pocket_maximum": 8850.00,
            "network_restriction": True,
            "referral_required": "Varies by plan type (HMO yes, PPO no)",
            "prior_authorization": "Varies by plan and service"
        },
        "eligibility_requirements": [
            "Enrolled in both Medicare Part A and Part B",
            "Resides in plan service area",
            "Does not have ESRD (with limited exceptions)",
            "Pays Part B premium"
        ]
    },
    "medicare_d": {
        "name": "Medicare Part D (Prescription Drug Coverage)",
        "description": "Outpatient prescription drug coverage through private plans",
        "covered_services": [
            "Outpatient prescription drugs on plan formulary",
            "Vaccines (Shingles, Tdap, COVID-19)",
            "Some covered Part B drugs excluded"
        ],
        "cost_sharing": {
            "deductible": 545.00,
            "initial_coverage_limit": 5030.00,
            "catastrophic_threshold": 8000.00,
            "initial_coverage_coinsurance": 0.25,
            "coverage_gap_discount": 0.70,
            "catastrophic_coinsurance": 0.00,
            "catastrophic_copay_generic": 0.00,
            "catastrophic_copay_brand": 0.00,
            "standard_monthly_premium": 34.50,
            "late_enrollment_penalty": "1% of national average premium per month delayed"
        },
        "coverage_limits": {
            "formulary_tiers": ["Tier 1 Preferred Generic", "Tier 2 Generic", "Tier 3 Preferred Brand", "Tier 4 Non-Preferred Brand", "Tier 5 Specialty"],
            "initial_coverage_limit": 5030.00,
            "catastrophic_threshold": 8000.00,
            "covered_drugs": "Plan-specific formulary"
        },
        "eligibility_requirements": [
            "Entitled to Medicare Part A or enrolled in Part B",
            "Must enroll during Initial Enrollment Period or face penalty",
            "Cannot be enrolled in Medicare Advantage plan with drug coverage (unless switching)"
        ]
    },
    "medicaid": {
        "name": "Medicaid",
        "description": "State and federal program providing health coverage for low-income individuals",
        "covered_services": [
            "Inpatient hospital services",
            "Outpatient hospital services",
            "Physician services",
            "Laboratory and X-ray services",
            "Nursing facility services (age 21+)",
            "Home health services",
            "Early and Periodic Screening, Diagnostic, and Treatment (EPSDT) for children",
            "Family planning services",
            "Rural health clinic services",
            "Federally Qualified Health Center services",
            "Midwife services",
            "Transportation services",
            "Tobacco cessation counseling for pregnant women"
        ],
        "cost_sharing": {
            "deductible": "Varies by state (some states $0)",
            "copay_primary_care": "Varies ($0-$5 typical)",
            "copay_specialist": "Varies ($0-$10 typical)",
            "copay_emergency": "Varies ($0-$15 typical)",
            "copay_prescription_generic": "Varies ($0-$4 typical)",
            "copay_prescription_brand": "Varies ($0-$8 typical)",
            "maximum_annual_out_of_pocket": "5% of family income (federal limit)",
            "exempt_populations": [
                "Children under 18",
                "Pregnant women",
                "Institutionalized individuals",
                "Individuals receiving hospice care",
                "Native Americans/Alaska Natives"
            ]
        },
        "coverage_limits": {
            "mandatory_benefits": "Federal minimum required services",
            "optional_benefits": "State-specific; varies significantly",
            "epsdt_children": "All medically necessary services for under 21",
            "waivers": "States may request 1115 or 1915 waivers for flexibility"
        },
        "eligibility_requirements": [
            "Income at or below 138% FPL in expansion states (ACA)",
            "Categorical eligibility: children, pregnant women, elderly, disabled",
            "Asset limits in non-expansion states (varies by state)",
            "US citizen or qualified immigrant",
            "State residency requirement"
        ]
    },
    "commercial": {
        "name": "Commercial/Group Health Plan",
        "description": "Employer-sponsored or individual health insurance plans",
        "covered_services": [
            "Inpatient hospital services",
            "Outpatient hospital services",
            "Physician services (primary care and specialist)",
            "Preventive care (ACA-required, no cost sharing)",
            "Emergency services",
            "Mental health and substance use disorder services",
            "Prescription drugs",
            "Rehabilitative services",
            "Laboratory services",
            "Maternity and newborn care",
            "Pediatric services (including dental and vision)",
            "Chronic disease management"
        ],
        "cost_sharing": {
            "deductible_individual": "Varies ($500-$8,000+ depending on plan tier)",
            "deductible_family": "Varies ($1,000-$16,000+)",
            "copay_primary_care": "Varies ($15-$40 typical)",
            "copay_specialist": "Varies ($30-$75 typical)",
            "copay_emergency": "Varies ($150-$500 typical)",
            "copay_urgent_care": "Varies ($50-$150 typical)",
            "coinsurance": "Varies (0%-40%, typically 10%-20%)",
            "out_of_pocket_maximum_individual": 9200.00,
            "out_of_pocket_maximum_family": 18400.00,
            "preventive_care_copay": 0.00,
            "tier_bronze_deductible_range": "$5,000-$8,000",
            "tier_silver_deductible_range": "$2,000-$4,500",
            "tier_gold_deductible_range": "$500-$1,500",
            "tier_platinum_deductible_range": "$0-$500"
        },
        "coverage_limits": {
            "out_of_pocket_maximum_individual": 9200.00,
            "out_of_pocket_maximum_family": 18400.00,
            "aca_essential_health_benefits": True,
            "no_annual_lifetime_limits": True,
            "network_restriction": "Varies (HMO/PPO/EPO/POS)",
            "referral_required": "Varies by plan type",
            "prior_authorization": "Varies by plan and service"
        },
        "eligibility_requirements": [
            "Employer group enrollment or individual market purchase",
            "Open enrollment period (Nov 1 - Jan 15 for ACA marketplace)",
            "Special enrollment period for qualifying life events",
            "No pre-existing condition exclusions (ACA)"
        ]
    }
}


@skill(name="eligibility_checker", category="healthcare")
class EligibilityCheckerSkill(AetheraSkill):
    """
    Interpret benefits and eligibility, calculate patient responsibility.
    """

    @property
    def name(self) -> str:
        return "eligibility_checker"

    @property
    def description(self) -> str:
        return "Interpret benefit structures, calculate patient responsibility (deductible/coinsurance/copay), check coverage limits"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["interpret_benefit", "calculate_responsibility", "check_coverage", "full_benefits"],
                    "description": "Action: interpret_benefit, calculate_responsibility, check_coverage, full_benefits"
                },
                "plan_type": {
                    "type": "string",
                    "description": "Insurance plan type (e.g., medicare_a, medicare_b, medicare_c, medicare_d, medicaid, commercial)"
                },
                "service_type": {
                    "type": "string",
                    "description": "Type of service (e.g., inpatient, outpatient, primary_care, specialist, emergency, preventive, prescription, dme, mental_health)"
                },
                "charge_amount": {
                    "type": "number",
                    "description": "Total charge amount for the service (for responsibility calculation)"
                },
                "allowed_amount": {
                    "type": "number",
                    "description": "Allowed/contracted amount for the service"
                },
                "deductible_remaining": {
                    "type": "number",
                    "description": "Remaining deductible amount for the benefit period"
                },
                "oop_remaining": {
                    "type": "number",
                    "description": "Remaining out-of-pocket maximum"
                }
            },
            "required": ["action", "plan_type"]
        }

    @property
    def requires_phi_protection(self) -> bool:
        return True

    @property
    def examples(self) -> list:
        return [
            {"input": {"action": "interpret_benefit", "plan_type": "medicare_b"}},
            {"input": {"action": "calculate_responsibility", "plan_type": "medicare_b", "charge_amount": 500, "allowed_amount": 400, "deductible_remaining": 0}},
            {"input": {"action": "check_coverage", "plan_type": "medicare_a", "service_type": "inpatient"}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "full_benefits")
        plan_type = kwargs.get("plan_type", "")
        service_type = kwargs.get("service_type", "")
        charge_amount = kwargs.get("charge_amount")
        allowed_amount = kwargs.get("allowed_amount")
        deductible_remaining = kwargs.get("deductible_remaining")
        oop_remaining = kwargs.get("oop_remaining")

        if not plan_type:
            return SkillResult(success=False, error="Plan type is required")

        plan_key = plan_type.lower().strip().replace(" ", "_")
        benefit_data = BENEFIT_STRUCTURES.get(plan_key)
        if not benefit_data:
            available = ", ".join(BENEFIT_STRUCTURES.keys())
            return SkillResult(success=False, error=f"Unknown plan type: {plan_type}. Available: {available}")

        try:
            if action == "interpret_benefit":
                result = self._interpret_benefit(benefit_data)
            elif action == "calculate_responsibility":
                result = self._calculate_responsibility(
                    benefit_data, plan_key, service_type, charge_amount,
                    allowed_amount, deductible_remaining, oop_remaining
                )
            elif action == "check_coverage":
                result = self._check_coverage(benefit_data, service_type)
            elif action == "full_benefits":
                result = self._full_benefits(benefit_data)
            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

            return SkillResult(success=True, data=result)

        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _interpret_benefit(self, benefit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Interpret benefit structure for a plan type."""
        return {
            "plan_name": benefit_data["name"],
            "description": benefit_data["description"],
            "covered_services": benefit_data["covered_services"],
            "cost_sharing_summary": self._summarize_cost_sharing(benefit_data["cost_sharing"]),
            "eligibility_requirements": benefit_data["eligibility_requirements"]
        }

    def _summarize_cost_sharing(self, cost_sharing: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create human-readable cost sharing summary."""
        summary = []
        for key, value in cost_sharing.items():
            if key.startswith("high_income") or key == "exempt_populations":
                continue
            label = key.replace("_", " ").title()
            if isinstance(value, float):
                if value < 1:
                    formatted = f"{int(value * 100)}%"
                else:
                    formatted = f"${value:,.2f}"
            elif isinstance(value, int):
                formatted = f"${value:,}"
            else:
                formatted = str(value)
            summary.append({"item": label, "amount": formatted})
        return summary

    def _calculate_responsibility(
        self,
        benefit_data: Dict[str, Any],
        plan_key: str,
        service_type: str,
        charge_amount: Optional[float],
        allowed_amount: Optional[float],
        deductible_remaining: Optional[float],
        oop_remaining: Optional[float]
    ) -> Dict[str, Any]:
        """Calculate patient financial responsibility."""
        if charge_amount is None and allowed_amount is None:
            return {
                "error": "Charge amount or allowed amount is required for calculation",
                "cost_sharing_structure": benefit_data["cost_sharing"]
            }

        base_amount = allowed_amount if allowed_amount else charge_amount
        if base_amount is None:
            base_amount = 0

        patient_deductible = 0.0
        patient_coinsurance = 0.0
        patient_copay = 0.0
        plan_pays = 0.0
        deductible_applied = 0.0

        cost_sharing = benefit_data["cost_sharing"]

        if plan_key == "medicare_b":
            annual_deductible = cost_sharing.get("annual_deductible", 240.00)
            coinsurance_rate = cost_sharing.get("coinsurance", 0.20)

            remaining = deductible_remaining if deductible_remaining is not None else annual_deductible
            if remaining > 0:
                deductible_applied = min(base_amount, remaining)
                patient_deductible = deductible_applied
                base_amount -= deductible_applied

            if service_type == "preventive":
                patient_coinsurance = 0
                plan_pays = base_amount
            elif service_type == "clinical_lab":
                patient_coinsurance = 0
                plan_pays = base_amount
            else:
                patient_coinsurance = round(base_amount * coinsurance_rate, 2)
                plan_pays = round(base_amount * (1 - coinsurance_rate), 2)

        elif plan_key == "medicare_a":
            hospital_deductible = cost_sharing.get("hospital_deductible", 1632.00)
            patient_deductible = min(base_amount, hospital_deductible)
            deductible_applied = patient_deductible
            remaining_after_ded = base_amount - patient_deductible
            plan_pays = remaining_after_ded

        elif plan_key == "medicare_c":
            oop_max = cost_sharing.get("out_of_pocket_maximum", 8850.00)
            if service_type == "primary_care":
                patient_copay = 25.0
            elif service_type == "specialist":
                patient_copay = 45.0
            elif service_type == "emergency":
                patient_copay = 100.0
            elif service_type == "inpatient":
                patient_copay = 300.0
            else:
                coinsurance_rate = 0.20
                patient_coinsurance = round(base_amount * coinsurance_rate, 2)
            plan_pays = round(base_amount - patient_copay - patient_coinsurance, 2)

        elif plan_key == "medicaid":
            if service_type == "primary_care":
                patient_copay = 3.0
            elif service_type == "specialist":
                patient_copay = 5.0
            elif service_type == "emergency":
                patient_copay = 10.0
            elif service_type == "prescription":
                patient_copay = 3.0
            else:
                patient_copay = 0.0
            plan_pays = round(base_amount - patient_copay, 2)

        elif plan_key == "commercial":
            oop_max = cost_sharing.get("out_of_pocket_maximum_individual", 9200.00)
            remaining = deductible_remaining if deductible_remaining is not None else 2000.0

            if service_type == "preventive":
                patient_deductible = 0
                patient_copay = 0
                patient_coinsurance = 0
                plan_pays = base_amount
            else:
                if remaining > 0:
                    deductible_applied = min(base_amount, remaining)
                    patient_deductible = deductible_applied
                    base_amount -= deductible_applied

                if service_type == "primary_care":
                    patient_copay = 25.0
                    plan_pays = round(base_amount - patient_copay, 2)
                elif service_type == "specialist":
                    patient_copay = 50.0
                    plan_pays = round(base_amount - patient_copay, 2)
                elif service_type == "emergency":
                    patient_copay = 250.0
                    plan_pays = round(base_amount - patient_copay, 2)
                else:
                    coinsurance_rate = 0.20
                    patient_coinsurance = round(base_amount * coinsurance_rate, 2)
                    plan_pays = round(base_amount * (1 - coinsurance_rate), 2)

        elif plan_key == "medicare_d":
            deductible = cost_sharing.get("deductible", 545.00)
            remaining = deductible_remaining if deductible_remaining is not None else deductible

            if remaining > 0:
                deductible_applied = min(base_amount, remaining)
                patient_deductible = deductible_applied
                base_amount -= deductible_applied

            coinsurance_rate = cost_sharing.get("initial_coverage_coinsurance", 0.25)
            patient_coinsurance = round(base_amount * coinsurance_rate, 2)
            plan_pays = round(base_amount * (1 - coinsurance_rate), 2)

        total_patient = round(patient_deductible + patient_coinsurance + patient_copay, 2)

        remaining_oop = oop_remaining
        if remaining_oop is not None:
            total_patient = min(total_patient, remaining_oop)

        return {
            "plan_type": plan_key,
            "service_type": service_type or "general",
            "billed_amount": charge_amount,
            "allowed_amount": allowed_amount,
            "patient_responsibility": {
                "deductible": round(patient_deductible, 2),
                "coinsurance": round(patient_coinsurance, 2),
                "copay": round(patient_copay, 2),
                "total": total_patient
            },
            "plan_responsibility": round(max(plan_pays, 0), 2),
            "deductible_applied": round(deductible_applied, 2),
            "notes": "Estimates based on standard benefit structure; actual amounts may vary by specific plan."
        }

    def _check_coverage(self, benefit_data: Dict[str, Any], service_type: str) -> Dict[str, Any]:
        """Check if a service type is covered under the plan."""
        covered = benefit_data["covered_services"]
        limits = benefit_data.get("coverage_limits", {})
        service_keywords = {
            "inpatient": ["inpatient", "hospital", "nursing facility"],
            "outpatient": ["outpatient", "hospital services"],
            "primary_care": ["physician", "doctor", "preventive", "health center"],
            "specialist": ["physician", "doctor", "specialist"],
            "emergency": ["emergency", "ambulance"],
            "preventive": ["preventive", "screening", "vaccination", "epsdt"],
            "prescription": ["prescription", "drug", "pharmacy"],
            "dme": ["durable medical equipment", "dme", "home health"],
            "mental_health": ["mental health", "psychiatric", "substance"],
            "lab": ["laboratory", "x-ray", "radiology", "pathology"],
            "maternity": ["maternity", "newborn"],
            "rehab": ["rehabilitative", "physical therapy", "therapy"],
            "hospice": ["hospice"],
            "home_health": ["home health"],
            "vision": ["vision"],
            "dental": ["dental"],
            "hearing": ["hearing"],
        }

        keywords = service_keywords.get(service_type, [service_type.lower()])
        matching_services = []
        for svc in covered:
            svc_lower = svc.lower()
            if any(kw in svc_lower for kw in keywords):
                matching_services.append(svc)

        is_covered = len(matching_services) > 0
        applicable_limits = {}
        for limit_key, limit_val in limits.items():
            for kw in keywords:
                if kw in limit_key.lower():
                    applicable_limits[limit_key] = limit_val

        return {
            "plan_name": benefit_data["name"],
            "service_type": service_type,
            "covered": is_covered,
            "matching_services": matching_services,
            "coverage_limits": applicable_limits,
            "all_covered_services": covered if not is_covered else None,
            "notes": "Contact plan for specific coverage verification." if not is_covered else None
        }

    def _full_benefits(self, benefit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Return full benefit structure."""
        return {
            "plan_name": benefit_data["name"],
            "description": benefit_data["description"],
            "covered_services": benefit_data["covered_services"],
            "cost_sharing": benefit_data["cost_sharing"],
            "coverage_limits": benefit_data["coverage_limits"],
            "eligibility_requirements": benefit_data["eligibility_requirements"]
        }