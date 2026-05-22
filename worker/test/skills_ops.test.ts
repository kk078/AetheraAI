import { describe, it, expect } from "vitest";
import { contractAnalyzer, qualityTracker, complianceChecker, credentialingTracker } from "../src/skills";

describe("contract_analyzer", () => {
  it("compares payers and picks best", async () => {
    const r = await contractAnalyzer.execute({ action: "compare_contracts", cpt_code: "99214" });
    expect((r.data as any).best_payer).toBe("aetna"); // 144.10 highest
    expect((r.data as any).comparison[0].vs_medicare_pct).toBeCloseTo(110, 0);
  });
  it("calculates reimbursement vs medicare", async () => {
    const r = await contractAnalyzer.execute({ action: "calculate_reimbursement", cpt_code: "99213", payer: "uhc" });
    expect((r.data as any).expected_reimbursement).toBe(96.6);
  });
});

describe("quality_tracker", () => {
  it("calculates a rate and target", async () => {
    const r = await qualityTracker.execute({ action: "calculate_rate", measure_id: "CBP", numerator: 65, denominator: 100 });
    expect((r.data as any).rate).toBe(65);
    expect((r.data as any).meets_target).toBe(false); // target 70
  });
  it("identifies gaps", async () => {
    const r = await qualityTracker.execute({ action: "identify_gaps", current_rates: { CBP: 60, COL: 85 } });
    expect((r.data as any).count).toBe(1); // CBP below 70; COL above 80
    expect((r.data as any).gaps[0].measure_id).toBe("CBP");
  });
});

describe("compliance_checker", () => {
  it("scores an audit", async () => {
    const r = await complianceChecker.execute({ action: "run_audit", regulation: "hipaa", findings: [
      { check_id: "HIPAA-1", status: "pass" }, { check_id: "HIPAA-2", status: "fail" }, { check_id: "HIPAA-3", status: "pass" },
    ]});
    expect((r.data as any).score).toBeCloseTo(67, 0); // 2/3
    expect((r.data as any).fails).toBe(1);
  });
  it("flags violations", async () => {
    const r = await complianceChecker.execute({ action: "flag_violations", findings: [{ check_id: "OIG-1", status: "fail" }] });
    expect((r.data as any).count).toBe(1);
  });
});

describe("credentialing_tracker", () => {
  it("summarizes status", async () => {
    const today = new Date();
    const future = new Date(today.getTime() + 400 * 86400000).toISOString().slice(0, 10);
    const soon = new Date(today.getTime() + 30 * 86400000).toISOString().slice(0, 10);
    const past = new Date(today.getTime() - 10 * 86400000).toISOString().slice(0, 10);
    const r = await credentialingTracker.execute({ action: "check_status", credentials: [
      { type: "state_license", expiry_date: future }, { type: "dea", expiry_date: soon }, { type: "board_cert", expiry_date: past },
    ]});
    expect((r.data as any).active).toBe(1);
    expect((r.data as any).expiring_soon).toBe(1);
    expect((r.data as any).expired).toBe(1);
  });
  it("generates a required-credential checklist", async () => {
    const r = await credentialingTracker.execute({ action: "generate_checklist", credentials: [{ type: "state_license" }, { type: "npi" }] });
    expect((r.data as any).missing).toContain("dea");
    expect((r.data as any).complete).toBe(false);
  });
});
