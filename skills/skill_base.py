"""
Aethera AI - Skill Base Class

Base class for all Aethera skills.
Skills are self-contained capabilities that process input and produce output.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class SkillResult:
    """Result of skill execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def skill(name: Optional[str] = None, category: str = "general"):
    """
    Decorator to register a skill.

    Usage:
        @skill(name="my_skill", category="healthcare")
        class MySkill(AetheraSkill):
            ...
    """
    def decorator(cls):
        cls._skill_name = name or cls.__name__.lower()
        cls._skill_category = category
        return cls
    return decorator


class AetheraSkill(ABC):
    """
    Base class for all Aethera skills.

    Skills are:
    - Stateless (no persistent state between calls)
    - Self-describing (name, description, parameters, examples)
    - Composable (skills can call other skills)
    - Discoverable (auto-registered via decorator)

    To create a skill:
    1. Create a new .py file in skills/builtin/ or skills/healthcare/ or skills/user/
    2. Subclass AetheraSkill
    3. Implement name, description, parameters, execute()
    4. The skill auto-registers on startup
    """

    # Class attributes set by @skill decorator
    _skill_name: str = ""
    _skill_category: str = "general"

    # Skill provenance — set by creation system, defaults for built-in skills
    _skill_version: str = "1.0.0"
    _skill_source: str = "builtin"  # "builtin", "user_created", "auto_generated"
    _skill_created_at: str = ""
    _skill_updated_at: str = ""

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique skill identifier, e.g. 'icd10_lookup'.
        Used for tool calling and skill invocation.
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Human-readable description of what this skill does.
        Used by the router to decide when to invoke this skill.
        Should be clear and specific about the skill's purpose.
        """
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """
        JSON Schema describing the skill's input parameters.
        Must follow OpenAI function-calling format.

        Example:
        {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The ICD-10 code to look up"
                },
                "include_children": {
                    "type": "boolean",
                    "description": "Include child codes",
                    "default": false
                }
            },
            "required": ["code"]
        }
        """
        pass

    @property
    def examples(self) -> List[Dict[str, Any]]:
        """
        Example invocations for few-shot prompting.
        Each example should have 'input' and optionally 'output'.
        """
        return []

    @property
    def category(self) -> str:
        """Skill category for UI grouping."""
        return self._skill_category or "general"

    @property
    def requires_phi_protection(self) -> bool:
        """
        If True, inputs/outputs are encrypted and routed to local models.
        Set to True for skills that handle PHI/PII data.
        """
        return False

    @property
    def cache_ttl(self) -> int:
        """
        Cache TTL in seconds. 0 means no caching.
        Useful for expensive operations like API calls.
        """
        return 0

    @property
    def version(self) -> str:
        """Skill version. Defaults to '1.0.0'."""
        return self._skill_version

    @property
    def source(self) -> str:
        """Skill origin: 'builtin', 'user_created', or 'auto_generated'."""
        return self._skill_source

    @property
    def created_at(self) -> str:
        """ISO timestamp when this skill was created."""
        return self._skill_created_at

    @property
    def updated_at(self) -> str:
        """ISO timestamp when this skill was last updated."""
        return self._skill_updated_at

    @abstractmethod
    async def execute(self, **kwargs) -> SkillResult:
        """
        Execute the skill and return structured result.

        Args:
            **kwargs: Input parameters as defined in self.parameters

        Returns:
            SkillResult with success status, data, and optional error
        """
        pass

    def to_tool_definition(self) -> dict:
        """
        Convert to OpenAI function-calling format for LLM tool use.

        Returns:
            Dict in OpenAI tool definition format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            },
            "metadata": {
                "version": self.version,
                "source": self.source,
                "category": self.category,
            }
        }

    def validate_input(self, **kwargs) -> tuple[bool, Optional[str]]:
        """
        Validate input against parameter schema.

        Args:
            **kwargs: Input parameters to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required parameters
        required = self.parameters.get("required", [])
        for param in required:
            if param not in kwargs or kwargs[param] is None:
                return False, f"Missing required parameter: {param}"

        # Check parameter types
        properties = self.parameters.get("properties", {})
        for param, value in kwargs.items():
            if param not in properties:
                continue  # Allow extra parameters

            expected_type = properties[param].get("type")
            if expected_type == "string" and not isinstance(value, str):
                return False, f"Parameter {param} must be a string"
            elif expected_type == "integer" and not isinstance(value, int):
                return False, f"Parameter {param} must be an integer"
            elif expected_type == "number" and not isinstance(value, (int, float)):
                return False, f"Parameter {param} must be a number"
            elif expected_type == "boolean" and not isinstance(value, bool):
                return False, f"Parameter {param} must be a boolean"
            elif expected_type == "array" and not isinstance(value, list):
                return False, f"Parameter {param} must be an array"
            elif expected_type == "object" and not isinstance(value, dict):
                return False, f"Parameter {param} must be an object"

        return True, None

    async def pre_execute(self, **kwargs):
        """
        Hook called before execute(). Override for preprocessing.
        """
        pass

    async def post_execute(self, result: SkillResult):
        """
        Hook called after execute(). Override for postprocessing.
        """
        pass

    async def run(self, **kwargs) -> SkillResult:
        """
        Execute skill with validation and hooks.

        Args:
            **kwargs: Input parameters

        Returns:
            SkillResult
        """
        # Validate input
        is_valid, error = self.validate_input(**kwargs)
        if not is_valid:
            return SkillResult(success=False, error=error)

        # Pre-execute hook
        try:
            await self.pre_execute(**kwargs)
        except Exception as e:
            return SkillResult(success=False, error=f"Pre-execution failed: {e}")

        # Execute
        try:
            result = await self.execute(**kwargs)
        except Exception as e:
            return SkillResult(success=False, error=f"Execution failed: {e}")

        # Post-execute hook
        try:
            await self.post_execute(result)
        except Exception as e:
            # Log but don't fail the result
            pass

        return result
