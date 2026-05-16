"""
Explainable AI layer — logs the reasoning chain for every response.

Every Aethera response carries an immutable audit trail showing:
1. What sensitivity was detected (PHI/PII)
2. Which specialist was selected and why
3. Which model was chosen and why
4. Which tools/skills were invoked
5. What RAG context was retrieved
6. What confidence was assigned
7. How long each step took

This module structures that reasoning chain for both the UI
(expandable "Show Reasoning" panel) and the audit log.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class StepType(str, Enum):
    SENSITIVITY_CHECK = "sensitivity_check"
    INTENT_CLASSIFICATION = "intent_classification"
    SPECIALIST_SELECTION = "specialist_selection"
    MODEL_SELECTION = "model_selection"
    TOOL_INVOCATION = "tool_invocation"
    RAG_RETRIEVAL = "rag_retrieval"
    LLM_CALL = "llm_call"
    CONFIDENCE_SCORING = "confidence_scoring"
    RESPONSE_GENERATION = "response_generation"
    PHI_REDACTION = "phi_redaction"


class StepStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ReasoningStep:
    step_type: StepType
    status: StepStatus = StepStatus.STARTED
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    duration_ms: int | None = None
    input_summary: str = ""
    output_summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def complete(self, output_summary: str = "", details: dict | None = None):
        self.status = StepStatus.COMPLETED
        self.completed_at = time.time()
        self.duration_ms = int((self.completed_at - self.started_at) * 1000)
        self.output_summary = output_summary
        if details:
            self.details.update(details)

    def fail(self, error: str):
        self.status = StepStatus.FAILED
        self.completed_at = time.time()
        self.duration_ms = int((self.completed_at - self.started_at) * 1000)
        self.error = error

    def skip(self, reason: str = ""):
        self.status = StepStatus.SKIPPED
        self.completed_at = time.time()
        self.duration_ms = 0
        self.output_summary = reason

    def to_dict(self) -> dict:
        return {
            "step_type": self.step_type.value,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "input_summary": self.input_summary[:200],
            "output_summary": self.output_summary[:500],
            "details": self.details,
            "error": self.error,
        }


@dataclass
class ReasoningChain:
    """Complete reasoning chain for a single user query."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    steps: list[ReasoningStep] = field(default_factory=list)
    total_duration_ms: int = 0
    final_specialist: str = ""
    final_model: str = ""
    final_confidence: float = 0.0
    phi_detected: bool = False
    phi_types: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    rag_sources: list[str] = field(default_factory=list)

    def add_step(self, step_type: StepType, input_summary: str = "", details: dict | None = None) -> ReasoningStep:
        step = ReasoningStep(
            step_type=step_type,
            input_summary=input_summary[:200],
            details=details or {},
        )
        self.steps.append(step)
        return step

    def finalize(self):
        """Calculate total duration and extract summary fields."""
        completed = [s for s in self.steps if s.completed_at]
        if completed:
            self.total_duration_ms = int((completed[-1].completed_at - self.steps[0].started_at) * 1000)

        for step in self.steps:
            if step.step_type == StepType.SPECIALIST_SELECTION and step.status == StepStatus.COMPLETED:
                self.final_specialist = step.details.get("specialist", "")
            if step.step_type == StepType.MODEL_SELECTION and step.status == StepStatus.COMPLETED:
                self.final_model = step.details.get("model", "")
            if step.step_type == StepType.CONFIDENCE_SCORING and step.status == StepStatus.COMPLETED:
                self.final_confidence = step.details.get("confidence", 0.0)
            if step.step_type == StepType.SENSITIVITY_CHECK and step.status == StepStatus.COMPLETED:
                self.phi_detected = step.details.get("phi_detected", False)
                self.phi_types = step.details.get("phi_types", [])
            if step.step_type == StepType.TOOL_INVOCATION and step.status == StepStatus.COMPLETED:
                tool_name = step.details.get("tool_name", "")
                if tool_name:
                    self.tools_used.append(tool_name)
            if step.step_type == StepType.RAG_RETRIEVAL and step.status == StepStatus.COMPLETED:
                sources = step.details.get("sources", [])
                self.rag_sources.extend(sources)

    def to_dict(self) -> dict:
        self.finalize()
        return {
            "id": self.id,
            "query": self.query[:200],
            "created_at": self.created_at.isoformat(),
            "total_duration_ms": self.total_duration_ms,
            "specialist": self.final_specialist,
            "model": self.final_model,
            "confidence": self.final_confidence,
            "phi_detected": self.phi_detected,
            "phi_types": self.phi_types,
            "tools_used": self.tools_used,
            "rag_sources": self.rag_sources,
            "steps": [s.to_dict() for s in self.steps],
        }

    def to_summary(self) -> str:
        """Human-readable one-paragraph summary of the reasoning chain."""
        self.finalize()
        parts = []
        parts.append(f"Query routed to **{self.final_specialist}** specialist")
        if self.phi_detected:
            parts.append(f"PHI detected ({', '.join(self.phi_types)}) — forced local model")
        parts.append(f"using **{self.final_model}**")
        if self.tools_used:
            parts.append(f"with tools: {', '.join(self.tools_used)}")
        parts.append(f"Confidence: {self.final_confidence:.0%}")
        parts.append(f"in {self.total_duration_ms}ms")
        return " ".join(parts) + "."


class ExplainerStore:
    """In-memory store of recent reasoning chains with optional persistence."""

    def __init__(self, max_chains: int = 1000):
        self._chains: dict[str, ReasoningChain] = {}
        self._max_chains = max_chains

    def create_chain(self, query: str) -> ReasoningChain:
        chain = ReasoningChain(query=query)
        self._chains[chain.id] = chain
        if len(self._chains) > self._max_chains:
            oldest = list(self._chains.keys())[0]
            del self._chains[oldest]
        return chain

    def get_chain(self, chain_id: str) -> ReasoningChain | None:
        return self._chains.get(chain_id)

    def get_recent(self, limit: int = 20) -> list[dict]:
        chains = sorted(self._chains.values(), key=lambda c: c.created_at, reverse=True)[:limit]
        return [c.to_dict() for c in chains]

    def get_summary(self, chain_id: str) -> str | None:
        chain = self._chains.get(chain_id)
        return chain.to_summary() if chain else None


# Global explainer store
_explainer_store = ExplainerStore()


def get_explainer_store() -> ExplainerStore:
    return _explainer_store