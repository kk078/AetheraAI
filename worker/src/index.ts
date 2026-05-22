import { Hono } from "hono";
import { cors } from "hono/cors";
import { streamSSE } from "hono/streaming";
import type { Env, ChatMessage } from "./types";
import { authorizeRequest } from "./auth";
import { makeLLMClient } from "./llm";
import { runAgentLoop } from "./agent";
import { REGISTRY } from "./skills";
import { route } from "./router";
import { SPECIALISTS, getSpecialist } from "./specialists";
import {
  saveMessage, getRecentMessages, deleteUserData,
  listConversations, getConversation, deleteConversation, dashboardStats,
} from "./db";
import { searchMemory, storeMemory, buildMemoryContext } from "./memory";
import { checkUpdates, getChangelog } from "./knowledge";
import { generateBriefing, getBriefing } from "./briefing";
import { analyzeSensitivity } from "./sensitivity";
import { logAudit, queryAudit, auditStats } from "./audit";
import { HEALTHCARE_ROUTES } from "./healthcare";
import { getSettings, updateSettings } from "./settings";
import {
  listAlerts, acknowledgeAlert, listActionItems, addActionItem, completeActionItem, queueStats,
  listAutomations, createAutomation, setAutomationEnabled, deleteAutomation,
  runScheduledAutomations, runMessageAutomations, generateUpdateAlerts,
} from "./proactive";

const app = new Hono<{ Bindings: Env }>();

app.use("*", cors());

// Auth gate (off unless API_AUTH_ENABLED). Cloudflare Access is the real login:
// a valid Cf-Access-Jwt-Assertion authorizes the request; a bearer key works as
// a fallback for API clients.
app.use("*", async (c, next) => {
  const ok = await authorizeRequest(
    c.env,
    c.req.path,
    c.req.method,
    c.req.header("authorization") ?? null,
    c.req.header("cf-access-jwt-assertion") ?? null,
  );
  if (!ok) return c.json({ detail: "Unauthorized" }, 401);
  await next();
});

app.get("/api/health", (c) =>
  c.json({ status: "ok", service: "aethera-ai-worker", skills: Object.keys(REGISTRY).length }),
);

app.get("/api/skills", (c) =>
  c.json({
    skills: Object.values(REGISTRY).map((s) => ({
      name: s.name,
      description: s.description,
      parameters: s.parameters,
    })),
  }),
);

app.post("/api/skills/:name/execute", async (c) => {
  const skill = REGISTRY[c.req.param("name")];
  if (!skill) return c.json({ error: "Skill not found" }, 404);
  const args = await c.req.json().catch(() => ({}));
  return c.json(await skill.execute(args, { env: c.env }));
});

app.get("/api/specialists", (c) =>
  c.json({
    specialists: SPECIALISTS.map((s) => ({
      name: s.name,
      display_name: s.display_name,
      description: s.description,
      tools: s.tools,
      priority: s.priority,
    })),
  }),
);

interface ChatResponse {
  conversation_id: string;
  specialist: string;
  confidence: number;
  reasoning: string;
  sensitivity: { level: string; contains_phi: boolean };
  message: { role: "assistant"; content: string };
  tools_used: string[];
  iterations: number;
  stop_reason: string;
}

/**
 * Core chat pipeline shared by /api/chat, /api/chat/stream, the per-specialist
 * routes, and /api/specialists/:name/query: route -> PHI scan -> memory recall
 * -> agent loop -> persist + memory store + audit.
 */
