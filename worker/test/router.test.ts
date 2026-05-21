import { describe, it, expect } from "vitest";
import { route } from "../src/router";

describe("route", () => {
  it("routes RCM/denial queries to healthcare_provider", () => {
    const r = route("help me write a denial appeal for this claim and check the modifier");
    expect(r.primary_specialist).toBe("healthcare_provider");
    expect(r.recommended_tools).toContain("appeals_writer");
    expect(r.confidence).toBeGreaterThan(0.5);
  });

  it("routes eligibility/remittance to healthcare_payer", () => {
    const r = route("parse this remittance ERA and check eligibility and the contract");
    expect(r.primary_specialist).toBe("healthcare_payer");
  });

  it("routes compliance to healthcare_regulatory", () => {
    const r = route("is this a HIPAA compliance and Stark anti-kickback issue for the OIG audit");
    expect(r.primary_specialist).toBe("healthcare_regulatory");
  });

  it("falls back to general with low confidence", () => {
    const r = route("tell me a story about a cat");
    expect(r.primary_specialist).toBe("general");
    expect(r.confidence).toBe(0.3);
  });

  it("honors a forced specialist", () => {
    const r = route("anything", "healthcare_analytics");
    expect(r.primary_specialist).toBe("healthcare_analytics");
    expect(r.confidence).toBe(1);
    expect(r.recommended_tools).toContain("rcm_kpi_calculator");
  });
});
