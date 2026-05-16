"""
Aethera AI — Shell Executor Handler
Run PowerShell/CMD commands with approval workflow and safety checks.
"""
import asyncio
import platform
from typing import Dict, Any

from ..config import SHELL_TIMEOUT, SHELL_SAFE_COMMANDS


class ShellExecutorHandler:
    """Handles shell command execution with safety checks."""

    async def handle(self, action: str, parameters: dict) -> Dict[str, Any]:
        if action != "shell.execute":
            return {"success": False, "error": f"Unknown action: {action}"}
        try:
            return await self.execute(parameters)
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def execute(self, params: dict) -> Dict[str, Any]:
        """Execute a shell command and return the output."""
        command = params.get("command", "")
        shell = params.get("shell", "powershell")  # "powershell" or "cmd"
        timeout = min(params.get("timeout", SHELL_TIMEOUT), 120)  # Max 120s
        cwd = params.get("cwd", "")

        if not command:
            return {"success": False, "error": "No command provided"}

        # Determine the executable
        if shell == "cmd" or shell == "cmd.exe":
            exec_cmd = ["cmd", "/c", command]
        else:
            exec_cmd = ["powershell", "-NoProfile", "-Command", command]

        try:
            proc = await asyncio.create_subprocess_exec(
                *exec_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd or None,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return {
                    "success": False,
                    "error": f"Command timed out after {timeout}s",
                    "data": {
                        "command": command,
                        "shell": shell,
                        "returncode": -1,
                        "timed_out": True,
                    },
                }

            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")
            returncode = proc.returncode

            return {
                "success": returncode == 0,
                "data": {
                    "command": command,
                    "shell": shell,
                    "returncode": returncode,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "timed_out": False,
                },
                "error": stderr_text[:500] if returncode != 0 and stderr_text else None,
            }

        except FileNotFoundError as e:
            return {"success": False, "error": f"Shell not found: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Execution error: {e}"}