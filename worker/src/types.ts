export interface Env {
  DB: D1Database;
  CACHE: KVNamespace;
  ASSETS_BUCKET: R2Bucket;
  // Static assets binding for the built React UI (see [assets] in wrangler.toml).
  // Optional so the Worker still runs in tests without an assets directory.
  ASSETS?: Fetcher;
  // Optional bindings for memory/RAG (phase 4). Typed structurally so the build
  // doesn't depend on a specific @cloudflare/workers-types Vectorize version,
  // and so the Worker still runs when these aren't bound yet.
  AI?: {
    run(model: string, inputs: { text: string | string[] }): Promise<{ data: number[][] }>;
  };
  VECTORIZE?: {
    upsert(vectors: Array<{ id: string; values: number[]; metadata?: Record<string, any> }>): Promise<unknown>;
    query(
      values: number[],
      options?: Record<string, any>,
    ): Promise<{ matches?: Array<{ id: string; score: number; metadata?: Record<string, any> }> }>;
  };
  // vars
  LLM_BASE_URL: string;
  DEFAULT_MODEL: string;
  API_AUTH_ENABLED: string;
  // Cloudflare Access (primary login). When set, a valid Cf-Access-Jwt-Assertion
  // header authorizes /api/* without an API key.
  ACCESS_TEAM_DOMAIN?: string;
  ACCESS_AUD?: string;
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
