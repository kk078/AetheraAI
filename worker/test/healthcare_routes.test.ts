import { describe, it, expect } from "vitest";
import { HEALTHCARE_ROUTES } from "../src/healthcare";
import { REGISTRY } from "../src/skills";

describe("healthcare adapter map", () => {
  it("every route targets a registered skill", () => {
    for (const [op, def] of Object.entries(HEALTHCARE_ROUTES)) {
      expect(REGISTRY[def.skill], `${op} -> ${def.skill}`).toBeDefined();
    }
  });

  it("code-lookup maps codeType -> code_type", () => {
    expect(HEALTHCARE_ROUTES["code-lookup"].map({ code: "E11.9", codeType: "icd10cm" }))
      .toEqual({ code: "E11.9", code_type: "icd10cm" });
  });

  it("denial-analyze wraps single car/rarc codes into arrays", () => {
    const args = HEALTHCARE_ROUTES["denial-analyze"].map({ car_code: "CO-16", rarc_code: "N290" });
    expect(args.carc_codes).toEqual(["CO-16"]);
    expect(args.rarc_codes).toEqual(["N290"]);
  });

  it("cci-check picks check_pair for two codes", () => {
    expect(HEALTHCARE_ROUTES["cci-check"].map({ codes: ["11042", "97597"] }))
      .toEqual({ action: "check_pair", code1: "11042", code2: "97597" });
  });

  it("cci-check picks list_edits for one code", () => {
    expect(HEALTHCARE_ROUTES["cci-check"].map({ codes: ["11042"] }))
      .toEqual({ action: "list_edits", code: "11042" });
  });

  it("edi-parse maps transaction_set -> content", () => {
    expect(HEALTHCARE_ROUTES["edi-parse"].map({ transaction_set: "ST*837*1~" }))
      .toEqual({ content: "ST*837*1~" });
  });

  it("coverage maps code -> cpt", () => {
    expect(HEALTHCARE_ROUTES["coverage"].map({ code: "70553", payer: "Medicare" }))
      .toEqual({ cpt: "70553", payer: "Medicare" });
  });
});

describe("healthcare adapter end-to-end (pure skills)", () => {
  it("coverage adapter executes coverage_checker", async () => {
    const def = HEALTHCARE_ROUTES["coverage"];
    const r = await REGISTRY[def.skill].execute(def.map({ code: "70553" }), {} as any);
    expect(r.success).toBe(true);
    expect((r.data as any).prior_auth).toBe(true);
  });

  it("edi-parse adapter executes edi_parser", async () => {
    const def = HEALTHCARE_ROUTES["edi-parse"];
    const r = await REGISTRY[def.skill].execute(def.map({ transaction_set: "ISA*00*~ST*835*0001~SE*2*0001~" }), {} as any);
    expect(r.success).toBe(true);
    expect((r.data as any).transaction_type).toBe("835");
  });
});
