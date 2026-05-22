"""
Tests for the agentic reason-act loop (orchestrator/agent.py).

The LLM and skill registry are faked so the loop is exercised end to end
without a live model or real skills.
"""

from dataclasses import dataclass
from typing import Any, Optional

import pytest

from orchestrator.agent import (
    AgentResult,
    ToolInvocation,
    run_agent_loop,
    _parse_arguments,
    _format_tool_content,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

@dataclass
class FakeSkillResult:
    success: bool
    data: Any = None
    error: Optional[str] = None


class FakeSkill:
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

    def to_tool_definition(self):
        return {
            "type": "function",
            "function": {"name": self._name, "description": "fake", "parameters": {}},
        }


class FakeRegistry:
    """Registry whose execute() returns queued results keyed by skill name."""

    def __init__(self, skills=None, results=None, raises=None):
        self._skills = {n: FakeSkill(n) for n in (skills or [])}
        self._results = results or {}
        self._raises = raises or {}
        self.calls = []

    def get(self, name):
        return self._skills.get(name)

    async def execute(self, name, **kwargs):
        self.calls.append((name, kwargs))
        if name in self._raises:
            raise self._raises[name]
        return self._results.get(name, FakeSkillResult(success=True, data={"ok": name}))


class ScriptedLLM:
    """Returns a queued list of assistant messages, one per call."""

    def __init__(self, messages):
        self._messages = list(messages)
        self.payloads = []

    async def __call__(self, payload):
        self.payloads.append(payload)
        message = self._messages.pop(0)
        return {"choices": [{"message": message}]}


def _tool_call(call_id, name, arguments):
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": arguments}}


# ---------------------------------------------------------------------------
# Loop behavior
# ---------------------------------------------------------------------------

async def test_returns_content_when_no_tool_calls():
    llm = ScriptedLLM([{"content": "Hello, how can I help with your claim?"}])
    result = await run_agent_loop(
        messages=[{"role": "user", "content": "hi"}],
        model="aethera-cloud-brain",
        tool_names=[],
        registry=FakeRegistry(),
        llm_client=llm,
    )
    assert isinstance(result, AgentResult)
    assert result.content == "Hello, how can I help with your claim?"
    assert result.tools_used == []
    assert result.iterations == 1
    assert result.stop_reason == "completed"


async def test_executes_tool_then_returns_final_answer():
    registry = FakeRegistry(
        skills=["code_lookup"],
        results={"code_lookup": FakeSkillResult(success=True, data={"code": "E11.9"})},
    )
    llm = ScriptedLLM([
        {"content": "", "tool_calls": [_tool_call("c1", "code_lookup", '{"query": "diabetes"}')]},
        {"content": "The code for type 2 diabetes is E11.9."},
    ])
    result = await run_agent_loop(
        messages=[{"role": "user", "content": "what is the code for diabetes"}],
        model="aethera-cloud-brain",
        tool_names=["code_lookup"],
        registry=registry,
        llm_client=llm,
    )
    assert result.content == "The code for type 2 diabetes is E11.9."
    assert result.tools_used == ["code_lookup"]
    assert result.iterations == 2
    assert registry.calls == [("code_lookup", {"query": "diabetes"})]

    # Tool definitions were advertised to the model on the first call.
    assert "tools" in llm.payloads[0]
    # The tool result was fed back as a role="tool" message.
    tool_messages = [m for m in result.messages if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "c1"


async def test_chains_multiple_tools_across_turns():
    registry = FakeRegistry(
        skills=["eligibility_checker", "claim_scrubber"],
        results={
            "eligibility_checker": FakeSkillResult(success=True, data={"eligible": True}),
            "claim_scrubber": FakeSkillResult(success=True, data={"clean": True}),
        },
    )
    llm = ScriptedLLM([
        {"content": "", "tool_calls": [_tool_call("c1", "eligibility_checker", "{}")]},
        {"content": "", "tool_calls": [_tool_call("c2", "claim_scrubber", "{}")]},
        {"content": "Eligible and the claim is clean."},
    ])
    result = await run_agent_loop(
        messages=[{"role": "user", "content": "process this claim"}],
        model="aethera-cloud-brain",
        tool_names=["eligibility_checker", "claim_scrubber"],
        registry=registry,
        llm_client=llm,
    )
    assert result.tools_used == ["eligibility_checker", "claim_scrubber"]
    assert result.iterations == 3
    assert result.stop_reason == "completed"


async def test_failed_tool_is_reported_to_model_and_loop_continues():
    registry = FakeRegistry(
        skills=["denial_analyzer"],
        results={"denial_analyzer": FakeSkillResult(success=False, error="payer API down")},
    )
    llm = ScriptedLLM([
        {"content": "", "tool_calls": [_tool_call("c1", "denial_analyzer", "{}")]},
        {"content": "I couldn't analyze the denial right now."},
    ])
    result = await run_agent_loop(
        messages=[{"role": "user", "content": "analyze denial"}],
        model="aethera-cloud-brain",
        tool_names=["denial_analyzer"],
        registry=registry,
        llm_client=llm,
    )
    assert result.invocations[0].success is False
    assert result.invocations[0].error == "payer API down"
    tool_msg = [m for m in result.messages if m.get("role") == "tool"][0]
    assert "payer API down" in tool_msg["content"]
    assert result.content == "I couldn't analyze the denial right now."


async def test_registry_exception_is_caught():
    registry = FakeRegistry(
        skills=["code_lookup"],
        raises={"code_lookup": ValueError("Skill not found: code_lookup")},
    )
    llm = ScriptedLLM([
        {"content": "", "tool_calls": [_tool_call("c1", "code_lookup", "{}")]},
        {"content": "done"},
    ])
    result = await run_agent_loop(
        messages=[{"role": "user", "content": "x"}],
        model="m",
        tool_names=["code_lookup"],
        registry=registry,
        llm_client=llm,
    )
    assert result.invocations[0].success is False
    assert "Skill not found" in result.invocations[0].error


async def test_invalid_argument_json_does_not_call_skill():
    registry = FakeRegistry(skills=["code_lookup"])
    llm = ScriptedLLM([
        {"content": "", "tool_calls": [_tool_call("c1", "code_lookup", "{not json}")]},
        {"content": "recovered"},
    ])
    result = await run_agent_loop(
        messages=[{"role": "user", "content": "x"}],
        model="m",
        tool_names=["code_lookup"],
        registry=registry,
        llm_client=llm,
    )
    assert registry.calls == []  # skill never executed
    assert result.invocations[0].success is False
    assert result.content == "recovered"


async def test_max_iterations_cap_stops_infinite_tool_loop():
    registry = FakeRegistry(skills=["code_lookup"])
    # Model always asks for another tool call → would loop forever without a cap.
    always_tool = {"content": "thinking",
                   "tool_calls": [_tool_call("c", "code_lookup", "{}")]}
    llm = ScriptedLLM([always_tool] * 10)
    result = await run_agent_loop(
        messages=[{"role": "user", "content": "x"}],
        model="m",
        tool_names=["code_lookup"],
        registry=registry,
        llm_client=llm,
        max_iterations=3,
    )
    assert result.stop_reason == "max_iterations"
    assert result.iterations == 3
    assert len(registry.calls) == 3
    assert result.content == "thinking"


async def test_unknown_tool_name_is_skipped_in_definitions():
    registry = FakeRegistry(skills=["code_lookup"])
    llm = ScriptedLLM([{"content": "hi"}])
    await run_agent_loop(
        messages=[{"role": "user", "content": "x"}],
        model="m",
        tool_names=["code_lookup", "does_not_exist"],
        registry=registry,
        llm_client=llm,
    )
    advertised = [t["function"]["name"] for t in llm.payloads[0]["tools"]]
    assert advertised == ["code_lookup"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def test_parse_arguments_variants():
    assert _parse_arguments('{"a": 1}') == ({"a": 1}, None)
    assert _parse_arguments({"a": 1}) == ({"a": 1}, None)
    assert _parse_arguments("") == ({}, None)
    assert _parse_arguments(None) == ({}, None)
    parsed, err = _parse_arguments("{bad}")
    assert parsed is None and err is not None
    parsed, err = _parse_arguments("[1, 2]")
    assert parsed is None and err is not None


def test_format_tool_content():
    ok = ToolInvocation(name="t", arguments={}, success=True, result={"x": 1})
    assert _format_tool_content(ok) == '{"x": 1}'
    bad = ToolInvocation(name="t", arguments={}, success=False, error="boom")
    assert "boom" in _format_tool_content(bad)
