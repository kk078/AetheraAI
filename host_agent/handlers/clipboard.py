"""
Aethera AI — Clipboard Handler
Read from and write to the system clipboard.
"""
import subprocess
import sys
from typing import Dict, Any

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


class ClipboardHandler:
    """Handles clipboard read and write operations."""

    async def handle(self, action: str, parameters: dict) -> Dict[str, Any]:
        dispatch = {
            "clipboard.read": self.read_clipboard,
            "clipboard.write": self.write_clipboard,
            "clipboard.clear": self.clear_clipboard,
        }
        handler = dispatch.get(action)
        if handler is None:
            return {"success": False, "error": f"Unknown action: {action}"}
        try:
            return await handler(parameters)
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def read_clipboard(self, params: dict) -> Dict[str, Any]:
        """Read the current clipboard content."""
        if HAS_PYPERCLIP:
            try:
                content = pyperclip.paste()
                return {
                    "success": True,
                    "data": {
                        "content": content,
                        "length": len(content),
                        "type": "text",
                    },
                }
            except pyperclip.PyperclipException:
                pass

        # Fallback: use PowerShell on Windows
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                    capture_output=True, text=True, timeout=5,
                )
                content = result.stdout
                return {
                    "success": True,
                    "data": {
                        "content": content,
                        "length": len(content),
                        "type": "text",
                    },
                }
            except Exception as e:
                return {"success": False, "error": f"Failed to read clipboard: {e}"}

        return {"success": False, "error": "No clipboard access method available"}

    async def write_clipboard(self, params: dict) -> Dict[str, Any]:
        """Write content to the clipboard."""
        content = params.get("content", "")
        content_type = params.get("type", "text")  # "text" or "html"

        if HAS_PYPERCLIP:
            try:
                pyperclip.copy(content)
                return {
                    "success": True,
                    "data": {
                        "length": len(content),
                        "type": content_type,
                        "message": "Clipboard updated",
                    },
                }
            except pyperclip.PyperclipException:
                pass

        # Fallback: use PowerShell on Windows
        if sys.platform == "win32":
            try:
                # Escape single quotes in content for PowerShell
                escaped = content.replace("'", "''")
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value '{escaped}'"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    return {
                        "success": True,
                        "data": {
                            "length": len(content),
                            "type": content_type,
                            "message": "Clipboard updated",
                        },
                    }
                return {"success": False, "error": f"Set-Clipboard failed: {result.stderr}"}
            except Exception as e:
                return {"success": False, "error": f"Failed to write clipboard: {e}"}

        return {"success": False, "error": "No clipboard access method available"}

    async def clear_clipboard(self, params: dict) -> Dict[str, Any]:
        """Clear the clipboard."""
        return await self.write_clipboard({"content": "", "type": "text"})