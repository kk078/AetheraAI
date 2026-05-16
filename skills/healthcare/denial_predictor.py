"""
Aethera AI - Denial Predictor Skill

Predict denial probability before submission using historical denial patterns
by CARC code, common denial reasons by service type, and payer-specific
denial trends. Returns probability score (0-1), risk factors, and prevention
recommendations.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="denial_predictor", category="healthcare")
class DenialPredictorSkill(AetheraSkill):
    """
    Predict denial probability before claim submission.
    """

    @property
    def name(self) -> str:
        return "denial_predictor"

    @property
    def description(self) -> str:
        return "Predict denial probability before submission using historical denial patterns, service type risk, and payer trends"

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
                    "description": "Modifiers paired with procedure codes"
                },
                "place_of_service": {
                    "type": "string",
                    "description": "Place of service code"
                },
                "payer": {
                    "type": "string",
                    "description": "Insurance payer name (e.g., Medicare, Aetna, UnitedHealthcare)"
                },
                "service_type": {
                    "type": "string",
                    "enum": ["office_visit", "emergency", "surgery", "radiology",
                             "lab", "therapy", "durable_medical_equipment", "home_health",
                             "inpatient", "outpatient", "ambulance", "other"],
                    "description": "Type of service being billed"
                },
                "prior_authorization_obtained": {
                    "type": "boolean",
                    "description": "Whether prior authorization was obtained"
                },
                "patient_new_or_established": {
                    "type": "string",
                    "enum": ["new", "established", "unknown"],
                    "description": "Patient new or established status"
                }
            },
            "required": ["diagnosis_codes", "procedure_codes", "payer"]
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
                    "payer": "Medicare",
                    "service_type": "office_visit"
                }
            },
            {
                "input": {
                    "diagnosis_codes": ["M54.5"],
                    "procedure_codes": ["97110", "97112"],
                    "payer": "Aetna",
                    "service_type": "therapy",
                    "prior_authorization_obtained": False
                }
            }
        ]

    # --- Historical denial rates by CARC code ---
    CARC_DENIAL_RATES: Dict[str, Dict[str, Any]] = {
        "CO-4":  {"rate": 0.72, "description": "Procedure inconsistent with modifier", "preventable": True},
        "CO-11": {"rate": 0.65, "description": "Diagnosis inconsistent with procedure", "preventable": True},
        "CO-16": {"rate": 0.58, "description": "Missing information for adjudication", "preventable": True},
        "CO-18": {"rate": 0.80, "description": "Duplicate claim", "preventable": True},
        "CO-22": {"rate": 0.35, "description": "Coordination of benefits issue", "preventable": True},
        "CO-27": {"rate": 0.90, "description": "Coverage terminated", "preventable": False},
        "CO-29": {"rate": 0.95, "description": "Filing time limit expired", "preventable": True},
        "CO-45": {"rate": 0.50, "description": "Charges exceed fee arrangement", "preventable": False},
        "CO-50": {"rate": 0.60, "description": "Not medically necessary", "preventable": True},
        "CO-97": {"rate": 0.55, "description": "Bundled/unbundled adjustment", "preventable": True},
        "PR-1":  {"rate": 1.0, "description": "Deductible", "preventable": False},
        "PR-2":  {"rate": 1.0, "description": "Coinsurance", "preventable": False},
        "PR-3":  {"rate": 1.0, "description": "Copay", "preventable": False},
    }

    # --- Denial risk by service type ---
    SERVICE_TYPE_RISK: Dict[str, Dict[str, Any]] = {
        "office_visit": {
            "base_denial_rate": 0.05,
            "common_denial_codes": ["CO-16", "CO-11"],
            "risk_factors": ["missing_referral", "wrong_pos"]
        },
        "emergency": {
            "base_denial_rate": 0.12,
            "common_denial_codes": ["CO-50", "CO-4", "CO-16"],
            "risk_factors": ["medical_necessity", "authorization"]
        },
        "surgery": {
            "base_denial_rate": 0.10,
            "common_denial_codes": ["CO-50", "CO-97", "CO-4"],
            "risk_factors": ["prior_auth", "bundling", "medical_necessity"]
        },
        "radiology": {
            "base_denial_rate": 0.09,
            "common_denial_codes": ["CO-50", "CO-16", "CO-4"],
            "risk_factors": ["prior_auth", "medical_necessity", "missing_clinical_info"]
        },
        "lab": {
            "base_denial_rate": 0.07,
            "common_denial_codes": ["CO-50", "CO-16"],
            "risk_factors": ["medical_necessity", "missing_diagnosis"]
        },
        "therapy": {
            "base_denial_rate": 0.18,
            "common_denial_codes": ["CO-50", "CO-97", "CO-16", "CO-11"],
            "risk_factors": ["prior_auth", "medical_necessity", "bundling", "session_limits"]
        },
        "durable_medical_equipment": {
            "base_denial_rate": 0.20,
            "common_denial_codes": ["CO-50", "CO-16", "CO-4"],
            "risk_factors": ["prior_auth", "medical_necessity", "documentation"]
        },
        "home_health": {
            "base_denial_rate": 0.15,
            "common_denial_codes": ["CO-50", "CO-16"],
            "risk_factors": ["homebound_status", "medical_necessity", "certification"]
        },
        "inpatient": {
            "base_denial_rate": 0.08,
            "common_denial_codes": ["CO-50", "CO-97"],
            "risk_factors": ["length_of_stay", "medical_necessity", "admission_status"]
        },
        "outpatient": {
            "base_denial_rate": 0.07,
            "common_denial_codes": ["CO-16", "CO-50"],
            "risk_factors": ["medical_necessity", "authorization"]
        },
        "ambulance": {
            "base_denial_rate": 0.22,
            "common_denial_codes": ["CO-50", "CO-16"],
            "risk_factors": ["medical_necessity", "transport_necessity"]
        },
        "other": {
            "base_denial_rate": 0.10,
            "common_denial_codes": ["CO-16", "CO-50"],
            "risk_factors": ["documentation", "medical_necessity"]
        }
    }

    # --- Payer-specific denial trend modifiers ---
    # Multiplier applied to base risk. >1.0 means higher-than-average denials.
    PAYER_RISK: Dict[str, Dict[str, Any]] = {
        "Medicare": {
            "multiplier": 0.85,
            "top_denial_reasons": ["CO-97 (bundling)", "CO-50 (medical necessity)", "CO-4 (modifier)"],
            "avg_days_to_denial": 30,
            "appeal_success_rate": 0.42
        },
        "Medicaid": {
            "multiplier": 1.20,
            "top_denial_reasons": ["CO-16 (missing info)", "CO-50 (medical necessity)", "CO-27 (coverage terminated)"],
            "avg_days_to_denial": 21,
            "appeal_success_rate": 0.35
        },
        "Aetna": {
            "multiplier": 0.95,
            "top_denial_reasons": ["CO-50 (medical necessity)", "CO-16 (missing info)", "CO-4 (modifier)"],
            "avg_days_to_denial": 25,
            "appeal_success_rate": 0.38
        },
        "UnitedHealthcare": {
            "multiplier": 1.05,
            "top_denial_reasons": ["CO-50 (medical necessity)", "CO-16 (missing info)", "CO-22 (COB)"],
            "avg_days_to_denial": 28,
            "appeal_success_rate": 0.40
        },
        "Cigna": {
            "multiplier": 1.00,
            "top_denial_reasons": ["CO-50 (medical necessity)", "CO-16 (missing info)"],
            "avg_days_to_denial": 22,
            "appeal_success_rate": 0.37
        },
        "Blue Cross Blue Shield": {
            "multiplier": 0.90,
            "top_denial_reasons": ["CO-16 (missing info)", "CO-50 (medical necessity)"],
            "avg_days_to_denial": 26,
            "appeal_success_rate": 0.44
        },
        "Humana": {
            "multiplier": 1.10,
            "top_denial_reasons": ["CO-50 (medical necessity)", "CO-16 (missing info)", "CO-97 (bundling)"],
            "avg_days_to_denial": 24,
            "appeal_success_rate": 0.33
        },
        "Kaiser": {
            "multiplier": 0.80,
            "top_denial_reasons": ["CO-16 (missing info)", "CO-22 (COB)"],
            "avg_days_to_denial": 20,
            "appeal_success_rate": 0.45
        },
        "Tricare": {
            "multiplier": 0.75,
            "top_denial_reasons": ["CO-16 (missing info)", "CO-4 (modifier)"],
            "avg_days_to_denial": 30,
            "appeal_success_rate": 0.48
        }
    }

    # --- High-risk diagnosis codes (frequently denied for medical necessity) ---
    HIGH_RISK_DIAGNOSIS: Dict[str, Dict[str, Any]] = {
        "M54.5": {"risk": 0.15, "reason": "Low back pain - often needs documentation of conservative treatment first"},
        "M54.2": {"risk": 0.12, "reason": "Cervicalgia - similar conservative treatment requirements"},
        "F32.1": {"risk": 0.10, "reason": "Major depressive disorder - may need prior auth for certain treatments"},
        "F41.1": {"risk": 0.10, "reason": "Generalized anxiety - therapy session limits common"},
        "R10.9": {"risk": 0.18, "reason": "Unspecified abdominal pain - unspecific diagnosis often denied"},
        "R06.02": {"risk": 0.20, "reason": "Shortness of breath - needs specificity for many procedures"},
        "G43.909": {"risk": 0.10, "reason": "Migraine - Botox/CGRP require specific criteria"},
        "E11.9": {"risk": 0.05, "reason": "Type 2 DM without complications - generally low risk"},
        "I10": {"risk": 0.04, "reason": "Essential hypertension - very commonly accepted"},
        "J06.9": {"risk": 0.08, "reason": "Acute upper respiratory infection - watch for antibiotic denial"},
        "K21.0": {"risk": 0.06, "reason": "GERD - generally well covered"},
        "M17.11": {"risk": 0.08, "reason": "Primary osteoarthritis, right knee - injection limits"},
        "G89.29": {"risk": 0.14, "reason": "Other chronic pain - often needs supporting documentation"},
        "Z79.899": {"risk": 0.16, "reason": "Long term medication use - may need medical necessity"},
        "F11.20": {"risk": 0.22, "reason": "Opioid dependence - requires specific authorization"},
    }

    # --- High-risk procedure codes ---
    HIGH_RISK_PROCEDURES: Dict[str, Dict[str, Any]] = {
        "97110": {"risk": 0.15, "reason": "Therapeutic exercises - session limits and bundling risk"},
        "97112": {"risk": 0.14, "reason": "Neuromuscular re-education - bundling with 97110"},
        "97140": {"risk": 0.18, "reason": "Manual therapy - CCI edit with 97110/97112, needs modifier 59"},
        "97530": {"risk": 0.12, "reason": "Therapeutic activities - bundling with 97110"},
        "90837": {"risk": 0.15, "reason": "Psychotherapy 60 min - session limits, medical necessity"},
        "90834": {"risk": 0.08, "reason": "Psychotherapy 45 min - moderate risk"},
        "64483": {"risk": 0.20, "reason": "ESI lumbar - frequency limits, prior auth common"},
        "77067": {"risk": 0.10, "reason": "Screening mammography - generally covered but age criteria"},
        "27447": {"risk": 0.12, "reason": "Total knee arthroplasty - prior auth required"},
        "22551": {"risk": 0.15, "reason": "Vertebroplasty - strict medical necessity criteria"},
        "43239": {"risk": 0.08, "reason": "EGD with biopsy - generally covered with right diagnosis"},
        "93306": {"risk": 0.10, "reason": "Transthoracic echo - diagnosis specificity important"},
        "99285": {"risk": 0.12, "reason": "ED visit high complexity - medical necessity documentation"},
        "83036": {"risk": 0.06, "reason": "HbA1c - well covered for diabetes monitoring"},
        "94010": {"risk": 0.08, "reason": "Spirometry - diagnosis must support pulmonary evaluation"},
    }

    # --- Prior authorization requirements by payer/procedure ---
    PRIOR_AUTH_REQUIRED: Dict[str, List[str]] = {
        "Medicare": ["27447", "22551", "64483", "93306"],
        "Aetna": ["27447", "22551", "64483", "90837", "97110", "97112", "97140"],
        "UnitedHealthcare": ["27447", "22551", "64483", "90837", "97110", "97140", "97530"],
        "Cigna": ["27447", "64483", "97110", "90837"],
        "Humana": ["27447", "22551", "64483", "97110", "97112", "97140", "90837"],
        "Blue Cross Blue Shield": ["27447", "64483", "97110", "22551"],
    }

    async def execute(self, **kwargs) -> SkillResult:
        diagnosis_codes = kwargs.get("diagnosis_codes", [])
        procedure_codes = kwargs.get("procedure_codes", [])
        modifiers = kwargs.get("modifiers", [])
        place_of_service = kwargs.get("place_of_service", "")
        payer = kwargs.get("payer", "Unknown")
        service_type = kwargs.get("service_type", "other")
        prior_auth = kwargs.get("prior_authorization_obtained", None)
        patient_status = kwargs.get("patient_new_or_established", "unknown")

        if not procedure_codes:
            return SkillResult(success=False, error="Procedure codes are required")
        if not payer:
            return SkillResult(success=False, error="Payer is required")

        try:
            result = self._predict_denial(
                diagnosis_codes=diagnosis_codes,
                procedure_codes=procedure_codes,
                modifiers=modifiers,
                place_of_service=place_of_service,
                payer=payer,
                service_type=service_type,
                prior_auth_obtained=prior_auth,
                patient_status=patient_status
            )
            return SkillResult(success=True, data=result)
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _predict_denial(
        self,
        diagnosis_codes: List[str],
        procedure_codes: List[str],
        modifiers: List[str],
        place_of_service: str,
        payer: str,
        service_type: str,
        prior_auth_obtained: Optional[bool],
        patient_status: str
    ) -> Dict[str, Any]:
        """Calculate denial probability and identify risk factors."""

        risk_factors: List[Dict[str, Any]] = []
        total_risk_score = 0.0

        # 1. Base risk from service type
        service_risk = self.SERVICE_TYPE_RISK.get(service_type, self.SERVICE_TYPE_RISK["other"])
        base_rate = service_risk["base_denial_rate"]
        total_risk_score += base_rate * 30  # Weight: 30%

        risk_factors.append({
            "factor": "service_type_risk",
            "detail": f"Service type '{service_type}' has a base denial rate of {base_rate:.0%}",
            "weight": 0.30,
            "contribution": base_rate
        })

        # 2. Payer-specific risk multiplier
        payer_info = self._find_payer(payer)
        payer_multiplier = payer_info.get("multiplier", 1.0)
        adjusted_base = base_rate * payer_multiplier
        payer_contribution = max(0, adjusted_base - base_rate)
        total_risk_score += payer_contribution * 20  # Weight: 20%

        risk_factors.append({
            "factor": "payer_risk",
            "detail": f"Payer '{payer}' has a risk multiplier of {payer_multiplier:.2f}. "
                      f"Top denial reasons: {', '.join(payer_info.get('top_denial_reasons', [])[:2])}",
            "weight": 0.20,
            "contribution": payer_contribution
        })

        # 3. Diagnosis-specific risk
        max_diag_risk = 0.0
        for dx in diagnosis_codes:
            dx = dx.strip().upper()
            if dx in self.HIGH_RISK_DIAGNOSIS:
                dx_info = self.HIGH_RISK_DIAGNOSIS[dx]
                diag_contribution = dx_info["risk"]
                if diag_contribution > max_diag_risk:
                    max_diag_risk = diag_contribution
                risk_factors.append({
                    "factor": "high_risk_diagnosis",
                    "detail": f"Diagnosis {dx} flagged: {dx_info['reason']}",
                    "weight": 0.15,
                    "contribution": diag_contribution
                })

        total_risk_score += max_diag_risk * 15  # Weight: 15%

        # 4. Procedure-specific risk
        max_proc_risk = 0.0
        for proc in procedure_codes:
            proc = proc.strip()
            if proc in self.HIGH_RISK_PROCEDURES:
                proc_info = self.HIGH_RISK_PROCEDURES[proc]
                proc_contribution = proc_info["risk"]
                if proc_contribution > max_proc_risk:
                    max_proc_risk = proc_contribution
                risk_factors.append({
                    "factor": "high_risk_procedure",
                    "detail": f"Procedure {proc} flagged: {proc_info['reason']}",
                    "weight": 0.15,
                    "contribution": proc_contribution
                })

        total_risk_score += max_proc_risk * 15  # Weight: 15%

        # 5. Prior authorization risk
        prior_auth_risk = 0.0
        prior_auth_procs = self.PRIOR_AUTH_REQUIRED.get(payer, [])
        for proc in procedure_codes:
            proc = proc.strip()
            if proc in prior_auth_procs:
                if prior_auth_obtained is True:
                    risk_factors.append({
                        "factor": "prior_authorization",
                        "detail": f"Procedure {proc} requires prior auth for {payer} - AUTHORIZATION OBTAINED",
                        "weight": 0.10,
                        "contribution": 0.0
                    })
                elif prior_auth_obtained is False:
                    prior_auth_risk = 0.35
                    risk_factors.append({
                        "factor": "prior_authorization",
                        "detail": f"Procedure {proc} requires prior auth for {payer} - NOT OBTAINED (HIGH RISK)",
                        "weight": 0.10,
                        "contribution": 0.35
                    })
                else:
                    prior_auth_risk = 0.18
                    risk_factors.append({
                        "factor": "prior_authorization",
                        "detail": f"Procedure {proc} may require prior auth for {payer} - STATUS UNKNOWN",
                        "weight": 0.10,
                        "contribution": 0.18
                    })

        total_risk_score += prior_auth_risk * 10  # Weight: 10%

        # 6. Modifier-related risk
        if procedure_codes and modifiers:
            has_59 = any(m.strip() in ("59", "XE", "XS", "XP", "XU") for m in modifiers)
            if has_59:
                risk_factors.append({
                    "factor": "modifier_59_usage",
                    "detail": "Modifier 59/X-modifiers present: increased scrutiny likely. Ensure distinct services documented.",
                    "weight": 0.05,
                    "contribution": 0.08
                })
                total_risk_score += 0.08 * 5

        # 7. Multiple procedure risk
        if len(procedure_codes) > 3:
            risk_factors.append({
                "factor": "multiple_procedures",
                "detail": f"Claim has {len(procedure_codes)} procedure codes: increased bundling/duplicate risk",
                "weight": 0.05,
                "contribution": 0.05
            })
            total_risk_score += 0.05 * 5

        # 8. Place of service risk modifier
        pos_risk = 0.0
        HIGH_RISK_POS = {"inpatient": 0.12, "outpatient_hospital": 0.08, "ambulatory_surgical": 0.06}
        if place_of_service:
            pos_risk = HIGH_RISK_POS.get(place_of_service.lower(), 0.02)
            if pos_risk > 0.02:
                risk_factors.append({
                    "factor": "place_of_service",
                    "detail": f"Place of service '{place_of_service}' has elevated denial risk ({pos_risk:.0%})",
                    "weight": 0.05,
                    "contribution": pos_risk,
                })

        # 9. New patient risk
        if patient_status == "new":
            risk_factors.append({
                "factor": "new_patient",
                "detail": "New patient visits have higher documentation scrutiny",
                "weight": 0.03,
                "contribution": 0.05,
            })

        # Normalize to 0-1 probability using weighted average
        # Each factor has a weight (importance) and contribution (risk level)
        # Probability = sum(weight * contribution) / sum(weights)
        total_weight = 0.0
        weighted_risk = 0.0
        for rf in risk_factors:
            w = rf.get("weight", 0)
            c = rf.get("contribution", 0)
            total_weight += w
            weighted_risk += w * c

        probability = min(max(weighted_risk / total_weight, 0.0), 1.0) if total_weight > 0 else 0.0

        # Risk level
        if probability >= 0.70:
            risk_level = "critical"
        elif probability >= 0.40:
            risk_level = "high"
        elif probability >= 0.20:
            risk_level = "moderate"
        else:
            risk_level = "low"

        # Generate prevention recommendations
        recommendations = self._generate_prevention_recommendations(
            risk_factors, payer, service_type, procedure_codes, prior_auth_obtained
        )

        return {
            "denial_probability": round(probability, 4),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "prevention_recommendations": recommendations,
            "payer_info": {
                "name": payer,
                "multiplier": payer_multiplier,
                "top_denial_reasons": payer_info.get("top_denial_reasons", []),
                "appeal_success_rate": payer_info.get("appeal_success_rate", 0.35),
                "avg_days_to_denial": payer_info.get("avg_days_to_denial", 25)
            },
            "service_type": service_type,
            "likely_denial_codes": self._predict_likely_denial_codes(service_type, payer_info),
            "likely_denial_codes_detail": self._enrich_denial_codes(
                self._predict_likely_denial_codes(service_type, payer_info)
            ),
        }

    def _find_payer(self, payer: str) -> Dict[str, Any]:
        """Find closest matching payer in database."""
        payer_lower = payer.lower()
        for known_payer, info in self.PAYER_RISK.items():
            if known_payer.lower() in payer_lower or payer_lower in known_payer.lower():
                return info
        # Default
        return {
            "multiplier": 1.0,
            "top_denial_reasons": ["CO-50 (medical necessity)", "CO-16 (missing info)"],
            "avg_days_to_denial": 25,
            "appeal_success_rate": 0.35
        }

    def _generate_prevention_recommendations(
        self,
        risk_factors: List[Dict[str, Any]],
        payer: str,
        service_type: str,
        procedure_codes: List[str],
        prior_auth_obtained: Optional[bool]
    ) -> List[Dict[str, Any]]:
        """Generate actionable prevention recommendations."""
        recommendations = []

        for rf in risk_factors:
            factor = rf["factor"]
            detail = rf["detail"]

            if factor == "high_risk_diagnosis":
                recommendations.append({
                    "action": "Strengthen diagnosis documentation",
                    "detail": f"Based on: {detail}. Ensure clinical notes clearly support medical necessity. Use the most specific diagnosis code available.",
                    "priority": "high"
                })

            elif factor == "high_risk_procedure":
                recommendations.append({
                    "action": "Verify coverage and authorization",
                    "detail": f"Based on: {detail}. Confirm procedure is covered under patient's plan and any prior auth requirements are met.",
                    "priority": "high"
                })

            elif factor == "prior_authorization":
                if prior_auth_obtained is False or prior_auth_obtained is None:
                    recommendations.append({
                        "action": "Obtain prior authorization before submission",
                        "detail": f"Based on: {detail}. Contact payer to obtain required authorization. Do not submit until authorized.",
                        "priority": "critical"
                    })

            elif factor == "payer_risk":
                recommendations.append({
                    "action": "Review payer-specific requirements",
                    "detail": f"Based on: {detail}. Check payer's clinical policies, LCD/NCD requirements, and billing guidelines.",
                    "priority": "medium"
                })

            elif factor == "modifier_59_usage":
                recommendations.append({
                    "action": "Document distinct services",
                    "detail": "Modifier 59 claims face extra scrutiny. Ensure documentation clearly shows separate site, session, or condition.",
                    "priority": "high"
                })

            elif factor == "multiple_procedures":
                recommendations.append({
                    "action": "Review bundling rules",
                    "detail": "Multiple procedures on same claim increase bundling risk. Verify CCI edits and append appropriate modifiers.",
                    "priority": "medium"
                })

        # Add service-type-specific recommendations
        service_risk = self.SERVICE_TYPE_RISK.get(service_type, {})
        for rf_type in service_risk.get("risk_factors", []):
            if rf_type == "medical_necessity":
                recommendations.append({
                    "action": "Include medical necessity documentation",
                    "detail": f"For {service_type} claims, ensure clinical rationale is clearly documented in the chart.",
                    "priority": "high"
                })
            elif rf_type == "prior_auth":
                if prior_auth_obtained is not True:
                    recommendations.append({
                        "action": "Verify prior authorization",
                        "detail": f"This {service_type} service commonly requires prior authorization. Verify with payer.",
                        "priority": "high"
                    })

        if not recommendations:
            recommendations.append({
                "action": "Standard submission",
                "detail": "No high-risk factors identified. Follow standard billing practices and ensure documentation is complete.",
                "priority": "low"
            })

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda r: priority_order.get(r["priority"], 3))

        return recommendations

    def _predict_likely_denial_codes(self, service_type: str, payer_info: Dict[str, Any]) -> List[str]:
        """Predict the most likely CARC codes if denied."""
        service_risk = self.SERVICE_TYPE_RISK.get(service_type, self.SERVICE_TYPE_RISK["other"])
        codes = list(set(service_risk.get("common_denial_codes", []) +
                         [c.split(" ")[0] for c in payer_info.get("top_denial_reasons", [])]))
        return codes[:5]

    def _enrich_denial_codes(self, codes: List[str]) -> List[Dict[str, Any]]:
        """Enrich denial codes with rates and preventability from CARC_DENIAL_RATES."""
        enriched = []
        for code in codes:
            carc_info = self.CARC_DENIAL_RATES.get(code, {})
            enriched.append({
                "code": code,
                "rate": carc_info.get("rate", 0.0),
                "description": carc_info.get("description", "Unknown denial code"),
                "preventable": carc_info.get("preventable", True),
            })
        # Sort by rate descending (most likely first)
        enriched.sort(key=lambda x: x["rate"], reverse=True)
        return enriched