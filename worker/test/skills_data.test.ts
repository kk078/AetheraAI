import { describe, it, expect } from "vitest";
import { codeLookup, feeSchedule, denialAnalyzer } from "../src/skills";

// Minimal in-memory D1 fake: routes by table name + WHERE column in the SQL.
function queryRows(tables: any, sql: string, args: any[]): any[] {
  const table = (sql.match(/FROM (\w+)/) || [])[1] || "";
  const rows: any[] = tables[table] ?? [];
  if (/WHERE cpt = /.test(sql)) return rows.filter((r) => r.cpt === args[0]);
  if (/WHERE locality = /.test(sql)) return rows.filter((r) => r.locality === args[0]);
  if (/WHERE parent = /.test(sql)) return rows.filter((r) => r.parent === args[0]);
  if (/WHERE code = /.test(sql)) return rows.filter((r) => r.code === args[0]);
  if (/LIKE/.test(sql)) {
    const term = String(args[0]).replace(/%/g, "").toLowerCase();
    let res = rows.filter((r) => String(r.description || "").toLowerCase().includes(term));
    if (/code_type = /.test(sql)) res = res.filter((r) => r.code_type === args[1]);
    return res;
  }
  return rows;
}

function makeCtx(tables: any): any {
  const DB = {
    prepare(sql: string) {
      const stmt: any = {
        _args: [] as any[],
        bind(...args: any[]) { stmt._args = args; return stmt; },
        async first() { return queryRows(tables, sql, stmt._args)[0] ?? null; },
        async all() { return { results: queryRows(tables, sql, stmt._args) }; },
      };
      return stmt;
    },
  };
  return { env: { DB } };
}

const TABLES = {
  code_set: [
    { code: "E11.9", code_type: "icd10cm", description: "Type 2 diabetes mellitus without complications", parent: "E11" },
    { code: "E11.65", code_type: "icd10cm", description: "Type 2 diabetes mellitus with hyperglycemia", parent: "E11" },
    { code: "99213", code_type: "cpt", description: "Office visit, established, low complexity", parent: "9921" },
  ],
  fee_rvu: [
    { cpt: "99213", work_rvu: 0.97, pe_rvu_nf: 1.55, mp_rvu_nf: 0.12, status: "A", description: "Office visit, low" },
  ],
  gpci: [
    { locality: "01010", work_gpci: 0.963, pe_gpci: 0.879, mp_gpci: 0.724, name: "Alabama - Rest of State", state: "AL" },
  ],
  denial_code: [
    { code: "CO-50", ctype: "CARC", description: "Not medically necessary", category: "clinical", appeal_priority: "high" },
    { code: "PR-1", ctype: "CARC", description: "Deductible amount", category: "patient_responsibility", appeal_priority: "low" },
  ],
};

describe("code_lookup (D1)", () => {
  it("looks up an exact code", async () => {
    const r = await codeLookup.execute({ code: "E11.9" }, makeCtx(TABLES));
    expect(r.success).toBe(true);
    expect((r.data as any).valid).toBe(true);
    expect((r.data as any).description).toContain("diabetes");
  });
  it("returns children when requested", async () => {
    const r = await codeLookup.execute({ code: "E11.9", include_children: true }, makeCtx(TABLES));
    const kids = (r.data as any).children.map((c: any) => c.code);
    expect(kids).toContain("E11.65");
  });
  it("keyword search", async () => {
    const r = await codeLookup.execute({ search: "diabetes" }, makeCtx(TABLES));
    expect((r.data as any).total).toBeGreaterThanOrEqual(2);
  });
  it("unknown code is valid:false", async () => {
    const r = await codeLookup.execute({ code: "Z99.9" }, makeCtx(TABLES));
    expect((r.data as any).valid).toBe(false);
  });
  it("errors with no DB", async () => {
    expect((await codeLookup.execute({ code: "E11.9" })).success).toBe(false);
  });
});

describe("fee_schedule (D1)", () => {
  it("lookup national allowed", async () => {
    const r = await feeSchedule.execute({ action: "lookup", cpt_code: "99213" }, makeCtx(TABLES));
    // (0.97 + 1.55 + 0.12) * 33.2875 = 87.88
    expect((r.data as any).national_average_allowed).toBeCloseTo(87.88, 1);
  });
  it("calculate by locality with GPCI", async () => {
    const r = await feeSchedule.execute({ action: "calculate", cpt_code: "99213", locality: "01010" }, makeCtx(TABLES));
    expect((r.data as any).allowed_amount).toBeCloseTo(79.34, 0);
    expect((r.data as any).locality).toContain("Alabama");
  });
  it("unknown CPT errors", async () => {
    const r = await feeSchedule.execute({ action: "lookup", cpt_code: "00000" }, makeCtx(TABLES));
    expect(r.success).toBe(false);
  });
});

describe("denial_analyzer (D1)", () => {
  it("decodes, categorizes by highest priority, recommends", async () => {
    const r = await denialAnalyzer.execute(
      { carc_codes: ["CO-50", "PR-1"], claim_amount: 200, paid_amount: 50 },
      makeCtx(TABLES),
    );
    expect(r.success).toBe(true);
    const d = r.data as any;
    expect(d.category.appeal_priority).toBe("high"); // CO-50 outranks PR-1
    expect(d.category.appealable).toBe(true);
    expect(d.financials.adjusted_amount).toBe(150);
    expect(d.financials.potential_recovery).toBe(150);
    expect(d.appeal_recommendation.appeal_level).toBe("Redetermination");
    expect(d.appeal_recommendation.recommendations.join(" ")).toContain("clinical evidence");
  });
  it("requires a CARC code", async () => {
    const r = await denialAnalyzer.execute({ carc_codes: [] }, makeCtx(TABLES));
    expect(r.success).toBe(false);
  });
});
