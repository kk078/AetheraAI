"""
Aethera AI - Model Cascade Module

Intelligent model routing with rate limit tracking and automatic failover.
Routes queries to the optimal model based on:
- Sensitivity (PHI/PII forces local)
- Task complexity and specialist requirements
- Current rate limit status across providers
- Historical performance and cost optimization

Model Cascade Order:
1. Ollama Cloud (primary brain - frontier models)
2. HuggingFace (overflow capacity)
3. Ollama Local (always available fallback)
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from collections import defaultdict

import redis.asyncio as redis


class UsageLevel(Enum):
    """Model usage levels for rate limit tracking."""
    L1_LIGHT = "L1-light"       # Local models, unlimited
    L2_MEDIUM = "L2-medium"     # Cloud medium usage
    L3_HEAVY = "L3-heavy"       # Cloud heavy usage
    L4_EXTRA_HEAVY = "L4-extra-heavy"  # Premium cloud models


class ProviderType(Enum):
    """LLM provider types."""
    OLLAMA_CLOUD = "ollama_cloud"
    OLLAMA_LOCAL = "ollama_local"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


@dataclass
class RateLimitStatus:
    """Current rate limit status for a provider."""
    provider: ProviderType
    current_usage: int
    limit: int
    reset_time: datetime
    percentage_used: float
    is_exhausted: bool
    recommended_action: str = ""


@dataclass
class ModelSelection:
    """Result of model selection process."""
    model_name: str
    provider: ProviderType
    reason: str
    fallback_chain: List[str] = field(default_factory=list)
    estimated_latency_ms: int = 0
    is_local: bool = False
    usage_level: UsageLevel = UsageLevel.L1_LIGHT


@dataclass
class CascadeConfig:
    """Configuration for model cascade."""
    # Rate limits
    ollama_cloud_session_limit: int = 100  # Per 5-hour session
    ollama_cloud_weekly_limit: int = 500   # Per week
    huggingface_daily_limit: int = 1000    # Per day

    # Session tracking
    session_start_time: Optional[datetime] = None
    session_duration_hours: int = 5
    weekly_reset_day: int = 0  # Monday (0=Monday, 6=Sunday)

    # Model preferences by task type
    specialist_model_map: Dict[str, str] = field(default_factory=dict)

    # Fallback order
    fallback_order: List[str] = field(default_factory=list)


class ModelCascade:
    """
    Intelligent model cascade with rate limit tracking.

    Routing Logic:
    ┌─────────────────────────────────────────────────────────────────┐
    │ PHI/PII DETECTED → ALWAYS aethera-local-fast (qwen3.5:4b GPU) │
    │                    Data NEVER leaves the machine               │
    └─────────────────────────────────────────────────────────────────┘

    For non-sensitive queries, route by task type:

    1. Simple/fast queries → aethera-local-fast (qwen3.5:4b GPU)
       - Code lookups, quick definitions, simple math
       - Instant response, zero cloud usage

    2. Healthcare analysis → aethera-cloud-brain (qwen3.5:122b)
       - Complex coding questions, denial analysis, appeals
       - Regulatory interpretation, contract analysis
       - Best quality, uses Level 3 cloud quota

    3. Deep reasoning → aethera-cloud-reason (deepseek-v4-flash)
       - Long document analysis (1M context window)
       - Multi-step research, literature review
       - Chain-of-thought reasoning tasks

    4. Coding tasks → aethera-cloud-coder (kimi-k2.6)
       - Code generation, debugging, architecture
       - Agentic coding workflows
       - Building Aethera features/plugins

    5. Tool calling / structured output → aethera-cloud-tools (gemma4:26b)
       - Document parsing, image/screenshot analysis
       - EDI parsing, form filling, structured extraction
       - Lower cloud usage (Level 2)

    6. Multi-agent debates → aethera-cloud-agent (nemotron-3-super)
       - When 2-3 specialists reason in parallel
       - Efficient: 120B MoE but only 12B active

    7. Medium queries → aethera-cloud-balanced (qwen3.5:35b)
       - Good enough for most queries, lower usage than 122b
       - Default for general conversation, drafting, summarization

    8. Overflow → hf-qwen-72b (HuggingFace free tier)
       - When Ollama Cloud session/weekly limit hit
       - Free, ~1000 req/day

    9. Last resort → aethera-local-smart (qwen3.5:9b CPU)
       - When ALL cloud is exhausted
       - Slower but capable, always available, unlimited
    """

    # Specialist to model mapping
    SPECIALIST_MODEL_MAP = {
        "healthcare_provider": "aethera-cloud-brain",
        "healthcare_payer": "aethera-cloud-brain",
        "healthcare_regulatory": "aethera-cloud-brain",
        "healthcare_clinical": "aethera-cloud-brain",
        "healthcare_analytics": "aethera-cloud-reason",
        "healthcare_it": "aethera-cloud-tools",
        "healthcare_pharmacy": "aethera-cloud-balanced",
        "healthcare_behavioral": "aethera-cloud-balanced",
        "healthcare_dental_vision": "aethera-cloud-balanced",
        "healthcare_workers_comp": "aethera-cloud-balanced",
        "software_engineering": "aethera-cloud-coder",
        "finance": "aethera-cloud-balanced",
        "legal": "aethera-cloud-brain",
        "media_marketing": "aethera-cloud-balanced",
        "research": "aethera-cloud-reason",
        "personal_assistant": "aethera-local-fast",
        "cloudflare_ops": "aethera-cloud-tools",
        "data_analytics": "aethera-cloud-reason",
        "general": "aethera-cloud-balanced",
    }

    # Model metadata
    MODEL_METADATA = {
        # Cloud models
        "aethera-cloud-brain": {
            "provider": ProviderType.OLLAMA_CLOUD,
            "usage_level": UsageLevel.L3_HEAVY,
            "latency_ms": 3000,
            "description": "Frontier 122B model - best for complex healthcare",
        },
        "aethera-cloud-reason": {
            "provider": ProviderType.OLLAMA_CLOUD,
            "usage_level": UsageLevel.L2_MEDIUM,
            "latency_ms": 4000,
            "description": "284B MoE reasoning model - 1M context",
        },
        "aethera-cloud-coder": {
            "provider": ProviderType.OLLAMA_CLOUD,
            "usage_level": UsageLevel.L3_HEAVY,
            "latency_ms": 3000,
            "description": "Best coding model - agentic, multimodal",
        },
        "aethera-cloud-tools": {
            "provider": ProviderType.OLLAMA_CLOUD,
            "usage_level": UsageLevel.L2_MEDIUM,
            "latency_ms": 2500,
            "description": "Tool calling + vision model",
        },
        "aethera-cloud-agent": {
            "provider": ProviderType.OLLAMA_CLOUD,
            "usage_level": UsageLevel.L2_MEDIUM,
            "latency_ms": 2500,
            "description": "Efficient MoE model for multi-agent",
        },
        "aethera-cloud-balanced": {
            "provider": ProviderType.OLLAMA_CLOUD,
            "usage_level": UsageLevel.L2_MEDIUM,
            "latency_ms": 2000,
            "description": "Balanced speed/intelligence",
        },
        "aethera-cloud-engineer": {
            "provider": ProviderType.OLLAMA_CLOUD,
            "usage_level": UsageLevel.L3_HEAVY,
            "latency_ms": 3000,
            "description": "Agentic engineering model",
        },
        # Local models
        "aethera-local-fast": {
            "provider": ProviderType.OLLAMA_LOCAL,
            "usage_level": UsageLevel.L1_LIGHT,
            "latency_ms": 500,
            "description": "Fast local GPU model (qwen3.5:4b)",
        },
        "aethera-local-tools": {
            "provider": ProviderType.OLLAMA_LOCAL,
            "usage_level": UsageLevel.L1_LIGHT,
            "latency_ms": 600,
            "description": "Local tool-calling model (gemma4:e2b)",
        },
        "aethera-local-smart": {
            "provider": ProviderType.OLLAMA_LOCAL,
            "usage_level": UsageLevel.L1_LIGHT,
            "latency_ms": 1500,
            "description": "Smart local CPU model (qwen3.5:9b)",
        },
        # HuggingFace overflow
        "hf-qwen-72b": {
            "provider": ProviderType.HUGGINGFACE,
            "usage_level": UsageLevel.L1_LIGHT,
            "latency_ms": 5000,
            "description": "HuggingFace free Qwen 72B",
        },
        "hf-mistral": {
            "provider": ProviderType.HUGGINGFACE,
            "usage_level": UsageLevel.L1_LIGHT,
            "latency_ms": 2000,
            "description": "HuggingFace free Mistral 7B",
        },
    }

    # Fallback chain for each model
    FALLBACK_CHAIN = {
        "aethera-cloud-brain": [
            "aethera-cloud-balanced",
            "aethera-cloud-reason",
            "hf-qwen-72b",
            "aethera-local-smart"
        ],
        "aethera-cloud-coder": [
            "aethera-cloud-engineer",
            "hf-qwen-72b",
            "aethera-local-smart"
        ],
        "aethera-cloud-tools": [
            "aethera-cloud-balanced",
            "aethera-local-tools",
            "aethera-local-smart"
        ],
        "aethera-cloud-reason": [
            "aethera-cloud-brain",
            "hf-qwen-72b",
            "aethera-local-smart"
        ],
        "aethera-cloud-agent": [
            "aethera-cloud-balanced",
            "aethera-cloud-tools",
            "aethera-local-smart"
        ],
        "aethera-cloud-engineer": [
            "aethera-cloud-coder",
            "aethera-cloud-balanced",
            "aethera-local-smart"
        ],
        "aethera-cloud-balanced": [
            "hf-qwen-72b",
            "aethera-local-tools",
            "aethera-local-smart"
        ],
        "aethera-local-fast": [
            "aethera-local-tools",
            "aethera-local-smart"
        ],
        "aethera-local-tools": [
            "aethera-local-fast",
            "aethera-local-smart"
        ],
        "aethera-local-smart": [
            "hf-qwen-72b",
            "hf-mistral"
        ],
        "hf-qwen-72b": [
            "hf-mistral",
            "aethera-local-smart"
        ],
        "hf-mistral": [
            "aethera-local-smart"
        ],
    }

    def __init__(self, redis_url: str = "redis://localhost:6379", config: Optional[CascadeConfig] = None):
        self.redis_url = redis_url
        self.config = config or CascadeConfig()
        self.redis_client: Optional[redis.Redis] = None
        self._session_start: Optional[datetime] = None
        self._weekly_start: Optional[datetime] = None

    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        except Exception as e:
            # Redis is optional - continue without it
            print(f"Warning: Redis not available, using in-memory tracking: {e}")
            self.redis_client = None

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()

    async def _increment_usage(self, provider: ProviderType, key: str) -> int:
        """Increment usage counter and return new value."""
        if not self.redis_client:
            return 0  # No tracking without Redis

        try:
            pipe = self.redis_client.pipeline()
            pipe.incr(f"aethera:usage:{provider.value}:{key}")

            # Set expiration if key is new
            if await self.redis_client.ttl(f"aethera:usage:{provider.value}:{key}") == -1:
                if key == "session":
                    pipe.expire(f"aethera:usage:{provider.value}:{key}", 5 * 3600)
                elif key == "weekly":
                    pipe.expire(f"aethera:usage:{provider.value}:{key}", 7 * 24 * 3600)
                elif key == "daily":
                    pipe.expire(f"aethera:usage:{provider.value}:{key}", 24 * 3600)

            await pipe.execute()
            result = await self.redis_client.get(f"aethera:usage:{provider.value}:{key}")
            return int(result) if result else 0
        except Exception:
            return 0

    async def _get_usage(self, provider: ProviderType, key: str) -> int:
        """Get current usage count."""
        if not self.redis_client:
            return 0

        try:
            result = await self.redis_client.get(f"aethera:usage:{provider.value}:{key}")
            return int(result) if result else 0
        except Exception:
            return 0

    async def check_rate_limit(
        self,
        provider: ProviderType,
        model_name: str
    ) -> tuple[bool, RateLimitStatus]:
        """
        Check if provider has available rate limit capacity.

        Returns:
            Tuple of (is_available, RateLimitStatus)
        """
        now = datetime.now()

        # Initialize session tracking if needed
        if self._session_start is None:
            self._session_start = now

        # Calculate reset times
        session_reset = self._session_start + timedelta(hours=5)
        weekly_reset = self._get_next_weekly_reset(now)
        daily_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

        # Get usage based on provider
        if provider == ProviderType.OLLAMA_CLOUD:
            session_usage = await self._get_usage(provider, "session")
            weekly_usage = await self._get_usage(provider, "weekly")
            limit = min(
                self._get_remaining_session_limit(session_usage),
                self._get_remaining_weekly_limit(weekly_usage)
            )
            is_exhausted = limit <= 0
            reset_time = min(session_reset, weekly_reset)
            percentage = max(
                (session_usage / self.config.ollama_cloud_session_limit) * 100,
                (weekly_usage / self.config.ollama_cloud_weekly_limit) * 100
            )

        elif provider == ProviderType.HUGGINGFACE:
            daily_usage = await self._get_usage(provider, "daily")
            limit = self.config.huggingface_daily_limit - daily_usage
            is_exhausted = limit <= 0
            reset_time = daily_reset
            percentage = (daily_usage / self.config.huggingface_daily_limit) * 100

        else:  # Local models - unlimited
            return True, RateLimitStatus(
                provider=provider,
                current_usage=0,
                limit=0,
                reset_time=now,
                percentage_used=0,
                is_exhausted=False,
                recommended_action="Local model - unlimited usage"
            )

        # Determine recommended action
        if is_exhausted:
            action = f"Rate limit exhausted. Switch to fallback model."
        elif percentage > 80:
            action = f"Warning: {percentage:.0f}% of quota used. Consider using local models."
        else:
            action = "OK to proceed"

        status = RateLimitStatus(
            provider=provider,
            current_usage=await self._get_usage(provider, "session" if provider == ProviderType.OLLAMA_CLOUD else "daily"),
            limit=limit,
            reset_time=reset_time,
            percentage_used=percentage,
            is_exhausted=is_exhausted,
            recommended_action=action
        )

        return not is_exhausted, status

    def _get_next_weekly_reset(self, now: datetime) -> datetime:
        """Get next weekly reset time (Monday 00:00)."""
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0 and now.hour >= 0:
            days_until_monday = 7
        return (now + timedelta(days=days_until_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def _get_remaining_session_limit(self, current_usage: int) -> int:
        """Get remaining session limit."""
        return max(0, self.config.ollama_cloud_session_limit - current_usage)

    def _get_remaining_weekly_limit(self, current_usage: int) -> int:
        """Get remaining weekly limit."""
        return max(0, self.config.ollama_cloud_weekly_limit - current_usage)

    async def select_model(
        self,
        specialist: str,
        is_phi: bool = False,
        is_pii: bool = False,
        complexity: str = "medium",
        force_model: Optional[str] = None
    ) -> ModelSelection:
        """
        Select optimal model based on specialist, sensitivity, and rate limits.

        Args:
            specialist: Specialist name handling the query
            is_phi: Whether query contains PHI
            is_pii: Whether query contains PII
            complexity: Query complexity (simple, medium, complex)
            force_model: Override model selection

        Returns:
            ModelSelection with chosen model and metadata
        """
        # Force local for PHI/PII
        if is_phi or is_pii:
            return ModelSelection(
                model_name="aethera-local-fast",
                provider=ProviderType.OLLAMA_LOCAL,
                reason="PHI/PII detected - routing to local model for privacy",
                fallback_chain=["aethera-local-tools", "aethera-local-smart"],
                is_local=True,
                usage_level=UsageLevel.L1_LIGHT,
                estimated_latency_ms=500
            )

        # Check for user preference override
        preferred_model = os.getenv("PREFERRED_MODEL", "").strip()
        if preferred_model and preferred_model in self.MODEL_METADATA:
            metadata = self.MODEL_METADATA[preferred_model]
            # Verify it's not a cloud model with exhausted quota
            if metadata["provider"] == ProviderType.OLLAMA_LOCAL:
                return ModelSelection(
                    model_name=preferred_model,
                    provider=metadata["provider"],
                    reason=f"User preference override: {preferred_model}",
                    fallback_chain=self.FALLBACK_CHAIN.get(preferred_model, []),
                    estimated_latency_ms=metadata["latency_ms"],
                    is_local=True,
                    usage_level=metadata["usage_level"]
                )
            # For cloud models, still check availability
            is_available, status = await self.check_rate_limit(metadata["provider"], preferred_model)
            if is_available:
                if metadata["provider"] == ProviderType.OLLAMA_CLOUD:
                    await self._increment_usage(metadata["provider"], "session")
                    await self._increment_usage(metadata["provider"], "weekly")
                elif metadata["provider"] == ProviderType.HUGGINGFACE:
                    await self._increment_usage(metadata["provider"], "daily")
                return ModelSelection(
                    model_name=preferred_model,
                    provider=metadata["provider"],
                    reason=f"User preference override: {preferred_model}",
                    fallback_chain=self.FALLBACK_CHAIN.get(preferred_model, []),
                    estimated_latency_ms=metadata["latency_ms"],
                    is_local=metadata["provider"] == ProviderType.OLLAMA_LOCAL,
                    usage_level=metadata["usage_level"]
                )
            # Preference model not available, continue with normal selection

        # Handle forced model
        if force_model and force_model in self.MODEL_METADATA:
            metadata = self.MODEL_METADATA[force_model]
            return ModelSelection(
                model_name=force_model,
                provider=metadata["provider"],
                reason=f"User forced model: {force_model}",
                fallback_chain=self.FALLBACK_CHAIN.get(force_model, []),
                estimated_latency_ms=metadata["latency_ms"],
                is_local=metadata["provider"] == ProviderType.OLLAMA_LOCAL,
                usage_level=metadata["usage_level"]
            )

        # Get default model for specialist
        default_model = self.SPECIALIST_MODEL_MAP.get(
            specialist, "aethera-cloud-balanced"
        )

        # Adjust for complexity
        if complexity == "simple":
            default_model = "aethera-local-fast"
        elif complexity == "complex" and default_model == "aethera-cloud-balanced":
            default_model = "aethera-cloud-brain"

        # Check rate limits and find available model
        selected_model = await self._find_available_model(
            starting_model=default_model
        )

        metadata = self.MODEL_METADATA.get(selected_model, {})

        return ModelSelection(
            model_name=selected_model,
            provider=metadata.get("provider", ProviderType.OLLAMA_LOCAL),
            reason=f"Selected based on specialist '{specialist}' and current rate limits",
            fallback_chain=self.FALLBACK_CHAIN.get(selected_model, []),
            estimated_latency_ms=metadata.get("latency_ms", 2000),
            is_local=metadata.get("provider") == ProviderType.OLLAMA_LOCAL,
            usage_level=metadata.get("usage_level", UsageLevel.L1_LIGHT)
        )

    async def _find_available_model(
        self,
        starting_model: str,
        tried: Optional[List[str]] = None,
        _depth: int = 0
    ) -> str:
        """
        Find available model following fallback chain.

        Checks rate limits and falls back to next model if exhausted.
        Uses depth limit to prevent infinite recursion.
        """
        if tried is None:
            tried = []

        # Depth limit to prevent infinite recursion
        if _depth > 15:
            return "aethera-local-smart"

        if starting_model in tried:
            return "aethera-local-smart"

        tried.append(starting_model)

        if starting_model not in self.MODEL_METADATA:
            return "aethera-local-smart"

        metadata = self.MODEL_METADATA[starting_model]
        provider = metadata["provider"]

        # Local models are always available
        if provider == ProviderType.OLLAMA_LOCAL:
            return starting_model

        # Check rate limit for cloud/HF models
        is_available, _ = await self.check_rate_limit(provider, starting_model)

        if is_available:
            # Increment usage counter
            if provider == ProviderType.OLLAMA_CLOUD:
                await self._increment_usage(provider, "session")
                await self._increment_usage(provider, "weekly")
            elif provider == ProviderType.HUGGINGFACE:
                await self._increment_usage(provider, "daily")
            return starting_model

        # Try fallback chain
        fallbacks = self.FALLBACK_CHAIN.get(starting_model, ["aethera-local-smart"])
        for fallback in fallbacks:
            if fallback not in tried:
                return await self._find_available_model(fallback, tried, _depth + 1)

        # Ultimate fallback
        return "aethera-local-smart"

    async def get_usage_summary(self) -> Dict[str, Any]:
        """Get current usage summary across all providers."""
        if not self.redis_client:
            return {
                "ollama_cloud": {"session": 0, "weekly": 0, "status": "tracking disabled"},
                "huggingface": {"daily": 0, "status": "tracking disabled"},
                "local": {"unlimited": True}
            }

        ollama_session = await self._get_usage(ProviderType.OLLAMA_CLOUD, "session")
        ollama_weekly = await self._get_usage(ProviderType.OLLAMA_CLOUD, "weekly")
        hf_daily = await self._get_usage(ProviderType.HUGGINGFACE, "daily")

        return {
            "ollama_cloud": {
                "session": {
                    "used": ollama_session,
                    "limit": self.config.ollama_cloud_session_limit,
                    "remaining": self.config.ollama_cloud_session_limit - ollama_session,
                    "percentage": (ollama_session / self.config.ollama_cloud_session_limit) * 100
                },
                "weekly": {
                    "used": ollama_weekly,
                    "limit": self.config.ollama_cloud_weekly_limit,
                    "remaining": self.config.ollama_cloud_weekly_limit - ollama_weekly,
                    "percentage": (ollama_weekly / self.config.ollama_cloud_weekly_limit) * 100
                }
            },
            "huggingface": {
                "daily": {
                    "used": hf_daily,
                    "limit": self.config.huggingface_daily_limit,
                    "remaining": self.config.huggingface_daily_limit - hf_daily,
                    "percentage": (hf_daily / self.config.huggingface_daily_limit) * 100
                }
            },
            "local": {
                "unlimited": True,
                "models": ["aethera-local-fast", "aethera-local-tools", "aethera-local-smart"]
            }
        }

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific model."""
        if model_name not in self.MODEL_METADATA:
            return None

        metadata = self.MODEL_METADATA[model_name]
        return {
            "model_name": model_name,
            "provider": metadata["provider"].value,
            "usage_level": metadata["usage_level"].value,
            "estimated_latency_ms": metadata["latency_ms"],
            "description": metadata["description"],
            "fallback_chain": self.FALLBACK_CHAIN.get(model_name, [])
        }

    def list_available_models(self) -> List[Dict[str, Any]]:
        """List all available models with metadata."""
        return [
            {
                "model_name": name,
                **{k: v.value if isinstance(v, Enum) else v for k, v in metadata.items()}
            }
            for name, metadata in self.MODEL_METADATA.items()
        ]


# Singleton instance
_cascade: Optional[ModelCascade] = None


def get_cascade(redis_url: str = "redis://localhost:6379") -> ModelCascade:
    """Get or create the singleton cascade instance."""
    global _cascade
    if _cascade is None:
        _cascade = ModelCascade(redis_url)
    return _cascade


async def get_or_initialize_cascade(redis_url: str = "redis://localhost:6379") -> ModelCascade:
    """Get cascade instance, initializing if needed."""
    cascade = get_cascade(redis_url)
    if cascade.redis_client is None:
        await cascade.initialize()
    return cascade
