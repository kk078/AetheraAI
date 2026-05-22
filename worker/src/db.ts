import type { Env, ChatMessage } from "./types";

/** Persist a single message to D1. */
export async function saveMessage(
  env: Env,
  conversationId: string,
  userId: string,
  role: string,
  content: string,
): Promise<void> {
  await env.DB.prepare(
    `INSERT INTO conversations (id, user_id, updated_at)
     VALUES (?1, ?2, datetime('now'))
     ON CONFLICT(id) DO UPDATE SET updated_at = datetime('now')`,
  )
    .bind(conversationId, userId)
    .run();

  await env.DB.prepare(
    `INSERT INTO messages (conversation_id, role, content, created_at)
     VALUES (?1, ?2, ?3, datetime('now'))`,
  )
    .bind(conversationId, role, content)
    .run();
}

/** Load recent messages for a conversation (oldest first). */
export async function getRecentMessages(
  env: Env,
  conversationId: string,
  limit = 10,
): Promise<ChatMessage[]> {
  const { results } = await env.DB.prepare(
    `SELECT role, content FROM messages
     WHERE conversation_id = ?1
     ORDER BY id DESC LIMIT ?2`,
  )
    .bind(conversationId, limit)
    .all<{ role: string; content: string }>();
  return (results ?? [])
    .reverse()
    .map((r) => ({ role: r.role as ChatMessage["role"], content: r.content }));
}

/** List conversations (most recently updated first) with message counts. */
export async function listConversations(
  env: Env,
  limit = 50,
  offset = 0,
): Promise<Array<{ id: string; user_id: string; title: string; created_at: string; updated_at: string; message_count: number }>> {
  const { results } = await env.DB.prepare(
    `SELECT c.id, c.user_id, c.title, c.created_at, c.updated_at,
            (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
     FROM conversations c
     ORDER BY c.updated_at DESC
     LIMIT ?1 OFFSET ?2`,
  )
    .bind(Math.min(limit, 200), Math.max(offset, 0))
    .all<any>();
  return results ?? [];
}

/** Load a single conversation with its messages (oldest first). */
export async function getConversation(
  env: Env,
  conversationId: string,
): Promise<{ id: string; title: string; created_at: string; updated_at: string; messages: ChatMessage[] } | null> {
  const conv = await env.DB.prepare(
    `SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?1`,
  )
    .bind(conversationId)
    .first<any>();
  if (!conv) return null;
  const { results } = await env.DB.prepare(
    `SELECT role, content FROM messages WHERE conversation_id = ?1 ORDER BY id ASC`,
  )
    .bind(conversationId)
    .all<{ role: string; content: string }>();
  return {
    ...conv,
    messages: (results ?? []).map((r) => ({ role: r.role as ChatMessage["role"], content: r.content })),
  };
}

/** Delete a single conversation and its messages. Returns true if it existed. */
export async function deleteConversation(env: Env, conversationId: string): Promise<boolean> {
  const existing = await env.DB.prepare(`SELECT id FROM conversations WHERE id = ?1`)
    .bind(conversationId)
    .first<{ id: string }>();
  if (!existing) return false;
  await env.DB.prepare(`DELETE FROM messages WHERE conversation_id = ?1`).bind(conversationId).run();
  await env.DB.prepare(`DELETE FROM conversations WHERE id = ?1`).bind(conversationId).run();
  return true;
}

/** Aggregate counts for the dashboard. Best-effort: returns zeros on error. */
export async function dashboardStats(env: Env): Promise<{ conversations: number; messages: number; audit_entries: number; knowledge_updates: number }> {
  const one = async (sql: string): Promise<number> => {
    try {
      const r = await env.DB.prepare(sql).first<{ n: number }>();
      return r?.n ?? 0;
    } catch {
      return 0;
    }
  };
  return {
    conversations: await one(`SELECT COUNT(*) AS n FROM conversations`),
    messages: await one(`SELECT COUNT(*) AS n FROM messages`),
    audit_entries: await one(`SELECT COUNT(*) AS n FROM audit_log`),
    knowledge_updates: await one(`SELECT COUNT(*) AS n FROM knowledge_updates`),
  };
}

/** HIPAA right-to-delete: remove a user's conversations and messages. */
export async function deleteUserData(env: Env, userId: string): Promise<number> {
  const { results } = await env.DB.prepare(
    `SELECT id FROM conversations WHERE user_id = ?1`,
  )
    .bind(userId)
    .all<{ id: string }>();
  for (const row of results ?? []) {
    await env.DB.prepare(`DELETE FROM messages WHERE conversation_id = ?1`).bind(row.id).run();
  }
  await env.DB.prepare(`DELETE FROM conversations WHERE user_id = ?1`).bind(userId).run();
  return (results ?? []).length;
}
