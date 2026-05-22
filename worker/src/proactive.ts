import type { Env } from "./types";
import { REGISTRY } from "./skills";
import { logAudit } from "./audit";

// Proactive subsystem: alerts, action queue, and automations, backed by D1.
// The cron handler generates alerts from new CMS/regulatory updates and runs
// scheduled automations; the chat handler runs message_received automations.
// All reads degrade to empty/safe values if the tables don't exist yet.

const SEVERITIES = new Set(["info", "warning", "urgent", "critical"]);
const PRIORITIES = new Set(["critical", "urgent", "normal", "low"]);

function parseJson(s: any): any {
  try {
    return s ? JSON.parse(s) : {};
  } catch {
    return {};
  }
}

// ---------------- Alerts ----------------

export interface NewAlert {
  severity?: string;
  title: string;
  message?: string;
  details?: string;
  source?: string;
  category?: string;
  metadata?: Record<string, any>;
  dedup_key?: string;
}

/** Insert an alert (idempotent when a dedup_key is given). Best-effort. */
export async function createAlert(env: Env, a: NewAlert): Promise<string | null> {
  if (!env.DB) return null;
  const id = crypto.randomUUID();
  const severity = SEVERITIES.has(String(a.severity)) ? a.severity! : "info";
  try {
    const sql = a.dedup_key
      ? `INSERT OR IGNORE INTO alert (id, severity, title, message, details, source, category, metadata, dedup_key)
         VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9)`
      : `INSERT INTO alert (id, severity, title, message, details, source, category, metadata, dedup_key)
         VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9)`;
    const r = await env.DB.prepare(sql)
      .bind(id, severity, a.title, a.message ?? "", a.details ?? "", a.source ?? "",
        a.category ?? "general", JSON.stringify(a.metadata ?? {}), a.dedup_key ?? "")
      .run();
    // INSERT OR IGNORE that deduped changes nothing — report no new alert.
    if (a.dedup_key && (r.meta?.changes ?? 1) === 0) return null;
    return id;
  } catch {
    return null;
  }
}

function mapAlert(r: any) {
  return {
    id: r.id,
    severity: r.severity,
    title: r.title,
    message: r.message,
    details: r.details,
    source: r.source,
    category: r.category,
    metadata: parseJson(r.metadata),
    acknowledged: !!r.acknowledged,
    acknowledged_at: r.acknowledged_at || null,
    timestamp: r.created_at,
  };
}

export async function listAlerts(env: Env, opts: { activeOnly?: boolean; limit?: number } = {}): Promise<any[]> {
  if (!env.DB) return [];
  const limit = Math.min(opts.limit ?? 100, 500);
  try {
    const sql = opts.activeOnly
      ? "SELECT * FROM alert WHERE acknowledged = 0 ORDER BY created_at DESC LIMIT ?1"
      : "SELECT * FROM alert ORDER BY created_at DESC LIMIT ?1";
    const res = await env.DB.prepare(sql).bind(limit).all<any>();
    return (res.results ?? []).map(mapAlert);
  } catch {
    return [];
  }
}

export async function acknowledgeAlert(env: Env, id: string): Promise<boolean> {
  if (!env.DB) return false;
  try {
    const r = await env.DB.prepare(
      "UPDATE alert SET acknowledged = 1, acknowledged_at = datetime('now') WHERE id = ?1",
    ).bind(id).run();
    return (r.meta?.changes ?? 0) > 0;
  } catch {
    return false;
  }
}

// ---------------- Action queue ----------------

export interface NewActionItem {
  title: string;
  description?: string;
  details?: string;
  priority?: string;
  specialist?: string;
  assignee?: string;
  due_date?: string;
  source?: string;
}

export async function addActionItem(env: Env, a: NewActionItem): Promise<string | null> {
  if (!env.DB) return null;
  const id = crypto.randomUUID();
  const priority = PRIORITIES.has(String(a.priority)) ? a.priority! : "normal";
  try {
    await env.DB.prepare(
      `INSERT INTO action_item (id, title, description, details, priority, specialist, assignee, due_date, source)
       VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9)`,
    )
      .bind(id, a.title, a.description ?? "", a.details ?? "", priority,
        a.specialist ?? "", a.assignee ?? "", a.due_date ?? "", a.source ?? "")
      .run();
    return id;
  } catch {
    return null;
  }
}

