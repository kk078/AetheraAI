"""
Aethera AI - Code Executor Skill

Sandboxed Python code execution with timeout, stdout/stderr capture,
restricted builtins, and structured results.
Uses subprocess isolation for safety.
"""

import ast
import json
import os
import subprocess
import sys
import textwrap
import tempfile
from typing import Any, Dict, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


# Restricted builtins that are never allowed
_UNSAFE_BUILTINS = frozenset({
    "__import__",
    "exec",
    "eval",
    "compile",
    "open",
    "input",
    "breakpoint",
    "memoryview",
    "globals",
    "locals",
    "vars",
    "dir",
    "getattr",
    "setattr",
    "delattr",
    "hasattr",
    "object",
    "type",
    "__build_class__",
})

# Modules that are never importable inside sandbox
_UNSAFE_MODULES = frozenset({
    "os",
    "sys",
    "subprocess",
    "shutil",
    "signal",
    "ctypes",
    "multiprocessing",
    "socket",
    "http",
    "urllib",
    "requests",
    "ftplib",
    "smtplib",
    "telnetlib",
    "xmlrpc",
    "asyncio",
    "threading",
    "concurrent",
    "pickle",
    "shelve",
    "marshal",
    "code",
    "codeop",
    "compileall",
    "pdb",
    "webbrowser",
    "antigravity",
    "distutils",
    "site",
    "importlib",
    "pkgutil",
    "zipimport",
    "winreg",
})

# Safe standard library modules
_SAFE_MODULES = frozenset({
    "math",
    "statistics",
    "random",
    "decimal",
    "fractions",
    "itertools",
    "collections",
    "functools",
    "operator",
    "re",
    "json",
    "datetime",
    "time",
    "string",
    "textwrap",
    "copy",
    "heapq",
    "bisect",
    "enum",
    "typing",
    "dataclasses",
    "difflib",
    "hashlib",
    "base64",
    "uuid",
    "pprint",
    "csv",
    "io",
    "struct",
})


