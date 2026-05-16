"""
Aethera AI - Diagram Generator Skill

Generate Mermaid diagram syntax from natural-language descriptions.
Supports: flowchart, sequence, class, state, ER, and Gantt diagrams.
Output is valid Mermaid syntax ready for rendering by the frontend.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mermaid diagram type definitions
# ---------------------------------------------------------------------------
DIAGRAM_TYPES = {
    "flowchart": {
        "directions": ["TB", "TD", "BT", "RL", "LR"],
        "default_direction": "TD",
        "description": "Flowchart diagram showing process flow and decisions",
    },
    "sequence": {
        "description": "Sequence diagram showing interactions between participants over time",
    },
    "class": {
        "directions": ["TB", "TD", "BT", "RL", "LR"],
        "default_direction": "TB",
        "description": "Class diagram showing object-oriented class relationships",
    },
    "state": {
        "directions": ["TB", "TD", "BT", "RL", "LR"],
        "default_direction": "LR",
        "description": "State diagram showing state transitions",
    },
    "er": {
        "description": "Entity-Relationship diagram showing database schema relationships",
    },
    "gantt": {
        "description": "Gantt chart showing project timeline and task scheduling",
    },
}


@skill(name="diagram_generator", category="general")
class DiagramGeneratorSkill(AetheraSkill):
    """
    Generate Mermaid diagrams from natural-language descriptions.
    """

    @property
    def name(self) -> str:
        return "diagram_generator"

    @property
    def description(self) -> str:
        return "Generate Mermaid diagrams: flowchart, sequence, class, state, ER, and Gantt from descriptions"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["generate", "validate", "list_types"],
                    "description": (
                        "'generate' to create a diagram, "
                        "'validate' to check Mermaid syntax, "
                        "'list_types' to show supported diagram types"
                    ),
                },
                "diagram_type": {
                    "type": "string",
                    "enum": ["flowchart", "sequence", "class", "state", "er", "gantt"],
                    "description": "Type of Mermaid diagram to generate"
                },
                "description": {
                    "type": "string",
                    "description": "Natural-language description of the diagram to generate"
                },
                "direction": {
                    "type": "string",
                    "enum": ["TB", "TD", "BT", "RL", "LR"],
                    "description": "Diagram direction (for flowchart, class, state). Default varies by type."
                },
                "title": {
                    "type": "string",
                    "description": "Optional title for the diagram"
                },
                "nodes": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Explicit node definitions (for flowchart/class/state). Each: {id, label, type?}"
                },
                "edges": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Explicit edge/connection definitions. Each: {from, to, label?, style?}"
                },
                "participants": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Participant definitions for sequence diagrams. Each: {name, alias?}"
                },
                "messages": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Message definitions for sequence diagrams. Each: {from, to, text, type?}"
                },
                "classes": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Class definitions for class diagrams. Each: {name, attributes?, methods?}"
                },
                "relationships": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Relationship definitions for class/ER diagrams. Each: {from, to, type?, label?}"
                },
                "entities": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Entity definitions for ER diagrams. Each: {name, attributes?}"
                },
                "states": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "State definitions for state diagrams. Each: {name, type?}"
                },
                "transitions": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Transition definitions for state diagrams. Each: {from, to, label?}"
                },
                "tasks": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Task definitions for Gantt diagrams. Each: {name, start, duration?, end?, status?, depends?}"
                },
                "sections": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Section names for Gantt diagram grouping"
                },
                "mermaid_source": {
                    "type": "string",
                    "description": "Raw Mermaid syntax to validate (for validate action)"
                },
            },
            "required": ["action"],
        }

    @property
    def examples(self) -> list:
        return [
            {
                "input": {
                    "action": "generate",
                    "diagram_type": "flowchart",
                    "description": "User login flow: start, enter credentials, validate, success or failure",
                }
            },
            {
                "input": {
                    "action": "generate",
                    "diagram_type": "sequence",
                    "participants": [
                        {"name": "Client"},
                        {"name": "Server"},
                        {"name": "Database"},
                    ],
                    "messages": [
                        {"from": "Client", "to": "Server", "text": "HTTP Request"},
                        {"from": "Server", "to": "Database", "text": "Query"},
                        {"from": "Database", "to": "Server", "text": "Results"},
                        {"from": "Server", "to": "Client", "text": "HTTP Response"},
                    ],
                }
            },
            {
                "input": {"action": "list_types"},
            },
        ]

    @property
    def cache_ttl(self) -> int:
        return 300

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")

        try:
            if action == "generate":
                return self._generate(kwargs)
            elif action == "validate":
                return self._validate(kwargs)
            elif action == "list_types":
                return self._list_types()
            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            logger.exception("Diagram generator error")
            return SkillResult(success=False, error=str(e))

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    def _generate(self, kwargs: dict) -> SkillResult:
        diagram_type = kwargs.get("diagram_type", "")
        description = kwargs.get("description", "")

        if not diagram_type:
            # Try to infer type from description
            if description:
                diagram_type = self._infer_diagram_type(description)
            if not diagram_type:
                return SkillResult(success=False, error="diagram_type is required")

        if diagram_type not in DIAGRAM_TYPES:
            return SkillResult(
                success=False,
                error=f"Unsupported diagram type: {diagram_type}. Use list_types to see options."
            )

        generators = {
            "flowchart": self._gen_flowchart,
            "sequence": self._gen_sequence,
            "class": self._gen_class,
            "state": self._gen_state,
            "er": self._gen_er,
            "gantt": self._gen_gantt,
        }

        generator = generators.get(diagram_type)
        if generator is None:
            return SkillResult(success=False, error=f"No generator for type: {diagram_type}")

        mermaid_code = generator(kwargs)
        title = kwargs.get("title", "")

        # Validate the generated code
        validation = self._validate_mermaid(mermaid_code)

        result_data: Dict[str, Any] = {
            "diagram_type": diagram_type,
            "mermaid": mermaid_code,
            "title": title,
            "valid": validation["valid"],
        }
        if not validation["valid"]:
            result_data["validation_warnings"] = validation["warnings"]

        return SkillResult(success=True, data=result_data)

    # ------------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------------

    def _validate(self, kwargs: dict) -> SkillResult:
        mermaid_source = kwargs.get("mermaid_source", "")
        if not mermaid_source:
            return SkillResult(success=False, error="mermaid_source is required for validate action")

        result = self._validate_mermaid(mermaid_source)
        return SkillResult(success=True, data=result)

    # ------------------------------------------------------------------
    # List types
    # ------------------------------------------------------------------

    def _list_types(self) -> SkillResult:
        types = [
            {
                "type": name,
                "description": info["description"],
                "directions": info.get("directions", []),
            }
            for name, info in DIAGRAM_TYPES.items()
        ]
        return SkillResult(success=True, data={"diagram_types": types})

    # ------------------------------------------------------------------
    # Flowchart generator
    # ------------------------------------------------------------------

    def _gen_flowchart(self, kwargs: dict) -> str:
        direction = kwargs.get("direction", DIAGRAM_TYPES["flowchart"]["default_direction"])
        nodes = kwargs.get("nodes", [])
        edges = kwargs.get("edges", [])
        description = kwargs.get("description", "")
        title = kwargs.get("title", "")

        lines: List[str] = []
        if title:
            lines.append(f"---\ntitle: {title}\n---")
        lines.append(f"flowchart {direction}")

        # Parse description if explicit nodes/edges are missing
        if not nodes and not edges and description:
            nodes, edges = self._parse_flowchart_description(description)

        # Render nodes
        node_lines = self._render_flowchart_nodes(nodes)
        if node_lines:
            lines.append(f"    {node_lines}")

        # Render edges
        for edge in edges:
            from_id = self._sanitize_id(str(edge.get("from", "")))
            to_id = self._sanitize_id(str(edge.get("to", "")))
            label = edge.get("label", "")
            style = edge.get("style", "")

            if style == "dotted":
                arrow = f"-.->{f'|{label}|' if label else ''}"
            elif style == "thick":
                arrow = f"==>{f'|{label}|' if label else ''}"
            else:
                arrow = f"-->{f'|{label}|' if label else ''}"

            lines.append(f"    {from_id} {arrow} {to_id}")

        return "\n".join(lines)

    @staticmethod
    def _render_flowchart_nodes(nodes: list) -> str:
        """Render flowchart node declarations as a newline-separated block string."""
        if not nodes:
            return ""
        parts = []
        for node in nodes:
            nid = DiagramGeneratorSkill._sanitize_id(str(node.get("id", "")))
            label = node.get("label", nid)
            ntype = node.get("type", "")

            if ntype == "decision":
                parts.append(f"{nid}{{{{{label}}}}}")
            elif ntype == "round":
                parts.append(f"{nid}({label})")
            elif ntype == "stadium":
                parts.append(f"{nid}([{label}])")
            elif ntype == "subroutine":
                parts.append(f"{nid}[[{label}]]")
            elif ntype == "database":
                parts.append(f"{nid}[({label})]")
            elif ntype == "hexagon":
                parts.append(f"{nid}{{{{{label}}}}}")
            elif ntype == "parallelogram":
                parts.append(f"{nid}[/{label}/]")
            elif ntype == "circle":
                parts.append(f"{nid}(({label}))")
            else:
                # Default rectangle
                parts.append(f"{nid}[{label}]")
        return "\n    ".join(parts)

    # ------------------------------------------------------------------
    # Sequence diagram generator
    # ------------------------------------------------------------------

    def _gen_sequence(self, kwargs: dict) -> str:
        participants = kwargs.get("participants", [])
        messages = kwargs.get("messages", [])
        description = kwargs.get("description", "")
        title = kwargs.get("title", "")

        lines: List[str] = []
        if title:
            lines.append(f"title: {title}")
        lines.append("sequenceDiagram")

        # Parse description if explicit data is missing
        if not participants and not messages and description:
            participants, messages = self._parse_sequence_description(description)

        # Render participants
        for p in participants:
            name = p.get("name", "")
            alias = p.get("alias", "")
            if alias:
                lines.append(f"    participant {alias} as {name}")
            else:
                lines.append(f"    participant {name}")

        # Render messages
        for msg in messages:
            frm = str(msg.get("from", ""))
            to = str(msg.get("to", ""))
            text = msg.get("text", "")
            msg_type = msg.get("type", "solid")

            if msg_type == "dashed":
                lines.append(f"    {frm}-->>{to}: {text}")
            elif msg_type == "solid_open":
                lines.append(f"    {frm}->>{to}: {text}")
            elif msg_type == "dashed_open":
                lines.append(f"    {frm}-->>{to}: {text}")
            elif msg_type == "async":
                lines.append(f"    {frm}-){to}: {text}")
            else:
                lines.append(f"    {frm}->>{to}: {text}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Class diagram generator
    # ------------------------------------------------------------------

    def _gen_class(self, kwargs: dict) -> str:
        classes = kwargs.get("classes", [])
        relationships = kwargs.get("relationships", [])
        description = kwargs.get("description", "")
        direction = kwargs.get("direction", DIAGRAM_TYPES["class"]["default_direction"])
        title = kwargs.get("title", "")

        lines: List[str] = []
        if title:
            lines.append(f"---\ntitle: {title}\n---")
        lines.append(f"classDiagram {direction}")

        # Parse description if missing explicit data
        if not classes and not relationships and description:
            classes, relationships = self._parse_class_description(description)

        # Render classes
        for cls in classes:
            name = cls.get("name", "Unnamed")
            attributes = cls.get("attributes", [])
            methods = cls.get("methods", [])

            lines.append(f"    class {name} {{")
            for attr in attributes:
                if isinstance(attr, dict):
                    vis = attr.get("visibility", "+")
                    aname = attr.get("name", "")
                    atype = attr.get("type", "")
                    lines.append(f"        {vis}{atype} {aname}")
                else:
                    lines.append(f"        +{attr}")
            for method in methods:
                if isinstance(method, dict):
                    vis = method.get("visibility", "+")
                    mname = method.get("name", "")
                    params = method.get("params", "")
                    rtype = method.get("return", "")
                    lines.append(f"        {vis}{mname}({params}) {rtype}")
                else:
                    lines.append(f"        +{method}")
            lines.append(f"    }}")

        # Render relationships
        rel_symbols = {
            "inherits": "--|>",
            "implements": "..|>",
            "composes": "*--",
            "aggregates": "o--",
            "associates": "-->",
            "depends": "..>",
        }
        for rel in relationships:
            frm = rel.get("from", "")
            to = rel.get("to", "")
            rtype = rel.get("type", "associates")
            label = rel.get("label", "")
            symbol = rel_symbols.get(rtype, "-->")
            card_from = rel.get("cardinality_from", "")
            card_to = rel.get("cardinality_to", "")

            card_from_str = f'"{card_from}" ' if card_from else ''
            card_to_str = f'"{card_to}" ' if card_to else ''
            line = f"    {frm} {card_from_str}{symbol} {card_to_str}{to}"
            if label:
                line += f" : {label}"
            lines.append(line)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # State diagram generator
    # ------------------------------------------------------------------

    def _gen_state(self, kwargs: dict) -> str:
        states = kwargs.get("states", [])
        transitions = kwargs.get("transitions", [])
        description = kwargs.get("description", "")
        direction = kwargs.get("direction", DIAGRAM_TYPES["state"]["default_direction"])
        title = kwargs.get("title", "")

        lines: List[str] = []
        if title:
            lines.append(f"---\ntitle: {title}\n---")
        lines.append(f"stateDiagram-v2 {direction}")

        # Parse description if missing explicit data
        if not states and not transitions and description:
            states, transitions = self._parse_state_description(description)

        # Render states
        for s in states:
            name = s.get("name", "")
            stype = s.get("type", "")
            if stype == "start":
                lines.append("    [*]")
            elif stype == "end":
                lines.append("    [*]")
            elif stype == "choice":
                lines.append(f"    state {name} <<choice>>")
            elif stype == "fork":
                lines.append(f"    state {name} <<fork>>")
            elif stype == "join":
                lines.append(f"    state {name} <<join>>")
            else:
                lines.append(f"    state {name}")

        # Render transitions
        for t in transitions:
            frm = t.get("from", "")
            to = t.get("to", "")
            label = t.get("label", "")

            if frm == "[*]" or to == "[*]":
                line = f"    {frm} --> {to}"
            else:
                line = f"    {frm} --> {to}"
            if label:
                line += f" : {label}"
            lines.append(line)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # ER diagram generator
    # ------------------------------------------------------------------

    def _gen_er(self, kwargs: dict) -> str:
        entities = kwargs.get("entities", [])
        relationships = kwargs.get("relationships", [])
        description = kwargs.get("description", "")
        title = kwargs.get("title", "")

        lines: List[str] = []
        if title:
            lines.append(f"---\ntitle: {title}\n---")
        lines.append("erDiagram")

        # Parse description if missing explicit data
        if not entities and not relationships and description:
            entities, relationships = self._parse_er_description(description)

        # Render entities
        for entity in entities:
            name = entity.get("name", "Unnamed")
            attributes = entity.get("attributes", [])

            lines.append(f"    {name} {{")
            for attr in attributes:
                if isinstance(attr, dict):
                    atype = attr.get("type", "string")
                    aname = attr.get("name", "")
                    key = attr.get("key", "")
                    comment = attr.get("comment", "")
                    line = f"        {atype} {aname}"
                    if key == "PK":
                        line += " PK"
                    elif key == "FK":
                        line += " FK"
                    elif key == "UK":
                        line += " UK"
                    if comment:
                        line += f' "{comment}"'
                    lines.append(line)
                else:
                    lines.append(f"        string {attr}")
            lines.append(f"    }}")

        # Render relationships
        rel_map = {
            "one_to_one": "||--||",
            "one_to_many": "||--|{",
            "one_to_zero_or_one": "||--o|",
            "one_to_zero_or_more": "||--o{",
            "many_to_one": "|{--||",
            "many_to_many": "|{--|{",
            "zero_or_one_to_one": "o|--||",
            "zero_or_more_to_one": "o{--||",
            "zero_or_more_to_many": "o{--|{",
        }
        for rel in relationships:
            frm = rel.get("from", "")
            to = rel.get("to", "")
            rtype = rel.get("type", "one_to_many")
            label = rel.get("label", "")
            symbol = rel_map.get(rtype, "||--|{")

            line = f"    {frm} {symbol} {to}"
            if label:
                line += f' : "{label}"'
            lines.append(line)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Gantt diagram generator
    # ------------------------------------------------------------------

    def _gen_gantt(self, kwargs: dict) -> str:
        tasks = kwargs.get("tasks", [])
        sections = kwargs.get("sections", [])
        description = kwargs.get("description", "")
        title = kwargs.get("title", "")

        lines: List[str] = []
        if title:
            lines.append(f"title {title}")
        lines.append("gantt")
        lines.append("    dateFormat  YYYY-MM-DD")

        # Parse description if missing explicit data
        if not tasks and description:
            tasks = self._parse_gantt_description(description)

        current_section = ""
        task_idx = 0
        for task in tasks:
            section = task.get("section", "")
            if section and section != current_section:
                lines.append(f"    section {section}")
                current_section = section

            name = task.get("name", f"Task {task_idx + 1}")
            start = task.get("start", "")
            duration = task.get("duration", "")
            end = task.get("end", "")
            status = task.get("status", "")
            depends = task.get("depends", "")

            task_line = f"    {name} "
            if status == "active":
                task_line += "active, "
            elif status == "done":
                task_line += "done, "
            elif status == "critical":
                task_line += "crit, "
            elif status == "milestone":
                task_line += "milestone, "

            if depends:
                task_line += f"after {depends}, "

            if start and duration:
                task_line += f"{start}, {duration}"
            elif start and end:
                task_line += f"{start}, {end}"
            elif start:
                task_line += start
            else:
                task_line += f"2026-01-01, 7d"

            lines.append(task_line)
            task_idx += 1

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Description parsers (natural language -> structured data)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_flowchart_description(description: str):
        """
        Parse a natural-language flowchart description into nodes and edges.
        Splits on common transition words (then, next, after, if, else, etc.)
        and constructs a simple linear or branching flow.
        """
        nodes = []
        edges = []
        seen_ids = set()

        # Split description into steps
        step_pattern = re.split(
            r"\s*(?:,\s*then\s+|\s*->\s*|\s*then\s+|\s*next\s+|\s*after\s+|\s*followed\s+by\s+|\s*;\s*)",
            description,
            flags=re.IGNORECASE,
        )
        steps = [s.strip() for s in step_pattern if s.strip()]

        # Handle "if ... else ..." patterns for branching
        branch_idx = 0
        for i, step in enumerate(steps):
            # Check for conditional
            if_match = re.match(r"(?:if|when|whether)\s+(.+?)(?:\s*(?:,|\.)?\s*(?:then))?$", step, re.IGNORECASE)
            else_match = re.match(r"(?:else|otherwise|if not)(?:\s+(.+))?$", step, re.IGNORECASE)

            if if_match:
                nid = f"D{branch_idx}"
                label = if_match.group(1).strip().rstrip("?")
                nodes.append({"id": nid, "label": label, "type": "decision"})
                seen_ids.add(nid)
                if i > 0:
                    prev_id = f"N{i - 1}" if f"N{i - 1}" in seen_ids else (f"D{branch_idx - 1}" if branch_idx > 0 else f"N0")
                    edges.append({"from": prev_id, "to": nid, "label": ""})
                branch_idx += 1
            elif else_match:
                # Connect from last decision
                last_decision = f"D{branch_idx - 1}" if branch_idx > 0 else None
                if last_decision:
                    nid = f"N{i}"
                    label = else_match.group(1) or "Alternative path"
                    nodes.append({"id": nid, "label": label, "type": "round"})
                    seen_ids.add(nid)
                    edges.append({"from": last_decision, "to": nid, "label": "No"})
            else:
                nid = f"N{i}"
                label = step[:50]  # Truncate long labels
                # Detect if this is a start/end
                if i == 0 and re.match(r"start|begin", label, re.IGNORECASE):
                    ntype = "stadium"
                elif i == len(steps) - 1 and re.match(r"end|finish|complete", label, re.IGNORECASE):
                    ntype = "stadium"
                else:
                    ntype = "round"
                nodes.append({"id": nid, "label": label, "type": ntype})
                seen_ids.add(nid)

                # Connect to previous node
                if i > 0:
                    prev_candidates = [f"N{i - 1}", f"D{branch_idx - 1}"]
                    prev_id = next((c for c in prev_candidates if c in seen_ids), None)
                    if prev_id:
                        edges.append({"from": prev_id, "to": nid, "label": ""})

        return nodes, edges

    @staticmethod
    def _parse_sequence_description(description: str):
        """Parse a natural-language sequence description into participants and messages."""
        participants = []
        messages = []
        seen = set()

        # Try to extract "A to B: message" patterns
        msg_pattern = re.compile(
            r"(\w[\w\s]*?)\s*(?:sends?\s+)?(?:to\s+)(\w[\w\s]*?)[\s:]+(.+?)(?:\.|,|$)",
            re.IGNORECASE,
        )
        for match in msg_pattern.finditer(description):
            sender = match.group(1).strip()
            receiver = match.group(2).strip()
            text = match.group(3).strip()

            if sender not in seen:
                participants.append({"name": sender})
                seen.add(sender)
            if receiver not in seen:
                participants.append({"name": receiver})
                seen.add(receiver)

            messages.append({"from": sender, "to": receiver, "text": text, "type": "solid"})

        # If no structured patterns found, create a simple back-and-forth
        if not participants:
            words = re.split(r"\s*[;,]\s*", description)
            words = [w.strip() for w in words if w.strip()]
            for w in words[:6]:
                name = w.split()[0] if w.split() else w
                if name not in seen and len(name) < 20:
                    participants.append({"name": name})
                    seen.add(name)

            p_list = [p["name"] for p in participants]
            for i, text in enumerate(words):
                if len(p_list) >= 2:
                    frm = p_list[i % len(p_list)]
                    to = p_list[(i + 1) % len(p_list)]
                    messages.append({"from": frm, "to": to, "text": text, "type": "solid"})

        return participants, messages

    @staticmethod
    def _parse_class_description(description: str):
        """Parse a natural-language class description."""
        classes = []
        relationships = []

        # Look for "Class A has/contains B" patterns
        class_pattern = re.compile(r"(\w+)\s+(?:has|contains|includes?|with)\s+(.+?)(?:\.|,|$)", re.IGNORECASE)
        inherit_pattern = re.compile(r"(\w+)\s+(?:extends|inherits\s+from|is\s+a\s+)\s+(\w+)", re.IGNORECASE)

        seen_classes = set()

        for match in class_pattern.finditer(description):
            cls_name = match.group(1).strip()
            rest = match.group(2).strip()

            if cls_name not in seen_classes:
                classes.append({"name": cls_name, "attributes": [], "methods": []})
                seen_classes.add(cls_name)

            # Parse attributes from "rest"
            attrs = re.split(r"\s*[,;]\s*|\s+and\s+", rest)
            for attr in attrs:
                attr = attr.strip()
                if attr:
                    if attr[0].isupper() and attr not in seen_classes:
                        # Looks like another class -> relationship
                        if attr not in seen_classes:
                            classes.append({"name": attr, "attributes": [], "methods": []})
                            seen_classes.add(attr)
                        relationships.append({
                            "from": cls_name, "to": attr,
                            "type": "associates", "label": "has"
                        })
                    else:
                        classes[-1]["attributes"].append(attr)

        for match in inherit_pattern.finditer(description):
            child = match.group(1).strip()
            parent = match.group(2).strip()

            for name in (child, parent):
                if name not in seen_classes:
                    classes.append({"name": name, "attributes": [], "methods": []})
                    seen_classes.add(name)

            relationships.append({
                "from": child, "to": parent,
                "type": "inherits", "label": ""
            })

        # If nothing parsed, create a single placeholder
        if not classes:
            classes.append({"name": "MainClass", "attributes": ["attribute1", "attribute2"], "methods": ["method1()"]})

        return classes, relationships

    @staticmethod
    def _parse_state_description(description: str):
        """Parse a natural-language state description."""
        states = []
        transitions = []
        seen = set()

        # Split by arrows or transitions
        parts = re.split(r"\s*(?:->|→|then|leads?\s+to|transitions?\s+to)\s*", description, flags=re.IGNORECASE)
        parts = [p.strip() for p in parts if p.strip()]

        # Add start state
        states.append({"name": "[*]", "type": "start"})
        seen.add("[*]")

        for i, part in enumerate(parts):
            # Check for condition label
            label = ""
            colon_idx = part.find(":")
            if colon_idx > 0:
                label = part[colon_idx + 1:].strip()
                part = part[:colon_idx].strip()

            name = part if part else f"State{i}"
            if name not in seen:
                stype = "choice" if re.match(r"(?:if|when|decide|check)", name, re.IGNORECASE) else ""
                states.append({"name": name, "type": stype})
                seen.add(name)

            # Create transition from previous
            if i == 0:
                transitions.append({"from": "[*]", "to": name, "label": label})
            else:
                prev = parts[i - 1] if i - 1 < len(parts) else "[*]"
                colon_idx_prev = parts[i - 1].find(":")
                if colon_idx_prev > 0:
                    prev = parts[i - 1][:colon_idx_prev].strip()
                transitions.append({"from": prev, "to": name, "label": label})

        # Add end state if the last state suggests finality
        if parts and re.match(r"(?:end|finish|complete|done|terminal)", parts[-1], re.IGNORECASE):
            last_state = parts[-1].split(":")[0].strip() if ":" in parts[-1] else parts[-1].strip()
            states.append({"name": "[*]", "type": "end"})
            transitions.append({"from": last_state, "to": "[*]", "label": ""})

        return states, transitions

    @staticmethod
    def _parse_er_description(description: str):
        """Parse a natural-language ER description."""
        entities = []
        relationships = []
        seen = set()

        # Look for "Entity has many X" or "Entity belongs to Y" patterns
        entity_pattern = re.compile(
            r"(\w+)\s+(?:has\s+many|has\s+one|belongs\s+to|contains)\s+(\w+)",
            re.IGNORECASE,
        )

        for match in entity_pattern.finditer(description):
            e1 = match.group(1).strip()
            e2 = match.group(2).strip()
            rel_text = match.group(0).lower()

            for name in (e1, e2):
                if name not in seen:
                    entities.append({"name": name, "attributes": []})
                    seen.add(name)

            if "has many" in rel_text:
                rtype = "one_to_many"
            elif "has one" in rel_text:
                rtype = "one_to_one"
            elif "belongs to" in rel_text:
                rtype = "many_to_one"
            else:
                rtype = "one_to_many"

            relationships.append({"from": e1, "to": e2, "type": rtype, "label": ""})

        # If nothing parsed, create placeholder
        if not entities:
            for word in re.split(r"\s+", description)[:3]:
                name = word.strip().capitalize()
                if name and name not in seen:
                    entities.append({"name": name, "attributes": []})
                    seen.add(name)

        return entities, relationships

    @staticmethod
    def _parse_gantt_description(description: str) -> list:
        """Parse a natural-language Gantt description into tasks."""
        tasks = []
        # Split by common delimiters
        parts = re.split(r"\s*(?:,?\s+then\s+|;\s*|\n)\s*", description, flags=re.IGNORECASE)
        parts = [p.strip() for p in parts if p.strip()]

        for i, part in enumerate(parts):
            # Try to extract task name and duration
            duration_match = re.search(r"(\d+)\s*(?:days?|weeks?|months?|hours?)", part, re.IGNORECASE)
            duration = duration_match.group(0) if duration_match else "7d"
            name = part.replace(duration_match.group(0), "").strip() if duration_match else part
            if not name:
                name = f"Task {i + 1}"

            tasks.append({
                "name": name,
                "start": f"2026-01-{min(i * 7 + 1, 28):02d}",
                "duration": duration,
                "section": "",
                "status": "",
            })

        return tasks

    # ------------------------------------------------------------------
    # Diagram type inference
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_diagram_type(description: str) -> str:
        """Infer the diagram type from a natural-language description."""
        lower = description.lower()

        if re.search(r"\b(sequence|interaction|message|request|response|between.*and)\b", lower):
            return "sequence"
        if re.search(r"\b(class|object|inherit|interface|method|attribute|extends)\b", lower):
            return "class"
        if re.search(r"\b(state|transition|lifecycle|machine|status)\b", lower):
            return "state"
        if re.search(r"\b(entity|relationship|table|schema|database|er\b)\b", lower):
            return "er"
        if re.search(r"\b(gantt|timeline|schedule|task|milestone|deadline|project)\b", lower):
            return "gantt"
        return "flowchart"  # Default

    # ------------------------------------------------------------------
    # Mermaid validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_mermaid(source: str) -> Dict[str, Any]:
        """
        Validate Mermaid syntax with structural checks.
        This is a static analysis — it does not render the diagram.
        """
        warnings: List[str] = []

        # Check for empty source
        if not source.strip():
            return {"valid": False, "warnings": ["Mermaid source is empty"]}

        # Check for recognized diagram type header
        first_line = source.strip().split("\n", 1)[0].strip()
        valid_headers = [
            "flowchart", "graph", "sequenceDiagram", "classDiagram",
            "stateDiagram", "stateDiagram-v2", "erDiagram", "gantt",
            "pie", "journey", "gitGraph", "mindmap", "timeline",
        ]
        has_header = any(first_line.startswith(h) for h in valid_headers)
        if not has_header:
            # Check if there's a title frontmatter
            lines = source.strip().split("\n")
            header_found = False
            for line in lines[:5]:
                if any(line.strip().startswith(h) for h in valid_headers):
                    header_found = True
                    break
            if not header_found:
                warnings.append("Missing recognized Mermaid diagram type header (e.g. flowchart, sequenceDiagram)")

        # Check for unbalanced braces
        open_braces = source.count("{")
        close_braces = source.count("}")
        if open_braces != close_braces:
            warnings.append(f"Unbalanced braces: {open_braces} opening vs {close_braces} closing")

        # Check for unbalanced parentheses
        open_parens = source.count("(")
        close_parens = source.count(")")
        if open_parens != close_parens:
            warnings.append(f"Unbalanced parentheses: {open_parens} opening vs {close_parens} closing")

        # Check for common syntax issues
        if "-->" in source and "->" in source and "sequenceDiagram" not in source:
            warnings.append("Mixed arrow syntax: both '-->' and '->' found. Use '->' for flowcharts, '-->' for sequence diagrams")

        # Check for invalid characters in node IDs (Mermaid IDs must be alphanumeric)
        id_pattern = re.compile(r"^\s*(\w[\w]*)\s*[{(\[]", re.MULTILINE)
        for match in id_pattern.finditer(source):
            nid = match.group(1)
            if not re.match(r"^[a-zA-Z_][\w]*$", nid):
                warnings.append(f"Invalid node ID: '{nid}'. IDs must start with a letter or underscore and contain only alphanumeric characters.")

        return {
            "valid": len(warnings) == 0,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_id(raw: str) -> str:
        """
        Convert a string into a valid Mermaid node ID.
        Replace spaces/special chars with underscores, strip leading digits.
        """
        sanitized = re.sub(r"[^\w]", "_", raw)
        # Remove leading non-alpha characters
        sanitized = re.sub(r"^[^a-zA-Z]+", "", sanitized)
        if not sanitized:
            sanitized = "node"
        return sanitized