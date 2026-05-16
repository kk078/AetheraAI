"""
Aethera AI - Presentation Builder Skill

Generate slide deck JSON structures from Markdown input.
Supports bullet, section, content, table, and image slide types
with speaker notes and full deck export.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="presentation_builder", category="content")
class PresentationBuilderSkill(AetheraSkill):
    """
    Build presentation slide decks as structured JSON.
    Converts Markdown content into slide types: bullet, section, content, table, image.
    """

    @property
    def name(self) -> str:
        return "presentation_builder"

    @property
    def description(self) -> str:
        return (
            "Generate slide deck JSON structures from Markdown, supporting "
            "bullet, section, content, table, and image slide types with speaker notes"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "create_deck",
                        "add_slide",
                        "add_speaker_notes",
                        "export_json",
                    ],
                    "description": "Action to perform",
                },
                "deck": {
                    "type": "object",
                    "description": (
                        "Existing deck object to modify (for add_slide/add_speaker_notes/export). "
                        "Omit when creating a new deck."
                    ),
                },
                "title": {
                    "type": "string",
                    "description": "Deck title (for create_deck) or slide title (for add_slide)",
                },
                "subtitle": {
                    "type": "string",
                    "description": "Deck subtitle (for create_deck)",
                },
                "author": {
                    "type": "string",
                    "description": "Deck author",
                },
                "theme": {
                    "type": "string",
                    "description": "Deck theme name",
                    "default": "default",
                },
                "markdown": {
                    "type": "string",
                    "description": (
                        "Markdown content to parse into slides (for create_deck). "
                        "Use --- or ```slide to separate slides. "
                        "Supports # heading, ## section, - bullets, | tables, ![alt](url) images."
                    ),
                },
                "slide_type": {
                    "type": "string",
                    "enum": ["bullet", "section", "content", "table", "image", "title"],
                    "description": "Type of slide to add (for add_slide)",
                },
                "content": {
                    "type": "string",
                    "description": "Slide body content (for add_slide with bullet/content types)",
                },
                "bullets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Bullet points (for add_slide with bullet type)",
                },
                "table_headers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Column headers for a table slide",
                },
                "table_rows": {
                    "type": "array",
                    "items": {"type": "array"},
                    "description": "Row data for a table slide",
                },
                "image_url": {
                    "type": "string",
                    "description": "Image URL for an image slide",
                },
                "image_alt": {
                    "type": "string",
                    "description": "Alt text for the image",
                },
                "slide_index": {
                    "type": "integer",
                    "description": "0-based index of the slide to add speaker notes to",
                },
                "notes": {
                    "type": "string",
                    "description": "Speaker notes text",
                },
                "slide_position": {
                    "type": "integer",
                    "description": "0-based position to insert the slide (defaults to append)",
                },
            },
            "required": ["action"],
        }

    @property
    def examples(self) -> list:
        return [
            {
                "input": {
                    "action": "create_deck",
                    "title": "Q3 Review",
                    "subtitle": "Performance Metrics",
                    "author": "Aethera AI",
                    "markdown": "# Q3 Review\n---\n## Key Metrics\n- Revenue up 12%\n- NPS score: 72\n---\n| Metric | Q2 | Q3 |\n|---|---|---|\n| Revenue | $1M | $1.12M |",
                }
            },
            {
                "input": {
                    "action": "add_slide",
                    "deck": {"title": "Q3 Review", "slides": []},
                    "slide_type": "bullet",
                    "title": "Action Items",
                    "bullets": ["Ship feature X", "Hire engineer"],
                }
            },
            {
                "input": {
                    "action": "add_speaker_notes",
                    "deck": {"title": "Q3 Review", "slides": [{"title": "Intro"}]},
                    "slide_index": 0,
                    "notes": "Welcome everyone to the Q3 review meeting.",
                }
            },
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        if not action:
            return SkillResult(success=False, error="Action is required")

        try:
            if action == "create_deck":
                return self._create_deck(kwargs)
            elif action == "add_slide":
                return self._add_slide(kwargs)
            elif action == "add_speaker_notes":
                return self._add_speaker_notes(kwargs)
            elif action == "export_json":
                return self._export_json(kwargs)
            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            return SkillResult(success=False, error=f"Presentation build failed: {e}")

    # ------------------------------------------------------------------
    # Deck creation
    # ------------------------------------------------------------------

    def _create_deck(self, kwargs: dict) -> SkillResult:
        """Create a new deck, optionally parsing Markdown into slides."""
        title = kwargs.get("title", "Untitled Presentation")
        subtitle = kwargs.get("subtitle", "")
        author = kwargs.get("author", "")
        theme = kwargs.get("theme", "default")
        markdown = kwargs.get("markdown", "")

        deck: Dict[str, Any] = {
            "title": title,
            "subtitle": subtitle,
            "author": author,
            "theme": theme,
            "created_at": datetime.now().isoformat(),
            "slides": [],
        }

        if markdown:
            slides = self._parse_markdown(markdown, title, subtitle)
            deck["slides"] = slides
        else:
            # Add a default title slide
            deck["slides"].append(self._make_title_slide(title, subtitle))

        return SkillResult(
            success=True,
            data={
                "deck": deck,
                "slide_count": len(deck["slides"]),
            },
        )

    def _make_title_slide(self, title: str, subtitle: str) -> Dict[str, Any]:
        """Build a title slide."""
        slide: Dict[str, Any] = {
            "type": "title",
            "title": title,
        }
        if subtitle:
            slide["subtitle"] = subtitle
        return slide

    # ------------------------------------------------------------------
    # Markdown parsing
    # ------------------------------------------------------------------

    def _parse_markdown(self, markdown: str, deck_title: str, deck_subtitle: str) -> List[Dict[str, Any]]:
        """Parse Markdown content into a list of slide dicts."""
        # Split on horizontal rules (---) or ```slide fences
        raw_blocks = re.split(r"\n---\n|\n```slide\n?", markdown)
        raw_blocks = [b.strip() for b in raw_blocks if b.strip()]

        slides: List[Dict[str, Any]] = []

        for block in raw_blocks:
            slide = self._parse_block(block)
            if slide:
                slides.append(slide)

        # If the first slide looks like a title slide matching the deck title, use deck metadata
        if slides and slides[0].get("type") == "title" and slides[0].get("title") == deck_title:
            if deck_subtitle:
                slides[0]["subtitle"] = deck_subtitle

        # If no slides were produced, add a default title slide
        if not slides:
            slides.append(self._make_title_slide(deck_title, deck_subtitle))

        return slides

    def _parse_block(self, block: str) -> Optional[Dict[str, Any]]:
        """Parse a single Markdown block into a slide dict."""
        lines = block.split("\n")
        # Remove empty trailing lines
        while lines and not lines[-1].strip():
            lines.pop()

        if not lines:
            return None

        first_line = lines[0].strip()

        # Title slide: starts with # (h1)
        if first_line.startswith("# ") and not first_line.startswith("## "):
            title = first_line[2:].strip()
            rest = lines[1:]
            if not rest or all(not l.strip() for l in rest):
                return {"type": "title", "title": title}
            # Title with subtitle on next line
            subtitle = ""
            if rest and rest[0].strip() and not rest[0].strip().startswith(("- ", "* ", "|")):
                subtitle = rest[0].strip()
                rest = rest[1:]
            slide: Dict[str, Any] = {"type": "title", "title": title}
            if subtitle:
                slide["subtitle"] = subtitle
            return slide

        # Section slide: starts with ## (h2) and little else
        if first_line.startswith("## "):
            section_title = first_line[3:].strip()
            rest = lines[1:]
            # If only h2 and nothing substantial below, make it a section slide
            substantial = [l for l in rest if l.strip() and not l.strip().startswith("```")]
            if len(substantial) <= 1:
                slide = {"type": "section", "title": section_title}
                if substantial:
                    slide["subtitle"] = substantial[0].strip().lstrip("- ").lstrip("* ")
                return slide

        # Table detection: lines containing pipes
        if self._is_table_block(lines):
            return self._parse_table_slide(lines)

        # Image detection: line starting with ![...](...)
        if first_line.startswith("!["):
            return self._parse_image_slide(lines)

        # Bullet detection: lines starting with - or *
        bullet_lines = [l for l in lines if l.strip().startswith(("- ", "* "))]
        if bullet_lines and len(bullet_lines) >= len(lines) * 0.5:
            return self._parse_bullet_slide(lines)

        # Default: content slide
        return self._parse_content_slide(lines)

    def _is_table_block(self, lines: List[str]) -> bool:
        """Check if block is primarily a Markdown table."""
        pipe_lines = [l for l in lines if "|" in l and l.strip().startswith("|")]
        return len(pipe_lines) >= 2  # At least header + separator

    def _parse_table_slide(self, lines: List[str]) -> Dict[str, Any]:
        """Parse a Markdown table into a table slide."""
        table_lines = [l for l in lines if "|" in l]
        if not table_lines:
            return {"type": "content", "title": "Table", "content": ""}

        # First row = headers, second row = separator (skip), rest = data
        headers = [c.strip() for c in table_lines[0].split("|") if c.strip()]
        rows: List[List[str]] = []

        for line in table_lines[2:]:  # Skip header and separator
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if cells:
                rows.append(cells)

        slide: Dict[str, Any] = {
            "type": "table",
            "title": headers[0] if headers else "Data Table",
            "table": {
                "headers": headers,
                "rows": rows,
            },
        }

        # Check for a heading before the table
        non_table = [l for l in lines if "|" not in l and l.strip()]
        if non_table and non_table[0].startswith("#"):
            slide["title"] = non_table[0].lstrip("# ").strip()

        return slide

    def _parse_image_slide(self, lines: List[str]) -> Dict[str, Any]:
        """Parse an image reference into an image slide."""
        first_line = lines[0].strip()
        # ![alt](url)
        match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", first_line)
        if not match:
            return {"type": "content", "title": "Image", "content": first_line}

        alt_text = match.group(1)
        image_url = match.group(2)

        slide: Dict[str, Any] = {
            "type": "image",
            "title": alt_text or "Image",
            "image_url": image_url,
            "alt_text": alt_text,
        }

        # Additional lines become caption or notes
        rest = [l for l in lines[1:] if l.strip()]
        if rest:
            slide["caption"] = " ".join(l.strip() for l in rest)

        return slide

    def _parse_bullet_slide(self, lines: List[str]) -> Dict[str, Any]:
        """Parse bullet points into a bullet slide."""
        title = ""
        bullets: List[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
            elif stripped.startswith("## "):
                title = stripped[3:].strip()
            elif stripped.startswith(("- ", "* ")):
                bullets.append(stripped[2:].strip())
            elif stripped:
                # Non-bullet, non-heading line: add as sub-content
                bullets.append(stripped)

        return {
            "type": "bullet",
            "title": title or "Key Points",
            "bullets": bullets,
        }

    def _parse_content_slide(self, lines: List[str]) -> Dict[str, Any]:
        """Parse a generic content block into a content slide."""
        title = ""
        body_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
            elif stripped.startswith("## "):
                title = stripped[3:].strip()
            else:
                body_lines.append(stripped)

        content = "\n".join(body_lines).strip()

        return {
            "type": "content",
            "title": title or "Content",
            "content": content,
        }

    # ------------------------------------------------------------------
    # Slide addition
    # ------------------------------------------------------------------

    def _add_slide(self, kwargs: dict) -> SkillResult:
        """Add a single slide to an existing deck."""
        deck = kwargs.get("deck")
        if not deck or not isinstance(deck, dict) or "slides" not in deck:
            return SkillResult(success=False, error="A valid deck object is required")

        slide_type = kwargs.get("slide_type", "content")
        slide_title = kwargs.get("title", "New Slide")
        position = kwargs.get("slide_position")

        slide = self._build_slide_from_kwargs(slide_type, kwargs, slide_title)

        if position is not None and 0 <= position <= len(deck["slides"]):
            deck["slides"].insert(position, slide)
        else:
            deck["slides"].append(slide)

        return SkillResult(
            success=True,
            data={
                "deck": deck,
                "added_slide": slide,
                "slide_count": len(deck["slides"]),
            },
        )

    def _build_slide_from_kwargs(self, slide_type: str, kwargs: dict, slide_title: str) -> Dict[str, Any]:
        """Construct a slide dict from kwargs based on the slide type."""
        if slide_type == "title":
            slide: Dict[str, Any] = {"type": "title", "title": slide_title}
            subtitle = kwargs.get("subtitle")
            if subtitle:
                slide["subtitle"] = subtitle
            return slide

        if slide_type == "section":
            slide = {"type": "section", "title": slide_title}
            content = kwargs.get("content")
            if content:
                slide["subtitle"] = content
            return slide

        if slide_type == "bullet":
            bullets = kwargs.get("bullets", [])
            if not bullets:
                content = kwargs.get("content", "")
                bullets = [l.strip().lstrip("- ").lstrip("* ") for l in content.split("\n") if l.strip()]
            return {"type": "bullet", "title": slide_title, "bullets": bullets}

        if slide_type == "table":
            table_headers = kwargs.get("table_headers", [])
            table_rows = kwargs.get("table_rows", [])
            return {
                "type": "table",
                "title": slide_title,
                "table": {
                    "headers": table_headers,
                    "rows": table_rows,
                },
            }

        if slide_type == "image":
            return {
                "type": "image",
                "title": slide_title,
                "image_url": kwargs.get("image_url", ""),
                "alt_text": kwargs.get("image_alt", ""),
            }

        # Default content slide
        return {
            "type": "content",
            "title": slide_title,
            "content": kwargs.get("content", ""),
        }

    # ------------------------------------------------------------------
    # Speaker notes
    # ------------------------------------------------------------------

    def _add_speaker_notes(self, kwargs: dict) -> SkillResult:
        """Add speaker notes to an existing slide in a deck."""
        deck = kwargs.get("deck")
        if not deck or not isinstance(deck, dict) or "slides" not in deck:
            return SkillResult(success=False, error="A valid deck object is required")

        slide_index = kwargs.get("slide_index")
        notes = kwargs.get("notes", "")

        if slide_index is None:
            return SkillResult(success=False, error="slide_index is required")
        if not notes:
            return SkillResult(success=False, error="notes text is required")

        slides = deck.get("slides", [])
        if slide_index < 0 or slide_index >= len(slides):
            return SkillResult(
                success=False,
                error=f"slide_index {slide_index} out of range (0-{len(slides) - 1})",
            )

        slides[slide_index]["speaker_notes"] = notes

        return SkillResult(
            success=True,
            data={
                "deck": deck,
                "slide_index": slide_index,
                "notes_added": notes,
            },
        )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_json(self, kwargs: dict) -> SkillResult:
        """Export the deck as a JSON string."""
        deck = kwargs.get("deck")
        if not deck or not isinstance(deck, dict):
            return SkillResult(success=False, error="A valid deck object is required")

        try:
            json_str = json.dumps(deck, indent=2, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            return SkillResult(success=False, error=f"JSON serialization failed: {e}")

        return SkillResult(
            success=True,
            data={
                "format": "json",
                "json": json_str,
                "slide_count": len(deck.get("slides", [])),
                "byte_count": len(json_str.encode("utf-8")),
            },
        )