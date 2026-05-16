# Aethera AI Skill Specification

This document describes how to create new skills for Aethera AI. Skills are self-contained capabilities that process input and produce structured output. They are the building blocks of Aethera's intelligence layer.

## Skill Anatomy

Every skill consists of a single Python file in one of three directories:

| Directory | Purpose |
|---|---|
| `skills/builtin/` | General-purpose skills shipped with Aethera (calculator, summarizer, etc.) |
| `skills/healthcare/` | Healthcare-specific skills (claim scrubbing, DRG grouping, etc.) |
| `skills/user/` | Custom skills created by users for their own workflows |

A skill file must contain:

1. **Module docstring** - Description of the skill
2. **Imports** - `from skills.skill_base import AetheraSkill, SkillResult, skill`
3. **Data constants** - Any lookup tables, databases, or reference data the skill needs
4. **Class definition** - Subclass of `AetheraSkill` decorated with `@skill()`
5. **Required properties** - `name`, `description`, `parameters`
6. **Optional properties** - `examples`, `requires_phi_protection`, `cache_ttl`
7. **`execute()` method** - The core logic, returning `SkillResult`

### Minimal Skill Template

```python
"""
Aethera AI - My Custom Skill

Short description of what this skill does.
"""

from typing import Dict, Any

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="my_skill", category="user")
class MySkill(AetheraSkill):

    @property
    def name(self) -> str:
        return "my_skill"

    @property
    def description(self) -> str:
        return "One-line description of what this skill does"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input_field": {
                    "type": "string",
                    "description": "Description of this input field"
                }
            },
            "required": ["input_field"]
        }

    async def execute(self, **kwargs) -> SkillResult:
        input_field = kwargs.get("input_field", "")
        if not input_field:
            return SkillResult(success=False, error="input_field is required")

        try:
            result_data = self._do_work(input_field)
            return SkillResult(success=True, data=result_data)
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _do_work(self, input_field: str) -> Dict[str, Any]:
        return {"output": input_field}
```

## Parameter Schema Format

Parameters follow the JSON Schema format used by OpenAI function calling:

```python
@property
def parameters(self) -> dict:
    return {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["lookup", "calculate", "validate"],
                "description": "Which action to perform"
            },
            "codes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of codes to process"
            },
            "threshold": {
                "type": "number",
                "description": "Optional threshold value",
                "default": 0.5
            },
            "verbose": {
                "type": "boolean",
                "description": "Return detailed output",
                "default": false
            }
        },
        "required": ["action", "codes"]
    }
```

Supported types: `string`, `integer`, `number`, `boolean`, `array`, `object`.

Use `enum` for fixed choices, `items` for array element schemas, and `default` for optional fields.

## Registration Process

Skills are auto-discovered at startup. The `SkillRegistry` scans these directories:

1. `skills/builtin/`
2. `skills/healthcare/`
3. `skills/user/`

For each `.py` file (excluding `__init__.py` and files starting with `_`):

1. The module is imported dynamically via `importlib`
2. All classes that subclass `AetheraSkill` are found via `inspect`
3. Each class is instantiated and registered with the `SkillRegistry`

**Steps to register a new skill:**

1. Create a `.py` file in the appropriate directory (`skills/user/` for custom skills)
2. Define a class that extends `AetheraSkill`
3. Apply the `@skill(name="your_skill", category="user")` decorator
4. Implement the required properties and `execute()` method
5. Restart Aethera (or trigger re-discovery) - the skill appears automatically

No additional configuration files, no manual registration, no imports to update.

## The `@skill` Decorator

```python
@skill(name="skill_name", category="healthcare")
class MySkill(AetheraSkill):
    ...
```

Parameters:
- `name` (str): Unique skill identifier. Used for invocation and tool definitions.
- `category` (str): Grouping for UI and search. Use `"healthcare"`, `"user"`, or `"general"`.

## SkillResult

Every `execute()` method must return a `SkillResult`:

```python
# Success
return SkillResult(success=True, data={"key": "value"})

# Failure
return SkillResult(success=False, error="Description of what went wrong")

# With metadata
return SkillResult(success=True, data=result, metadata={"cache_hit": True})
```

- `success` (bool, required): Whether the skill completed successfully
- `data` (Any, optional): The result payload on success
- `error` (str, optional): Human-readable error message on failure
- `metadata` (dict, optional): Additional metadata about the execution

## PHI Protection

If a skill handles Protected Health Information (PHI), set `requires_phi_protection`:

