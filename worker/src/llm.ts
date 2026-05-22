import type { Env } from "./types";

export type LLMClient = (payload: Record<string, unknown>) => Promise<any>;

/**
 * Build an LLM client that calls an OpenAI-compatible chat-completions endpoint
 * (Ollama Cloud by default). Transport errors return a synthetic response so the
 * agent loop terminates cleanly instead of throwing.
 */
export function makeLLMClient(env: Env): LLMClient {
  return async (payload) => {
    try {
      const res = await fetch(`${env.LLM_BASE_URL}/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(env.OLLAMA_API_KEY ? { Authorization: `Bearer ${env.OLLAMA_API_KEY}` } : {}),
        },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const detail = await res.text().catch(() => "");
        return { choices: [{ message: { content: `LLM service error (${res.status}). ${detail.slice(0, 200)}` } }] };
      }
      return await res.json();
    } catch (e) {
      return { choices: [{ message: { content: "The AI service is currently unavailable. Please try again." } }] };
    }
  };
}
