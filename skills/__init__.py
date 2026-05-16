"""
Aethera AI - Skills Package

Skills are self-contained capabilities that process input and produce output.
They are the equivalent of Claude's built-in tools.

Skills are:
- Stateless (no persistent state between calls)
- Self-describing (name, description, parameters, examples)
- Composable (skills can call other skills)
- Discoverable (auto-registered via decorator)
"""

from skills.skill_base import AetheraSkill, skill
from skills.skill_registry import SkillRegistry

__all__ = ["AetheraSkill", "skill", "SkillRegistry"]
