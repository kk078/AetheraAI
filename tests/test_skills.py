"""
Aethera AI - Skills Tests

Tests for skill execution and registration.
"""
import pytest
import sys
sys.path.insert(0, '..')

from skills.skill_registry import SkillRegistry
from skills.builtin.calculator import CalculatorSkill
from skills.builtin.summarizer import SummarizerSkill


class TestCalculatorSkill:
    """Test calculator skill."""

    @pytest.fixture
    def calculator(self):
        return CalculatorSkill()

    def test_basic_math(self, calculator):
        """Test basic mathematical operations."""
        result = calculator.execute("calculate", {"expression": "2 + 2"})
        assert result.success is True
        assert result.data == 4

    def test_complex_expression(self, calculator):
        """Test complex expressions."""
        result = calculator.execute("calculate", {"expression": "(10 * 5) + 100"})
        assert result.success is True
        assert result.data == 150

    def test_financial_calculation(self, calculator):
        """Test financial calculations."""
        # Present Value
        result = calculator.execute("pv", {
            "future_value": 1000,
            "rate": 0.05,
            "periods": 10
        })
        assert result.success is True
        assert result.data > 0
        assert result.data < 1000  # PV should be less than FV

    def test_bmi_calculation(self, calculator):
        """Test BMI calculation."""
        result = calculator.execute("bmi", {
            "weight_kg": 70,
            "height_m": 1.75
        })
        assert result.success is True
        assert 20 < result.data < 25  # Normal BMI range

    def test_invalid_expression(self, calculator):
        """Test invalid expression handling."""
        result = calculator.execute("calculate", {"expression": "invalid"})
        assert result.success is False
        assert result.error is not None


class TestSummarizerSkill:
    """Test summarizer skill."""

    @pytest.fixture
    def summarizer(self):
        return SummarizerSkill()

    def test_text_summarization(self, summarizer):
        """Test text summarization."""
        text = """
        Healthcare billing is complex. It involves multiple steps including
        patient registration, insurance verification, service documentation,
        coding, claim submission, payment posting, and denial management.
        Each step requires attention to detail and compliance with regulations.
        """

        result = summarizer.execute("summarize", {"text": text})
        assert result.success is True
        assert len(result.data) < len(text)  # Summary should be shorter

    def test_extractive_summary(self, summarizer):
        """Test extractive summarization."""
        text = "The quick brown fox jumps over the lazy dog."

        result = summarizer._extractive_summary(text, num_sentences=1)
        assert len(result) <= len(text)


class TestSkillRegistry:
    """Test skill registry."""

    @pytest.fixture
    def registry(self):
        return SkillRegistry()

    def test_register_skill(self, registry):
        """Test skill registration."""
        skill = CalculatorSkill()
        registry.register(skill)

        assert registry.get_skill("calculator") is not None

    def test_list_skills(self, registry):
        """Test listing registered skills."""
        registry.register(CalculatorSkill())

        skills = registry.list_skills()
        assert len(skills) > 0
        assert any(s['name'] == 'calculator' for s in skills)

    def test_execute_skill(self, registry):
        """Test skill execution via registry."""
        registry.register(CalculatorSkill())

        result = registry.execute("calculator", "calculate", {"expression": "5 * 5"})
        assert result.success is True
        assert result.data == 25

    def test_unknown_skill(self, registry):
        """Test unknown skill handling."""
        result = registry.execute("unknown_skill", "action", {})
        assert result.success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