async function handleChat(
  env: Env,
  waitUntil: (p: Promise<unknown>) => void,
  ip: string,
  body: any,
  forcedSpecialist?: string,
): Promise<ChatResponse> {
  const message: string = body.message ?? body.query ?? "";
  const userId: string = body.user_id ?? "default_user";
  const conversationId: string = body.conversation_id ?? crypto.randomUUID();
  const model: string = body.model ?? env.DEFAULT_MODEL;

  const sensitivity = analyzeSensitivity(message);
  const routing = route(message, forcedSpecialist ?? body.specialist);
  const specialist = getSpecialist(routing.primary_specialist)!;

  let systemPrompt = specialist.system_prompt;
  if (sensitivity.contains_phi) {
    systemPrompt +=
      "\n\nIMPORTANT: This conversation may contain PHI. Maintain strict confidentiality, " +
      "do not repeat identifiers unnecessarily, and follow HIPAA minimum-necessary principles.";
  }
  try {
    const memCtx = buildMemoryContext(await searchMemory(env, message, userId, 5));
    if (memCtx) systemPrompt += memCtx;
  } catch {
    /* memory is supplementary */
  }

  const messages: ChatMessage[] = [{ role: "system", content: systemPrompt }];
  if (body.conversation_id) {
    try {
      messages.push(...(await getRecentMessages(env, conversationId, 10)));
    } catch {
      /* history is optional */
    }
  }
  messages.push({ role: "user", content: message });

  const result = await runAgentLoop(messages, model, routing.recommended_tools, {
    llmClient: makeLLMClient(env),
    ctx: { env },
  });

  try {
    await saveMessage(env, conversationId, userId, "user", message);
    await saveMessage(env, conversationId, userId, "assistant", result.content);
  } catch {
    /* persistence is best-effort */
  }

  const memoryText = `User: ${message}\nAssistant: ${result.content}`;
  waitUntil(
    storeMemory(env, crypto.randomUUID(), memoryText, { user_id: userId, conversation_id: conversationId }),
  );
  waitUntil(
    logAudit(env, {
      user_id: userId, action: "chat", resource: conversationId,
      details: `specialist=${routing.primary_specialist}; model=${model}; tools=${result.tools_used.join(",")}`,
      ip, sensitivity: sensitivity.level,
    }),
  );
  waitUntil(runMessageAutomations(env, { message, specialist: routing.primary_specialist }));

  return {
    conversation_id: conversationId,
    specialist: routing.primary_specialist,
    confidence: routing.confidence,
    reasoning: routing.reasoning,
    sensitivity: { level: sensitivity.level, contains_phi: sensitivity.contains_phi },
    message: { role: "assistant", content: result.content },
    tools_used: result.tools_used,
    iterations: result.iterations,
    stop_reason: result.stop_reason,
  };
}

/** Wrap executionCtx.waitUntil so a missing ctx never throws. */
function safeWaitUntil(c: { executionCtx?: ExecutionContext }): (p: Promise<unknown>) => void {
  return (p) => {
    try {
      c.executionCtx?.waitUntil(p);
    } catch {
      (p as Promise<unknown>).catch(() => {});
    }
  };
}

app.post("/api/chat", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  if (!body.message) return c.json({ error: "'message' is required" }, 400);
  return c.json(await handleChat(c.env, safeWaitUntil(c), c.req.header("cf-connecting-ip") ?? "", body));
});

app.post("/api/chat/specialist/:name", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  if (!body.message) return c.json({ error: "'message' is required" }, 400);
  const name = c.req.param("name");
  if (!getSpecialist(name)) return c.json({ error: "Specialist not found" }, 404);
  return c.json(await handleChat(c.env, safeWaitUntil(c), c.req.header("cf-connecting-ip") ?? "", body, name));
});

// Multi-agent coordination isn't ported; serve via the primary specialist so
// the UI gets a real answer (single-specialist) rather than a 404.
app.post("/api/chat/multi-agent", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  if (!body.message) return c.json({ error: "'message' is required" }, 400);
  const res = await handleChat(c.env, safeWaitUntil(c), c.req.header("cf-connecting-ip") ?? "", body);
  return c.json({ ...res, mode: "single_specialist", note: "multi-agent coordination runs as the primary specialist on the Worker" });
});

// SSE streaming chat. The agent loop is non-streaming, so we run it to
// completion and emit the final answer as one SSE message + [DONE]. The shape
// matches the non-streaming response so the UI can render it uniformly.
app.post("/api/chat/stream", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  if (!body.message) return c.json({ error: "'message' is required" }, 400);
  const res = await handleChat(c.env, safeWaitUntil(c), c.req.header("cf-connecting-ip") ?? "", body);
  return streamSSE(c, async (stream) => {
    await stream.writeSSE({ data: JSON.stringify({ type: "message", ...res }) });
    await stream.writeSSE({ data: "[DONE]" });
  });
});

