"""
Aethera AI — Host Agent System Monitor Handler
Provides CPU, RAM, GPU, disk, and network statistics via psutil and GPUtil.
"""
import platform
from typing import Dict, Any

import psutil

try:
    import GPUtil
    HAS_GPUTIL = True
except ImportError:
    HAS_GPUTIL = False


class SystemMonitorHandler:
    """Handles system.stats and system.processes actions."""

    async def handle(self, action: str, parameters: dict) -> Dict[str, Any]:
        """
        Dispatch a system monitor action.

        Args:
            action: "system.stats" or "system.processes"
            parameters: Action-specific parameters

        Returns:
            Result dict with system information
        """
        if action == "system.stats":
            return await self.stats(parameters)
        elif action == "system.processes":
            return await self.processes(parameters)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    async def stats(self, parameters: dict) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_per_core = psutil.cpu_percent(interval=0, percpu=True)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()
        boot_time = psutil.boot_time()

        result = {
            "success": True,
            "data": {
                "hostname": platform.node(),
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu": {
                    "percent": cpu_percent,
                    "per_core": cpu_per_core,
                    "count_physical": psutil.cpu_count(logical=False),
                    "count_logical": psutil.cpu_count(logical=True),
                    "freq": None,
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": round(disk.percent, 1),
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent if net_io else 0,
                    "bytes_recv": net_io.bytes_recv if net_io else 0,
                    "packets_sent": net_io.packets_sent if net_io else 0,
                    "packets_recv": net_io.packets_recv if net_io else 0,
                },
                "boot_time": boot_time,
                "uptime_seconds": psutil.time.time() - boot_time if hasattr(psutil, 'time') else 0,
            },
        }

        # Add CPU frequency if available
        try:
            freq = psutil.cpu_freq()
            if freq:
                result["data"]["cpu"]["freq"] = {
                    "current": freq.current,
                    "min": freq.min,
                    "max": freq.max,
                }
        except (NotImplementedError, FileNotFoundError):
            pass

        # Add disk I/O stats
        if disk_io:
            result["data"]["disk_io"] = {
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes,
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count,
            }

        # Add GPU stats if available
        if HAS_GPUTIL:
            try:
                gpus = GPUtil.getGPUs()
                result["data"]["gpu"] = []
                for gpu in gpus:
                    result["data"]["gpu"].append({
                        "id": gpu.id,
                        "name": gpu.name,
                        "load_percent": round(gpu.load * 100, 1),
                        "memory_total_mb": round(gpu.memoryTotal),
                        "memory_used_mb": round(gpu.memoryUsed),
                        "memory_free_mb": round(gpu.memoryFree),
                        "memory_percent": round(gpu.memoryUsed / gpu.memoryTotal * 100, 1) if gpu.memoryTotal > 0 else 0,
                        "temperature_c": gpu.temperature,
                    })
            except Exception:
                result["data"]["gpu"] = "unavailable"

        return result

    async def processes(self, parameters: dict) -> Dict[str, Any]:
        """List running processes with optional filtering."""
        sort_by = parameters.get("sort_by", "memory_percent")
        limit = min(parameters.get("limit", 50), 200)
        name_filter = parameters.get("name_filter", "").lower()

        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
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
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort
        key = sort_by if sort_by in ("cpu_percent", "memory_percent", "pid") else "memory_percent"
        procs.sort(key=lambda p: p.get(key, 0), reverse=(key != "pid"))

        return {
            "success": True,
            "data": {
                "processes": procs[:limit],
                "total": len(procs),
                "sort_by": key,
            },
        }