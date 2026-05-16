"""
Aethera AI - Specialists Package

Domain expert modules for routing queries to specialized knowledge areas.
Each specialist has a complete system prompt and tool definitions.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import importlib
import logging

logger = logging.getLogger("aethera.specialists")


@dataclass
class SpecialistConfig:
    """Configuration for a specialist."""
    name: str
    display_name: str
    description: str
    color: str
    default_model: str
    keywords: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    priority: int = 3
    enabled: bool = True
    system_prompt: str = ""
    category: str = "general"


# Specialist registry - maps name to config
SPECIALISTS: Dict[str, SpecialistConfig] = {}


def register_specialist(config: SpecialistConfig) -> SpecialistConfig:
    """Register a specialist configuration."""
    SPECIALISTS[config.name] = config
    return config


def get_specialist(name: str) -> Optional[SpecialistConfig]:
    """Get specialist by name."""
    return SPECIALISTS.get(name)


def list_specialists() -> List[Dict[str, Any]]:
    """List all registered specialists."""
    return [
        {
            "name": s.name,
            "display_name": s.display_name,
            "description": s.description,
            "color": s.color,
            "default_model": s.default_model,
            "keywords": s.keywords,
            "tools": s.tools,
            "priority": s.priority,
            "enabled": s.enabled,
            "category": s.category,
        }
        for s in SPECIALISTS.values()
        if s.enabled
    ]


def get_specialist_prompt(name: str, user_context: Optional[str] = None) -> Optional[str]:
    """Get a specialist's system prompt, optionally augmented with user context."""
    spec = SPECIALISTS.get(name)
    if not spec or not spec.system_prompt:
        return None
    prompt = spec.system_prompt
    if user_context:
        prompt += f"\n\n## User Context\n{user_context}"
    return prompt


# All available specialist module names
_SPECIALIST_MODULES = [
    "healthcare_provider",
    "healthcare_payer",
    "healthcare_regulatory",
    "healthcare_clinical",
    "healthcare_analytics",
    "healthcare_it",
    "healthcare_pharmacy",
    "healthcare_behavioral",
    "healthcare_dental_vision",
    "healthcare_workers_comp",
    "finance",
    "legal",
    "software_engineering",
    "media_marketing",
    "research",
    "personal_assistant",
    "cloudflare_ops",
    "data_analytics",
    "general",
]


def _load_all_specialists():
    """Load all specialist modules, skipping any that fail to import."""
    for module_name in _SPECIALIST_MODULES:
        try:
            full_module = f"specialists.{module_name}"
            importlib.import_module(full_module)
        except ImportError as e:
            logger.debug(f"Specialist module '{module_name}' not available: {e}")
        except Exception as e:
            logger.warning(f"Error loading specialist '{module_name}': {e}")


# Auto-load all available specialists on import
_load_all_specialists()