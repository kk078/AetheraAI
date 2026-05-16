"""
Aethera AI - Data Visualizer Skill

Generate Vega-Lite chart specifications from data.
Supports bar, line, pie, scatter, and histogram charts.
Outputs JSON chart specs that the frontend can render directly.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from skills.skill_base import AetheraSkill, SkillResult, skill


# Common color palettes
CATEGORY_10 = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
    "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac",
]

SEQUENTIAL_BLUE = [
    "#c6dbef", "#9ecae1", "#6baed6", "#4292c6", "#2171b5", "#084594",
]


@skill(name="data_visualizer", category="data")
class DataVisualizerSkill(AetheraSkill):
    """
    Generate Vega-Lite chart specification JSON from data.
    Supports bar, line, pie, scatter, and histogram charts.
    """

    @property
    def name(self) -> str:
        return "data_visualizer"

    @property
    def description(self) -> str:
        return (
            "Generate Vega-Lite chart specifications (bar, line, pie, scatter, histogram) "
            "from data, outputting JSON for frontend rendering"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter", "histogram"],
                    "description": "Type of chart to generate",
                },
                "data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Data records as array of objects",
                },
                "x_field": {
                    "type": "string",
                    "description": "Field name for x-axis (or category for bar/pie)",
                },
                "y_field": {
                    "type": "string",
                    "description": "Field name for y-axis (or value for bar/pie)",
                },
                "color_field": {
                    "type": "string",
                    "description": "Field name for color encoding (grouping)",
                },
                "size_field": {
                    "type": "string",
                    "description": "Field name for size encoding (scatter point size)",
                },
                "title": {
                    "type": "string",
                    "description": "Chart title",
                },
                "width": {
                    "type": "integer",
                    "description": "Chart width in pixels",
                    "default": 600,
                },
                "height": {
                    "type": "integer",
                    "description": "Chart height in pixels",
                    "default": 400,
                },
                "x_label": {
                    "type": "string",
                    "description": "Custom label for x-axis",
                },
                "y_label": {
                    "type": "string",
                    "description": "Custom label for y-axis",
                },
                "bins": {
                    "type": "integer",
                    "description": "Number of bins for histogram",
                    "default": 10,
                },
                "stacked": {
                    "type": "boolean",
                    "description": "Whether to stack bars (for bar charts with color grouping)",
                    "default": False,
                },
                "sort_x": {
                    "type": "string",
                    "enum": ["ascending", "descending", "none"],
                    "description": "Sort order for x-axis categories",
                    "default": "none",
                },
                "color_palette": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Custom color palette as hex strings",
                },
                "orientation": {
                    "type": "string",
                    "enum": ["vertical", "horizontal"],
                    "description": "Bar chart orientation",
                    "default": "vertical",
                },
            },
            "required": ["chart_type", "data"],
        }

    @property
    def examples(self) -> list:
        return [
            {
                "input": {
                    "chart_type": "bar",
                    "data": [
                        {"category": "A", "value": 10},
                        {"category": "B", "value": 25},
                        {"category": "C", "value": 15},
                    ],
                    "x_field": "category",
                    "y_field": "value",
                    "title": "Sales by Category",
                }
            },
            {
                "input": {
                    "chart_type": "line",
                    "data": [
                        {"month": "Jan", "revenue": 1000},
                        {"month": "Feb", "revenue": 1200},
                        {"month": "Mar", "revenue": 1500},
                    ],
                    "x_field": "month",
                    "y_field": "revenue",
                    "title": "Monthly Revenue",
                }
            },
            {
                "input": {
                    "chart_type": "scatter",
                    "data": [
                        {"x": 1, "y": 2.3},
                        {"x": 2, "y": 4.1},
                        {"x": 3, "y": 3.8},
                    ],
                    "x_field": "x",
                    "y_field": "y",
                }
            },
        ]

    async def execute(self, **kwargs) -> SkillResult:
        chart_type = kwargs.get("chart_type", "")
        data = kwargs.get("data", [])

        if not chart_type:
            return SkillResult(success=False, error="chart_type is required")
        if not data or not isinstance(data, list):
            return SkillResult(success=False, error="data must be a non-empty array of objects")

        try:
            if chart_type == "bar":
                spec = self._build_bar(kwargs, data)
            elif chart_type == "line":
                spec = self._build_line(kwargs, data)
            elif chart_type == "pie":
                spec = self._build_pie(kwargs, data)
            elif chart_type == "scatter":
                spec = self._build_scatter(kwargs, data)
            elif chart_type == "histogram":
                spec = self._build_histogram(kwargs, data)
            else:
                return SkillResult(success=False, error=f"Unknown chart_type: {chart_type}")

            return SkillResult(
                success=True,
                data={
                    "chart_type": chart_type,
                    "spec": spec,
                    "record_count": len(data),
                },
            )
        except Exception as e:
            return SkillResult(success=False, error=f"Chart generation failed: {e}")

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _base_spec(self, kwargs: dict, data: list) -> Dict[str, Any]:
        """Build the common base of any Vega-Lite spec."""
        title = kwargs.get("title", "")
        width = kwargs.get("width", 600)
        height = kwargs.get("height", 400)

        spec: Dict[str, Any] = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "data": {"values": data},
        }

        if title:
            spec["title"] = {"text": title}

        if width:
            spec["width"] = width
        if height:
            spec["height"] = height

        return spec

    def _axis_encoding(self, kwargs: dict, field: str, axis_name: str) -> Dict[str, Any]:
        """Build an axis encoding block."""
        encoding: Dict[str, Any] = {"field": field}

        # Detect type from first non-null value in data
        # (already done via inferTypes by Vega-Lite, but we provide hints)

        label = kwargs.get(f"{axis_name}_label")
        if label:
            encoding["axis"] = {"title": label}

        sort = kwargs.get("sort_x", "none")
        if axis_name == "x" and sort != "none":
            encoding["sort"] = sort

        return encoding

    def _add_color_encoding(self, kwargs: dict, data: list) -> Optional[Dict[str, Any]]:
        """Build a color encoding if color_field is provided."""
        color_field = kwargs.get("color_field")
        if not color_field:
            return None

        palette = kwargs.get("color_palette", CATEGORY_10)

        return {
            "field": color_field,
            "type": "nominal",
            "scale": {"range": palette},
            "legend": {"title": color_field},
        }

    # ------------------------------------------------------------------
    # Chart builders
    # ------------------------------------------------------------------

    def _build_bar(self, kwargs: dict, data: list) -> Dict[str, Any]:
        """Build a bar chart spec."""
        x_field = kwargs.get("x_field", "")
        y_field = kwargs.get("y_field", "")
        if not x_field or not y_field:
            raise ValueError("x_field and y_field are required for bar charts")

        spec = self._base_spec(kwargs, data)

        orientation = kwargs.get("orientation", "vertical")
        stacked = kwargs.get("stacked", False)
        color_field = kwargs.get("color_field")

        x_enc = self._axis_encoding(kwargs, x_field, "x")
        y_enc = self._axis_encoding(kwargs, y_field, "y")

        # Determine types
        y_values = [row.get(y_field) for row in data if row.get(y_field) is not None]
        if all(isinstance(v, (int, float)) for v in y_values):
            y_enc["type"] = "quantitative"
        else:
            y_enc["type"] = "nominal"

        x_values = [row.get(x_field) for row in data if row.get(x_field) is not None]
        if all(isinstance(v, (int, float)) for v in x_values):
            x_enc["type"] = "quantitative"
        else:
            x_enc["type"] = "nominal"

        # For horizontal bars, swap x and y in the mark
        if orientation == "horizontal":
            x_enc, y_enc = y_enc, x_enc
            # Swap labels too
            x_label = kwargs.get("x_label")
            y_label = kwargs.get("y_label")
            if x_label:
                x_enc.setdefault("axis", {})["title"] = x_label
            if y_label:
                y_enc.setdefault("axis", {})["title"] = y_label

        encoding: Dict[str, Any] = {
            "x": x_enc,
            "y": y_enc,
        }

        if color_field:
            color_enc = self._add_color_encoding(kwargs, data)
            if color_enc:
                encoding["color"] = color_enc
                if stacked:
                    y_enc["stack"] = "stack"
                else:
                    y_enc["stack"] = None

        spec["mark"] = {"type": "bar", "tooltip": True}
        spec["encoding"] = encoding

        return spec

    def _build_line(self, kwargs: dict, data: list) -> Dict[str, Any]:
        """Build a line chart spec."""
        x_field = kwargs.get("x_field", "")
        y_field = kwargs.get("y_field", "")
        if not x_field or not y_field:
            raise ValueError("x_field and y_field are required for line charts")

        spec = self._base_spec(kwargs, data)

        x_enc = self._axis_encoding(kwargs, x_field, "x")
        y_enc = self._axis_encoding(kwargs, y_field, "y")
        y_enc["type"] = "quantitative"

        # Detect x type
        x_values = [row.get(x_field) for row in data if row.get(x_field) is not None]
        if all(isinstance(v, (int, float)) for v in x_values):
            x_enc["type"] = "quantitative"
        else:
            x_enc["type"] = "nominal"

        encoding: Dict[str, Any] = {
            "x": x_enc,
            "y": y_enc,
        }

        color_field = kwargs.get("color_field")
        if color_field:
            color_enc = self._add_color_encoding(kwargs, data)
            if color_enc:
                encoding["color"] = color_enc

        spec["mark"] = {"type": "line", "tooltip": True, "point": True}
        spec["encoding"] = encoding

        return spec

    def _build_pie(self, kwargs: dict, data: list) -> Dict[str, Any]:
        """Build a pie chart spec (using Vega-Lite arc mark)."""
        x_field = kwargs.get("x_field", "")
        y_field = kwargs.get("y_field", "")

        # For pie charts, we use theta for the angle and color for slices
        # Vega-Lite represents pies as arc marks
        category_field = x_field or kwargs.get("color_field", "")
        value_field = y_field or ""

        if not category_field:
            # Try to infer: first string column as category, first numeric as value
            if data:
                for key in data[0]:
                    vals = [row.get(key) for row in data if row.get(key) is not None]
                    if all(isinstance(v, str) for v in vals) and not category_field:
                        category_field = key
                    elif all(isinstance(v, (int, float)) for v in vals) and not value_field:
                        value_field = key

        if not category_field or not value_field:
            raise ValueError("x_field (category) and y_field (value) are required for pie charts")

        spec = self._base_spec(kwargs, data)

        palette = kwargs.get("color_palette", CATEGORY_10)

        encoding: Dict[str, Any] = {
            "theta": {
                "field": value_field,
                "type": "quantitative",
                "stack": True,
            },
            "color": {
                "field": category_field,
                "type": "nominal",
                "scale": {"range": palette},
                "legend": {"title": category_field},
            },
        }

        spec["mark"] = {"type": "arc", "innerRadius": 0, "tooltip": True}
        spec["encoding"] = encoding

        return spec

    def _build_scatter(self, kwargs: dict, data: list) -> Dict[str, Any]:
        """Build a scatter plot spec."""
        x_field = kwargs.get("x_field", "")
        y_field = kwargs.get("y_field", "")
        if not x_field or not y_field:
            raise ValueError("x_field and y_field are required for scatter charts")

        spec = self._base_spec(kwargs, data)

        x_enc = self._axis_encoding(kwargs, x_field, "x")
        y_enc = self._axis_encoding(kwargs, y_field, "y")
        x_enc["type"] = "quantitative"
        y_enc["type"] = "quantitative"

        encoding: Dict[str, Any] = {
            "x": x_enc,
            "y": y_enc,
        }

        color_field = kwargs.get("color_field")
        if color_field:
            color_enc = self._add_color_encoding(kwargs, data)
            if color_enc:
                encoding["color"] = color_enc

        size_field = kwargs.get("size_field")
        if size_field:
            encoding["size"] = {
                "field": size_field,
                "type": "quantitative",
                "legend": {"title": size_field},
            }

        spec["mark"] = {"type": "point", "tooltip": True, "filled": True}
        spec["encoding"] = encoding

        return spec

    def _build_histogram(self, kwargs: dict, data: list) -> Dict[str, Any]:
        """Build a histogram spec."""
        x_field = kwargs.get("x_field", "")
        if not x_field:
            # Try to find the first numeric field
            if data:
                for key in data[0]:
                    vals = [row.get(key) for row in data if row.get(key) is not None]
                    if all(isinstance(v, (int, float)) for v in vals):
                        x_field = key
                        break
            if not x_field:
                raise ValueError("x_field is required for histograms (must be numeric)")

        spec = self._base_spec(kwargs, data)
        bins = kwargs.get("bins", 10)

        x_enc = self._axis_encoding(kwargs, x_field, "x")
        x_enc["type"] = "quantitative"
        x_enc["bin"] = {"maxbins": bins}

        encoding: Dict[str, Any] = {
            "x": x_enc,
            "y": {
                "aggregate": "count",
                "type": "quantitative",
            },
        }

        color_field = kwargs.get("color_field")
        if color_field:
            color_enc = self._add_color_encoding(kwargs, data)
            if color_enc:
                encoding["color"] = color_enc

        y_label = kwargs.get("y_label", "Count")
        encoding["y"]["axis"] = {"title": y_label}

        spec["mark"] = {"type": "bar", "tooltip": True}
        spec["encoding"] = encoding

        return spec