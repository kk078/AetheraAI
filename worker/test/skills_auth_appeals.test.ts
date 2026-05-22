import { describe, it, expect } from "vitest";
import { appealsWriter, priorAuth, telehealthRules } from "../src/skills";

describe("appeals_writer", () => {
  it("generates a letter referencing the claim", async () => {
    const r = await appealsWriter.execute({
      action: "generate", payer: "Aetna", claim_number: "CLM123", patient_name: "J. Doe",
      date_of_service: "2026-01-10", carc_code: "CO-50", clinical_rationale: "Failed conservative care",
      supporting_documents: ["Op note", "PT records"], provider_name: "Dr. Smith",
    });
    expect((r.data as any).letter).toContain("CLM123");
    expect((r.data as any).letter).toContain("Failed conservative care");
    expect((r.data as any).strength).toBe("strong");
  });
  it("flags missing documentation", async () => {
    const r = await appealsWriter.execute({ action: "generate", payer: "Aetna", claim_number: "X" });
    expect((r.data as any).strength).toBe("needs_more_documentation");
  });
});

describe("prior_auth", () => {
  it("flags PA required with criteria", async () => {
    const r = await priorAuth.execute({ action: "full_lookup", payer: "Aetna", procedure_code: "70553" });
    expect((r.data as any).required).toBe(true);
    expect((r.data as any).documents.length).toBeGreaterThan(0);
  });
  it("resolves payer aliases", async () => {
    const r = await priorAuth.execute({ action: "check_pa", payer: "UnitedHealthcare", procedure_code: "70553" });
    expect((r.data as any).payer).toBe("uhc");
    expect((r.data as any).required).toBe(true);
  });
  it("no rule on file -> not required", async () => {
    const r = await priorAuth.execute({ action: "check_pa", payer: "Medicare", procedure_code: "99213" });
    expect((r.data as any).required).toBe(false);
  });
  it("unknown payer errors", async () => {
    expect((await priorAuth.execute({ action: "check_pa", payer: "Nope", procedure_code: "70553" })).success).toBe(false);
  });
});

describe("telehealth_rules", () => {
  it("returns medicare rules", async () => {
    const r = await telehealthRules.execute({ action: "medicare_rules" });
    expect((r.data as any).common_modifiers["95"]).toContain("audio");
  });
  it("state rules with parity", async () => {
    const r = await telehealthRules.execute({ action: "check_state_rules", state: "ca" });
    expect((r.data as any).parity).toBe(true);
  });
  it("billing requirements pick modifier by modality", async () => {
    const r = await telehealthRules.execute({ action: "get_billing_requirements", modality: "audio-only" });
    expect((r.data as any).modifier).toBe("93");
  });
});
