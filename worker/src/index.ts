import { Hono } from "hono";
import { cors } from "hono/cors";
import type { Env, ChatMessage } from "./types";
import { requestAuthorized } from "./auth";
import { makeLLMClient } from "./llm";
import { runAgentLoop } from "./agent";
import { REGISTRY } from "./skills";
import { route } from "./router";
import { SPECIALISTS, getSpecialist } from "./specialists";
import { saveMessage, getRecentMessages, deleteUserData } from "./db";
import { searchMemory, storeMemory, buildMemoryContext } from "./memory";
import { checkUpdates, getChangelog } from "./knowledge";
import { generateBriefing, getBriefing } from "./briefing";
import { analyzeSensitivity } from "./sensitivity";
import { logAudit, queryAudit } from "./audit";

const app = new Hono<{ Bindings: Env }>();

app.use("*", cors());

// Auth gate (off unless API_AUTH_ENABLED). Cloudflare Access is the real login.
app.use("*", async (c, next) => {
  if (!requestAuthorized(c.env, c.req.path, c.req.method, c.req.header("authorization") ?? null)) {
    return c.json({ detail: "Unauthorized" }, 401);
  }
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

app.post("/api/chat", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const message: string = body.message ?? "";
  if (!message) return c.json({ error: "'message' is required" }, 400);
  const userId: string = body.user_id ?? "default_user";
  const conversationId: string = body.conversation_id ?? crypto.randomUUID();
  const model: string = body.model ?? c.env.DEFAULT_MODEL;

  // PHI/PII scan of the input (detection + audit; no local model to route to).
  const sensitivity = analyzeSensitivity(message);

  // Route to a specialist (or honor a forced one), then use its system prompt
  // and tool set for the agent loop.
  const routing = route(message, body.specialist);
  const specialist = getSpecialist(routing.primary_specialist)!;

  // Semantic recall of relevant past memories (no-op until Vectorize is bound).
  let systemPrompt = specialist.system_prompt;
  if (sensitivity.contains_phi) {
    systemPrompt +=
      "\n\nIMPORTANT: This conversation may contain PHI. Maintain strict confidentiality, " +
      "do not repeat identifiers unnecessarily, and follow HIPAA minimum-necessary principles.";
  }
  try {
    const memCtx = buildMemoryContext(await searchMemory(c.env, message, userId, 5));
    if (memCtx) systemPrompt += memCtx;
  } catch {
    /* memory is supplementary */
  }

  const messages: ChatMessage[] = [{ role: "system", content: systemPrompt }];
  if (body.conversation_id) {
    try {
      messages.push(...(await getRecentMessages(c.env, conversationId, 10)));
    } catch {
      /* history is optional */
    }
  }
  messages.push({ role: "user", content: message });

  const result = await runAgentLoop(messages, model, routing.recommended_tools, {
    llmClient: makeLLMClient(c.env),
    ctx: { env: c.env },
  });

  try {
    await saveMessage(c.env, conversationId, userId, "user", message);
    await saveMessage(c.env, conversationId, userId, "assistant", result.content);
  } catch {
    /* persistence is best-effort */
  }

  // Store this turn as a memory for future recall (background, best-effort).
  const memoryText = `User: ${message}\nAssistant: ${result.content}`;
  const storePromise = storeMemory(c.env, crypto.randomUUID(), memoryText, {
    user_id: userId,
    conversation_id: conversationId,
  });
  try {
    c.executionCtx.waitUntil(storePromise);
  } catch {
    storePromise.catch(() => {});
  }

  // Append-only audit entry (metadata only; PHI redacted on write).
  const auditPromise = logAudit(c.env, {
    user_id: userId, action: "chat", resource: conversationId,
    details: `specialist=${routing.primary_specialist}; model=${model}; tools=${result.tools_used.join(",")}`,
    ip: c.req.header("cf-connecting-ip") ?? "", sensitivity: sensitivity.level,
  });
  try { c.executionCtx.waitUntil(auditPromise); } catch { auditPromise.catch(() => {}); }

  return c.json({
    conversation_id: conversationId,
    specialist: routing.primary_specialist,
    confidence: routing.confidence,
    reasoning: routing.reasoning,
    sensitivity: { level: sensitivity.level, contains_phi: sensitivity.contains_phi },
    message: { role: "assistant", content: result.content },
    tools_used: result.tools_used,
    iterations: result.iterations,
    stop_reason: result.stop_reason,
  });
});

app.get("/api/audit", async (c) => {
  const limit = Number(c.req.query("limit") ?? 100);
  const user_id = c.req.query("user_id") ?? undefined;
  return c.json({ entries: await queryAudit(c.env, { user_id, limit }) });
});

app.delete("/api/compliance/user-data/:userId", async (c) => {
  const userId = c.req.param("userId");
  const removed = await deleteUserData(c.env, userId);
  await logAudit(c.env, { user_id: userId, action: "delete_user_data", resource: userId, details: `conversations_deleted=${removed}`, sensitivity: "phi" });
  return c.json({ user_id: userId, conversations_deleted: removed });
});

app.post("/api/memory/search", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  if (!body.query) return c.json({ error: "'query' is required" }, 400);
  const matches = await searchMemory(c.env, body.query, body.user_id, body.top_k ?? 5);
  return c.json({ matches });
});

app.post("/api/memory", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  if (!body.text) return c.json({ error: "'text' is required" }, 400);
  const stored = await storeMemory(c.env, body.id ?? crypto.randomUUID(), body.text, body.metadata ?? {});
  return c.json({ stored });
});

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

// Cron Triggers handler (schedules in wrangler.toml):
//   every 12 hours -> refresh CMS/regulatory updates, then regenerate briefing
//   daily at 07:00 -> regenerate the morning briefing
async function scheduled(event: ScheduledController, env: Env, ctx: ExecutionContext) {
  const run = async () => {
    if (event.cron === "0 7 * * *") {
      await generateBriefing(env);
      return;
    }
    await checkUpdates(env);
    await generateBriefing(env);
  };
  ctx.waitUntil(run());
}

export default { fetch: (req: Request, env: Env, ctx: ExecutionContext) => app.fetch(req, env, ctx), scheduled };
