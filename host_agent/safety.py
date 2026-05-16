"""
Aethera AI — Host Agent Safety Gate
Classifies PC control actions by risk level and determines
whether user confirmation is required before execution.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set

from .config import SHELL_SAFE_COMMANDS, CONFIRMATION_TIMEOUT


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class SafetyDecision:
    action: str
    risk_level: RiskLevel
    requires_confirmation: bool
    description: str
    timeout_seconds: int


# Action classification: maps action prefixes to (risk_level, requires_confirmation, description_template)
_ACTION_CLASSIFICATION: Dict[str, tuple] = {
    # Filesystem — destructive actions are HIGH
    "filesystem.delete": (RiskLevel.HIGH, True, "Delete: {path}"),
    "filesystem.write": (RiskLevel.MEDIUM, None, "Write file: {path}"),
    "filesystem.move": (RiskLevel.MEDIUM, True, "Move: {source} -> {destination}"),
    "filesystem.rename": (RiskLevel.MEDIUM, True, "Rename: {source} -> {destination}"),
    "filesystem.browse": (RiskLevel.LOW, False, "Browse directory: {path}"),
    "filesystem.read": (RiskLevel.LOW, False, "Read file: {path}"),
    "filesystem.search": (RiskLevel.LOW, False, "Search files: {pattern}"),

    # Application launcher — force close is HIGH
    "app.close": (RiskLevel.HIGH, True, "Force close application: {app}"),
    "app.kill": (RiskLevel.HIGH, True, "Kill process: {pid} {name}"),
    "app.open": (RiskLevel.LOW, False, "Open application: {app}"),
    "app.switch": (RiskLevel.LOW, False, "Switch to window: {title}"),
    "app.list": (RiskLevel.LOW, False, "List running applications"),

    # Shell execution — always requires confirmation unless safe
    "shell.execute": (RiskLevel.HIGH, None, "Execute command: {command}"),

    # Screen capture — LOW risk, but still audited
    "screen.capture": (RiskLevel.LOW, False, "Capture screen"),
    "screen.ocr": (RiskLevel.LOW, False, "OCR screen text"),

    # Clipboard — write is MEDIUM
    "clipboard.read": (RiskLevel.LOW, False, "Read clipboard"),
    "clipboard.write": (RiskLevel.MEDIUM, None, "Write to clipboard: {content_preview}"),

    # System monitor — always LOW
    "system.stats": (RiskLevel.LOW, False, "Get system statistics"),
    "system.processes": (RiskLevel.LOW, False, "List processes"),

    # Browser — form fills are MEDIUM
    "browser.navigate": (RiskLevel.LOW, False, "Navigate to: {url}"),
    "browser.extract": (RiskLevel.LOW, False, "Extract data from page"),
    "browser.screenshot": (RiskLevel.LOW, False, "Browser screenshot"),
    "browser.fill": (RiskLevel.MEDIUM, None, "Fill form field: {selector}"),
    "browser.click": (RiskLevel.MEDIUM, None, "Click element: {selector}"),
    "browser.submit": (RiskLevel.MEDIUM, True, "Submit form on page"),
}


class SafetyGate:
    """
    Classifies PC control actions and determines confirmation requirements.

    For actions where confirmation is None (conditional), additional logic
    determines whether confirmation is needed based on parameters.
    """

    def __init__(self, confirmation_timeout: int = CONFIRMATION_TIMEOUT):
        self.confirmation_timeout = confirmation_timeout
        self._safe_shell_commands: Set[str] = SHELL_SAFE_COMMANDS

    def classify(self, action: str, parameters: dict) -> SafetyDecision:
        """
        Classify an action and determine if confirmation is required.

        Args:
            action: The action string (e.g., "filesystem.delete")
            parameters: The action parameters dict

        Returns:
            SafetyDecision with risk level and confirmation requirement
        """
        # Find matching classification (exact match first, then prefix)
        risk_level, confirm, desc_template = self._find_classification(action)

        # Build description from template
        description = desc_template.format(**{k: v for k, v in parameters.items() if isinstance(v, str)})

        # Resolve conditional confirmation (None means "depends on context")
        requires_confirmation = self._resolve_confirmation(action, parameters, confirm)

        return SafetyDecision(
            action=action,
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
            description=description,
            timeout_seconds=self.confirmation_timeout,
        )

    def _find_classification(self, action: str) -> tuple:
        """Find the classification for an action, with fallback."""
        if action in _ACTION_CLASSIFICATION:
            return _ACTION_CLASSIFICATION[action]
        # Try prefix match
        prefix = action.rsplit(".", 1)[0] if "." in action else action
        if prefix in _ACTION_CLASSIFICATION:
            return _ACTION_CLASSIFICATION[prefix]
        # Default: unknown action is HIGH risk requiring confirmation
        return (RiskLevel.HIGH, True, f"Unknown action: {action}")

    def _resolve_confirmation(self, action: str, parameters: dict, confirm: Optional[bool]) -> bool:
        """Resolve conditional confirmation based on action and parameters."""
        if confirm is not None:
            return confirm

        # Conditional logic for actions where confirmation depends on parameters
        if action == "filesystem.write":
            # Writing to an existing file requires confirmation
            import os
            path = parameters.get("path", "")
            return os.path.exists(path) if path else True

        if action == "shell.execute":
            # Safe commands don't require confirmation
            command = parameters.get("command", "").strip()
            first_word = command.split()[0].lower() if command else ""
            return first_word not in self._safe_shell_commands

        if action == "clipboard.write":
            # Writing clipboard content requires confirmation by default
            return True

        if action in ("browser.fill", "browser.click"):
            return True  # Form interactions require confirmation by default

        # Default: require confirmation for uncertain actions
        return True

    def get_all_actions(self) -> List[str]:
        """Return all known action strings."""
        return list(_ACTION_CLASSIFICATION.keys())

    def get_actions_requiring_confirmation(self) -> List[str]:
        """Return actions that always require confirmation."""
        return [a for a, (_, c, _) in _ACTION_CLASSIFICATION.items() if c is True]