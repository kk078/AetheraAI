export interface Env {
  DB: D1Database;
  CACHE: KVNamespace;
  ASSETS_BUCKET: R2Bucket;
  // vars
  LLM_BASE_URL: string;
  DEFAULT_MODEL: string;
  API_AUTH_ENABLED: string;
  // secrets
  OLLAMA_API_KEY?: string;
  API_KEYS?: string;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  tool_calls?: ToolCall[];
  tool_call_id?: string;
  name?: string;
}

export interface ToolCall {
  id: string;
  type: "function";
  function: { name: string; arguments: string };
}
