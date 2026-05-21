import { Hono } from "hono";
import { cors } from "hono/cors";
import type { Env, ChatMessage } from "./types";
import { requestAuthorized } from "./auth";
import { makeLLMClient } from "./llm";
import { runAgentLoop } from "./agent";
import { REGISTRY } from "./skills";
import { saveMessage, getRecentMessages, deleteUserData } from "./db";

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
  return c.json(skill.execute(args));
});

app.post("/api/chat", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const message: string = body.message ?? "";
  if (!message) return c.json({ error: "'message' is required" }, 400);
  const userId: string = body.user_id ?? "default_user";
  const conversationId: string = body.conversation_id ?? crypto.randomUUID();
  const model: string = body.model ?? c.env.DEFAULT_MODEL;

  const messages: ChatMessage[] = [
    {
      role: "system",
      content:
        "You are Aethera, a healthcare revenue-cycle AI. Use the available tools to compute answers precisely.",
    },
  ];
  if (body.conversation_id) {
    try {
      messages.push(...(await getRecentMessages(c.env, conversationId, 10)));
    } catch {
      /* history is optional */
    }
  }
  messages.push({ role: "user", content: message });

  const result = await runAgentLoop(messages, model, Object.keys(REGISTRY), {
    llmClient: makeLLMClient(c.env),
  });

  try {
    await saveMessage(c.env, conversationId, userId, "user", message);
    await saveMessage(c.env, conversationId, userId, "assistant", result.content);
  } catch {
    /* persistence is best-effort */
  }

  return c.json({
    conversation_id: conversationId,
    message: { role: "assistant", content: result.content },
    tools_used: result.tools_used,
    iterations: result.iterations,
    stop_reason: result.stop_reason,
  });
});

app.delete("/api/compliance/user-data/:userId", async (c) => {
  const removed = await deleteUserData(c.env, c.req.param("userId"));
  return c.json({ user_id: c.req.param("userId"), conversations_deleted: removed });
});

export default app;