app.post("/api/specialists/:specialist/query", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  if (!body.query && !body.message) return c.json({ error: "'query' is required" }, 400);
  const name = c.req.param("specialist");
  if (!getSpecialist(name)) return c.json({ error: "Specialist not found" }, 404);
  return c.json(await handleChat(c.env, safeWaitUntil(c), c.req.header("cf-connecting-ip") ?? "", body, name));
});

// --- Healthcare tool endpoints (adapters over skills; see healthcare.ts) ---
app.post("/api/healthcare/:op", async (c) => {
  const op = c.req.param("op");
  const def = HEALTHCARE_ROUTES[op];
  if (!def) return c.json({ error: `Unknown healthcare operation '${op}'` }, 404);
  const skill = REGISTRY[def.skill];
  if (!skill) return c.json({ error: `Skill '${def.skill}' not registered` }, 500);
  const body = await c.req.json().catch(() => ({}));
  return c.json(await skill.execute(def.map(body), { env: c.env }));
});

// --- Conversations (D1) ---
app.get("/api/conversations", async (c) => {
  const limit = Number(c.req.query("limit") ?? 50);
  const offset = Number(c.req.query("offset") ?? 0);
  return c.json({ conversations: await listConversations(c.env, limit, offset) });
});

app.get("/api/conversations/:id", async (c) => {
  const conv = await getConversation(c.env, c.req.param("id"));
  if (!conv) return c.json({ error: "Conversation not found" }, 404);
  return c.json(conv);
});

app.delete("/api/conversations/:id", async (c) => {
  const ok = await deleteConversation(c.env, c.req.param("id"));
  if (!ok) return c.json({ error: "Conversation not found" }, 404);
  return c.json({ deleted: true, conversation_id: c.req.param("id") });
});

// --- Code lookup shortcut used by the UI clipboard/code views ---
app.get("/api/codes/:codeType/:code", async (c) => {
  const skill = REGISTRY["code_lookup"];
  const res = await skill.execute({ code: c.req.param("code"), code_type: c.req.param("codeType") }, { env: c.env });
  return c.json(res);
});

// --- Audit ---
app.get("/api/audit", async (c) => {
  const limit = Number(c.req.query("limit") ?? 100);
  const user_id = c.req.query("user_id") ?? undefined;
  return c.json({ entries: await queryAudit(c.env, { user_id, limit }) });
});

app.get("/api/audit/stats", async (c) => c.json(await auditStats(c.env)));

app.post("/api/audit/export", async (c) => {
  const entries = await queryAudit(c.env, { limit: 500 });
  const body = await c.req.json().catch(() => ({}));
  if ((body.format ?? "json") === "csv") {
    const cols = ["id", "ts", "user_id", "action", "resource", "details", "sensitivity"];
    const esc = (v: any) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const csv = [cols.join(","), ...entries.map((e) => cols.map((k) => esc(e[k])).join(","))].join("\n");
    return c.text(csv, 200, { "Content-Type": "text/csv" });
  }
  return c.json({ format: "json", count: entries.length, entries });
});

app.delete("/api/compliance/user-data/:userId", async (c) => {
  const userId = c.req.param("userId");
  const removed = await deleteUserData(c.env, userId);
  await logAudit(c.env, { user_id: userId, action: "delete_user_data", resource: userId, details: `conversations_deleted=${removed}`, sensitivity: "phi" });
  return c.json({ user_id: userId, conversations_deleted: removed });
});

// --- Memory ---
app.post("/api/memory/search", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  if (!body.query) return c.json({ error: "'query' is required" }, 400);
  const matches = await searchMemory(c.env, body.query, body.user_id, body.top_k ?? 5);
  return c.json({ matches });
});

app.get("/api/memory/search", async (c) => {
  const query = c.req.query("query");
  if (!query) return c.json({ error: "'query' is required" }, 400);
  const topK = Number(c.req.query("top_k") ?? 10);
  const matches = await searchMemory(c.env, query, c.req.query("user_id") ?? undefined, topK);
  return c.json({ matches });
});

app.post("/api/memory", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  if (!body.text) return c.json({ error: "'text' is required" }, 400);
  const stored = await storeMemory(c.env, body.id ?? crypto.randomUUID(), body.text, body.metadata ?? {});
  return c.json({ stored });
});

