import { describe, it, expect } from "vitest";
import { rcmKpiCalculator, emLevelAdvisor, patientCostEstimator } from "../src/skills";

describe("rcm_kpi_calculator", () => {
  it("computes and grades KPIs", () => {
    const r = rcmKpiCalculator.execute({
      total_ar: 400000, average_daily_charges: 10000,
      total_claims: 1000, clean_claims: 970, denied_claims: 40,
      total_charges: 1000000, total_payments: 600000, contractual_adjustments: 380000,
    });
    expect(r.success).toBe(true);
    const k = (r.data as any).kpis;
    expect(k.days_in_ar.value).toBe(40);
    expect(k.days_in_ar.status).toBe("good");
    expect(k.clean_claim_rate.value).toBe(97);
    expect(k.denial_rate.value).toBe(4);
  });

  it("fails with no usable inputs", () => {
    expect(rcmKpiCalculator.execute({ total_ar: 100 }).success).toBe(false);
  });
});

describe("em_level_advisor", () => {
  it("by time (established)", () => {
    const r = emLevelAdvisor.execute({ method: "time", patient_type: "established", total_time_minutes: 35 });
    expect((r.data as any).recommended_code).toBe("99214");
  });
  it("by MDM 2-of-3", () => {
    const r = emLevelAdvisor.execute({
      method: "mdm", patient_type: "new",
      problems_level: "moderate", data_level: "moderate", risk_level: "low",
    });
    expect((r.data as any).mdm_level).toBe("moderate");
    expect((r.data as any).recommended_code).toBe("99204");
  });
  it("rejects below-threshold time", () => {
    expect(emLevelAdvisor.execute({ method: "time", patient_type: "established", total_time_minutes: 5 }).success).toBe(false);
  });
});

describe("patient_cost_estimator", () => {
  it("deductible + coinsurance", () => {
    const r = patientCostEstimator.execute({ charge: 300, allowed_amount: 200, deductible_remaining: 50, coinsurance_rate: 0.2 });
    expect((r.data as any).estimated_patient_responsibility).toBe(80);
    expect((r.data as any).contractual_adjustment).toBe(100);
  });
  it("caps at OOP max", () => {
    const r = patientCostEstimator.execute({ charge: 1000, allowed_amount: 1000, deductible_remaining: 1000, oop_max_remaining: 250 });
    expect((r.data as any).estimated_patient_responsibility).toBe(250);
    expect((r.data as any).breakdown.capped_at_oop_max).toBe(true);
  });
});
