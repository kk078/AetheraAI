"""
Aethera AI - Multi-Agent Reasoning

Coordinates multiple specialist agents for complex queries requiring diverse expertise.
Uses LLM-based synthesis to produce integrated multi-perspective responses.
"""
import asyncio
import logging
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger("aethera.multi_agent")


@dataclass
class AgentResponse:
    """Response from a specialist agent."""
    specialist: str
    content: str
    confidence: float
    reasoning: str
    sources: List[str]


class MultiAgentCoordinator:
    """
    Coordinates multiple specialist agents for complex queries.

    Use cases:
    - Complex medical billing + regulatory questions
    - Clinical + coding + compliance multi-faceted queries
    - Cross-domain analysis requiring multiple perspectives
    """

    def __init__(self):
        self.specialists = [
            "healthcare_provider",
            "healthcare_payer",
            "healthcare_regulatory",
            "healthcare_clinical",
            "finance",
            "legal",
        ]
        self._litellm_url = os.getenv("LITELLM_URL", "http://litellm:4000")
        self._model = os.getenv("MULTI_AGENT_MODEL", "aethera-cloud-agent")

    async def coordinate(
        self,
        query: str,
        context: Optional[Dict] = None,
        max_agents: int = 3,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Coordinate multiple specialists on a complex query.

        Args:
            query: The user query
            context: Additional context (user preferences, sensitivity, etc.)
            max_agents: Maximum number of specialists to consult
            conversation_history: Prior messages for continuity

        Returns:
            Synthesized response with multiple perspectives
        """
        # Select relevant specialists based on query
        relevant_specialists = self._select_specialists(query, max_agents)

        if not relevant_specialists:
            relevant_specialists = self.specialists[:2]

        # Query each specialist in parallel
        tasks = [
            self._query_specialist(specialist, query, context, conversation_history)
            for specialist in relevant_specialists
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_responses = []
        for r in responses:
            if isinstance(r, Exception):
                logger.warning(f"Specialist query failed: {r}")
            elif isinstance(r, AgentResponse):
                valid_responses.append(r)

        if not valid_responses:
            return {
                "content": "Unable to coordinate specialist responses. Please try again.",
                "specialists_consulted": [],
                "perspectives": [],
                "average_confidence": 0.0,
                "synthesis": None,
            }

        # Synthesize responses using LLM
        synthesis = await self._synthesize_with_llm(valid_responses, query, context)

        return {
            "content": synthesis,
            "specialists_consulted": [r.specialist for r in valid_responses],
            "perspectives": [
                {"specialist": r.specialist, "content": r.content, "confidence": r.confidence}
                for r in valid_responses
            ],
            "average_confidence": sum(r.confidence for r in valid_responses) / len(valid_responses),
        }

    def _select_specialists(self, query: str, max_agents: int) -> List[str]:
        """Select relevant specialists based on query keywords."""
        query_lower = query.lower()

        keyword_map = {
            "healthcare_provider": ["claim", "billing", "revenue", "coding", "cpt", "icd", "drg", "fee schedule"],
            "healthcare_payer": ["coverage", "prior auth", "adjudication", "medicare", "medicaid", "denial", "appeal"],
            "healthcare_regulatory": ["hipaa", "compliance", "regulation", "cms", "stark", "anti-kickback", "oig"],
            "healthcare_clinical": ["diagnosis", "treatment", "drug", "medication", "clinical", "patient", "dosage"],
            "finance": ["payment", "reimbursement", "fee", "cost", "financial", "tax", "deductible"],
            "legal": ["liability", "malpractice", "contract", "privacy", "gdpr", "consent", "litigation"],
        }

        scores = {}
        for specialist, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                scores[specialist] = score

        sorted_specs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [spec for spec, _ in sorted_specs[:max_agents]]

    async def _query_specialist(
        self,
        specialist: str,
        query: str,
        context: Optional[Dict],
        conversation_history: Optional[List[Dict]],
    ) -> AgentResponse:
        """Query a single specialist via the LLM with its system prompt."""
        try:
            import importlib
            import httpx

            module_name = f"specialists.{specialist}"
            system_prompt = ""
            try:
                module = importlib.import_module(module_name)
                system_prompt = getattr(module, "SYSTEM_PROMPT", "")
            except (ImportError, AttributeError):
                pass

            if not system_prompt:
                system_prompt = f"You are Aethera's {specialist.replace('_', ' ')} specialist. Provide a focused analysis from your domain expertise."

            # Inject context if available
            if context:
                ctx_parts = []
                if context.get("sensitivity"):
                    ctx_parts.append(f"Sensitivity level: {context['sensitivity']}")
                if context.get("user_preferences"):
                    ctx_parts.append(f"User preferences: {context['user_preferences']}")
                if ctx_parts:
                    system_prompt += "\n\nContext: " + "; ".join(ctx_parts)

            messages = [{"role": "system", "content": system_prompt}]

            # Include conversation history for continuity
            if conversation_history:
                for msg in conversation_history[-6:]:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role in ("user", "assistant") and content:
                        messages.append({"role": role, "content": content})

            messages.append({"role": "user", "content": query})

            payload = {
                "model": self._model,
                "messages": messages,
                "temperature": 0.5,
                "max_tokens": 2048,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._litellm_url}/v1/chat/completions",
                    json=payload,
                    timeout=60,
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return AgentResponse(
                        specialist=specialist,
                        content=content,
                        confidence=0.7,
                        reasoning=f"LLM response from {specialist} perspective",
                        sources=[],
                    )
                else:
                    logger.warning(f"LLM call failed for {specialist}: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error querying specialist {specialist}: {e}")

        return AgentResponse(
            specialist=specialist,
            content=f"[{specialist}] Analysis unavailable",
            confidence=0.0,
            reasoning=f"Error querying {specialist}",
            sources=[],
        )

    async def _synthesize_with_llm(
        self,
        responses: List[AgentResponse],
        query: str,
        context: Optional[Dict],
    ) -> str:
        """Use LLM to synthesize multiple specialist perspectives."""
        if len(responses) == 1:
            return responses[0].content

        import httpx

        perspectives = "\n\n".join(
            f"**{r.specialist.replace('_', ' ').title()}**:\n{r.content}"
            for r in responses
        )

        synthesis_prompt = (
            "You are an expert medical billing and healthcare analyst synthesizing multiple specialist perspectives. "
            "Create a comprehensive, well-organized response that integrates the insights from each specialist below. "
            "Highlight areas of agreement and disagreement. Prioritize actionable recommendations. "
            "Use clear headers and bullet points.\n\n"
            f"ORIGINAL QUESTION: {query}\n\n"
            f"SPECIALIST PERSPECTIVES:\n{perspectives}\n\n"
            "Provide an integrated analysis:"
        )

        messages = [{"role": "user", "content": synthesis_prompt}]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._litellm_url}/v1/chat/completions",
                    json={
                        "model": self._model,
                        "messages": messages,
                        "temperature": 0.4,
                        "max_tokens": 4096,
                    },
                    timeout=90,
                )
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Synthesis LLM call failed: {e}")

        # Fallback: concatenate perspectives
        parts = ["Based on analysis from multiple specialists:\n"]
        for r in responses:
            parts.append(f"\n**{r.specialist.replace('_', ' ').title()} Perspective**:")
            parts.append(r.content)
        parts.append("\n\n**Integrated Analysis**:")
        parts.append("The above perspectives provide a comprehensive view of this complex issue.")
        return "\n".join(parts)


# Singleton instance
_coordinator: Optional[MultiAgentCoordinator] = None


def get_coordinator() -> MultiAgentCoordinator:
    """Get the multi-agent coordinator."""
    global _coordinator
    if _coordinator is None:
        _coordinator = MultiAgentCoordinator()
    return _coordinator