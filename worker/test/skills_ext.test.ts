import { describe, it, expect } from "vitest";
import {
  arPrioritizer, underpaymentDetector, timelyFilingCalculator,
  modifierRecommender, medicalNecessityBuilder, hccGapFinder,
  structuredExtractor, dataInsights,
} from "../src/skills";

describe("ar_prioritizer", () => {
  it("ranks by score and summarizes buckets", () => {
    const r = arPrioritizer.execute({ accounts: [
      { account_id: "A", balance: 100, age_days: 10, payer_class: "commercial" },
      { account_id: "B", balance: 100, age_days: 200, payer_class: "commercial" },
      { account_id: "C", balance: 5000, age_days: 45, payer_class: "self_pay" },
    ]});
    const wl = (r.data as any).worklist;
    expect(wl[0].account_id).toBe("C");
    expect((r.data as any).summary.total_ar).toBe(5200);
  });
});

describe("underpayment_detector", () => {
  it("totals recoverable variance", () => {
    const r = underpaymentDetector.execute({ lines: [
      { cpt: "99214", units: 1, expected_rate: 120, paid_amount: 100 },
      { cpt: "99214", units: 2, expected_rate: 120, paid_amount: 200 },
    ]});
    expect((r.data as any).summary.total_recoverable_variance).toBe(60);
  });
});

describe("timely_filing_calculator", () => {
  it("flags expired", () => {
    const dos = new Date(Date.now() - 120 * 86400000).toISOString().slice(0, 10);
    const r = timelyFilingCalculator.execute({ date_of_service: dos, payer_class: "commercial" });
    expect((r.data as any).status).toBe("expired");
  });
});

describe("modifier_recommender", () => {
  it("maps scenario to modifiers", () => {
    const r = modifierRecommender.execute({ scenario: { bilateral_procedure: true, side: "left", multiple_procedures: true } });
    const mods = (r.data as any).modifiers;
    expect(mods).toContain("50");
    expect(mods).toContain("LT");
    expect(mods).toContain("51");
  });
});

describe("medical_necessity_builder", () => {
  it("rates strong when fully documented", () => {
    const r = medicalNecessityBuilder.execute({
      cpt: "72148", service_description: "lumbar MRI", diagnoses: ["M54.5"],
      clinical_indications: ["radicular pain"], failed_conservative: ["PT"], supporting_findings: ["diminished reflex"],
    });
    expect((r.data as any).strength).toBe("strong");
  });
});

describe("hcc_gap_finder", () => {
  it("finds unrecaptured HCCs", () => {
    const r = hccGapFinder.execute({ prior_year_hccs: ["HCC19", "HCC85"], current_year_dx: ["E11.9"], revenue_per_raf: 10000 });
    const gaps = (r.data as any).recapture_gaps.map((g: any) => g.hcc);
    expect(gaps).toContain("HCC85");
    expect(gaps).not.toContain("HCC19");
    expect((r.data as any).estimated_revenue_at_risk).toBeCloseTo(3310, 0);
  });
});

describe("structured_extractor", () => {
  it("extracts email and ssn", () => {
    const r = structuredExtractor.execute({ text: "jane@doe.com SSN 123-45-6789", fields: [
      { name: "email", type: "email" }, { name: "ssn", type: "ssn" },
    ]});
    expect((r.data as any).extracted.email).toBe("jane@doe.com");
    expect((r.data as any).extracted.ssn).toBe("123-45-6789");
  });
});

describe("data_insights", () => {
  it("group_by sum", () => {
    const r = dataInsights.execute({ action: "group_by", group_field: "payer", agg_field: "amount", agg: "sum",
      records: [{ payer: "A", amount: 100 }, { payer: "A", amount: 300 }, { payer: "B", amount: 200 }] });
    const by: any = {}; (r.data as any).groups.forEach((g: any) => (by[g.group] = g.value));
    expect(by.A).toBe(400);
    expect(by.B).toBe(200);
  });
});
