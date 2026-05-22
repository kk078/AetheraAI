import type { ChatMessage, ToolCall } from "./types";
import type { LLMClient } from "./llm";
import { REGISTRY, toolDefinitions, type SkillResult, type SkillContext } from "./skills";

const DEFAULT_MAX_ITERATIONS = 8;

export interface ToolInvocation {
  name: string;
  arguments: Record<string, unknown>;
  success: boolean;
  result?: unknown;
  error?: string;
}

export interface AgentResult {
  content: string;
  tools_used: string[];
  invocations: ToolInvocation[];
  iterations: number;
  stop_reason: "completed" | "max_iterations";
  messages: ChatMessage[];
}

function parseArgs(raw: unknown): [Record<string, any> | null, string | null] {
  if (raw == null || raw === "") return [{}, null];
  if (typeof raw === "object") return [raw as Record<string, any>, null];
  try {
    const parsed = JSON.parse(String(raw));
    if (typeof parsed !== "object" || parsed === null) return [null, "Tool arguments must be a JSON object"];
    return [parsed, null];
  } catch {
    return [null, "Tool arguments were not valid JSON"];
  }
}

async function executeToolCall(tc: ToolCall, ctx?: SkillContext): Promise<ToolInvocation> {
  const name = tc.function?.name || "unknown";
  const [args, parseErr] = parseArgs(tc.function?.arguments);
  if (parseErr) return { name, arguments: {}, success: false, error: parseErr };
  const skill = REGISTRY[name];
  if (!skill) return { name, arguments: args!, success: false, error: `Skill not found: ${name}` };
  try {
    const res: SkillResult = await skill.execute(args!, ctx);
    return res.success
      ? { name, arguments: args!, success: true, result: res.data }
      : { name, arguments: args!, success: false, error: res.error || "Tool execution failed" };
  } catch (e: any) {
    return { name, arguments: args!, success: false, error: String(e?.message ?? e) };
  }
}

function toolContent(inv: ToolInvocation): string {
  if (!inv.success) return JSON.stringify({ error: inv.error });
  try {
    return JSON.stringify(inv.result);
  } catch {
    return String(inv.result);
  }
}

/**
 * Agentic reason-act loop (TS port of orchestrator/agent.py): the model proposes
 * tool calls, we execute them via the skill registry, feed results back, and
 * iterate until a final answer or the iteration cap.
 */
export async function runAgentLoop(
  messages: ChatMessage[],
  model: string,
  toolNames: string[],
  opts: { llmClient: LLMClient; ctx?: SkillContext; maxIterations?: number; temperature?: number; maxTokens?: number },
): Promise<AgentResult> {
  const tools = toolDefinitions(toolNames);
  const working: ChatMessage[] = [...messages];
  const invocations: ToolInvocation[] = [];
  const toolsUsed: string[] = [];
  let lastContent = "";
  const maxIterations = opts.maxIterations ?? DEFAULT_MAX_ITERATIONS;

  for (let iteration = 1; iteration <= maxIterations; iteration++) {
    const payload: Record<string, unknown> = {
      model,
      messages: working,
      stream: false,
      temperature: opts.temperature ?? 0.7,
      max_tokens: opts.maxTokens ?? 4096,
    };
    if (tools.length) payload.tools = tools;

    const data = await opts.llmClient(payload);
    const message = data?.choices?.[0]?.message ?? {};
    if (message.content) lastContent = message.content;

    const toolCalls: ToolCall[] = message.tool_calls ?? [];
    if (!toolCalls.length) {
      return {
        content: message.content ?? "",
        tools_used: toolsUsed,
        invocations,
        iterations: iteration,
        stop_reason: "completed",
        messages: working,
      };
    }

    working.push({ role: "assistant", content: message.content ?? "", tool_calls: toolCalls });
    for (const tc of toolCalls) {
      const inv = await executeToolCall(tc, opts.ctx);
      invocations.push(inv);
      toolsUsed.push(inv.name);
      working.push({ role: "tool", tool_call_id: tc.id, name: inv.name, content: toolContent(inv) });
    }
  }

  return {
    content: lastContent,
    tools_used: toolsUsed,
    invocations,
    iterations: maxIterations,
    stop_reason: "max_iterations",
    messages: working,
  };
}
