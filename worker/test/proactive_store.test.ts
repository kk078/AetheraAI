import { describe, it, expect } from "vitest";
import {
  createAlert, listAlerts, acknowledgeAlert,
  addActionItem, listActionItems, completeActionItem, queueStats,
  createAutomation, listAutomations, setAutomationEnabled, deleteAutomation,
  runScheduledAutomations, runMessageAutomations, generateUpdateAlerts,
} from "../src/proactive";

// Minimal in-memory D1 fake: parses INSERT column lists and handles the
// specific SELECT/UPDATE/DELETE shapes used by src/proactive.ts.
function fakeDB() {
  const tables: Record<string, any[]> = { alert: [], action_item: [], automation: [], knowledge_updates: [] };
  let seq = 0;

  function exec(sql: string, args: any[]) {
    const ins = sql.match(/INSERT(?: OR IGNORE)? INTO (\w+) \(([^)]+)\)/i);
    if (ins) {
      const table = ins[1];
      const cols = ins[2].split(",").map((s) => s.trim());
      const row: any = {};
      cols.forEach((c, i) => (row[c] = args[i]));
      row.created_at = `t${String(++seq).padStart(4, "0")}`;
      if (table === "alert") { row.acknowledged = 0; row.acknowledged_at = ""; }
      if (table === "action_item") { row.status = row.status ?? "pending"; row.completed_at = ""; }
      if (table === "automation") { row.last_run_at = ""; row.run_count = 0; }
      if (/OR IGNORE/i.test(sql) && row.dedup_key) {
        if (tables[table].some((r) => r.dedup_key === row.dedup_key)) return { meta: { changes: 0 } };
      }
      tables[table].push(row);
      return { meta: { changes: 1 } };
    }
    if (/^UPDATE alert SET acknowledged/i.test(sql)) {
      const r = tables.alert.find((x) => x.id === args[0]);
      if (r) { r.acknowledged = 1; r.acknowledged_at = "now"; return { meta: { changes: 1 } }; }
      return { meta: { changes: 0 } };
    }
    if (/^UPDATE action_item SET status = 'completed'/i.test(sql)) {
      const r = tables.action_item.find((x) => x.id === args[0] && x.status === "pending");
      if (r) { r.status = "completed"; r.completed_at = "now"; return { meta: { changes: 1 } }; }
      return { meta: { changes: 0 } };
    }
    if (/^UPDATE automation SET enabled/i.test(sql)) {
      const r = tables.automation.find((x) => x.id === args[0]);
      if (r) { r.enabled = args[1]; return { meta: { changes: 1 } }; }
      return { meta: { changes: 0 } };
    }
    if (/^UPDATE automation SET last_run_at/i.test(sql)) {
      const r = tables.automation.find((x) => x.id === args[0]);
      if (r) { r.last_run_at = "now"; r.run_count = (r.run_count ?? 0) + 1; return { meta: { changes: 1 } }; }
      return { meta: { changes: 0 } };
    }
    if (/^DELETE FROM automation/i.test(sql)) {
      const before = tables.automation.length;
      tables.automation = tables.automation.filter((x) => x.id !== args[0]);
      return { meta: { changes: before - tables.automation.length } };
    }
    if (/INSERT INTO audit_log/i.test(sql)) return { meta: { changes: 1 } };
    return { meta: { changes: 0 } };
  }

  function query(sql: string, args: any[]): any[] {
    if (/FROM alert/i.test(sql)) {
      let rows = tables.alert.slice();
      if (/acknowledged = 0/i.test(sql)) rows = rows.filter((r) => !r.acknowledged);
      return rows.reverse();
    }
    if (/GROUP BY priority/i.test(sql)) {
      const by: Record<string, number> = {};
      tables.action_item.filter((r) => r.status === "pending").forEach((r) => (by[r.priority] = (by[r.priority] ?? 0) + 1));
      return Object.entries(by).map(([priority, n]) => ({ priority, n }));
    }
    if (/COUNT\(\*\) AS n FROM action_item WHERE status='pending'/i.test(sql)) return [{ n: tables.action_item.filter((r) => r.status === "pending").length }];
    if (/COUNT\(\*\) AS n FROM action_item WHERE status='completed'/i.test(sql)) return [{ n: tables.action_item.filter((r) => r.status === "completed").length }];
    if (/FROM action_item/i.test(sql)) {
      return tables.action_item.filter((r) => r.status === (args[0] ?? "pending")).reverse();
    }
    if (/FROM automation WHERE id/i.test(sql)) return tables.automation.filter((r) => r.id === args[0]);
    if (/FROM automation WHERE enabled = 1 AND trigger = 'schedule'/i.test(sql)) return tables.automation.filter((r) => r.enabled && r.trigger === "schedule");
    if (/FROM automation WHERE enabled = 1 AND trigger = 'message_received'/i.test(sql)) return tables.automation.filter((r) => r.enabled && r.trigger === "message_received");
    if (/FROM automation/i.test(sql)) return tables.automation.slice().reverse();
    if (/FROM knowledge_updates/i.test(sql)) return tables.knowledge_updates.slice().reverse();
    return [];
  }

  const db: any = {
    _tables: tables,
    prepare(sql: string) {
      let a: any[] = [];
      const s: any = {
        bind(...args: any[]) { a = args; return s; },
        async run() { return exec(sql, a); },
        async all() { return { results: query(sql, a) }; },
        async first() { return query(sql, a)[0] ?? null; },
      };
      return s;
    },
  };
  return db;
}