```python
@property
def requires_phi_protection(self) -> bool:
    return True
```

When `True`, the Aethera framework encrypts inputs/outputs and routes processing to local models instead of cloud APIs. Always set this to `True` for skills that may receive or produce patient-identifiable data.

## Multi-Action Skills

Many skills support multiple actions via an `action` parameter. This pattern keeps related functionality together:

```python
@property
def parameters(self) -> dict:
    return {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["check_status", "calculate", "generate_report"],
                "description": "Which action to perform"
            },
            # ... other parameters
        },
        "required": ["action"]
    }

async def execute(self, **kwargs) -> SkillResult:
    action = kwargs.get("action", "")
    if action == "check_status":
        return SkillResult(success=True, data=self._check_status(kwargs))
    elif action == "calculate":
        return SkillResult(success=True, data=self._calculate(kwargs))
    elif action == "generate_report":
        return SkillResult(success=True, data=self._generate_report(kwargs))
    else:
        return SkillResult(success=False, error=f"Unknown action: {action}")
```

## Examples

Provide example invocations for few-shot prompting. These help the LLM understand when and how to use your skill:

```python
@property
def examples(self) -> list:
    return [
        {"input": {"action": "lookup", "code": "99213"}},
        {"input": {"action": "validate", "codes": ["99213", "99214"]}},
    ]
```

## Best Practices

1. **Be stateless** - Skills should not maintain state between calls. All context comes from `kwargs`.
2. **Return structured data** - Use dicts with clear keys, not free-form strings.
3. **Handle errors gracefully** - Return `SkillResult(success=False, error=...)` instead of raising exceptions.
4. **Include references** - Add `reference` fields in output data citing the source of formulas, rules, or data.
5. **Validate inputs early** - Check required parameters at the start of `execute()`.
6. **Keep data in-module** - Reference data (code tables, fee schedules) should be defined as module-level constants.
7. **Set PHI protection** - When in doubt, set `requires_phi_protection = True`.
8. **Document with docstrings** - The class docstring appears in skill listings and helps the router.
9. **Use type hints** - Makes the code more maintainable and helps with static analysis.
10. **Test edge cases** - Handle empty inputs, out-of-range values, and missing optional parameters.

## Complete Example: Drug Interaction Checker

```python
"""
Aethera AI - Drug Interaction Checker

Check for known drug-drug interactions.
"""

from typing import Dict, Any, List

from skills.skill_base import AetheraSkill, SkillResult, skill


INTERACTIONS: Dict[str, Dict[str, Any]] = {
    ("warfarin", "aspirin"): {
        "severity": "major",
        "description": "Increased bleeding risk",
        "recommendation": "Avoid combination if possible; monitor INR closely"
    },
    ("metformin", "contrast_dye"): {
        "severity": "major",
        "description": "Risk of lactic acidosis",
        "recommendation": "Discontinue metformin before and after contrast procedures"
    },
}


@skill(name="drug_interaction", category="healthcare")
class DrugInteractionSkill(AetheraSkill):

    @property
    def name(self) -> str:
        return "drug_interaction"

    @property
    def description(self) -> str:
        return "Check for known drug-drug interactions and provide clinical recommendations"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "drugs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of drug names to check for interactions"
                }
            },
            "required": ["drugs"]
        }

    @property
    def requires_phi_protection(self) -> bool:
        return True

    @property
    def examples(self) -> list:
        return [
            {"input": {"drugs": ["warfarin", "aspirin"]}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        drugs = kwargs.get("drugs", [])
        if not drugs or len(drugs) < 2:
            return SkillResult(success=False, error="At least 2 drugs required")

        interactions = self._check_interactions(drugs)
        return SkillResult(success=True, data=interactions)

    def _check_interactions(self, drugs: List[str]) -> Dict[str, Any]:
        found = []
        drugs_lower = [d.lower().strip() for d in drugs]
        for i in range(len(drugs_lower)):
            for j in range(i + 1, len(drugs_lower)):
                pair = (drugs_lower[i], drugs_lower[j])
                rev_pair = (drugs_lower[j], drugs_lower[i])
                info = INTERACTIONS.get(pair) or INTERACTIONS.get(rev_pair)
                if info:
                    found.append({
                        "drug_1": drugs[i],
                        "drug_2": drugs[j],
                        **info
                    })
        return {
            "drugs_checked": drugs,
            "interactions_found": len(found),
            "interactions": found,
            "has_major": any(i["severity"] == "major" for i in found)
        }
```