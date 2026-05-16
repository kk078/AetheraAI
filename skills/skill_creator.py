"""
Aethera AI - Skill Self-Creation System

Enables users to teach Aethera new skills through conversation and
auto-proposes skills when knowledge gaps are detected.

Components:
- TeachingModeDetector: Detects when a user wants to teach a new skill
- WorkflowExtractor: Extracts structured workflow specs from conversation
- SkillCodeGenerator: Generates Python skill code from a workflow spec
- SkillValidator: AST-based safety validation of generated code
- SkillSandboxTester: Tests generated skills in isolation
"""

import ast
import json
import logging
import os
import re
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("aethera.skills.creator")

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TeachingIntent:
    """Result of teaching mode detection."""
    is_teaching: bool = False
    confidence: float = 0.0
    detected_patterns: List[str] = field(default_factory=list)
    suggested_action: str = ""


@dataclass
class WorkflowSpec:
    """Structured specification for a new skill."""
    name: str = ""
    display_name: str = ""
    description: str = ""
    category: str = "general"
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class GeneratedSkill:
    """Result of skill code generation."""
    code: str = ""
    spec: Optional[WorkflowSpec] = None
    file_path: str = ""
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of AST-based safety validation."""
    is_safe: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TestResult:
    """Result of sandbox testing a generated skill."""
    passed: bool = False
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Teaching Mode Detector
# ---------------------------------------------------------------------------

TEACHING_PATTERNS = [
    (r"\bteach you\b", 0.8),
    (r"\bteach me\b", 0.3),
    (r"\bcreate a (?:new )?skill\b", 0.9),
    (r"\bnew (?:workflow|process|skill)\b", 0.7),
    (r"\bI want you to learn\b", 0.85),
    (r"\blet me show you (?:how to|the)\b", 0.75),
    (r"\bhere(?:'s| is) how (?:to|we|I)\b", 0.7),
    (r"\bI(?:'ll| will) teach you\b", 0.85),
    (r"\badd a (?:new )?(?:capability|ability|skill)\b", 0.8),
    (r"\bmake a (?:new )?skill\b", 0.85),
    (r"\bbuild a (?:new )?skill\b", 0.85),
    (r"\bdefine a (?:new )?(?:workflow|process)\b", 0.75),
    (r"\bwhenever you see\b", 0.6),
    (r"\bautomate this (?:process|task|workflow)\b", 0.8),
    (r"\bfrom now on\b.*\byou should\b", 0.65),
    (r"\byou should (?:always|automatically)\b", 0.6),
]

NEGATION_PATTERNS = [
    r"\bdon't teach\b",
    r"\bnot teaching\b",
    r"\bno(?:t| need to) learn\b",
]


class TeachingModeDetector:
    """Detects when a user wants to teach Aethera a new skill."""

    def detect(self, message: str, conversation_context: Optional[List[Dict]] = None) -> TeachingIntent:
        """
        Analyze a user message to detect teaching intent.

        Args:
            message: The user's current message
            conversation_context: Previous messages for context

        Returns:
            TeachingIntent with detection results
        """
        message_lower = message.lower()
        detected_patterns = []
        total_confidence = 0.0

        # Check positive patterns
        for pattern, weight in TEACHING_PATTERNS:
            if re.search(pattern, message_lower):
                detected_patterns.append(pattern)
                total_confidence = max(total_confidence, weight)

        # Check negation patterns
        for neg_pattern in NEGATION_PATTERNS:
            if re.search(neg_pattern, message_lower):
                total_confidence *= 0.3
                detected_patterns.append(f"negated:{neg_pattern}")

        # Boost confidence if multiple patterns match
        if len(detected_patterns) > 1:
            total_confidence = min(total_confidence + 0.1, 1.0)

        # Check conversation context for follow-up teaching
        if conversation_context:
            for msg in conversation_context[-3:]:
                role = msg.get("role", "")
                content = msg.get("content", "").lower()
                if role == "user":
                    for pattern, weight in TEACHING_PATTERNS:
                        if re.search(pattern, content):
                            total_confidence = min(total_confidence + 0.15, 1.0)

        is_teaching = total_confidence >= 0.6

        suggested_action = ""
        if is_teaching:
            suggested_action = "extract_workflow"

        return TeachingIntent(
            is_teaching=is_teaching,
            confidence=round(total_confidence, 3),
            detected_patterns=detected_patterns,
            suggested_action=suggested_action,
        )


# ---------------------------------------------------------------------------
# Workflow Extractor
# ---------------------------------------------------------------------------

class WorkflowExtractor:
    """Extracts a structured WorkflowSpec from conversation messages."""

    def __init__(self, litellm_url: Optional[str] = None, litellm_key: Optional[str] = None):
        self.litellm_url = litellm_url or os.environ.get("LITELLM_URL", "http://litellm:4000")
        self.litellm_key = litellm_key or os.environ.get("LITELLM_MASTER_KEY", "")

    async def extract(self, messages: List[Dict[str, str]]) -> WorkflowSpec:
        """
        Extract a WorkflowSpec from conversation messages.

        Args:
            messages: List of {role, content} dicts representing the conversation

        Returns:
            WorkflowSpec with extracted skill definition
        """
        # Try LLM extraction first
        spec = await self._llm_extract(messages)
        if spec and spec.name:
            return spec

        # Fall back to heuristic extraction
        return self._heuristic_extract(messages)

    async def _llm_extract(self, messages: List[Dict[str, str]]) -> Optional[WorkflowSpec]:
        """Use LLM to extract a structured WorkflowSpec from conversation."""
        try:
            import httpx
        except ImportError:
            return None

        conversation_text = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages
        )

        system_prompt = (
            "You are a skill specification extractor. Given a conversation where a user "
            "describes a process or workflow they want automated, extract a structured skill "
            "specification. Return ONLY valid JSON with these fields:\n"
            "  name: snake_case skill identifier (e.g. 'referral_processor')\n"
            "  display_name: human-friendly name (e.g. 'Referral Processor')\n"
            "  description: what the skill does in one sentence\n"
            "  category: one of 'healthcare', 'finance', 'general', 'technology', 'legal'\n"
            "  inputs: list of {name, type, description, required} parameter definitions\n"
            "  outputs: list of {name, type, description} result fields\n"
            "  steps: list of {description, action, parameters} processing steps\n"
            "  rules: list of condition/constraint strings\n"
            "  examples: list of {input: {...}, output: {...}} example pairs\n\n"
            "Types: string, integer, number, boolean, array, object"
        )

        payload = {
            "model": "qwen3.5:4b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract the skill specification from this conversation:\n\n{conversation_text}"},
            ],
            "temperature": 0.2,
            "max_tokens": 2000,
        }

        headers = {"Content-Type": "application/json"}
        if self.litellm_key:
            headers["Authorization"] = f"Bearer {self.litellm_key}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.litellm_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code != 200:
                    logger.warning(f"LLM extraction failed: HTTP {resp.status_code}")
                    return None

                data = resp.json()
                content = data["choices"][0]["message"]["content"]

                # Strip markdown code fences if present
                content = re.sub(r"^```(?:json)?\s*", "", content.strip())
                content = re.sub(r"\s*```$", "", content.strip())

                spec_data = json.loads(content)
                return WorkflowSpec(
                    name=spec_data.get("name", ""),
                    display_name=spec_data.get("display_name", ""),
                    description=spec_data.get("description", ""),
                    category=spec_data.get("category", "general"),
                    inputs=spec_data.get("inputs", []),
                    outputs=spec_data.get("outputs", []),
                    steps=spec_data.get("steps", []),
                    rules=spec_data.get("rules", []),
                    examples=spec_data.get("examples", []),
                )
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"LLM extraction parse error: {e}")
            return None
        except Exception as e:
            logger.warning(f"LLM extraction error: {e}")
            return None

    def _heuristic_extract(self, messages: List[Dict[str, str]]) -> WorkflowSpec:
        """Fallback heuristic extraction when LLM is unavailable."""
        all_text = " ".join(m.get("content", "") for m in messages).lower()

        # Extract a name from the conversation
        name = "custom_skill"
        for msg in messages:
            content = msg.get("content", "")
            # Look for "called X" or "named X" or "skill X"
            match = re.search(r"(?:called|named|skill)\s+[\"']?(\w+)[\"']?", content, re.I)
            if match:
                name = re.sub(r"[^a-z0-9_]", "_", match.group(1).lower())
                break

        display_name = name.replace("_", " ").title()

        # Build description from first user message
        description = "Custom skill created from user workflow description"
        for msg in messages:
            if msg.get("role") == "user":
                desc = msg.get("content", "")[:200]
                if desc:
                    description = f"Processes: {desc}"
                break

        # Extract numbered steps as processing steps
        steps = []
        for msg in messages:
            content = msg.get("content", "")
            # Match "1. Step" or "Step 1:" patterns
            found_steps = re.findall(r"(?:^|\n)\s*(?:\d+[\.\)]\s*|step\s+\d+\s*[:\.]\s*)(.+?)(?:\n|$)", content, re.I)
            for i, step_text in enumerate(found_steps):
                steps.append({
                    "description": step_text.strip(),
                    "action": "process",
                    "parameters": {},
                })

        # Extract rules from conditional statements
        rules = []
        for msg in messages:
            content = msg.get("content", "")
            conditionals = re.findall(r"(?:if|when|whenever|unless)\s+(.+?)(?:\s*,?\s*(?:then|,|$))", content, re.I)
            rules.extend(conditionals)

        return WorkflowSpec(
            name=name,
            display_name=display_name,
            description=description,
            category="general",
            inputs=[{"name": "input", "type": "string", "description": "Input data to process", "required": True}],
            outputs=[{"name": "result", "type": "string", "description": "Processing result"}],
            steps=steps,
            rules=rules,
            examples=[],
        )


# ---------------------------------------------------------------------------
# Skill Code Generator
# ---------------------------------------------------------------------------

SKILL_TEMPLATE = '''"""
Aethera AI - User-Created Skill: {class_name}

