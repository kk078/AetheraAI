import { describe, it, expect } from "vitest";
import { cciEditor, drgGrouper, apcGrouper } from "../src/skills";

function q(tables: any, sql: string, a: any[]): any[] {
  const table = (sql.match(/FROM (\w+)/) || [])[1] || "";
  const rows: any[] = tables[table] ?? [];
  if (table === "cci_edit") {
    if (/col1 = \?1 OR col2 = \?1/.test(sql)) return rows.filter((r) => r.col1 === a[0] || r.col2 === a[0]);
    return rows.filter((r) => (r.col1 === a[0] && r.col2 === a[1]) || (r.col1 === a[1] && r.col2 === a[0]));
  }
  if (table === "ms_drg") return rows.filter((r) => r.drg === a[0]);
  if (table === "drg_dx") return rows.filter((r) => r.dx === a[0]);
  if (table === "apc") return rows.filter((r) => r.apc === a[0]);
  if (table === "cpt_apc") return rows.filter((r) => r.cpt === a[0]);
  return rows;
}

function ctx(tables: any): any {
  const DB = {
    prepare(sql: string) {
      const s: any = { _a: [], bind(...a: any[]) { s._a = a; return s; }, async first() { return q(tables, sql, s._a)[0] ?? null; }, async all() { return { results: q(tables, sql, s._a) }; } };
      return s;
    },
  };
  return { env: { DB } };
}

const T = {
  cci_edit: [
    { col1: "99213", col2: "99214", modifier_indicator: 0, rationale: "E/M mutually exclusive" },
    { col1: "99214", col2: "36415", modifier_indicator: 1, rationale: "blood draw component of E/M" },
    { col1: "97110", col2: "97140", modifier_indicator: 1, rationale: "manual therapy overlaps exercise" },
  ],
  ms_drg: [
    { drg: "065", description: "ICH/infarction w MCC", weight: 2.0142, gmlos: 6.8, type: "MEDICAL", severity: "MCC" },
    { drg: "066", description: "ICH/infarction w CC", weight: 1.2136, gmlos: 5.1, type: "MEDICAL", severity: "CC" },
    { drg: "067", description: "ICH/infarction w/o CC/MCC", weight: 0.8654, gmlos: 3.9, type: "MEDICAL", severity: "none" },
  ],
  drg_dx: [{ dx: "I63.9", base_drg: "065-067", description: "Cerebral infarction" }],
  apc: [
    { apc: "0304", description: "Level 4 MSK", status_indicator: "T", payment_rate: 2345.67, weight: 3.616, device_intensive: 1 },
    { apc: "0501", description: "Level 1 Cardiac", status_indicator: "S", payment_rate: 678.9, weight: 1.046, device_intensive: 0 },
  ],
  cpt_apc: [
    { cpt: "27447", apc: "0304", description: "Total knee arthroplasty" },
    { cpt: "93000", apc: "0501", description: "ECG" },
    { cpt: "93306", apc: "0501", description: "Echo" },
  ],
};

describe("cci_editor", () => {
  it("flags a bundled pair (indicator 0)", async () => {
    const r = await cciEditor.execute({ action: "check_pair", code1: "99213", code2: "99214" }, ctx(T));
    expect((r.data as any).billable_together).toBe(false);
    expect((r.data as any).modifier_can_override).toBe(false);
  });
  it("allows billing for an unlisted pair", async () => {
    const r = await cciEditor.execute({ action: "check_pair", code1: "99213", code2: "70450" }, ctx(T));
    expect((r.data as any).billable_together).toBe(true);
  });
  it("modifier 59 overrides when indicator is 1", async () => {
    const r = await cciEditor.execute({ action: "check_with_modifier", code1: "99214", code2: "36415", modifier: "59" }, ctx(T));
    expect((r.data as any).modifier_allows_billing).toBe(true);
  });
  it("modifier cannot override indicator 0", async () => {
    const r = await cciEditor.execute({ action: "check_with_modifier", code1: "99213", code2: "99214", modifier: "59" }, ctx(T));
    expect((r.data as any).modifier_allows_billing).toBe(false);
  });
  it("lists edits for a code", async () => {
    const r = await cciEditor.execute({ action: "list_edits", code: "97140" }, ctx(T));
    expect((r.data as any).total).toBe(1);
  });
});

describe("drg_grouper", () => {
  it("looks up a DRG and computes reimbursement", async () => {
    const r = await drgGrouper.execute({ action: "lookup_drg", drg_code: "066", base_rate: 6000 }, ctx(T));
    expect((r.data as any).reimbursement).toBeCloseTo(7281.6, 1);
  });
  it("assigns by severity (no secondary -> w/o CC/MCC)", async () => {
    const r = await drgGrouper.execute({ action: "assign_drg", principal_dx: "I63.9" }, ctx(T));
    expect((r.data as any).drg_assigned).toBe("067");
  });
  it("assigns MCC with >=2 secondary dx", async () => {
    const r = await drgGrouper.execute({ action: "assign_drg", principal_dx: "I63.9", secondary_dx: ["x", "y"] }, ctx(T));
    expect((r.data as any).drg_assigned).toBe("065");
  });
});

describe("apc_grouper", () => {
  it("assigns APC from CPT and totals payment", async () => {
    const r = await apcGrouper.execute({ action: "assign_apc", cpt_codes: ["27447"] }, ctx(T));
    expect((r.data as any).assignments[0].apc).toBe("0304");
    expect((r.data as any).assignments[0].device_intensive).toBe(true);
    expect((r.data as any).total_payment).toBeCloseTo(2345.67, 2);
  });
  it("calculates OPPS payment across CPTs", async () => {
    const r = await apcGrouper.execute({ action: "calculate_opps_payment", cpt_codes: ["93000", "93306"] }, ctx(T));
    expect((r.data as any).total_payment).toBeCloseTo(1357.8, 1);
  });
  it("looks up an APC", async () => {
    const r = await apcGrouper.execute({ action: "lookup_apc", apc_code: "0501" }, ctx(T));
    expect((r.data as any).payment_rate).toBe(678.9);
  });
});
