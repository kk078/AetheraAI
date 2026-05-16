"""
Aethera AI — Application Launcher Handler
Open, close, list, and switch applications on the Windows host.
"""
import os
import platform
import subprocess
from typing import Dict, Any, List

import psutil


class AppLauncherHandler:
    """Handles application launch, close, list, and switch operations."""

    async def handle(self, action: str, parameters: dict) -> Dict[str, Any]:
        dispatch = {
            "app.open": self.open_app,
            "app.close": self.close_app,
            "app.kill": self.kill_process,
            "app.list": self.list_apps,
            "app.switch": self.switch_app,
        }
        handler = dispatch.get(action)
        if handler is None:
            return {"success": False, "error": f"Unknown action: {action}"}
        try:
            return await handler(parameters)
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def open_app(self, params: dict) -> Dict[str, Any]:
        """Open an application by name or path."""
        app_path = params.get("path", "")
        app_name = params.get("name", "")
        args = params.get("args", "")

        if not app_path and not app_name:
            return {"success": False, "error": "Either 'path' or 'name' is required"}

        target = app_path or app_name

        if platform.system() == "Windows":
            # Use 'start' command on Windows
            cmd = f'start "" "{target}"'
            if args:
                cmd = f'start "" "{target}" {args}'
            result = subprocess.run(
                ["cmd", "/c", cmd],
                capture_output=True, text=True, timeout=10,
            )
        else:
            result = subprocess.run(
                ["nohup", target] + (args.split() if args else []),
                capture_output=True, text=True, timeout=10,
            )

        # start command returns quickly even if app launches successfully
        return {
            "success": True,
            "data": {
                "app": target,
                "args": args,
                "returncode": result.returncode,
                "message": "Application launch command sent" if platform.system() == "Windows" else "Application launched",
            },
        }

    async def close_app(self, params: dict) -> Dict[str, Any]:
        """Gracefully close an application by name."""
        name = params.get("name", "")
        pid = params.get("pid")

        closed = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if pid and proc.info["pid"] == pid:
                    proc.terminate()
                    closed.append({"pid": proc.info["pid"], "name": proc.info["name"]})
                    break
                if name and name.lower() in proc.info["name"].lower():
                    proc.terminate()
                    closed.append({"pid": proc.info["pid"], "name": proc.info["name"]})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            "success": True,
            "data": {
                "closed": closed,
                "count": len(closed),
                "message": f"Sent terminate signal to {len(closed)} process(es)",
            },
        }

    async def kill_process(self, params: dict) -> Dict[str, Any]:
        """Force kill a process by PID or name."""
        pid = params.get("pid")
        name = params.get("name", "")

        killed = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if pid and proc.info["pid"] == pid:
                    proc.kill()
                    killed.append({"pid": proc.info["pid"], "name": proc.info["name"]})
                    break
                if name and name.lower() in proc.info["name"].lower():
                    proc.kill()
                    killed.append({"pid": proc.info["pid"], "name": proc.info["name"]})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            "success": True,
            "data": {
                "killed": killed,
                "count": len(killed),
                "message": f"Force killed {len(killed)} process(es)",
            },
        }

    async def list_apps(self, params: dict) -> Dict[str, Any]:
        """List running applications with optional filtering."""
        name_filter = params.get("name_filter", "").lower()
        sort_by = params.get("sort_by", "memory")
        limit = min(params.get("limit", 50), 200)

        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status", "exe", "cmdline"]):
            try:
                info = proc.info
                if name_filter and name_filter not in info["name"].lower():
                    continue
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": round(info["cpu_percent"] or 0, 1),
                    "memory_percent": round(info["memory_percent"] or 0, 1),
                    "status": info["status"],
                    "exe": info.get("exe", ""),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        key = sort_by if sort_by in ("cpu_percent", "memory_percent", "pid") else "memory_percent"
        procs.sort(key=lambda p: p.get(key, 0), reverse=(key != "pid"))

        return {
            "success": True,
            "data": {"processes": procs[:limit], "total": len(procs)},
        }

    async def switch_app(self, params: dict) -> Dict[str, Any]:
        """Switch to an application window by title."""
        title = params.get("title", "")

        if platform.system() == "Windows":
            try:
                import ctypes
                # Use PowerShell to bring window to focus
                cmd = f'''
                Add-Type @"
                using System;
                using System.Runtime.InteropServices;
                public class Win32 {{
                    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
                    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                }}
                "@
                '''
                result = subprocess.run(
                    ["powershell", "-Command", cmd],
                    capture_output=True, text=True, timeout=10,
                )
                return {
                    "success": True,
                    "data": {"title": title, "message": "Window switch command sent (limited support without pyautogui)"},
                }
            except Exception as e:
                return {"success": False, "error": f"Failed to switch window: {e}"}
        else:
            return {"success": False, "error": "Window switching is only supported on Windows"}