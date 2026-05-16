"""
Aethera AI — Filesystem Handler
Browse, read, write, delete, move, and organize files on the host.
"""
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from ..config import MAX_FILE_SIZE, MAX_DIRECTORY_DEPTH


class FilesystemHandler:
    """Handles filesystem operations on the Windows host."""

    async def handle(self, action: str, parameters: dict) -> Dict[str, Any]:
        dispatch = {
            "filesystem.browse": self.browse,
            "filesystem.read": self.read,
            "filesystem.write": self.write,
            "filesystem.delete": self.delete,
            "filesystem.move": self.move,
            "filesystem.rename": self.rename,
            "filesystem.search": self.search,
            "filesystem.mkdir": self.mkdir,
            "filesystem.exists": self.exists,
            "filesystem.info": self.info,
        }
        handler = dispatch.get(action)
        if handler is None:
            return {"success": False, "error": f"Unknown action: {action}"}
        try:
            return await handler(parameters)
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def browse(self, params: dict) -> Dict[str, Any]:
        """List directory contents with metadata."""
        path = params.get("path", str(Path.home()))
        pattern = params.get("pattern", "*")
        show_hidden = params.get("show_hidden", False)

        path_obj = Path(path)
        if not path_obj.exists():
            return {"success": False, "error": f"Path does not exist: {path}"}
        if not path_obj.is_dir():
            return {"success": False, "error": f"Path is not a directory: {path}"}

        entries = []
        try:
            for entry in path_obj.iterdir():
                if not show_hidden and entry.name.startswith("."):
                    continue
                if pattern != "*" and not entry.match(pattern):
                    continue
                try:
                    stat = entry.stat()
                    entries.append({
                        "name": entry.name,
                        "path": str(entry),
                        "is_dir": entry.is_dir(),
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "extension": entry.suffix if entry.is_file() else "",
                    })
                except (PermissionError, OSError):
                    entries.append({"name": entry.name, "path": str(entry), "error": "access denied"})
        except PermissionError:
            return {"success": False, "error": f"Permission denied: {path}"}

        # Sort: directories first, then by name
        entries.sort(key=lambda e: (not e.get("is_dir", False), e.get("name", "")))

        return {
            "success": True,
            "data": {
                "path": str(path_obj),
                "parent": str(path_obj.parent),
                "entries": entries,
                "total": len(entries),
            },
        }

    async def read(self, params: dict) -> Dict[str, Any]:
        """Read file contents."""
        path = params.get("path", "")
        encoding = params.get("encoding", "utf-8")
        offset = params.get("offset", 0)
        limit = params.get("limit", 0)  # 0 = read all

        path_obj = Path(path)
        if not path_obj.exists():
            return {"success": False, "error": f"File not found: {path}"}
        if path_obj.is_dir():
            return {"success": False, "error": f"Path is a directory: {path}"}
        if path_obj.stat().st_size > MAX_FILE_SIZE:
            return {"success": False, "error": f"File too large (max {MAX_FILE_SIZE} bytes)"}

        try:
            # Try text first, fall back to binary info
            with open(path, "r", encoding=encoding, errors="replace") as f:
                if offset:
                    for _ in range(offset):
                        f.readline()
                if limit:
                    lines = [f.readline() for _ in range(limit)]
                    content = "".join(lines)
                else:
                    content = f.read()
        except UnicodeDecodeError:
            return {
                "success": True,
                "data": {
                    "path": str(path_obj),
                    "size": path_obj.stat().st_size,
                    "binary": True,
                    "content": f"[Binary file: {path_obj.stat().st_size} bytes]",
                    "encoding": encoding,
                },
            }

        return {
            "success": True,
            "data": {
                "path": str(path_obj),
                "content": content,
                "size": path_obj.stat().st_size,
                "encoding": encoding,
                "binary": False,
            },
        }

    async def write(self, params: dict) -> Dict[str, Any]:
        """Write content to a file."""
        path = params.get("path", "")
        content = params.get("content", "")
        encoding = params.get("encoding", "utf-8")
        append = params.get("append", False)

        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if append else "w"
        with open(path, mode, encoding=encoding) as f:
            f.write(content)

        return {
            "success": True,
            "data": {
                "path": str(path_obj),
                "size": path_obj.stat().st_size,
                "appended": append,
            },
        }

    async def delete(self, params: dict) -> Dict[str, Any]:
        """Delete a file or directory."""
        path = params.get("path", "")
        path_obj = Path(path)

        if not path_obj.exists():
            return {"success": False, "error": f"Path not found: {path}"}

        if path_obj.is_dir():
            shutil.rmtree(str(path_obj))
        else:
            path_obj.unlink()

        return {"success": True, "data": {"path": str(path_obj), "deleted": True}}

    async def move(self, params: dict) -> Dict[str, Any]:
        """Move a file or directory."""
        source = params.get("source", "")
        destination = params.get("destination", "")

        src = Path(source)
        dst = Path(destination)

        if not src.exists():
            return {"success": False, "error": f"Source not found: {source}"}

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

        return {"success": True, "data": {"source": str(src), "destination": str(dst)}}

    async def rename(self, params: dict) -> Dict[str, Any]:
        """Rename a file or directory."""
        source = params.get("source", "")
        new_name = params.get("new_name", "")

        src = Path(source)
        if not src.exists():
            return {"success": False, "error": f"Source not found: {source}"}

        dst = src.parent / new_name
        src.rename(dst)

        return {"success": True, "data": {"old_path": str(src), "new_path": str(dst)}}

    async def search(self, params: dict) -> Dict[str, Any]:
        """Search for files by name pattern."""
        path = params.get("path", str(Path.home()))
        pattern = params.get("pattern", "*")
        max_depth = min(params.get("max_depth", 3), MAX_DIRECTORY_DEPTH)
        file_type = params.get("type", "all")  # "files", "dirs", "all"

        results = []
        root = Path(path)
        if not root.exists():
            return {"success": False, "error": f"Path not found: {path}"}

        for depth in range(max_depth + 1):
            for entry in root.rglob(pattern) if depth > 0 else root.glob(pattern):
                rel_depth = len(entry.relative_to(root).parts) - 1
                if rel_depth > depth:
                    continue
                if file_type == "files" and entry.is_dir():
                    continue
                if file_type == "dirs" and entry.is_file():
                    continue
                try:
                    stat = entry.stat()
                    results.append({
                        "name": entry.name,
                        "path": str(entry),
                        "is_dir": entry.is_dir(),
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                    })
                except (PermissionError, OSError):
                    continue
                if len(results) >= 100:
                    break
            if len(results) >= 100:
                break

        return {"success": True, "data": {"path": path, "pattern": pattern, "results": results, "total": len(results)}}

    async def mkdir(self, params: dict) -> Dict[str, Any]:
        """Create a directory."""
        path = params.get("path", "")
        parents = params.get("parents", True)

        path_obj = Path(path)
        path_obj.mkdir(parents=parents, exist_ok=False)

        return {"success": True, "data": {"path": str(path_obj), "created": True}}

    async def exists(self, params: dict) -> Dict[str, Any]:
        """Check if a path exists."""
        path = params.get("path", "")
        path_obj = Path(path)

        return {
            "success": True,
            "data": {
                "path": str(path_obj),
                "exists": path_obj.exists(),
                "is_file": path_obj.is_file() if path_obj.exists() else False,
                "is_dir": path_obj.is_dir() if path_obj.exists() else False,
            },
        }

    async def info(self, params: dict) -> Dict[str, Any]:
        """Get detailed file/directory info."""
        path = params.get("path", "")
        path_obj = Path(path)

        if not path_obj.exists():
            return {"success": False, "error": f"Path not found: {path}"}

        stat = path_obj.stat()
        return {
            "success": True,
            "data": {
                "path": str(path_obj),
                "name": path_obj.name,
                "suffix": path_obj.suffix,
                "is_dir": path_obj.is_dir(),
                "is_file": path_obj.is_file(),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "parent": str(path_obj.parent),
            },
        }