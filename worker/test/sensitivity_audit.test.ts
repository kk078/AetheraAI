import { describe, it, expect, vi } from "vitest";
import { analyzeSensitivity, redact } from "../src/sensitivity";
import { logAudit, queryAudit } from "../src/audit";
import { npiLookup } from "../src/skills";

describe("sensitivity", () => {
  it("flags PII (SSN) when no healthcare context", () => {
    const s = analyzeSensitivity("My number is 123-45-6789");
    expect(s.contains_pii).toBe(true);
    expect(s.contains_phi).toBe(false);
    expect(s.level).toBe("pii");
  });
  it("treats PII in a healthcare context as PHI", () => {
    const s = analyzeSensitivity("The patient SSN is 123-45-6789 with a new diagnosis");
    expect(s.contains_phi).toBe(true);
    expect(s.level).toBe("phi");
  });
  it("detects MRN as PHI and redacts", () => {
    const s = analyzeSensitivity("MRN: 123456 admitted today");
    expect(s.contains_phi).toBe(true);
    expect(s.redacted).toContain("[MRN REDACTED]");
    expect(s.redacted).not.toContain("123456");
  });
  it("clean text -> none", () => {
    expect(analyzeSensitivity("compute the RCM KPIs").level).toBe("none");
  });
  it("redact masks email", () => {
    expect(redact("reach me at a@b.com")).toContain("[EMAIL REDACTED]");
  });
});

describe("audit", () => {
  function fakeDB() {
    const rows: any[] = [];
    const db: any = {
      _rows: rows,
      prepare(sql: string) {
        const s: any = {
          _a: [],
          bind(...a: any[]) { s._a = a; return s; },
          async run() {
            if (/INSERT/.test(sql)) rows.push({ id: s._a[0], user_id: s._a[1], action: s._a[2], resource: s._a[3], details: s._a[4], sensitivity: s._a[6] });
            return { meta: { changes: 1 } };
          },
          async all() { return { results: rows.slice().reverse() }; },
        };
        return s;
      },
    };
    return db;
  }

  it("writes a redacted entry and queries it", async () => {
    const env: any = { DB: fakeDB() };
    await logAudit(env, { user_id: "u1", action: "chat", resource: "conv1", details: "MRN: 999999 here", sensitivity: "phi" });
    const entries = await queryAudit(env, {});
    expect(entries.length).toBe(1);
    expect(entries[0].action).toBe("chat");
    expect(entries[0].details).toContain("[MRN REDACTED]"); // PHI redacted at write
    expect(entries[0].details).not.toContain("999999");
  });

  it("no-op without DB", async () => {
    await logAudit({} as any, { action: "x" }); // should not throw
    expect(await queryAudit({} as any)).toEqual([]);
  });
});

describe("npi_lookup (connector)", () => {
  it("parses a live-style NPPES response", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ result_count: 1, results: [{ enumeration_type: "NPI-1", basic: { first_name: "JANE", last_name: "SMITH", status: "A" }, addresses: [{ city: "Austin", state: "TX" }], taxonomies: [{ primary: true, desc: "Family Medicine" }] }] }),
    }));
    vi.stubGlobal("fetch", fetchMock as any);
    const r = await npiLookup.execute({ npi: "1234567890" });
    expect((r.data as any).found).toBe(true);
    expect((r.data as any).name).toBe("JANE SMITH");
    expect((r.data as any).taxonomy).toBe("Family Medicine");
    vi.unstubAllGlobals();
  });
  it("rejects a non-10-digit NPI", async () => {
    expect((await npiLookup.execute({ npi: "123" })).success).toBe(false);
  });
});
