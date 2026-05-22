import { describe, it, expect } from "vitest";
import { riskAdjuster, eligibilityChecker } from "../src/skills";

function q(t: any, sql: string, a: any[]): any[] {
  const table = (sql.match(/FROM (\w+)/) || [])[1] || "";
  const rows: any[] = t[table] ?? [];
  if (table === "hcc") return rows.filter((r) => r.hcc === a[0] && r.model === a[1]);
  if (table === "hcc_dx") return rows.filter((r) => r.dx === a[0] && r.model === a[1]);
  if (table === "benefit_plan") return rows.filter((r) => r.plan_type === a[0]);
  return rows;
}
function ctx(t: any): any {
  const DB = { prepare(sql: string) { const s: any = { _a: [], bind(...a: any[]) { s._a = a; return s; }, async first() { return q(t, sql, s._a)[0] ?? null; }, async all() { return { results: q(t, sql, s._a) }; } }; return s; } };
  return { env: { DB } };
}

const T = {
  hcc: [
    { hcc: "HCC8", description: "Metastatic Cancer", weight: 1.285, hierarchy_parent: "", model: "V24" },
    { hcc: "HCC9", description: "Lung/Severe Cancer", weight: 0.632, hierarchy_parent: "HCC8", model: "V24" },
    { hcc: "HCC18", description: "Diabetes w/ Chronic Complications", weight: 0.399, hierarchy_parent: "", model: "V24" },
    { hcc: "HCC19", description: "Diabetes w/o Complication", weight: 0.316, hierarchy_parent: "HCC18", model: "V24" },
  ],
  hcc_dx: [
    { dx: "E11.9", hcc: "HCC19", model: "V24" },
    { dx: "C78.00", hcc: "HCC8", model: "V24" },
    { dx: "C34.90", hcc: "HCC9", model: "V24" },
  ],
  benefit_plan: [
    { plan_type: "medicare_b", name: "Medicare Part B", description: "Outpatient", cost_sharing: JSON.stringify({ annual_deductible: 240, coinsurance: 0.2 }), coverage_limits: "{}", covered_services: JSON.stringify(["Doctor services", "Clinical laboratory services"]) },
    { plan_type: "commercial_ppo", name: "Commercial PPO", description: "PPO", cost_sharing: JSON.stringify({ deductible: 1500, coinsurance: 0.2, oop_max: 8000 }), coverage_limits: "{}", covered_services: JSON.stringify(["Office visits", "Lab and imaging"]) },
  ],
};

describe("risk_adjuster", () => {
  it("calculates RAF with demographic + disease", async () => {
    const r = await riskAdjuster.execute({ action: "calculate_raf", diagnosis_codes: ["E11.9"], age: 70, sex: "female" }, ctx(T));
    // demo 0.940 (70-74 F) + disease 0.316 (HCC19) = 1.256
    expect((r.data as any).raf_score).toBeCloseTo(1.256, 3);
    expect((r.data as any).components.disease).toBeCloseTo(0.316, 3);
  });
  it("suppresses a child HCC when its parent is present", async () => {
    const r = await riskAdjuster.execute({ action: "calculate_raf", diagnosis_codes: ["C78.00", "C34.90"], age: 70, sex: "female" }, ctx(T));
    expect((r.data as any).suppressed_by_hierarchy).toContain("HCC9");
    expect((r.data as any).components.disease).toBeCloseTo(1.285, 3); // only HCC8 counts
  });
  it("applies institutional + dual factors", async () => {
    const r = await riskAdjuster.execute({ action: "calculate_raf", diagnosis_codes: ["E11.9"], age: 70, sex: "female", dual_eligible: true, institutional: true }, ctx(T));
    // (0.940 + 0.316 + 0.114) * 1.714
    expect((r.data as any).raf_score).toBeCloseTo(2.349, 2);
  });
  it("looks up an HCC", async () => {
    const r = await riskAdjuster.execute({ action: "lookup_hcc", hcc: "HCC18" }, ctx(T));
    expect((r.data as any).weight).toBe(0.399);
  });
});

describe("eligibility_checker", () => {
  it("returns full benefits", async () => {
    const r = await eligibilityChecker.execute({ action: "full_benefits", plan_type: "medicare_b" }, ctx(T));
    expect((r.data as any).cost_sharing.annual_deductible).toBe(240);
  });
  it("checks coverage by keyword", async () => {
    const r = await eligibilityChecker.execute({ action: "check_coverage", plan_type: "medicare_b", service: "lab" }, ctx(T));
    expect((r.data as any).covered).toBe(true);
  });
  it("calculates patient responsibility", async () => {
    const r = await eligibilityChecker.execute({ action: "calculate_responsibility", plan_type: "commercial_ppo", charge: 1000, deductible_remaining: 500 }, ctx(T));
    // 500 deductible + 20% of remaining 500 = 600
    expect((r.data as any).estimated_patient_responsibility).toBe(600);
    expect((r.data as any).plan_pays).toBe(400);
  });
  it("errors for unknown plan", async () => {
    const r = await eligibilityChecker.execute({ action: "full_benefits", plan_type: "nope" }, ctx(T));
    expect(r.success).toBe(false);
  });
});
