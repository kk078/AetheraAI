import { describe, it, expect } from "vitest";
import { coverageChecker, denialPredictor, ediParser, calculator } from "../src/skills";

describe("coverage_checker", () => {
  it("returns policy + prior_auth for a known CPT", async () => {
    const r = await coverageChecker.execute({ cpt: "70553" });
    expect(r.success).toBe(true);
    expect((r.data as any).covered).toBe(true);
    expect((r.data as any).prior_auth).toBe(true);
    expect((r.data as any).criteria.length).toBeGreaterThan(0);
  });
  it("degrades gracefully for an unknown CPT", async () => {
    const r = await coverageChecker.execute({ code: "00000" });
    expect(r.success).toBe(true);
    expect((r.data as any).covered).toBe(null);
  });
  it("requires a cpt", async () => {
    expect((await coverageChecker.execute({})).success).toBe(false);
  });
});

describe("denial_predictor", () => {
  it("scores a high-risk claim", async () => {
    const r = await denialPredictor.execute({ claim_data: {
      diagnosis_codes: [], requires_prior_auth: true, prior_auth: false, modifier_missing: true,
    }});
    expect((r.data as any).risk_level).toBe("high");
    expect((r.data as any).risk_factors).toContain("Prior auth required but not on file");
  });
  it("scores a clean claim low", async () => {
    const r = await denialPredictor.execute({ claim_data: {
      diagnosis_codes: ["E11.9"], requires_prior_auth: false, eligibility_verified: true,
    }});
    expect((r.data as any).risk_level).toBe("low");
    expect((r.data as any).denial_probability).toBe(0);
  });
});

describe("edi_parser", () => {
  it("parses an 837 and identifies the transaction type", async () => {
    const r = await ediParser.execute({ content: "ISA*00*~GS*HC*~ST*837*0001~NM1*85*2*CLINIC~SE*4*0001~" });
    expect(r.success).toBe(true);
    expect((r.data as any).transaction_type).toBe("837");
    expect((r.data as any).transaction_name).toBe("Claim");
    expect((r.data as any).segment_count).toBe(5);
  });
  it("requires content", async () => {
    expect((await ediParser.execute({})).success).toBe(false);
  });
});

describe("calculator", () => {
  it("evaluates arithmetic", async () => {
    const r = await calculator.execute({ expression: "(2 + 3) * 4 - 6 / 2" });
    expect(r.success).toBe(true);
    expect((r.data as any).result).toBe(17);
  });
  it("rejects non-arithmetic input", async () => {
    expect((await calculator.execute({ expression: "process.exit(1)" })).success).toBe(false);
  });
});