app.get("/api/memory/profile/:userId", async (c) => {
  const userId = c.req.param("userId");
  let profile: Record<string, any> = {};
  try {
    const raw = await c.env.CACHE.get(`memory:profile:${userId}`);
    if (raw) profile = JSON.parse(raw);
  } catch {
    /* default empty profile */
  }
  return c.json({ user_id: userId, profile });
});

app.post("/api/memory/profile/:userId", async (c) => {
  const userId = c.req.param("userId");
  const updates = await c.req.json().catch(() => ({}));
  let current: Record<string, any> = {};
  try {
    const raw = await c.env.CACHE.get(`memory:profile:${userId}`);
    if (raw) current = JSON.parse(raw);
  } catch {
    /* start fresh */
  }
  const next = { ...current, ...updates };
  try {
    await c.env.CACHE.put(`memory:profile:${userId}`, JSON.stringify(next));
  } catch {
    /* best-effort */
  }
  return c.json({ user_id: userId, profile: next });
});

// Profile alias without an explicit userId (UI default).
app.get("/api/memory/profile", async (c) => {
  let profile: Record<string, any> = {};
  try {
    const raw = await c.env.CACHE.get("memory:profile:default_user");
    if (raw) profile = JSON.parse(raw);
  } catch {
    /* default empty profile */
  }
  return c.json({ user_id: "default_user", profile });
});

app.post("/api/memory/profile", async (c) => {
  const updates = await c.req.json().catch(() => ({}));
  let current: Record<string, any> = {};
  try {
    const raw = await c.env.CACHE.get("memory:profile:default_user");
    if (raw) current = JSON.parse(raw);
  } catch {
    /* start fresh */
  }
  const next = { ...current, ...updates };
  try {
    await c.env.CACHE.put("memory:profile:default_user", JSON.stringify(next));
  } catch {
    /* best-effort */
  }
  return c.json({ user_id: "default_user", profile: next });
});

// --- Settings (KV) ---
app.get("/api/settings", async (c) => c.json(await getSettings(c.env)));
app.post("/api/settings", async (c) => {
  const updates = await c.req.json().catch(() => ({}));
  return c.json(await updateSettings(c.env, updates));
});

// Privacy settings (subset of app settings) + audit-log view used by the UI.
app.get("/api/settings/privacy", async (c) => c.json({ settings: await getSettings(c.env) }));
app.post("/api/settings/privacy", async (c) => {
  const updates = await c.req.json().catch(() => ({}));
  return c.json({ settings: await updateSettings(c.env, updates) });
});
app.get("/api/settings/privacy/audit-log", async (c) => {
  const limit = Number(c.req.query("limit") ?? 100);
  return c.json({ entries: await queryAudit(c.env, { limit }) });
});

// --- Dashboard ---
app.get("/api/dashboard", async (c) => {
  const stats = await dashboardStats(c.env);
  let briefing: any = null;
  try { briefing = await getBriefing(c.env); } catch { /* optional */ }
  return c.json({
    stats: { ...stats, skills: Object.keys(REGISTRY).length, specialists: SPECIALISTS.length },
    recent_updates: await getChangelog(c.env, 7, 5),
    briefing,
  });
});

// --- Alerts ---
app.get("/api/alerts", async (c) => {
  const activeOnly = c.req.query("active_only") !== "false";
  return c.json({ alerts: await listAlerts(c.env, { activeOnly }) });
});
app.post("/api/alerts/:id/acknowledge", async (c) => {
  const ok = await acknowledgeAlert(c.env, c.req.param("id"));
  return ok ? c.json({ acknowledged: true, id: c.req.param("id") }) : c.json({ error: "Alert not found" }, 404);
});

// --- Action queue ---
app.get("/api/queue", async (c) => c.json({ items: await listActionItems(c.env, {}) }));
app.get("/api/queue/stats", async (c) => c.json(await queueStats(c.env)));
app.post("/api/queue", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  if (!body.title) return c.json({ error: "'title' is required" }, 400);
  const id = await addActionItem(c.env, body);
  return id ? c.json({ id, created: true }) : c.json({ error: "Could not create action item" }, 500);
});
app.post("/api/queue/:id/complete", async (c) => {
  const ok = await completeActionItem(c.env, c.req.param("id"));
  return ok ? c.json({ completed: true, id: c.req.param("id") }) : c.json({ error: "Item not found or already completed" }, 404);
});