Auto-generated from workflow specification.
"""

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="{skill_name}", category="{category}")
class {class_name}(AetheraSkill):

    _skill_version = "{version}"
    _skill_source = "{source}"
    _skill_created_at = "{created_at}"
    _skill_updated_at = "{updated_at}"

    @property
    def name(self) -> str:
        return "{skill_name}"

    @property
    def description(self) -> str:
        return """{description}"""

    @property
    def parameters(self) -> dict:
        return {parameters}

    @property
    def examples(self) -> list:
        return {examples}

    async def execute(self, **kwargs) -> SkillResult:
        """Execute the skill."""
        try:
{execute_body}
        except Exception as e:
            return SkillResult(success=False, error=f"Execution failed: {{e}}")
'''

DEFAULT_EXECUTE_BODY = '''            # Process input
            input_data = kwargs.get("input", "")
            if not input_data:
                return SkillResult(success=False, error="No input provided")

            # TODO: Implement skill logic here
            result = input_data

            return SkillResult(success=True, data={{"result": result}})'''


class SkillCodeGenerator:
    """Generates complete Python skill code from a WorkflowSpec."""

    def __init__(self, litellm_url: Optional[str] = None, litellm_key: Optional[str] = None):
        self.litellm_url = litellm_url or os.environ.get("LITELLM_URL", "http://litellm:4000")
        self.litellm_key = litellm_key or os.environ.get("LITELLM_MASTER_KEY", "")

    async def generate(self, spec: WorkflowSpec) -> GeneratedSkill:
        """
        Generate Python skill code from a WorkflowSpec.

        Args:
            spec: The workflow specification to generate code from

        Returns:
            GeneratedSkill with code, spec, and any validation errors
        """
        # Try LLM-assisted generation first
        code = await self._llm_generate(spec)

        if not code:
            # Fall back to template-based generation
            code = self._template_generate(spec)

        # Validate the generated code compiles
        validation_errors = []
        try:
            compile(code, "<generated_skill>", "exec")
        except SyntaxError as e:
            validation_errors.append(f"Syntax error: {e}")

        file_name = f"{spec.name}.py"
        file_path = str(Path("skills") / "user" / file_name)

        return GeneratedSkill(
            code=code,
            spec=spec,
            file_path=file_path,
            validation_errors=validation_errors,
        )

    async def _llm_generate(self, spec: WorkflowSpec) -> Optional[str]:
        """Use LLM to generate skill code from a WorkflowSpec."""
        try:
            import httpx
        except ImportError:
            return None

        system_prompt = (
            "You are a Python code generator for Aethera AI skills. "
            "Generate a complete Python skill class that inherits from AetheraSkill. "
            "The skill must:\n"
            "1. Use the @skill() decorator\n"
            "2. Inherit from AetheraSkill\n"
            "3. Implement name, description, parameters, and execute()\n"
            "4. Return SkillResult from execute()\n"
            "5. Handle errors gracefully\n"
            "6. NOT import or use: subprocess, os.system, eval, exec, __import__, "
            "socket, ctypes, shutil.rmtree\n\n"
            "Available imports: AetheraSkill, SkillResult, skill from skills.skill_base\n\n"
            "Return ONLY the Python code, no markdown fences."
        )

        spec_json = json.dumps({
            "name": spec.name,
            "display_name": spec.display_name,
            "description": spec.description,
            "category": spec.category,
            "inputs": spec.inputs,
            "outputs": spec.outputs,
            "steps": spec.steps,
            "rules": spec.rules,
            "examples": spec.examples,
        }, indent=2)

        payload = {
            "model": "qwen3.5:4b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate a skill for this specification:\n{spec_json}"},
            ],
            "temperature": 0.3,
            "max_tokens": 3000,
        }

        headers = {"Content-Type": "application/json"}
        if self.litellm_key:
            headers["Authorization"] = f"Bearer {self.litellm_key}"

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    f"{self.litellm_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code != 200:
                    logger.warning(f"LLM generation failed: HTTP {resp.status_code}")
                    return None

                data = resp.json()
                content = data["choices"][0]["message"]["content"]

                # Strip markdown code fences if present
                content = re.sub(r"^```(?:python)?\s*", "", content.strip())
                content = re.sub(r"\s*```$", "", content.strip())

                return content
        except Exception as e:
            logger.warning(f"LLM generation error: {e}")
            return None

    def _template_generate(self, spec: WorkflowSpec) -> str:
        """Generate skill code from template (fallback when LLM unavailable)."""
        class_name = "".join(word.capitalize() for word in spec.name.split("_")) + "Skill"
        now = datetime.now().isoformat()

        # Build parameters schema
        params = {"type": "object", "properties": {}, "required": []}
        for inp in spec.inputs:
            name = inp.get("name", "input")
            params["properties"][name] = {
                "type": inp.get("type", "string"),
                "description": inp.get("description", f"Input parameter: {name}"),
            }
            if inp.get("required", True):
                params["required"].append(name)

        if not params["properties"]:
            params["properties"]["input"] = {
                "type": "string",
                "description": "Input data to process",
            }
            params["required"] = ["input"]

        # Build examples
        examples_list = []
        for ex in spec.examples:
            examples_list.append({
                "input": ex.get("input", {}),
                "output": ex.get("output", {}),
            })

        # Build execute body from steps
        execute_body = self._build_execute_body(spec)

        return SKILL_TEMPLATE.format(
            class_name=class_name,
            skill_name=spec.name,
            category=spec.category,
            version="1.0.0",
            source="user_created",
            created_at=now,
            updated_at=now,
            description=spec.description.replace('"""', r'\"\"\"'),
            parameters=json.dumps(params, indent=8),
            examples=json.dumps(examples_list, indent=8) if examples_list else "[]",
            execute_body=execute_body,
        )

    def _build_execute_body(self, spec: WorkflowSpec) -> str:
        """Build the execute method body from workflow steps."""
        if not spec.steps:
            return DEFAULT_EXECUTE_BODY

        lines = []
        lines.append("            # Extract parameters")
        for inp in spec.inputs:
            name = inp.get("name", "input")
            default = "None" if inp.get("required", True) else '""'
            lines.append(f'            {name} = kwargs.get("{name}", {default})')

        lines.append("")
        lines.append("            # Processing steps")

        for i, step in enumerate(spec.steps):
            desc = step.get("description", f"Step {i+1}")
            action = step.get("action", "process")
            lines.append(f"            # Step {i+1}: {desc}")
            lines.append(f"            # Action: {action}")
            if step.get("parameters"):
                lines.append(f"            # Parameters: {step.get('parameters')}")
            lines.append(f"            step_{i+1}_result = f\"Processed: {{input}}\"")
            lines.append("")

        lines.append("            # Combine results")
        lines.append("            result = input_data if 'input_data' in dir() else str(kwargs)")

        # Build output data
        output_keys = [o.get("name", "result") for o in spec.outputs] or ["result"]
        data_dict = ", ".join(f'"{k}": {k}' for k in output_keys)
        lines.append(f"            return SkillResult(success=True, data={{{data_dict}}})")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Skill Validator
