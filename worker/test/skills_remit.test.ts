import { describe, it, expect } from "vitest";
import { claimStatus, remittanceParser } from "../src/skills";

const EDI_835 =
  "ISA*00*          *00*          *ZZ*SENDERID       *ZZ*RECEIVERID     *240101*1200*^*00501*000000002*0*P*:~" +
  "GS*HC*SENDERID*RECEIVERID*20240101*1200*2*X*005010X221~" +
  "ST*835*0002*005010X221~" +
  "BPR*I*150.00*C*CHK*20240115*1*999999999*DA*12345*9876543210~" +
  "TRN*1*1*1234567890~" +
  "NM1*PR*2*INSURANCE CO*****46*9876543210~" +
  "NM1*PE*2*DR SMITH*****XX*1234567890~" +
  "CLP*CLAIM001*1*150.00*120.00*30.00*HC*20240101*1~" +
  "SVC*HC:99213***1***1~" +
  "CAS*PR*1*30.00~" +
  "SE*11*0002~GE*2*2~IEA*1*000000002~";

function dbCtx(): any {
  const rows = [{ code: "CO-50", ctype: "CARC", description: "Not medically necessary", category: "clinical", appeal_priority: "high" }];
  const DB = { prepare(sql: string) { const s: any = { _a: [], bind(...a: any[]) { s._a = a; return s; }, async first() { return rows.find((r) => r.code === s._a[0]) ?? null; } }; return s; } };
  return { env: { DB } };
}

describe("claim_status", () => {
  it("interprets a finalized denial as final", async () => {
    const r = await claimStatus.execute({ action: "full_status", status_code: "F2" });
    expect((r.data as any).category).toBe("finalized");
    expect((r.data as any).final).toBe(true);
  });
  it("pending status is not final", async () => {
    const r = await claimStatus.execute({ action: "check_final", status_code: "20" });
    expect((r.data as any).final).toBe(false);
  });
  it("unknown code errors", async () => {
    expect((await claimStatus.execute({ action: "full_status", status_code: "ZZ" })).success).toBe(false);
  });
});

describe("remittance_parser", () => {
  it("parses an 835 into claims", async () => {
    const r = await remittanceParser.execute({ action: "parse_835", remittance_text: EDI_835 });
    const d = r.data as any;
    expect(d.total_paid).toBe(150);
    expect(d.payer).toBe("INSURANCE CO");
    expect(d.claims[0].claim_id).toBe("CLAIM001");
    expect(d.claims[0].paid).toBe(120);
    expect(d.claims[0].adjustments[0]).toEqual({ group: "PR", code: "1", amount: 30 });
  });
  it("summarizes totals", async () => {
    const r = await remittanceParser.execute({ action: "summarize", remittance_text: EDI_835 });
    expect((r.data as any).total_charge).toBe(150);
    expect((r.data as any).total_patient_responsibility).toBe(30);
  });
  it("decodes a CARC via D1", async () => {
    const r = await remittanceParser.execute({ action: "decode_carc", code: "CO-50" }, dbCtx());
    expect((r.data as any).description).toContain("medically necessary");
  });
});
