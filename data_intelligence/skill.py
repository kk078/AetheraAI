"""
Aethera AI — Dataset Intelligence Skill

Wraps the DataIntelligencePipeline as an AetheraSkill,
exposing it through the skill registry for LLM tool calling.
"""

import logging
from typing import Any, Dict, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill

logger = logging.getLogger("aethera.skills.data_intelligence")


@skill(name="data_intelligence", category="data")
class DatasetIntelligenceSkill(AetheraSkill):
    """
    Data intelligence skill for dataset processing.

    Actions:
    - curate: Load, clean, deduplicate, validate data
    - annotate: Label data for categories, sentiment, entities
    - preprocess: Normalize, transform, feature engineering
    - quality: Score data quality (completeness, accuracy, consistency, timeliness)
    - schema: Detect schema (types, keys, constraints)
    - version: Create a version snapshot
    - export: Export in CSV, JSON, Parquet, or XLSX
    - full_pipeline: Run all stages
    """

    @property
    def name(self) -> str:
        return "data_intelligence"

    @property
    def description(self) -> str:
        return (
            "Process and analyze datasets: curate, annotate, preprocess, "
            "score quality, detect schema, version, and export data. "
            "Supports CSV, JSON, XLSX, and Parquet formats."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "curate", "annotate", "preprocess", "quality",
                        "schema", "version", "export", "full_pipeline",
                    ],
                    "description": "The data intelligence action to perform",
                },
                "dataset_id": {
                    "type": "string",
                    "description": "ID of an existing dataset to process",
                },
                "name": {
                    "type": "string",
                    "description": "Name for a new dataset",
                },
                "source_type": {
                    "type": "string",
                    "enum": ["file", "inline", "url"],
                    "description": "Data source type",
                },
                "source_path": {
                    "type": "string",
                    "description": "File path or URL for the data source",
                },
                "data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Inline data as array of objects",
                },
                "format": {
                    "type": "string",
                    "enum": ["csv", "json", "xlsx", "parquet"],
                    "description": "Data format (default: csv)",
                },
                "export_format": {
                    "type": "string",
                    "enum": ["csv", "json", "jsonl", "parquet", "xlsx"],
                    "description": "Export format (default: csv)",
                },
                "options": {
                    "type": "object",
                    "description": "Processing options (annotation_types, sample_size, etc.)",
                },
            },
            "required": ["action"],
        }

    @property
    def examples(self) -> list:
        return [
            {
                "input": {
                    "action": "full_pipeline",
                    "name": "sales_data",
                    "source_type": "file",
                    "source_path": "/data/sales.csv",
                    "format": "csv",
                },
                "output": "Processed 1,000 rows through 7 stages. Quality score: 0.87",
            },
            {
                "input": {
                    "action": "quality",
                    "dataset_id": "ds_abc123",
                },
                "output": "Quality scores: completeness=0.95, accuracy=0.88, consistency=0.92, timeliness=0.78",
            },
            {
                "input": {
                    "action": "export",
                    "dataset_id": "ds_abc123",
                    "export_format": "parquet",
                },
                "output": "Exported 500 rows in Parquet format",
            },
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "full_pipeline")
        dataset_id = kwargs.get("dataset_id", "")
        name = kwargs.get("name", "")
        source_type = kwargs.get("source_type", "inline")
        source_path = kwargs.get("source_path", "")
        data = kwargs.get("data", [])
        fmt = kwargs.get("format", "csv")
        export_format = kwargs.get("export_format", "csv")
        options = kwargs.get("options", {})

        try:
            from data_intelligence.pipeline import DataIntelligencePipeline
            from data_intelligence.context import DataPipelineContext
            import uuid

            # Map actions to stage names
            action_to_stages = {
                "curate": ["curation"],
                "annotate": ["curation", "annotation"],
                "preprocess": ["curation", "preprocessing"],
                "quality": ["curation", "quality"],
                "schema": ["curation", "schema_detect"],
                "version": ["curation", "versioning"],
                "export": ["curation", "export"],
                "full_pipeline": None,  # Run all stages
            }

            stages = action_to_stages.get(action)

            # Set export format in options if exporting
            if action == "export":
                options["export_format"] = export_format

            context = DataPipelineContext(
                dataset_id=dataset_id or f"ds_{uuid.uuid4().hex[:12]}",
                name=name,
                source_type=source_type,
                source_path=source_path,
                format=fmt,
                options=options,
                rows=data or [],
                export_format=export_format if action == "export" else "",
            )

            pipeline = DataIntelligencePipeline()
            result = await pipeline.run(context, stages=stages)

            return SkillResult(
                success=True,
                data={
                    "dataset_id": result.dataset_id,
                    "name": result.name,
                    "status": result.status,
                    "stages_completed": result.stages_completed,
                    "stages_failed": result.stages_failed,
                    "row_count": result.row_count,
                    "column_count": result.column_count,
                    "quality_scores": result.quality_scores,
                    "schema_info": result.schema_info,
                    "version_number": result.version_number,
                    "export_available": result.export_available,
                    "annotations_count": result.annotations_count,
                },
            )

        except Exception as e:
            logger.error(f"Data intelligence skill error: {e}")
            return SkillResult(success=False, error=str(e))