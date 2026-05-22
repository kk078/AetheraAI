import { describe, it, expect } from "vitest";
import { medicalCalculator, labInterpreter, claimScrubber } from "../src/skills";

describe("medical_calculator", () => {
  it("bmi with category", async () => {
    const r = await medicalCalculator.execute({ calculator: "bmi", params: { weight_kg: 80, height_cm: 175 } });
    expect((r.data as any).bmi).toBeCloseTo(26.12, 1);
    expect((r.data as any).category).toBe("Overweight");
  });
  it("creatinine clearance (Cockcroft-Gault, female)", async () => {
    const r = await medicalCalculator.execute({ calculator: "creatinine_clearance", params: { age: 65, weight_kg: 70, creatinine_mg_dl: 1.0, sex: "female" } });
    // ((140-65)*70)/(72*1.0)*0.85 = 61.98
    expect((r.data as any).crcl_ml_min).toBeCloseTo(61.98, 1);
  });
  it("map", async () => {
    const r = await medicalCalculator.execute({ calculator: "map", params: { systolic: 120, diastolic: 80 } });
    expect((r.data as any).map_mmhg).toBeCloseTo(93.33, 1);
  });
  it("anion gap high", async () => {
    const r = await medicalCalculator.execute({ calculator: "anion_gap", params: { sodium: 140, chloride: 100, bicarbonate: 18 } });
    expect((r.data as any).anion_gap).toBe(22);
    expect((r.data as any).interpretation).toBe("High anion gap");
  });
  it("unknown calculator errors", async () => {
    expect((await medicalCalculator.execute({ calculator: "nope", params: {} })).success).toBe(false);
  });
});

describe("lab_interpreter", () => {
  it("flags critical low sodium", async () => {
    const r = await labInterpreter.execute({ action: "compare_to_range", test_name: "sodium", value: 118 });
    expect((r.data as any).status).toBe("critical_low");
    expect((r.data as any).critical).toBe(true);
  });
  it("normal value", async () => {
    const r = await labInterpreter.execute({ action: "interpret", test_name: "potassium", value: 4.0 });
    expect((r.data as any).status).toBe("normal");
  });
  it("trend increasing", async () => {
    const r = await labInterpreter.execute({ action: "trend_analysis", test_name: "creatinine", values: [0.8, 1.2, 1.9] });
    expect((r.data as any).trend).toBe("increasing");
  });
  it("unknown test errors", async () => {
    expect((await labInterpreter.execute({ action: "interpret", test_name: "unobtainium", value: 1 })).success).toBe(false);
  });
});

describe("claim_scrubber", () => {
  it("flags bad formats and MUE", async () => {
    const r = await claimScrubber.execute({
      diagnosis_codes: ["E11.9", "BADCODE"],
      procedure_codes: ["99214", "97110"],
      units: [1, 8],
    });
    const types = (r.data as any).issues.map((i: any) => i.type);
    expect(types).toContain("icd10_format"); // BADCODE
    expect(types).toContain("mue");          // 97110 units 8 > 4
    expect((r.data as any).risk_level).not.toBe("clean");
  });
  it("clean claim", async () => {
    const r = await claimScrubber.execute({ diagnosis_codes: ["E11.9"], procedure_codes: ["99213"], units: [1] });
    expect((r.data as any).clean).toBe(true);
    expect((r.data as any).risk_level).toBe("clean");
  });
  it("flags duplicates", async () => {
    const r = await claimScrubber.execute({ diagnosis_codes: ["E11.9"], procedure_codes: ["99213", "99213"] });
    expect((r.data as any).issues.some((i: any) => i.type === "duplicate")).toBe(true);
  });
});