describe("alerts", () => {
  it("create, list active, acknowledge", async () => {
    const env: any = { DB: fakeDB() };
    await createAlert(env, { severity: "warning", title: "AR spike", message: "Days in AR rising" });
    let alerts = await listAlerts(env, { activeOnly: true });
    expect(alerts.length).toBe(1);
    expect(alerts[0].severity).toBe("warning");
    expect(alerts[0].acknowledged).toBe(false);
    const ok = await acknowledgeAlert(env, alerts[0].id);
    expect(ok).toBe(true);
    alerts = await listAlerts(env, { activeOnly: true });
    expect(alerts.length).toBe(0);
  });

  it("dedup_key prevents duplicate alerts", async () => {
    const env: any = { DB: fakeDB() };
    await createAlert(env, { title: "x", dedup_key: "k1" });
    await createAlert(env, { title: "x", dedup_key: "k1" });
    expect((await listAlerts(env, { activeOnly: false })).length).toBe(1);
  });

  it("invalid severity falls back to info", async () => {
    const env: any = { DB: fakeDB() };
    await createAlert(env, { severity: "bogus", title: "y" });
    expect((await listAlerts(env, {}))[0].severity).toBe("info");
  });
});

describe("action queue", () => {
  it("add, list, complete, stats", async () => {
    const env: any = { DB: fakeDB() };
    await addActionItem(env, { title: "Work denial", priority: "urgent" });
    await addActionItem(env, { title: "Low task", priority: "low" });
    let items = await listActionItems(env, {});
    expect(items.length).toBe(2);
    let stats = await queueStats(env);
    expect(stats.pending).toBe(2);
    expect(stats.by_priority.urgent).toBe(1);
    await completeActionItem(env, items[0].id);
    items = await listActionItems(env, {});
    expect(items.length).toBe(1);
    stats = await queueStats(env);
    expect(stats.pending).toBe(1);
    expect(stats.completed).toBe(1);
  });
});

describe("automations", () => {
  it("create, list, toggle, delete", async () => {
    const env: any = { DB: fakeDB() };
    const a = await createAutomation(env, { name: "Daily digest", trigger: "schedule", action: "create_alert", actionValue: "digest ready" });
    expect(a.enabled).toBe(true);
    expect((await listAutomations(env)).length).toBe(1);
    await setAutomationEnabled(env, a.id, false);
    expect((await listAutomations(env))[0].enabled).toBe(false);
    await deleteAutomation(env, a.id);
    expect((await listAutomations(env)).length).toBe(0);
  });

  it("scheduled create_alert automation produces an alert", async () => {
    const env: any = { DB: fakeDB() };
    await createAutomation(env, { name: "Notify", trigger: "schedule", action: "create_alert", actionValue: "hello" });
    const ran = await runScheduledAutomations(env);
    expect(ran).toBe(1);
    const alerts = await listAlerts(env, {});
    expect(alerts.length).toBe(1);
    expect(alerts[0].title).toBe("Notify");
  });

  it("message_received automation with contains_keyword queues an action item", async () => {
    const env: any = { DB: fakeDB() };
    await createAutomation(env, { name: "Denial follow-up", trigger: "message_received", condition: "contains_keyword", conditionValue: "denial", action: "send_message", actionValue: "review denial" });
    await runMessageAutomations(env, { message: "We got a DENIAL on claim 123", specialist: "healthcare_provider" });
    expect((await listActionItems(env, {})).length).toBe(1);
    // non-matching message does nothing
    await runMessageAutomations(env, { message: "hello there", specialist: "general" });
    expect((await listActionItems(env, {})).length).toBe(1);
  });
});

describe("generateUpdateAlerts", () => {
  it("creates one alert per knowledge update, idempotently", async () => {
    const env: any = { DB: fakeDB() };
    env.DB._tables.knowledge_updates.push({ id: "u1", title: "CMS rule", summary: "s", url: "http://x", source: "cms", category: "healthcare_regulatory" });
    expect(await generateUpdateAlerts(env)).toBe(1);
    expect(await generateUpdateAlerts(env)).toBe(0); // dedup on second run
    expect((await listAlerts(env, {})).length).toBe(1);
  });

  it("no-op without DB", async () => {
    expect(await generateUpdateAlerts({} as any)).toBe(0);
    expect(await listAlerts({} as any, {})).toEqual([]);
  });
});
