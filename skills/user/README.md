# User Skills Directory

This directory is for custom skills you create for your own workflows.

## How to Add a Custom Skill

1. Create a new `.py` file in this directory (e.g., `my_skill.py`)
2. Subclass `AetheraSkill` and implement the required interface
3. Apply the `@skill()` decorator to register it
4. Restart Aethera -- the skill is auto-discovered and available

## Quick Template

```python
"""
Aethera AI - My Custom Skill
"""

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="my_skill", category="user")
class MySkill(AetheraSkill):

    @property
    def name(self) -> str:
        return "my_skill"

    @property
    def description(self) -> str:
        return "What this skill does"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input_field": {
                    "type": "string",
                    "description": "Description of the input"
                }
            },
            "required": ["input_field"]
        }

    async def execute(self, **kwargs) -> SkillResult:
        input_field = kwargs.get("input_field", "")
        if not input_field:
            return SkillResult(success=False, error="input_field is required")
        try:
            return SkillResult(success=True, data={"result": input_field})
        except Exception as e:
            return SkillResult(success=False, error=str(e))
```

## Guidelines

- Skills must be **stateless** -- all context comes from `kwargs`
- Return `SkillResult(success=False, error="message")` for errors, not exceptions
- Set `requires_phi_protection = True` if your skill handles patient data
- See `skills/SKILL_SPEC.md` for the full specification and advanced patterns