@skill(name="code_executor", category="developer")
class CodeExecutorSkill(AetheraSkill):
    """
    Execute Python code in a sandboxed subprocess with timeout,
    restricted builtins, and structured output capture.
    """

    @property
    def name(self) -> str:
        return "code_executor"

    @property
    def description(self) -> str:
        return (
            "Execute Python code in a sandboxed environment with timeout, "
            "restricted builtins, stdout/stderr capture, and structured results"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds (max 60)",
                    "default": 10,
                },
                "allowed_modules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional module names to allow beyond the default safe set",
                },
                "capture_output_limit": {
                    "type": "integer",
                    "description": "Maximum characters of stdout/stderr to capture",
                    "default": 50000,
                },
                "input_data": {
                    "type": "object",
                    "description": "Key-value pairs injected as variables into the execution namespace",
                },
            },
            "required": ["code"],
        }

    @property
    def examples(self) -> list:
        return [
            {"input": {"code": "print(sum(range(1, 101)))"}},
            {"input": {"code": "import math\nprint(math.sqrt(144))", "timeout": 5}},
            {"input": {"code": "result = [x**2 for x in range(10)]\nprint(result)", "allowed_modules": ["math"]}},
        ]

    @property
    def cache_ttl(self) -> int:
        return 0  # Never cache code execution results

    async def execute(self, **kwargs) -> SkillResult:
        code = kwargs.get("code", "")
        if not code:
            return SkillResult(success=False, error="Code is required")

        timeout = min(kwargs.get("timeout", 10), 60)
        extra_modules = kwargs.get("allowed_modules", [])
        output_limit = kwargs.get("capture_output_limit", 50000)
        input_data = kwargs.get("input_data", {})

        # Static analysis: reject code containing unsafe patterns before execution
        safety_error = self._static_safety_check(code)
        if safety_error:
            return SkillResult(success=False, error=safety_error)

        # Build the set of allowed modules
        allowed_modules = _SAFE_MODULES | frozenset(extra_modules)

        # Build the sandboxed runner script
        runner_code = self._build_runner(code, allowed_modules, input_data, output_limit, timeout)

        # Execute in subprocess
        try:
            result = self._run_subprocess(runner_code, timeout)
            return SkillResult(success=True, data=result)
        except Exception as e:
            return SkillResult(success=False, error=f"Execution error: {e}")

    # ------------------------------------------------------------------
    # Static safety analysis
    # ------------------------------------------------------------------

    def _static_safety_check(self, code: str) -> Optional[str]:
        """Parse the code with ast and reject clearly unsafe patterns."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"Syntax error in code: {e}"

        for node in ast.walk(tree):
            # Block __import__ calls
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "__import__":
                    return "Forbidden: __import__ is not allowed"
                # Block eval / exec calls
                if isinstance(func, ast.Name) and func.id in ("eval", "exec", "compile"):
                    return f"Forbidden: {func.id}() is not allowed"

            # Block attribute access to dunder attributes like obj.__class__
            if isinstance(node, ast.Attribute):
                attr_name = node.attr
                if attr_name.startswith("__") and attr_name.endswith("__"):
                    # Allow a small whitelist of safe dunder attrs
                    safe_dunder = {"__name__", "__doc__", "__version__"}
                    if attr_name not in safe_dunder:
                        return f"Forbidden: access to {attr_name} is not allowed"

        return None

    # ------------------------------------------------------------------
    # Runner script generation
    # ------------------------------------------------------------------

    def _build_runner(self, user_code: str, allowed_modules: frozenset, input_data: dict, output_limit: int, timeout: int = 30) -> str:
        """Build a self-contained Python script that runs user code in a restricted namespace."""
        # Serialize input_data as JSON for injection
        input_json = json.dumps(input_data, default=str)

        # Build the import guard
        allowed_modules_str = repr(sorted(allowed_modules))

        runner = f'''
import sys
import json
import signal
import traceback
import io
import builtins as _builtins

# ---- Timeout handler ----
def _timeout_handler(signum, frame):
    raise TimeoutError("Execution timed out")

signal.signal(signal.SIGALRM, _timeout_handler)
signal.alarm({min(timeout, 60)})

# ---- Restricted import ----
_original_import = _builtins.__import__

def _restricted_import(name, *args, **kwargs):
    top_level = name.split(".")[0]
    _allowed = {allowed_modules_str}
    if top_level not in _allowed:
        raise ImportError(f"Module '{{name}}' is not allowed in sandbox. Allowed: {{sorted(_allowed)}}")
    return _original_import(name, *args, **kwargs)

_builtins.__import__ = _restricted_import

# ---- Restricted builtins ----
_safe_builtins = {{k: v for k, v in vars(_builtins).items()}}
_unsafe = {repr(sorted(_UNSAFE_BUILTINS))}
for _u in _unsafe:
    _safe_builtins.pop(_u, None)

class _NoOpen:
    """Stub that blocks file open."""
    def __call__(self, *a, **kw):
        raise PermissionError("open() is not allowed in sandbox")
    def __getattr__(self, name):
        raise PermissionError("open() is not allowed in sandbox")

_safe_builtins["open"] = _NoOpen()
_safe_builtins["__import__"] = _restricted_import

# ---- Namespace with input_data ----
_namespace = dict(_safe_builtins)
_input_data = json.loads({repr(input_json)})
_namespace.update(_input_data)

# ---- Capture stdout/stderr ----
_stdout_buf = io.StringIO()
_stderr_buf = io.StringIO()
_old_stdout = sys.stdout
_old_stderr = sys.stderr
sys.stdout = _stdout_buf
sys.stderr = _stderr_buf

# ---- Execute user code ----
_result = {{
    "success": False,
    "stdout": "",
    "stderr": "",
    "return_value": None,
    "error": None,
    "error_traceback": None,
}}

try:
    exec({repr(user_code)}, _namespace)
    _result["success"] = True
except Exception as _e:
    _result["success"] = False
    _result["error"] = str(_e)
    _result["error_traceback"] = traceback.format_exc()
finally:
    sys.stdout = _old_stdout
    sys.stderr = _old_stderr
    _result["stdout"] = _stdout_buf.getvalue()[:{output_limit}]
    _result["stderr"] = _stderr_buf.getvalue()[:{output_limit}]

    # Capture last expression result if user assigned to 'result' or 'return_value'
    for _rv_name in ("result", "return_value", "output"):
        if _rv_name in _namespace:
            try:
                json.dumps(_namespace[_rv_name])  # Check serializable
                _result["return_value"] = _namespace[_rv_name]
            except (TypeError, ValueError):
                _result["return_value"] = repr(_namespace[_rv_name])
            break

print(json.dumps(_result))
'''
        return runner

    # ------------------------------------------------------------------
    # Subprocess execution
    # ------------------------------------------------------------------

    def _run_subprocess(self, runner_code: str, timeout: int) -> Dict[str, Any]:
        """Run the sandboxed code in a subprocess and collect results."""
        # Write runner to a temp file to avoid command-line escaping issues
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, f"aethera_sandbox_{os.getpid()}.py")

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(runner_code)

            proc = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmp_dir,
                # Restrict environment
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "TEMP": tmp_dir,
                    "TMP": tmp_dir,
                    "HOME": tmp_dir,
                    "USER": "sandbox",
                    "PYTHONIOENCODING": "utf-8",
                    "PYTHONUNBUFFERED": "1",
                    "NO_COLOR": "1",
                },
            )

            # Parse the JSON result printed by the runner
            stdout = proc.stdout
            stderr = proc.stderr

            if proc.returncode != 0 and not stdout.strip():
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": stderr[:50000],
                    "error": f"Process exited with code {proc.returncode}",
                    "error_traceback": stderr[:50000],
                    "return_value": None,
                }

            # The runner prints a JSON line as the last line of stdout
            try:
                # Find the JSON result line (last non-empty line)
                lines = stdout.strip().split("\n")
                result_line = lines[-1] if lines else ""
                # But there might be user print() output before the JSON result
                # The runner uses exec() then prints json at the end
                # So the very last output should be the JSON
                result = json.loads(result_line)
            except json.JSONDecodeError:
                # If we cannot parse JSON, treat all stdout as captured output
                result = {
                    "success": True,
                    "stdout": stdout[:50000],
                    "stderr": stderr[:50000],
                    "return_value": None,
                    "error": None,
                    "error_traceback": None,
                }

            # If the runner printed output before the JSON, capture it separately
            all_lines = stdout.strip().split("\n")
            if len(all_lines) > 1:
                try:
                    json.loads(all_lines[-1])
                    # Lines before the JSON are user stdout
                    user_stdout = "\n".join(all_lines[:-1])
                    # Use user_stdout if the parsed result has empty stdout
                    if not result.get("stdout") and user_stdout:
                        result["stdout"] = user_stdout[:50000]
                except json.JSONDecodeError:
                    pass

            if stderr:
                result["stderr"] = (result.get("stderr", "") + "\n" + stderr[:50000])[:50000]

            result["exit_code"] = proc.returncode
            result["timeout"] = timeout
            return result

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "error": f"Execution timed out after {timeout} seconds",
                "error_traceback": None,
                "return_value": None,
                "timeout": timeout,
            }
        finally:
            # Clean up temp file
            try:
                os.remove(tmp_path)
            except OSError:
                pass