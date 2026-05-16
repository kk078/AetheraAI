"""
AetheraAI — Tests for skill registry, execution, and auto-discovery.
Phase 14: Comprehensive Tests
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills.skill_base import AetheraSkill, SkillResult, skill
from skills.skill_registry import SkillRegistry, get_registry


# --- Concrete subclass for testing ---

@skill(name="test_skill", category="test")
class MockSkill(AetheraSkill):
    """A mock skill for testing."""

    @property
    def name(self):
        return "test_skill"

    @property
    def description(self):
        return "A test skill for unit tests"

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "input_text": {"type": "string", "description": "Input text"},
                "count": {"type": "integer", "description": "Number of items"},
            },
            "required": ["input_text"],
        }

    async def execute(self, **kwargs):
        text = kwargs.get("input_text", "")
        return SkillResult(success=True, data={"result": text.upper()})


class TestSkillResult:
    """Tests for SkillResult dataclass."""

    def test_success_result(self):
        result = SkillResult(success=True, data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_failure_result(self):
        result = SkillResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None

    def test_default_metadata(self):
        result = SkillResult(success=True)
        assert result.metadata == {}


class TestSkillDecorator:
    """Tests for @skill decorator."""

    def test_skill_decorator_sets_name(self):
        assert hasattr(MockSkill, "_skill_name")
        assert MockSkill._skill_name == "test_skill"

    def test_skill_decorator_sets_category(self):
        assert hasattr(MockSkill, "_skill_category")
        assert MockSkill._skill_category == "test"


class TestAetheraSkillBase:
    """Tests for AetheraSkill base class behavior."""

    @pytest.fixture
    def skill_instance(self):
        return MockSkill()

    def test_validate_input_required_present(self, skill_instance):
        valid, error = skill_instance.validate_input(input_text="hello")
        assert valid is True
        assert error is None

    def test_validate_input_required_missing(self, skill_instance):
        valid, error = skill_instance.validate_input(count=5)
        assert valid is False
        assert error is not None

    def test_validate_input_allows_extra_params(self, skill_instance):
        valid, error = skill_instance.validate_input(input_text="hello", extra_param="ignored")
        assert valid is True

    def test_to_tool_definition_format(self, skill_instance):
        tool_def = skill_instance.to_tool_definition()
        assert tool_def["type"] == "function"
        assert "function" in tool_def
        assert tool_def["function"]["name"] == "test_skill"
        assert "parameters" in tool_def["function"]

    @pytest.mark.asyncio
    async def test_run_calls_validate_then_execute(self, skill_instance):
        result = await skill_instance.run(input_text="hello")
        assert result.success is True
        assert result.data == {"result": "HELLO"}

    @pytest.mark.asyncio
    async def test_run_fails_on_invalid_input(self, skill_instance):
        result = await skill_instance.run(count=5)
        assert result.success is False

    def test_skill_name_property(self, skill_instance):
        assert skill_instance.name == "test_skill"

    def test_skill_description_property(self, skill_instance):
        assert "test skill" in skill_instance.description.lower()

    def test_skill_category_default(self, skill_instance):
        assert skill_instance.category == "test"


class TestSkillRegistry:
    """Tests for SkillRegistry singleton and registration."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        # SkillRegistry is a singleton, so we need to clear it
        reg = SkillRegistry()
        reg._skills = {}
        reg._categories = {}
        return reg

    def test_register_skill(self, registry):
        mock_skill = MockSkill()
        registry.register(mock_skill)
        assert registry.get("test_skill") is not None

    def test_register_adds_to_category(self, registry):
        mock_skill = MockSkill()
        registry.register(mock_skill)
        skills_in_category = registry.get_by_category("test")
        assert len(skills_in_category) == 1

    def test_unregister_skill(self, registry):
        mock_skill = MockSkill()
        registry.register(mock_skill)
        registry.unregister("test_skill")
        assert registry.get("test_skill") is None

    def test_get_unknown_skill(self, registry):
        assert registry.get("nonexistent_skill") is None

    def test_list_all_skills(self, registry):
        mock_skill = MockSkill()
        registry.register(mock_skill)
        all_skills = registry.list()
        assert len(all_skills) >= 1

    def test_list_skills_by_category(self, registry):
        mock_skill = MockSkill()
        registry.register(mock_skill)
        test_skills = registry.list(category="test")
        assert len(test_skills) == 1

    def test_search_by_name(self, registry):
        mock_skill = MockSkill()
        registry.register(mock_skill)
        results = registry.search("test")
        assert len(results) >= 1

    def test_search_no_match(self, registry):
        results = registry.search("xyzzy_nonexistent_12345")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_execute_skill_success(self, registry):
        mock_skill = MockSkill()
        registry.register(mock_skill)
        result = await registry.execute("test_skill", input_text="hello")
        assert result.success is True
        assert result.data == {"result": "HELLO"}

    @pytest.mark.asyncio
    async def test_execute_skill_not_found(self, registry):
        with pytest.raises(ValueError):
            await registry.execute("nonexistent_skill", input_text="hello")

    def test_get_tool_definitions(self, registry):
        mock_skill = MockSkill()
        registry.register(mock_skill)
        defs = registry.get_tool_definitions()
        assert isinstance(defs, list)
        assert len(defs) >= 1
        assert defs[0]["type"] == "function"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])