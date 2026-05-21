"""
Aethera AI - Patient Cost Estimator Skill

Estimate a patient's out-of-pocket responsibility for a service given their
benefit parameters, and produce a Good Faith Estimate (No Surprises Act) for
self-pay / uninsured patients.
"""

from typing import Any, Dict, List

from skills.skill_base import AetheraSkill, SkillResult, skill

GFE_DISCLAIMER = (
    "This Good Faith Estimate shows the costs of items and services that are "
    "reasonably expected for your health care need. It is not a contract and "
    "does not require you to obtain the listed services. Actual charges may "
    "differ. You have the right to dispute a final bill that exceeds this "
    "estimate by $400 or more (No Surprises Act)."
)


@skill(name="patient_cost_estimator", category="healthcare")
class PatientCostEstimatorSkill(AetheraSkill):

    @property
    def name(self) -> str:
        return "patient_cost_estimator"

    @property
    def description(self) -> str:
        return (
            "Estimate a patient's out-of-pocket cost for a service from their "
            "benefits (deductible remaining, coinsurance, copay, OOP max), or "
            "build a Good Faith Estimate (No Surprises Act) for self-pay/uninsured."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["estimate", "good_faith_estimate"],
                    "description": "estimate = insured OOP; good_faith_estimate = self-pay itemized estimate",
                },
                "charge": {"type": "number", "description": "Billed charge for the service"},
                "allowed_amount": {"type": "number", "description": "Plan-allowed amount (defaults to charge)"},
                "deductible_remaining": {"type": "number"},
                "coinsurance_rate": {"type": "number", "description": "Patient coinsurance as a fraction, e.g. 0.2"},
                "copay": {"type": "number"},
                "oop_max_remaining": {"type": "number", "description": "Remaining out-of-pocket maximum"},
                "items": {
                    "type": "array",
                    "description": "For good_faith_estimate: line items",
                    "items": {"type": "object"},
                },
            },
        }

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "estimate")
        try:
            if action == "good_faith_estimate":
                return self._gfe(kwargs)
            return self._estimate(kwargs)
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _estimate(self, kw: Dict[str, Any]) -> SkillResult:
        charge = float(kw.get("charge", 0) or 0)
        if charge <= 0:
            return SkillResult(success=False, error="'charge' is required and must be > 0")
        allowed = float(kw.get("allowed_amount", charge) or charge)
        ded_remaining = float(kw.get("deductible_remaining", 0) or 0)
        coins_rate = float(kw.get("coinsurance_rate", 0) or 0)
        copay = float(kw.get("copay", 0) or 0)
        oop_remaining = kw.get("oop_max_remaining")

        # Patient pays copay, then deductible up to what's left, then coinsurance
        # on the remaining allowed amount.
        deductible_applied = min(ded_remaining, allowed)
        remainder = max(0.0, allowed - deductible_applied)
        coinsurance = round(remainder * coins_rate, 2)
        patient = round(copay + deductible_applied + coinsurance, 2)

        capped = False
        if oop_remaining is not None:
            oop_remaining = float(oop_remaining)
            if patient > oop_remaining:
                patient = round(oop_remaining, 2)
                capped = True

        plan_pays = round(allowed - (patient - copay), 2)
        return SkillResult(success=True, data={
            "allowed_amount": round(allowed, 2),
            "estimated_patient_responsibility": patient,
            "breakdown": {
                "copay": round(copay, 2),
                "deductible_applied": round(deductible_applied, 2),
                "coinsurance": coinsurance,
                "capped_at_oop_max": capped,
            },
            "estimated_plan_payment": max(0.0, plan_pays),
            "contractual_adjustment": round(charge - allowed, 2),
        })

    def _gfe(self, kw: Dict[str, Any]) -> SkillResult:
        items = kw.get("items") or []
        if not items:
            charge = float(kw.get("charge", 0) or 0)
            if charge <= 0:
                return SkillResult(success=False, error="Provide 'items' or a 'charge' for the GFE")
            items = [{"description": "Service", "charge": charge}]
        line_items = []
        total = 0.0
        for it in items:
            amt = float(it.get("charge", 0) or 0)
            total += amt
            line_items.append({
                "description": it.get("description", "Service"),
                "code": it.get("code"),
                "charge": round(amt, 2),
            })
        return SkillResult(success=True, data={
            "good_faith_estimate": {
                "line_items": line_items,
                "total_estimate": round(total, 2),
                "dispute_threshold": round(total + 400, 2),
            },
            "disclaimer": GFE_DISCLAIMER,
        })
