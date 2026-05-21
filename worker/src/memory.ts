import type { Env } from "./types";

// Workers AI embedding model — 768-dim. The Vectorize index must be created
// with matching dimensions:
//   wrangler vectorize create aethera-ai-memory --dimensions=768 --metric=cosine
const EMBED_MODEL = "@cf/baai/bge-base-en-v1.5";

export interface MemoryMatch {
  score: number;
  text: string;
  user_id?: string;
  conversation_id?: string;
}

/** Embed text via Workers AI. Returns null if AI isn't bound or the call fails. */
export async function embed(env: Env, text: string): Promise<number[] | null> {
  if (!env.AI || !text) return null;
  try {
    const res = await env.AI.run(EMBED_MODEL, { text });
    return res?.data?.[0] ?? null;
  } catch {
    return null;
  }
}

/** Upsert a memory into Vectorize. No-op (returns false) if memory isn't bound. */
export async function storeMemory(
  env: Env,
  id: string,
  text: string,
  metadata: Record<string, any> = {},
): Promise<boolean> {
  if (!env.VECTORIZE) return false;
  const values = await embed(env, text);
  if (!values) return false;
  try {
    await env.VECTORIZE.upsert([{ id, values, metadata: { ...metadata, text: text.slice(0, 2000) } }]);
    return true;
  } catch {
    return false;
  }
}

/**
 * Semantic search over stored memories, scoped to a user. Returns [] when
 * memory isn't bound (so callers degrade gracefully).
 */
export async function searchMemory(
  env: Env,
  query: string,
  userId?: string,
  topK = 5,
): Promise<MemoryMatch[]> {
  if (!env.VECTORIZE) return [];
  const values = await embed(env, query);
  if (!values) return [];
  try {
    // Over-fetch when filtering by user so the post-filter still returns topK.
    const res = await env.VECTORIZE.query(values, {
      topK: userId ? topK * 3 : topK,
      returnMetadata: true,
    });
    let matches: MemoryMatch[] = (res.matches ?? []).map((m) => ({
      score: m.score,
      text: String(m.metadata?.text ?? ""),
      user_id: m.metadata?.user_id,
      conversation_id: m.metadata?.conversation_id,
    }));
    if (userId) matches = matches.filter((m) => !m.user_id || m.user_id === userId);
    return matches.slice(0, topK);
  } catch {
    return [];
  }
}

/** Render retrieved memories into a system-prompt block (pure; testable). */
export function buildMemoryContext(matches: MemoryMatch[]): string {
  const lines = matches.filter((m) => m.text).map((m) => `  - ${m.text}`);
  if (!lines.length) return "";
  return (
    "\n\n--- Relevant memory from past conversations ---\n" +
    lines.join("\n") +
    "\n--- End memory ---\n"
  );
}