// --- Automations ---
app.get("/api/automations", async (c) => c.json({ automations: await listAutomations(c.env) }));
app.post("/api/automations", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  if (!body.name) return c.json({ error: "'name' is required" }, 400);
  const automation = await createAutomation(c.env, body);
  return automation ? c.json({ automation }) : c.json({ error: "Could not create automation" }, 500);
});
app.post("/api/automations/:id/enable", async (c) => {
  const ok = await setAutomationEnabled(c.env, c.req.param("id"), true);
  return ok ? c.json({ enabled: true, id: c.req.param("id") }) : c.json({ error: "Automation not found" }, 404);
});
app.post("/api/automations/:id/disable", async (c) => {
  const ok = await setAutomationEnabled(c.env, c.req.param("id"), false);
  return ok ? c.json({ enabled: false, id: c.req.param("id") }) : c.json({ error: "Automation not found" }, 404);
});
app.delete("/api/automations/:id", async (c) => {
  const ok = await deleteAutomation(c.env, c.req.param("id"));
  return ok ? c.json({ deleted: true, id: c.req.param("id") }) : c.json({ error: "Automation not found" }, 404);
});

// --- Models ---
app.get("/api/models", (c) =>
  c.json({
    default: c.env.DEFAULT_MODEL,
    models: [{ id: c.env.DEFAULT_MODEL, provider: "ollama_cloud", default: true }],
  }),
);

// --- Proactive: knowledge updates + briefing (also driven by Cron Triggers) ---
app.get("/api/knowledge/updates", async (c) => {
  const days = Number(c.req.query("days") ?? 7);
  return c.json({ updates: await getChangelog(c.env, days, 50) });
});

app.post("/api/knowledge/check", async (c) => {
  return c.json(await checkUpdates(c.env));
});

app.get("/api/briefing", async (c) => {
  const briefing = (await getBriefing(c.env)) ?? (await generateBriefing(c.env));
  return c.json(briefing);
});

app.post("/api/briefing/generate", async (c) => {
  return c.json(await generateBriefing(c.env));
});

app.get("/api/news", async (c) => {
  const limit = Number(c.req.query("limit") ?? 10);
  return c.json({ news: await getChangelog(c.env, 30, limit) });
});

// Host-only / not-yet-ported features: features that need a local runtime
// (voice STT/TTS, clipboard, PC control, the Cloudflare tunnel) or a Python
// subsystem not ported to the Worker. Return an explicit, documented 501 so the
// UI degrades gracefully instead of hitting an undefined route.
const NOT_PORTABLE = [
  "/api/voice", "/api/clipboard", "/api/upload", "/api/backup", "/api/cloudflare",
  "/api/plugins", "/api/connectors", "/api/temporal", "/api/pc",
  "/api/memory/facts", "/api/memory/learning", "/api/memory/knowledge-graph",
  "/api/memory/knowledge-gaps", "/api/memory/health-records", "/api/memory/consolidate",
  "/api/memory/forget",
];
app.all("/api/*", (c) => {
  const path = c.req.path;
  if (NOT_PORTABLE.some((p) => path === p || path.startsWith(p + "/"))) {
    return c.json(
      { detail: "Not available on the Cloudflare Worker", portable: false, path },
      501,
    );
  }
  return c.json({ detail: "Not found", path }, 404);
});

// Cron Triggers handler (schedules in wrangler.toml):
//   every 12 hours -> refresh CMS/regulatory updates, then regenerate briefing
//   daily at 07:00 -> regenerate the morning briefing
async function scheduled(event: ScheduledController, env: Env, ctx: ExecutionContext) {
  const run = async () => {
    if (event.cron === "0 7 * * *") {
      await generateBriefing(env);
      await runScheduledAutomations(env);
      return;
    }
    await checkUpdates(env);
    await generateUpdateAlerts(env);
    await generateBriefing(env);
    await runScheduledAutomations(env);
  };
  ctx.waitUntil(run());
}

export default { fetch: (req: Request, env: Env, ctx: ExecutionContext) => app.fetch(req, env, ctx), scheduled };
