import type { Env } from "./types";
import { getChangelog } from "./knowledge";

const BRIEFING_KEY = "briefing:latest";

/** Assemble a morning briefing from recent regulatory updates; cache it in KV. */
export async function generateBriefing(env: Env): Promise<any> {
  const updates = await getChangelog(env, 7, 10);
  const briefing = {
    generated_at: new Date().toISOString(),
    headline: updates.length
      ? `${updates.length} new CMS/regulatory update(s) this week`
      : "No new regulatory updates this week",
    counts: { recent_regulatory_updates: updates.length },
    regulatory_updates: updates,
  };
  try {
    if (env.CACHE) await env.CACHE.put(BRIEFING_KEY, JSON.stringify(briefing));
  } catch {
    /* cache write is best-effort */
  }
  return briefing;
}

/** Read the most recently generated briefing from KV. */
export async function getBriefing(env: Env): Promise<any | null> {
  if (!env.CACHE) return null;
  try {
    const v = await env.CACHE.get(BRIEFING_KEY);
    return v ? JSON.parse(v) : null;
  } catch {
    return null;
  }
}