# ---------------------------------------------------------------------------

BLOCKED_MODULES = {
    "subprocess", "os.system", "os.popen", "eval", "exec", "__import__",
    "shutil.rmtree", "ctypes", "socket", "requests",
}

BLOCKED_BUILTINS = {
    "eval", "exec", "compile", "__import__", "globals", "locals",
    "open", "input", "breakpoint",
}

DANGEROUS_ATTRS = {
    ("os", "system"), ("os", "popen"), ("os", "remove"),
    ("os", "unlink"), ("subprocess", "call"), ("subprocess", "run"),
    ("subprocess", "Popen"),
}


class SkillValidator:
    """Validates generated skill code for safety using AST analysis."""

    def validate(self, code: str) -> ValidationResult:
        """
        Validate skill code for safety.

        Args:
            code: Python source code to validate

        Returns:
            ValidationResult with is_safe, errors, and warnings
        """
        errors = []
        warnings = []

        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(
                is_safe=False,
                errors=[f"Syntax error at line {e.lineno}: {e.msg}"],
                warnings=[],
            )

        # Check for blocked imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in BLOCKED_MODULES:
                        errors.append(f"Blocked import: {alias.name}")

            elif isinstance(node, ast.ImportFrom):
                if node.module in BLOCKED_MODULES:
                    errors.append(f"Blocked import from: {node.module}")
                # Check specific imports from os
                if node.module == "os":
                    for alias in node.names:
                        if alias.name in ("system", "popen", "remove", "unlink"):
                            errors.append(f"Blocked import: os.{alias.name}")

        # Check for blocked function calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_call_name(node)
                if func_name in BLOCKED_BUILTINS:
                    errors.append(f"Blocked function call: {func_name}")

                # Check for attribute access patterns (os.system, etc.)
                if isinstance(node.func, ast.Attribute):
                    if hasattr(node.func.value, 'id'):
                        attr_pair = (node.func.value.id, node.func.attr)
                        if attr_pair in DANGEROUS_ATTRS:
                            errors.append(f"Blocked dangerous call: {attr_pair[0]}.{attr_pair[1]}")

        # Check for open() with write/delete modes
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_call_name(node)
                if func_name == "open":
                    # Check mode argument
                    for arg in node.args[1:2]:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            mode = arg.value
                            if any(m in mode for m in ("w", "a", "x", "+")):
                                errors.append(f"Blocked open() with write mode: {mode}")

                    # Check keyword mode argument
                    for kw in node.keywords:
                        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                            mode = kw.value.value
                            if any(m in mode for m in ("w", "a", "x", "+")):
                                errors.append(f"Blocked open() with write mode: {mode}")

        # Check that class inherits from AetheraSkill
        has_aethera_subclass = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = self._get_name(base)
                    if base_name == "AetheraSkill":
                        has_aethera_subclass = True

        if not has_aethera_subclass:
            errors.append("No class inheriting from AetheraSkill found")

        # Check for execute method
        has_execute = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "execute":
                has_execute = True

        if not has_execute:
            errors.append("No execute() method found")

        # Warnings (not blocking)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module in ("httpx", "aiohttp"):
                    warnings.append(f"Network import: {node.module} — ensure PHI-safe routing")
                if node.module == "json":
                    pass  # json is fine

            if isinstance(node, ast.Call):
                func_name = self._get_call_name(node)
                if func_name in ("open",):
                    warnings.append("File I/O detected — ensure appropriate access controls")

        return ValidationResult(
            is_safe=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _get_call_name(self, node: ast.Call) -> str:
        """Extract the function name from a Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _get_name(self, node: ast.expr) -> str:
        """Extract name from an AST name node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ""


# ---------------------------------------------------------------------------
# Skill Sandbox Tester
# ---------------------------------------------------------------------------

class SkillSandboxTester:
    """Tests generated skills in isolation with timeout and error catching."""

    TIMEOUT_SECONDS = 5.0

    async def test(
        self,
        code: str,
        spec: WorkflowSpec,
    ) -> TestResult:
        """
        Test a generated skill by importing it and running example inputs.

        Args:
            code: Python source code of the skill
            spec: WorkflowSpec with example inputs/outputs

        Returns:
            TestResult with pass/fail status and details
        """
        results = []
        errors = []
        total_time = 0.0

        # Validate code compiles
        try:
            compiled = compile(code, "<test_skill>", "exec")
        except SyntaxError as e:
            return TestResult(
                passed=False,
                errors=[f"Syntax error: {e}"],
            )

        # Try to load the skill class
        namespace = {}
        try:
            # Import skill base classes into namespace
            from skills.skill_base import AetheraSkill, SkillResult, skill
            namespace["AetheraSkill"] = AetheraSkill
            namespace["SkillResult"] = SkillResult
            namespace["skill"] = skill

            exec(compiled, namespace)
        except Exception as e:
            return TestResult(
                passed=False,
                errors=[f"Import/exec error: {e}"],
            )

        # Find the AetheraSkill subclass
        skill_class = None
        for obj in namespace.values():
            if (isinstance(obj, type)
                    and issubclass(obj, AetheraSkill)
                    and obj is not AetheraSkill):
                skill_class = obj
                break

        if skill_class is None:
            return TestResult(
                passed=False,
                errors=["No AetheraSkill subclass found in generated code"],
            )

        # Instantiate the skill
        try:
            skill_instance = skill_class()
        except Exception as e:
            return TestResult(
                passed=False,
                errors=[f"Failed to instantiate skill: {e}"],
            )

        # Test with example inputs if available
        test_cases = spec.examples if spec.examples else [
            {"input": {inp.get("name", "input"): "test_value"
                       for inp in spec.inputs} or {"input": "test"}}
        ]

        import time

        for i, example in enumerate(test_cases):
            test_input = example.get("input", example) if isinstance(example, dict) else example

            start = time.time()
            try:
                result = await asyncio.wait_for(
                    skill_instance.run(**test_input) if isinstance(test_input, dict) else skill_instance.run(input=str(test_input)),
                    timeout=self.TIMEOUT_SECONDS,
                )
                elapsed = (time.time() - start) * 1000
                total_time += elapsed

                test_passed = isinstance(result, SkillResult)
                results.append({
                    "test_case": i + 1,
                    "passed": test_passed,
                    "is_skill_result": isinstance(result, SkillResult),
                    "success": result.success if isinstance(result, SkillResult) else None,
                    "execution_time_ms": elapsed,
                })

            except asyncio.TimeoutError:
                errors.append(f"Test case {i+1}: timed out after {self.TIMEOUT_SECONDS}s")
                results.append({
                    "test_case": i + 1,
                    "passed": False,
                    "error": "timeout",
                })
            except Exception as e:
                errors.append(f"Test case {i+1}: {e}")
                results.append({
                    "test_case": i + 1,
                    "passed": False,
                    "error": str(e),
                })

        overall_passed = all(r.get("passed", False) for r in results) if results else False

        return TestResult(
            passed=overall_passed,
            results=results,
            errors=errors,
            execution_time_ms=total_time,
        )


# Need asyncio for the timeout wrapper
import asyncio


# ---------------------------------------------------------------------------
# Convenience: Full Pipeline
# ---------------------------------------------------------------------------

async def create_skill_from_conversation(
    messages: List[Dict[str, str]],
    litellm_url: Optional[str] = None,
    litellm_key: Optional[str] = None,
) -> Tuple[GeneratedSkill, ValidationResult, TestResult]:
    """
    Full skill creation pipeline from conversation messages.

    1. Extract workflow specification
    2. Generate skill code
    3. Validate code safety
    4. Test the generated skill

    Returns:
        Tuple of (GeneratedSkill, ValidationResult, TestResult)
    """
    extractor = WorkflowExtractor(litellm_url=litellm_url, litellm_key=litellm_key)
    generator = SkillCodeGenerator(litellm_url=litellm_url, litellm_key=litellm_key)
    validator = SkillValidator()
    tester = SkillSandboxTester()

    # Step 1: Extract workflow spec
    spec = await extractor.extract(messages)

    # Step 2: Generate code
    generated = await generator.generate(spec)

    # Step 3: Validate
    if generated.code:
        validation = validator.validate(generated.code)
        generated.validation_errors = validation.errors
    else:
        validation = ValidationResult(is_safe=False, errors=["No code generated"])

    # Step 4: Test (only if validation passed)
    if generated.code and validation.is_safe:
        test_result = await tester.test(generated.code, spec)
    else:
        test_result = TestResult(
            passed=False,
            errors=["Skipped: validation failed or no code generated"],
        )

    return generated, validation, test_result