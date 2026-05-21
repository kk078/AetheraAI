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
