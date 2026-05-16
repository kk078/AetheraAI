"""
Aethera AI - File Converter Skill

Convert between common file formats:
  CSV <-> JSON <-> YAML
  Markdown -> HTML
  Text transformations (trim, sort, dedupe, normalize line endings)

All conversions are pure-Python with no external binary dependencies.
Optional: pyyaml for YAML support.
"""

import csv
import io
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported format pairs
# ---------------------------------------------------------------------------
CONVERSION_MAP = {
    "csv_json", "json_csv",
    "csv_yaml", "yaml_csv",
    "json_yaml", "yaml_json",
    "md_html",
}

FORMAT_EXTENSIONS = {
    "csv": ".csv",
    "json": ".json",
    "yaml": ".yaml",
    "md": ".md",
    "html": ".html",
    "txt": ".txt",
}


@skill(name="file_converter", category="general")
class FileConverterSkill(AetheraSkill):
    """
    Convert between file formats: CSV, JSON, YAML, Markdown, HTML, and text.
    """

    @property
    def name(self) -> str:
        return "file_converter"

    @property
    def description(self) -> str:
        return "Convert between file formats: CSV, JSON, YAML, Markdown-to-HTML, and text transformations"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["convert", "detect_format", "batch_convert"],
                    "description": (
                        "'convert' to transform one format to another, "
                        "'detect_format' to identify a file's format, "
                        "'batch_convert' to convert multiple files at once"
                    ),
                },
                "input_path": {
                    "type": "string",
                    "description": "Path to the input file (for convert and detect_format)"
                },
                "input_content": {
                    "type": "string",
                    "description": "Raw content string instead of a file path"
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the output file. If omitted, content is returned in the result."
                },
                "input_format": {
                    "type": "string",
                    "enum": ["csv", "json", "yaml", "md", "html", "txt"],
                    "description": "Source format. Auto-detected from extension if not provided."
                },
                "output_format": {
                    "type": "string",
                    "enum": ["csv", "json", "yaml", "html", "txt"],
                    "description": "Target format (required for convert action)"
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths for batch_convert action"
                },
                "output_directory": {
                    "type": "string",
                    "description": "Directory for batch_convert output files"
                },
                "csv_delimiter": {
                    "type": "string",
                    "description": "CSV field delimiter. Default is comma.",
                    "default": ","
                },
                "json_indent": {
                    "type": "integer",
                    "description": "JSON indentation level. Default is 2.",
                    "default": 2
                },
                "text_transform": {
                    "type": "string",
                    "enum": ["trim_lines", "sort_lines", "dedupe_lines", "normalize_newlines", "strip_blank_lines"],
                    "description": "Text transformation to apply (used when output_format is 'txt')"
                },
            },
            "required": ["action"],
        }

    @property
    def examples(self) -> list:
        return [
            {"input": {"action": "convert", "input_path": "/data/table.csv", "output_format": "json"}},
            {"input": {"action": "convert", "input_content": '{"key":"value"}', "input_format": "json", "output_format": "yaml"}},
            {"input": {"action": "detect_format", "input_path": "/data/mystery_file"}},
            {"input": {"action": "batch_convert", "files": ["/a.csv", "/b.csv"], "output_format": "json", "output_directory": "/out"}},
        ]

    @property
    def cache_ttl(self) -> int:
        return 60

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")

        try:
            if action == "convert":
                return await self._action_convert(kwargs)
            elif action == "detect_format":
                return self._action_detect_format(kwargs)
            elif action == "batch_convert":
                return await self._action_batch_convert(kwargs)
            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            logger.exception("File converter error")
            return SkillResult(success=False, error=str(e))

    # ------------------------------------------------------------------
    # convert
    # ------------------------------------------------------------------

    async def _action_convert(self, kwargs: dict) -> SkillResult:
        input_path = kwargs.get("input_path", "")
        input_content = kwargs.get("input_content", "")
        output_path = kwargs.get("output_path", "")
        input_format = kwargs.get("input_format", "")
        output_format = kwargs.get("output_format", "")
        csv_delimiter = kwargs.get("csv_delimiter", ",")
        json_indent = kwargs.get("json_indent", 2)
        text_transform = kwargs.get("text_transform", "")

        # Read content
        if input_content:
            content = input_content
            if not input_format:
                input_format = self._detect_format_from_content(content)
        elif input_path:
            path = Path(input_path)
            if not path.exists():
                return SkillResult(success=False, error=f"Input file not found: {input_path}")
            content = path.read_text(encoding="utf-8", errors="replace")
            if not input_format:
                input_format = self._detect_format_from_extension(path)
        else:
            return SkillResult(success=False, error="Either input_path or input_content is required")

        if not input_format:
            return SkillResult(success=False, error="Could not determine input format. Specify input_format.")
        if not output_format:
            return SkillResult(success=False, error="output_format is required for convert action")

        # Text-only transforms
        if output_format == "txt" and text_transform:
            result_content = self._apply_text_transform(content, text_transform)
        elif input_format == output_format:
            result_content = content
        else:
            conversion_key = f"{input_format}_{output_format}"
            converter = self._get_converter(conversion_key, csv_delimiter, json_indent)
            if converter is None:
                return SkillResult(
                    success=False,
                    error=f"Conversion from {input_format} to {output_format} is not supported"
                )
            result_content = converter(content)

        # Write to file if output_path given
        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(result_content, encoding="utf-8")

        return SkillResult(
            success=True,
            data={
                "input_format": input_format,
                "output_format": output_format,
                "content": result_content,
                "output_path": output_path or None,
                "size_bytes": len(result_content.encode("utf-8")),
            }
        )

    # ------------------------------------------------------------------
    # detect_format
    # ------------------------------------------------------------------

    def _action_detect_format(self, kwargs: dict) -> SkillResult:
        input_path = kwargs.get("input_path", "")
        input_content = kwargs.get("input_content", "")

        if input_path:
            path = Path(input_path)
            ext_format = self._detect_format_from_extension(path)
            if path.exists():
                content = path.read_text(encoding="utf-8", errors="replace")[:4096]
                content_format = self._detect_format_from_content(content)
            else:
                content_format = None
        elif input_content:
            ext_format = None
            content_format = self._detect_format_from_content(input_content[:4096])
        else:
            return SkillResult(success=False, error="Either input_path or input_content is required")

        detected = content_format or ext_format or "unknown"
        confidence = "high" if (content_format and ext_format and content_format == ext_format) else \
                     "medium" if (content_format or ext_format) else "low"

        return SkillResult(
            success=True,
            data={
                "detected_format": detected,
                "confidence": confidence,
                "by_extension": ext_format,
                "by_content": content_format,
            }
        )

    # ------------------------------------------------------------------
    # batch_convert
    # ------------------------------------------------------------------

    async def _action_batch_convert(self, kwargs: dict) -> SkillResult:
        files: List[str] = kwargs.get("files", [])
        output_format = kwargs.get("output_format", "")
        output_directory = kwargs.get("output_directory", "")
        csv_delimiter = kwargs.get("csv_delimiter", ",")
        json_indent = kwargs.get("json_indent", 2)

        if not files:
            return SkillResult(success=False, error="files list is required for batch_convert")
        if not output_format:
            return SkillResult(success=False, error="output_format is required for batch_convert")
        if output_directory:
            Path(output_directory).mkdir(parents=True, exist_ok=True)

        results: List[Dict[str, Any]] = []
        for file_path_str in files:
            path = Path(file_path_str)
            if not path.exists():
                results.append({"file": file_path_str, "success": False, "error": "File not found"})
                continue

            input_format = self._detect_format_from_extension(path)
            if not input_format:
                results.append({"file": file_path_str, "success": False, "error": "Cannot detect input format"})
                continue

            content = path.read_text(encoding="utf-8", errors="replace")
            conversion_key = f"{input_format}_{output_format}"
            converter = self._get_converter(conversion_key, csv_delimiter, json_indent)
            if converter is None:
                results.append({"file": file_path_str, "success": False, "error": f"Cannot convert {input_format} -> {output_format}"})
                continue

            try:
                converted = converter(content)
                out_name = path.stem + FORMAT_EXTENSIONS.get(output_format, f".{output_format}")
                out_path = str(Path(output_directory) / out_name) if output_directory else ""
                if out_path:
                    Path(out_path).write_text(converted, encoding="utf-8")
                results.append({"file": file_path_str, "success": True, "output_path": out_path, "size_bytes": len(converted.encode("utf-8"))})
            except Exception as e:
                results.append({"file": file_path_str, "success": False, "error": str(e)})

        succeeded = sum(1 for r in results if r["success"])
        return SkillResult(
            success=True,
            data={
                "total": len(files),
                "succeeded": succeeded,
                "failed": len(files) - succeeded,
                "results": results,
            }
        )

    # ------------------------------------------------------------------
    # Format detection helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_format_from_extension(path: Path) -> Optional[str]:
        ext = path.suffix.lower()
        mapping = {
            ".csv": "csv", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
            ".md": "md", ".markdown": "md", ".html": "html", ".htm": "html",
            ".txt": "txt",
        }
        return mapping.get(ext)

    @staticmethod
    def _detect_format_from_content(content: str) -> Optional[str]:
        stripped = content.strip()
        if not stripped:
            return None

        # JSON
        if stripped[0] in ("{", "["):
            try:
                json.loads(stripped)
                return "json"
            except json.JSONDecodeError:
                pass

        # YAML (heuristic: look for key: value lines without braces)
        yaml_indicator = re.match(r"^[a-zA-Z_][\w]*\s*:", stripped, re.MULTILINE)
        if yaml_indicator and stripped[0] not in ("{", "["):
            return "yaml"

        # HTML
        if stripped.lower().startswith("<!doctype html") or re.match(r"<html[\s>]", stripped, re.IGNORECASE):
            return "html"

        # Markdown (common markers)
        md_markers = re.match(r"^(#{1,6}\s|[-*+]\s|\*\*|__|\[.*\]\(.*\))", stripped, re.MULTILINE)
        if md_markers:
            return "md"

        # CSV (simple: first line has comma-separated fields, consistent columns)
        first_line = stripped.split("\n", 1)[0]
        if "," in first_line:
            col_count = len(first_line.split(","))
            if col_count >= 2:
                lines = stripped.split("\n")[:5]
                if all(len(line.split(",")) == col_count for line in lines if line.strip()):
                    return "csv"

        return "txt"

    # ------------------------------------------------------------------
    # Converter registry
    # ------------------------------------------------------------------

    def _get_converter(self, conversion_key: str, csv_delimiter: str, json_indent: int):
        """Return the converter function for a given conversion key, or None."""
        converters = {
            "csv_json": lambda c: self._csv_to_json(c, csv_delimiter, json_indent),
            "json_csv": lambda c: self._json_to_csv(c, csv_delimiter),
            "csv_yaml": lambda c: self._csv_to_yaml(c, csv_delimiter),
            "yaml_csv": lambda c: self._yaml_to_csv(c, csv_delimiter),
            "json_yaml": lambda c: self._json_to_yaml(c),
            "yaml_json": lambda c: self._yaml_to_json(c, json_indent),
            "md_html": lambda c: self._md_to_html(c),
        }
        return converters.get(conversion_key)

    # ------------------------------------------------------------------
    # CSV <-> JSON
    # ------------------------------------------------------------------

    def _csv_to_json(self, content: str, delimiter: str, indent: int) -> str:
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        rows = [row for row in reader]
        return json.dumps(rows, indent=indent, ensure_ascii=False)

    def _json_to_csv(self, content: str, delimiter: str) -> str:
        data = json.loads(content)
        if isinstance(data, dict):
            data = [data]
        if not data:
            return ""
        fieldnames = list(data[0].keys())
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    # ------------------------------------------------------------------
    # CSV <-> YAML
    # ------------------------------------------------------------------

    def _csv_to_yaml(self, content: str, delimiter: str) -> str:
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        rows = [dict(row) for row in reader]
        return self._dict_to_yaml(rows)

    def _yaml_to_csv(self, content: str, delimiter: str) -> str:
        data = self._yaml_to_python(content)
        if isinstance(data, dict):
            data = [data]
        if not data:
            return ""
        fieldnames = list(data[0].keys())
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    # ------------------------------------------------------------------
    # JSON <-> YAML
    # ------------------------------------------------------------------

    def _json_to_yaml(self, content: str) -> str:
        data = json.loads(content)
        return self._dict_to_yaml(data)

    def _yaml_to_json(self, content: str, indent: int) -> str:
        data = self._yaml_to_python(content)
        return json.dumps(data, indent=indent, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Markdown -> HTML
    # ------------------------------------------------------------------

    def _md_to_html(self, content: str) -> str:
        """Convert Markdown to self-contained HTML without external dependencies."""
        html = content

        # Headers
        html = re.sub(r"^######\s+(.+)$", r"<h6>\1</h6>", html, flags=re.MULTILINE)
        html = re.sub(r"^#####\s+(.+)$", r"<h5>\1</h5>", html, flags=re.MULTILINE)
        html = re.sub(r"^####\s+(.+)$", r"<h4>\1</h4>", html, flags=re.MULTILINE)
        html = re.sub(r"^###\s+(.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^##\s+(.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^#\s+(.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        # Horizontal rules
        html = re.sub(r"^(---|\*\*\*|___)\s*$", "<hr>", html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", html)
        html = re.sub(r"___(.+?)___", r"<strong><em>\1</em></strong>", html)
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"__(.+?)__", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        html = re.sub(r"_(.+?)_", r"<em>\1</em>", html)

        # Inline code
        html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

        # Code blocks (fenced)
        html = re.sub(r"```(\w*)\n(.*?)```", r'<pre><code class="\1">\2</code></pre>', html, flags=re.DOTALL)

        # Links and images
        html = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', html)
        html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

        # Unordered lists
        html = re.sub(r"^[-*+]\s+(.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
        html = re.sub(r"((?:<li>.*</li>\n?)+)", r"<ul>\1</ul>", html)

        # Ordered lists
        html = re.sub(r"^\d+\.\s+(.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)

        # Blockquotes
        html = re.sub(r"^>\s+(.+)$", r"<blockquote>\1</blockquote>", html, flags=re.MULTILINE)

        # Paragraphs — wrap lines that aren't already tags
        lines = html.split("\n")
        processed = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                processed.append("")
            elif stripped.startswith("<") or stripped.startswith("&lt;"):
                processed.append(line)
            else:
                processed.append(f"<p>{line}</p>")
        html = "\n".join(processed)

        # Wrap in basic HTML document
        return (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<title>Converted Document</title>\n"
            "<style>body{font-family:sans-serif;max-width:800px;margin:2em auto;padding:0 1em;"
            "line-height:1.6;color:#333}pre{background:#f4f4f4;padding:1em;overflow-x:auto}"
            "code{background:#f4f4f4;padding:2px 4px}blockquote{border-left:4px solid #ddd;"
            "margin-left:0;padding-left:1em;color:#666}img{max-width:100%}</style>\n"
            "</head>\n<body>\n" + html + "\n</body>\n</html>"
        )

    # ------------------------------------------------------------------
    # Text transforms
    # ------------------------------------------------------------------

    def _apply_text_transform(self, content: str, transform: str) -> str:
        transforms = {
            "trim_lines": self._trim_lines,
            "sort_lines": self._sort_lines,
            "dedupe_lines": self._dedupe_lines,
            "normalize_newlines": self._normalize_newlines,
            "strip_blank_lines": self._strip_blank_lines,
        }
        fn = transforms.get(transform)
        if fn is None:
            return content
        return fn(content)

    @staticmethod
    def _trim_lines(content: str) -> str:
        return "\n".join(line.strip() for line in content.split("\n"))

    @staticmethod
    def _sort_lines(content: str) -> str:
        lines = content.split("\n")
        return "\n".join(sorted(lines))

    @staticmethod
    def _dedupe_lines(content: str) -> str:
        lines = content.split("\n")
        seen = set()
        result = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                result.append(line)
        return "\n".join(result)

    @staticmethod
    def _normalize_newlines(content: str) -> str:
        # Normalize \r\n and \r to \n
        return content.replace("\r\n", "\n").replace("\r", "\n")

    @staticmethod
    def _strip_blank_lines(content: str) -> str:
        return "\n".join(line for line in content.split("\n") if line.strip())

    # ------------------------------------------------------------------
    # YAML helpers (optional pyyaml dependency)
    # ------------------------------------------------------------------

    def _yaml_to_python(self, content: str) -> Any:
        """Parse YAML string to Python object. Requires pyyaml."""
        try:
            import yaml  # noqa: F811
            return yaml.safe_load(content)
        except ImportError:
            raise RuntimeError(
                "PyYAML is required for YAML support. Install with: pip install pyyaml"
            )

    def _dict_to_yaml(self, data: Any) -> str:
        """Serialize Python object to YAML string. Requires pyyaml."""
        try:
            import yaml  # noqa: F811
            return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
        except ImportError:
            raise RuntimeError(
                "PyYAML is required for YAML support. Install with: pip install pyyaml"
            )

