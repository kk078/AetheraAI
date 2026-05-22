import { describe, it, expect } from "vitest";
import { drugReference, ndcPricer } from "../src/skills";

function q(t: any, sql: string, a: any[]): any[] {
  const table = (sql.match(/FROM (\w+)/) || [])[1] || "";
  const rows: any[] = t[table] ?? [];
  if (table === "drug") return rows.filter((r) => r.name === a[0]);
  if (table === "drug_interaction") return rows.filter((r) => r.drug_a === a[0] && r.drug_b === a[1]);
  if (table === "drug_formulary") return rows.filter((r) => r.drug === a[0] && r.payer === a[1]);
  if (table === "ndc") return rows.filter((r) => r.ndc === a[0]);
  return rows;
}
function ctx(t: any): any {
  const DB = { prepare(sql: string) { const s: any = { _a: [], bind(...a: any[]) { s._a = a; return s; }, async first() { return q(t, sql, s._a)[0] ?? null; }, async all() { return { results: q(t, sql, s._a) }; } }; return s; } };
  return { env: { DB } };
}

const T = {
  drug: [
    { name: "warfarin", drug_class: "Anticoagulant", indication: "Thromboembolism", route: "Oral", common_dosage: "to INR", black_box_warning: "bleeding", generic_available: 1 },
    { name: "metformin", drug_class: "Biguanide", indication: "T2DM", route: "Oral", common_dosage: "500-2550", black_box_warning: "lactic acidosis", generic_available: 1 },
  ],
  drug_interaction: [
    { drug_a: "aspirin", drug_b: "warfarin", severity: "major", note: "bleeding" },
    { drug_a: "atorvastatin", drug_b: "warfarin", severity: "moderate", note: "monitor INR" },
  ],
  drug_formulary: [{ drug: "metformin", payer: "Medicare", tier: 1 }],
  ndc: [
    { ndc: "00074433902", drug_name: "Adalimumab", strength: "40 mg/0.8 mL", asp: 2950.0, awp: 8600.0, wac: 7100.0, nadac: 0, units_per_package: 2 },
  ],
};

describe("drug_reference", () => {
  it("looks up a drug", async () => {
    const r = await drugReference.execute({ action: "lookup", drug_name: "Warfarin" }, ctx(T));
    expect((r.data as any).drug_class).toBe("Anticoagulant");
    expect((r.data as any).generic_available).toBe(true);
  });
  it("detects a major interaction", async () => {
    const r = await drugReference.execute({ action: "check_interactions", drug_list: ["Aspirin", "warfarin", "metformin"] }, ctx(T));
    expect((r.data as any).total).toBe(1);
    expect((r.data as any).major_count).toBe(1);
  });
  it("returns formulary tier", async () => {
    const r = await drugReference.execute({ action: "formulary_info", drug_name: "metformin", payer: "Medicare" }, ctx(T));
    expect((r.data as any).tier).toBe(1);
    expect((r.data as any).on_formulary).toBe(true);
  });
});

describe("ndc_pricer", () => {
  it("compares benchmarks", async () => {
    const r = await ndcPricer.execute({ action: "compare_benchmarks", ndc: "00074433902" }, ctx(T));
    expect((r.data as any).prices.asp).toBe(2950);
    expect((r.data as any).awp_to_wac_spread).toBeCloseTo(1500, 0);
  });
  it("calculates cost by benchmark", async () => {
    const r = await ndcPricer.execute({ action: "calculate", ndc: "00074433902", units: 4, benchmark: "asp" }, ctx(T));
    expect((r.data as any).total_cost).toBeCloseTo(11800, 0);
  });
  it("errors on unknown NDC", async () => {
    const r = await ndcPricer.execute({ action: "lookup", ndc: "99999999999" }, ctx(T));
    expect(r.success).toBe(false);
  });
});