function mapActionItem(r: any) {
  return {
    id: r.id,
    title: r.title,
    description: r.description,
    details: r.details,
    priority: r.priority,
    status: r.status,
    specialist: r.specialist || null,
    assignee: r.assignee || null,
    dueDate: r.due_date || null,
    createdAt: r.created_at,
    completedAt: r.completed_at || null,
  };
}

export async function listActionItems(env: Env, opts: { status?: string; limit?: number } = {}): Promise<any[]> {
  if (!env.DB) return [];
  const limit = Math.min(opts.limit ?? 200, 500);
  const status = opts.status ?? "pending";
  try {
    const res = await env.DB.prepare(
      "SELECT * FROM action_item WHERE status = ?1 ORDER BY created_at DESC LIMIT ?2",
    ).bind(status, limit).all<any>();
    return (res.results ?? []).map(mapActionItem);
  } catch {
    return [];
  }
}

export async function completeActionItem(env: Env, id: string): Promise<boolean> {
  if (!env.DB) return false;
  try {
    const r = await env.DB.prepare(
      "UPDATE action_item SET status = 'completed', completed_at = datetime('now') WHERE id = ?1 AND status = 'pending'",
    ).bind(id).run();
    return (r.meta?.changes ?? 0) > 0;
  } catch {
    return false;
  }
}

export async function queueStats(env: Env): Promise<{ pending: number; completed: number; by_priority: Record<string, number> }> {
  const empty = { pending: 0, completed: 0, by_priority: {} as Record<string, number> };
  if (!env.DB) return empty;
  try {
    const pending = (await env.DB.prepare("SELECT COUNT(*) AS n FROM action_item WHERE status='pending'").first<{ n: number }>())?.n ?? 0;
    const completed = (await env.DB.prepare("SELECT COUNT(*) AS n FROM action_item WHERE status='completed'").first<{ n: number }>())?.n ?? 0;
    const byP = await env.DB.prepare("SELECT priority, COUNT(*) AS n FROM action_item WHERE status='pending' GROUP BY priority").all<{ priority: string; n: number }>();
    const by_priority: Record<string, number> = {};
    for (const r of byP.results ?? []) by_priority[r.priority] = r.n;
    return { pending, completed, by_priority };
  } catch {
    return empty;
  }
}

// ---------------- Automations ----------------

export interface NewAutomation {
  name: string;
  trigger?: string;
  condition?: string;
  conditionValue?: string;
  action?: string;
  actionValue?: string;
  enabled?: boolean;
}

export async function createAutomation(env: Env, a: NewAutomation): Promise<any | null> {
  if (!env.DB) return null;
  const id = crypto.randomUUID();
  try {
    await env.DB.prepare(
      `INSERT INTO automation (id, name, trigger, condition, condition_value, action, action_value, enabled)
       VALUES (?1,?2,?3,?4,?5,?6,?7,?8)`,
    )
      .bind(id, a.name, a.trigger ?? "schedule", a.condition ?? "always", a.conditionValue ?? "",
        a.action ?? "create_alert", a.actionValue ?? "", a.enabled === false ? 0 : 1)
      .run();
    const row = await env.DB.prepare("SELECT * FROM automation WHERE id = ?1").bind(id).first<any>();
    return row ? mapAutomation(row) : null;
  } catch {
    return null;
  }
}

function mapAutomation(r: any) {
  return {
    id: r.id,
    name: r.name,
    trigger: r.trigger,
    condition: r.condition,
    conditionValue: r.condition_value || "",
    action: r.action,
    actionValue: r.action_value || "",
    enabled: !!r.enabled,
    createdAt: r.created_at,
    lastRunAt: r.last_run_at || null,
    runCount: r.run_count ?? 0,
  };
}

export async function listAutomations(env: Env): Promise<any[]> {
  if (!env.DB) return [];
  try {
    const res = await env.DB.prepare("SELECT * FROM automation ORDER BY created_at DESC").all<any>();
    return (res.results ?? []).map(mapAutomation);
  } catch {
    return [];
  }
}

export async function setAutomationEnabled(env: Env, id: string, enabled: boolean): Promise<boolean> {
  if (!env.DB) return false;
  try {
    const r = await env.DB.prepare("UPDATE automation SET enabled = ?2 WHERE id = ?1").bind(id, enabled ? 1 : 0).run();
    return (r.meta?.changes ?? 0) > 0;
  } catch {
    return false;
  }
}

