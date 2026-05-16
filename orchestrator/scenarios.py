"""
Counterfactual / 'What if' scenario analysis engine.

Compares baseline state against alternative scenarios to project
differences in revenue, denial rates, compliance exposure, etc.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

import yaml
from pydantic import BaseModel


class ScenarioType(str, Enum):
    REVENUE = "revenue"
    DENIAL = "denial"
    COMPLIANCE = "compliance"
    VOLUME = "volume"
    MIX = "mix"
    CUSTOM = "custom"


class ImpactLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ScenarioVariable:
    name: str
    baseline_value: float
    scenario_value: float
    unit: str = ""
    description: str = ""


@dataclass
class ScenarioResult:
    metric: str
    baseline: float
    projected: float
    delta: float
    delta_pct: float
    impact: ImpactLevel
    confidence: float
    notes: str = ""


@dataclass
class Scenario:
    id: str
    name: str
    description: str
    scenario_type: ScenarioType
    variables: list[ScenarioVariable] = field(default_factory=list)
    results: list[ScenarioResult] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    confidence: float = 0.0


class ScenarioEngine:
    """
    Counterfactual analysis engine for healthcare operations.

    Supports 'what if' questions like:
    - What if denial rate dropped from 12% to 8%?
    - What if we upcoded all DRGs by one severity level?
    - What if CMS changes the conversion factor by 5%?
    - What if patient volume increases 20%?
    """

    # Revenue impact thresholds
    IMPACT_THRESHOLDS = {
        ImpactLevel.LOW: 0.02,       # < 2% change
        ImpactLevel.MEDIUM: 0.05,    # 2-5% change
        ImpactLevel.HIGH: 0.10,      # 5-10% change
        ImpactLevel.CRITICAL: 1.0,   # > 10% change
    }

    def __init__(self, config_path: str | None = None):
        self._scenarios: dict[str, Scenario] = {}
        self._config = self._load_config(config_path) if config_path else {}

    def _load_config(self, path: str) -> dict:
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f) or {}
        except (FileNotFoundError, yaml.YAMLError):
            return {}

    def _classify_impact(self, delta_pct: float) -> ImpactLevel:
        abs_pct = abs(delta_pct)
        if abs_pct < self.IMPACT_THRESHOLDS[ImpactLevel.LOW]:
            return ImpactLevel.LOW
        elif abs_pct < self.IMPACT_THRESHOLDS[ImpactLevel.MEDIUM]:
            return ImpactLevel.MEDIUM
        elif abs_pct < self.IMPACT_THRESHOLDS[ImpactLevel.HIGH]:
            return ImpactLevel.HIGH
        return ImpactLevel.CRITICAL

    # ------------------------------------------------------------------
    # Revenue scenarios
    # ------------------------------------------------------------------

    def revenue_denial_impact(
        self,
        total_charges: float,
        baseline_denial_rate: float,
        scenario_denial_rate: float,
        avg_charge_per_claim: float = 0,
    ) -> Scenario:
        """What if denial rate changes?"""
        baseline_revenue = total_charges * (1 - baseline_denial_rate)
        projected_revenue = total_charges * (1 - scenario_denial_rate)
        delta = projected_revenue - baseline_revenue
        delta_pct = delta / baseline_revenue if baseline_revenue else 0

        claim_count = int(total_charges / avg_charge_per_claim) if avg_charge_per_claim else 0

        result = ScenarioResult(
            metric="Net Revenue",
            baseline=round(baseline_revenue, 2),
            projected=round(projected_revenue, 2),
            delta=round(delta, 2),
            delta_pct=round(delta_pct, 4),
            impact=self._classify_impact(delta_pct),
            confidence=0.7,
            notes=f"Denial rate: {baseline_denial_rate:.1%} → {scenario_denial_rate:.1%}"
            + (f" ({claim_count} claims)" if claim_count else ""),
        )

        return Scenario(
            id=f"denial-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name="Denial Rate Impact on Revenue",
            description=f"Revenue impact of changing denial rate from {baseline_denial_rate:.1%} to {scenario_denial_rate:.1%}",
            scenario_type=ScenarioType.DENIAL,
            variables=[
                ScenarioVariable("denial_rate", baseline_denial_rate, scenario_denial_rate, "%", "Claim denial rate"),
                ScenarioVariable("total_charges", total_charges, total_charges, "$", "Total submitted charges"),
            ],
            results=[result],
            assumptions=["Denial types and payer mix remain constant", "No secondary impact on follow-up claims"],
            confidence=0.7,
        )

    def revenue_volume_impact(
        self,
        baseline_revenue: float,
        volume_change_pct: float,
        avg_revenue_per_encounter: float = 0,
    ) -> Scenario:
        """What if patient volume changes?"""
        projected_revenue = baseline_revenue * (1 + volume_change_pct)
        delta = projected_revenue - baseline_revenue
        delta_pct = volume_change_pct

        encounters = int(baseline_revenue / avg_revenue_per_encounter) if avg_revenue_per_encounter else 0
        projected_encounters = int(encounters * (1 + volume_change_pct))

        result = ScenarioResult(
            metric="Total Revenue",
            baseline=round(baseline_revenue, 2),
            projected=round(projected_revenue, 2),
            delta=round(delta, 2),
            delta_pct=round(delta_pct, 4),
            impact=self._classify_impact(delta_pct),
            confidence=0.6,
            notes=f"Volume change: {volume_change_pct:+.1%}"
            + (f" ({encounters} → {projected_encounters} encounters)" if encounters else ""),
        )

        return Scenario(
            id=f"volume-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name="Patient Volume Impact on Revenue",
            description=f"Revenue impact of {volume_change_pct:+.1%} change in patient volume",
            scenario_type=ScenarioType.VOLUME,
            variables=[
                ScenarioVariable("volume_change", 0, volume_change_pct, "%", "Volume change percentage"),
            ],
            results=[result],
            assumptions=["Revenue per encounter stays constant", "Capacity can absorb volume change"],
            confidence=0.6,
        )

    def revenue_conversion_factor_impact(
        self,
        total_rvus: float,
        baseline_cf: float,
        scenario_cf: float,
    ) -> Scenario:
        """What if Medicare conversion factor changes?"""
        baseline_revenue = total_rvus * baseline_cf
        projected_revenue = total_rvus * scenario_cf
        delta = projected_revenue - baseline_revenue
        delta_pct = delta / baseline_revenue if baseline_revenue else 0

        result = ScenarioResult(
            metric="Medicare Revenue",
            baseline=round(baseline_revenue, 2),
            projected=round(projected_revenue, 2),
            delta=round(delta, 2),
            delta_pct=round(delta_pct, 4),
            impact=self._classify_impact(delta_pct),
            confidence=0.85,
            notes=f"CF: ${baseline_cf:.2f} → ${scenario_cf:.2f} per RVU",
        )

        return Scenario(
            id=f"cf-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name="Conversion Factor Impact",
            description=f"Revenue impact of CF change from ${baseline_cf:.2f} to ${scenario_cf:.2f}",
            scenario_type=ScenarioType.REVENUE,
            variables=[
                ScenarioVariable("conversion_factor", baseline_cf, scenario_cf, "$/RVU", "Medicare CF"),
                ScenarioVariable("total_rvus", total_rvus, total_rvus, "RVUs", "Total work RVUs"),
            ],
            results=[result],
            assumptions=["RVU mix stays constant", "GPCI adjustments unchanged"],
            confidence=0.85,
        )

    def revenue_payer_mix_impact(
        self,
        baseline_mix: dict[str, float],
        scenario_mix: dict[str, float],
        payer_rates: dict[str, float],
        total_charges: float,
    ) -> Scenario:
        """What if payer mix shifts?"""
        baseline_revenue = sum(
            total_charges * baseline_mix.get(payer, 0) * rate
            for payer, rate in payer_rates.items()
        )
        projected_revenue = sum(
            total_charges * scenario_mix.get(payer, 0) * rate
            for payer, rate in payer_rates.items()
        )
        delta = projected_revenue - baseline_revenue
        delta_pct = delta / baseline_revenue if baseline_revenue else 0

        result = ScenarioResult(
            metric="Blended Revenue",
            baseline=round(baseline_revenue, 2),
            projected=round(projected_revenue, 2),
            delta=round(delta, 2),
            delta_pct=round(delta_pct, 4),
            impact=self._classify_impact(delta_pct),
            confidence=0.5,
            notes="Payer mix shift impact on blended collection rate",
        )

        variables = []
        for payer in set(list(baseline_mix.keys()) + list(scenario_mix.keys())):
            variables.append(ScenarioVariable(
                f"{payer}_mix",
                baseline_mix.get(payer, 0),
                scenario_mix.get(payer, 0),
                "%",
                f"{payer} payer mix",
            ))

        return Scenario(
            id=f"mix-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name="Payer Mix Impact on Revenue",
            description="Revenue impact of payer mix shift",
            scenario_type=ScenarioType.MIX,
            variables=variables,
            results=[result],
            assumptions=["Per-payer collection rates remain constant", "Total charges unchanged"],
            confidence=0.5,
        )

    # ------------------------------------------------------------------
    # Compliance scenarios
    # ------------------------------------------------------------------

    def compliance_audit_risk(
        self,
        claim_volume: int,
        error_rate: float,
        avg_claim_value: float,
        penalty_multiplier: float = 3.0,
    ) -> Scenario:
        """What is the financial exposure from coding errors?"""
        error_count = int(claim_volume * error_rate)
        exposure = error_count * avg_claim_value * penalty_multiplier

        result = ScenarioResult(
            metric="Audit Financial Exposure",
            baseline=0,
            projected=round(exposure, 2),
            delta=round(exposure, 2),
            delta_pct=1.0,
            impact=ImpactLevel.CRITICAL if exposure > 100000 else ImpactLevel.HIGH,
            confidence=0.4,
            notes=f"{error_count} estimated errors at {error_rate:.1%} rate, {penalty_multiplier}x penalty",
        )

        return Scenario(
            id=f"audit-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name="Audit Financial Exposure",
            description=f"Financial exposure from {error_rate:.1%} coding error rate on {claim_volume} claims",
            scenario_type=ScenarioType.COMPLIANCE,
            variables=[
                ScenarioVariable("error_rate", 0, error_rate, "%", "Coding error rate"),
                ScenarioVariable("penalty_multiplier", 0, penalty_multiplier, "x", "FCA penalty multiplier"),
            ],
            results=[result],
            assumptions=["All errors treated as FCA violations (worst case)", "Self-disclosure not factored in"],
            confidence=0.4,
        )

    # ------------------------------------------------------------------
    # Multi-variable scenario
    # ------------------------------------------------------------------

    def custom_scenario(
        self,
        name: str,
        description: str,
        variables: list[dict],
        baseline_revenue: float,
    ) -> Scenario:
        """Build a custom multi-variable scenario."""
        total_multiplier = 1.0
        scenario_vars = []

        for v in variables:
            sv = ScenarioVariable(
                name=v["name"],
                baseline_value=v.get("baseline", 0),
                scenario_value=v.get("scenario_value", 0),
                unit=v.get("unit", ""),
                description=v.get("description", ""),
            )
            scenario_vars.append(sv)
            if v.get("revenue_impact_pct"):
                total_multiplier += v["revenue_impact_pct"]

        projected_revenue = baseline_revenue * total_multiplier
        delta = projected_revenue - baseline_revenue
        delta_pct = delta / baseline_revenue if baseline_revenue else 0

        result = ScenarioResult(
            metric="Projected Revenue",
            baseline=round(baseline_revenue, 2),
            projected=round(projected_revenue, 2),
            delta=round(delta, 2),
            delta_pct=round(delta_pct, 4),
            impact=self._classify_impact(delta_pct),
            confidence=0.3,
            notes="Custom multi-variable scenario",
        )

        return Scenario(
            id=f"custom-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name=name,
            description=description,
            scenario_type=ScenarioType.CUSTOM,
            variables=scenario_vars,
            results=[result],
            assumptions=["Variables are independent unless noted"],
            confidence=0.3,
        )

    # ------------------------------------------------------------------
    # Scenario management
    # ------------------------------------------------------------------

    def save_scenario(self, scenario: Scenario) -> str:
        self._scenarios[scenario.id] = scenario
        return scenario.id

    def get_scenario(self, scenario_id: str) -> Scenario | None:
        return self._scenarios.get(scenario_id)

    def list_scenarios(self) -> list[dict]:
        return [
            {
                "id": s.id,
                "name": s.name,
                "type": s.scenario_type.value,
                "created_at": s.created_at.isoformat(),
                "confidence": s.confidence,
            }
            for s in self._scenarios.values()
        ]

    def compare_scenarios(self, scenario_ids: list[str]) -> dict:
        """Compare multiple scenarios side by side."""
        scenarios = [self._scenarios[sid] for sid in scenario_ids if sid in self._scenarios]
        if not scenarios:
            return {"error": "No valid scenario IDs provided"}

        comparison = {
            "scenarios": [],
            "summary": {},
        }
        for s in scenarios:
            comparison["scenarios"].append({
                "id": s.id,
                "name": s.name,
                "type": s.scenario_type.value,
                "results": [
                    {
                        "metric": r.metric,
                        "baseline": r.baseline,
                        "projected": r.projected,
                        "delta": r.delta,
                        "delta_pct": f"{r.delta_pct:+.2%}",
                        "impact": r.impact.value,
                    }
                    for r in s.results
                ],
            })

        return comparison