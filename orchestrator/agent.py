"""
Aethera AI - Agentic reason-act loop.

Lets the model actually *use* tools: the model proposes tool calls, this loop
executes them via the skill registry, feeds the results back, and iterates until
the model produces a final answer (or the iteration cap is hit).

Without this loop the orchestrator can only do a single LLM call and surface tool
calls as inert text — it cannot complete multi-step revenue-cycle tasks
(e.g. look up a code, scrub a claim, then draft an appeal) on its own.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("aethera.agent")

DEFAULT_MAX_ITERATIONS = 8

# An LLM client takes an OpenAI-style chat-completions payload and returns the
# parsed JSON response. Injected so the loop is testable without a live model.
LLMClient = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]


@dataclass
class ToolInvocation:
    """Record of a single tool call the model made and its outcome."""
    name: str
    arguments: Dict[str, Any]
    success: bool
    result: Any = None
    error: Optional[str] = None


@dataclass
class AgentResult:
    """Outcome of an agent run."""
    content: str
    tools_used: List[str] = field(default_factory=list)
    invocations: List[ToolInvocation] = field(default_factory=list)
    iterations: int = 0
    stop_reason: str = "completed"  # completed | max_iterations
    messages: List[Dict[str, Any]] = field(default_factory=list)


def _build_tool_definitions(registry: Any, tool_names: List[str]) -> List[dict]:
    """Resolve skill names to OpenAI tool definitions, skipping unknown skills."""
    if registry is None or not tool_names:
        return []
    definitions = []
    for name in tool_names:
        skill = registry.get(name)
        if skill is not None:
            definitions.append(skill.to_tool_definition())
        else:
            logger.debug("Tool '%s' not found in skill registry; skipping", name)
    return definitions


def _parse_arguments(raw_args: Any) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parse tool-call arguments, which arrive as a JSON string from the model."""
    if raw_args is None or raw_args == "":
        return {}, None
    if isinstance(raw_args, dict):
        return raw_args, None
    try:
        parsed = json.loads(raw_args)
    except (json.JSONDecodeError, TypeError):
        return None, "Tool arguments were not valid JSON"
    if not isinstance(parsed, dict):
        return None, "Tool arguments must be a JSON object"
    return parsed, None


def _format_tool_content(invocation: ToolInvocation) -> str:
    """Serialize a tool result into the string the model sees as the tool message."""
    if not invocation.success:
        return json.dumps({"error": invocation.error or "Tool execution failed"})
    try:
        return json.dumps(invocation.result, default=str)
    except (TypeError, ValueError):
        return str(invocation.result)


async def _execute_tool_call(registry: Any, tool_call: Dict[str, Any]) -> ToolInvocation:
    """Execute one tool call against the skill registry, never raising."""
    func = tool_call.get("function", {}) or {}
    name = func.get("name", "") or "unknown"

    args, parse_error = _parse_arguments(func.get("arguments"))
    if parse_error is not None:
        return ToolInvocation(name=name, arguments={}, success=False, error=parse_error)

    if registry is None:
        return ToolInvocation(name=name, arguments=args, success=False,
                              error="Skill registry unavailable")

    try:
        result = await registry.execute(name, **args)
    except Exception as e:  # registry raises ValueError for unknown skills, etc.
        logger.warning("Tool '%s' execution raised: %s", name, e)
        return ToolInvocation(name=name, arguments=args, success=False, error=str(e))

    # Skills return a SkillResult (success/data/error); tolerate plain values too.
    success = getattr(result, "success", True)
    if success:
        data = getattr(result, "data", result)
        return ToolInvocation(name=name, arguments=args, success=True, result=data)
    return ToolInvocation(name=name, arguments=args, success=False,
                          error=getattr(result, "error", None) or "Tool execution failed")


async def run_agent_loop(
    messages: List[Dict[str, Any]],
    model: str,
    tool_names: List[str],
    *,
    registry: Any,
    llm_client: LLMClient,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AgentResult:
    """
    Drive a reason-act loop until the model answers or the iteration cap is hit.

    On each turn the model may emit ``tool_calls``; each is executed via the skill
    registry and its result is appended as a ``role="tool"`` message before the
    next turn. The loop ends when the model returns a message with no tool calls.
    """
    tool_definitions = _build_tool_definitions(registry, tool_names)
    working: List[Dict[str, Any]] = list(messages)
    invocations: List[ToolInvocation] = []
    tools_used: List[str] = []
    last_content = ""

    for iteration in range(1, max_iterations + 1):
        payload: Dict[str, Any] = {
            "model": model,
            "messages": working,
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tool_definitions:
            payload["tools"] = tool_definitions

        data = await llm_client(payload)
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message", {}) or {}
        if message.get("content"):
            last_content = message["content"]

        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return AgentResult(
                content=message.get("content") or "",
                tools_used=tools_used,
                invocations=invocations,
                iterations=iteration,
                stop_reason="completed",
                messages=working,
            )

        # Preserve the assistant turn (with its tool_calls) so tool results can
        # be correlated by the model on the next turn.
        working.append({
            "role": "assistant",
            "content": message.get("content") or "",
            "tool_calls": tool_calls,
        })

        for tool_call in tool_calls:
            invocation = await _execute_tool_call(registry, tool_call)
            invocations.append(invocation)
            tools_used.append(invocation.name)
            working.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id"),
                "name": invocation.name,
                "content": _format_tool_content(invocation),
            })

    logger.info("Agent loop hit max_iterations (%d); returning last content", max_iterations)
    return AgentResult(
        content=last_content,
        tools_used=tools_used,
        invocations=invocations,
        iterations=max_iterations,
        stop_reason="max_iterations",
        messages=working,
    )
