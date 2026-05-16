"""
Aethera AI — PC Control Skill
Orchestrator-side skill that routes PC control commands
to the connected host agent via the PCControlManager.
"""
from typing import Any, Dict

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="pc_control", category="system")
class PCControlSkill(AetheraSkill):
    """Skill for controlling the user's PC via the host agent."""

    @property
    def name(self) -> str:
        return "pc_control"

    @property
    def description(self) -> str:
        return (
            "Control the user's PC: browse files, launch apps, run commands, "
            "capture screens, read/write clipboard, monitor system stats, "
            "and automate web browsers. Destructive actions require confirmation."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The PC control action to execute",
                    "enum": [
                        "filesystem.browse", "filesystem.read", "filesystem.write",
                        "filesystem.delete", "filesystem.move", "filesystem.search",
                        "app.open", "app.close", "app.list", "app.switch",
                        "shell.execute",
                        "screen.capture", "screen.ocr",
                        "clipboard.read", "clipboard.write",
                        "system.stats", "system.processes",
                        "browser.navigate", "browser.extract", "browser.screenshot",
                    ],
                },
                "parameters": {
                    "type": "object",
                    "description": "Action-specific parameters",
                    "properties": {
                        "path": {"type": "string", "description": "File/directory path"},
                        "content": {"type": "string", "description": "Content to write"},
                        "command": {"type": "string", "description": "Shell command to execute"},
                        "url": {"type": "string", "description": "URL to navigate to"},
                        "name": {"type": "string", "description": "Application name"},
                        "query": {"type": "string", "description": "Search query"},
                    },
                },
            },
            "required": ["action"],
        }

    @property
    def requires_phi_protection(self) -> bool:
        return False

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        params = kwargs.get("parameters", {})
        user_id = kwargs.get("user_id", "default_user")
        session_id = kwargs.get("session_id", "")

        if not action:
            return SkillResult(success=False, error="Action is required")

        # Get the PC control manager
        from orchestrator.pc_control import get_pc_control_manager
        manager = get_pc_control_manager()

        # Check if a host agent is connected
        status = manager.get_status()
        if status["total_agents"] == 0:
            return SkillResult(
                success=False,
                error="No host agent connected. Please start the host agent on your PC.",
                metadata={"action": action, "host_agent_required": True},
            )

        # Send command to host agent
        result = await manager.send_command(
            action=action,
            parameters=params,
            user_id=user_id,
            session_id=session_id,
        )

        # Convert result to SkillResult
        if result.get("success"):
            return SkillResult(
                success=True,
                data=result.get("data", {}),
                metadata={"action": action, "requires_confirmation": False},
            )
        else:
            # Check if confirmation is required
            if result.get("requires_confirmation"):
                return SkillResult(
                    success=False,
                    error=result.get("error", "Action requires confirmation"),
                    data=result.get("data", {}),
                    metadata={
                        "action": action,
                        "requires_confirmation": True,
                        "command_id": result.get("command_id"),
                        "description": result.get("description", ""),
                        "risk_level": result.get("risk_level", "high"),
                    },
                )
            return SkillResult(
                success=False,
                error=result.get("error", "Command failed"),
                metadata={"action": action},
            )