export async function deleteAutomation(env: Env, id: string): Promise<boolean> {
  if (!env.DB) return false;
  try {
    const r = await env.DB.prepare("DELETE FROM automation WHERE id = ?1").bind(id).run();
    return (r.meta?.changes ?? 0) > 0;
  } catch {
    return false;
  }
}

// ---------------- Engine ----------------

/** Perform an automation's action. Returns a short description of what ran. */
async function performAction(env: Env, a: any): Promise<string> {
  const name = a.name as string;
  const actionValue = (a.action_value ?? a.actionValue ?? "") as string;
  switch (a.action) {
    case "create_alert": {
      const severity = a.condition === "severity_is" && SEVERITIES.has(a.condition_value) ? a.condition_value : "info";
      await createAlert(env, { severity, title: name, message: actionValue || name, source: `automation:${a.id}`, category: "automation" });
      return "created alert";
    }
    case "send_message":
    case "notify_channel": {
      await addActionItem(env, { title: name, description: actionValue || name, priority: "normal", source: `automation:${a.id}` });
      return "queued action item";
    }
    case "execute_skill": {
      const skill = REGISTRY[actionValue];
      if (!skill) return "skill not found";
      try {
        const res = await skill.execute({}, { env });
        await addActionItem(env, { title: `${name}: ${actionValue}`, description: JSON.stringify(res).slice(0, 500), priority: "low", source: `automation:${a.id}` });
        return "executed skill";
      } catch {
        return "skill error";
      }
    }
    default:
      return "unsupported action";
  }
}

/** Run all enabled schedule-triggered automations (called from the cron handler). */
export async function runScheduledAutomations(env: Env): Promise<number> {
  if (!env.DB) return 0;
  let ran = 0;
  try {
    const res = await env.DB.prepare(
      "SELECT * FROM automation WHERE enabled = 1 AND trigger = 'schedule'",
    ).all<any>();
    for (const a of res.results ?? []) {
      const what = await performAction(env, a);
      await env.DB.prepare("UPDATE automation SET last_run_at = datetime('now'), run_count = run_count + 1 WHERE id = ?1").bind(a.id).run();
      await logAudit(env, { action: "automation_run", resource: a.id, details: `${a.name}: ${what}` });
      ran++;
    }
  } catch {
    /* table may not exist yet */
  }
  return ran;
}

/** Evaluate message_received automations after a chat turn. Best-effort. */
export async function runMessageAutomations(env: Env, ctx: { message: string; specialist: string }): Promise<void> {
  if (!env.DB) return;
  try {
    const res = await env.DB.prepare(
      "SELECT * FROM automation WHERE enabled = 1 AND trigger = 'message_received'",
    ).all<any>();
    const msg = ctx.message.toLowerCase();
    for (const a of res.results ?? []) {
      let matched = false;
      if (a.condition === "always") matched = true;
      else if (a.condition === "contains_keyword") matched = !!a.condition_value && msg.includes(String(a.condition_value).toLowerCase());
      else if (a.condition === "specialist_is") matched = ctx.specialist === a.condition_value;
      if (!matched) continue;
      await performAction(env, a);
      await env.DB.prepare("UPDATE automation SET last_run_at = datetime('now'), run_count = run_count + 1 WHERE id = ?1").bind(a.id).run();
    }
  } catch {
    /* best-effort */
  }
}

/**
 * Create alerts for recent CMS/regulatory updates (idempotent via dedup_key).
 * Ties the alerts feed to the real knowledge_updates the cron ingests.
 */
export async function generateUpdateAlerts(env: Env): Promise<number> {
  if (!env.DB) return 0;
  let made = 0;
  try {
    const res = await env.DB.prepare(
      "SELECT id, title, summary, url, source, category FROM knowledge_updates ORDER BY fetched_at DESC LIMIT 20",
    ).all<any>();
    for (const u of res.results ?? []) {
      const id = await createAlert(env, {
        severity: "info",
        title: `Regulatory update: ${u.title}`.slice(0, 200),
        message: (u.summary || "New CMS/regulatory update").slice(0, 500),
        details: u.url || "",
        source: u.source || "knowledge",
        category: u.category || "healthcare_regulatory",
        metadata: { url: u.url, knowledge_id: u.id },
        dedup_key: `ku:${u.id}`,
      });
      if (id) made++;
    }
  } catch {
    /* knowledge_updates / alert tables may not exist yet */
  }
  return made;
}
