"""
Aethera AI — Data Intelligence Pipeline Context

Carries state through the data processing pipeline stages.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DataPipelineContext:
    """Accumulates state through the data intelligence pipeline stages."""

    # Input identification
    dataset_id: str = ""
    name: str = ""
    description: str = ""
    source_type: str = ""  # 'file', 'inline', 'url'
    source_path: str = ""
    format: str = ""  # 'csv', 'json', 'xlsx', 'parquet', 'text'

    # Data
    rows: List[Dict[str, Any]] = field(default_factory=list)
    headers: List[str] = field(default_factory=list)

    # Processing options
    options: Dict[str, Any] = field(default_factory=dict)

    # Curation results
    cleaned_rows: List[Dict[str, Any]] = field(default_factory=list)
    duplicates_removed: int = 0
    validation_errors: List[str] = field(default_factory=list)

    # Annotation results
    annotations: List[Dict[str, Any]] = field(default_factory=list)

    # Preprocessing results
    transformed_rows: List[Dict[str, Any]] = field(default_factory=list)
    transformations_applied: List[str] = field(default_factory=list)

    # Schema detection results
    schema_info: Dict[str, Any] = field(default_factory=dict)
    detected_primary_key: Optional[str] = None
    detected_foreign_keys: List[Dict[str, str]] = field(default_factory=list)

    # Quality scoring results
    quality_scores: Dict[str, float] = field(default_factory=dict)
    quality_details: Dict[str, Any] = field(default_factory=dict)

    # Versioning results
    version_id: str = ""
    version_number: int = 0
    checksum: str = ""

    # Export results
    export_content: Optional[str] = None
    export_path: Optional[str] = None
    export_format: str = ""
    export_bytes: Optional[bytes] = None

    # Internal tracking
    stages_completed: List[str] = field(default_factory=list)
    stages_failed: Dict[str, str] = field(default_factory=dict)

    @property
    def row_count(self) -> int:
        return len(self.rows) or len(self.cleaned_rows)

    @property
    def column_count(self) -> int:
        return len(self.headers)


@dataclass
class DataPipelineResult:
    """Final result from the data intelligence pipeline."""

    dataset_id: str = ""
    name: str = ""
    status: str = "pending"  # pending, processing, completed, partial, failed
    stages_completed: List[str] = field(default_factory=list)
    stages_failed: Dict[str, str] = field(default_factory=dict)
    row_count: int = 0
    column_count: int = 0
    duplicates_removed: int = 0
    validation_errors: List[str] = field(default_factory=list)
    annotations_count: int = 0
    transformations_applied: List[str] = field(default_factory=list)
    schema_info: Dict[str, Any] = field(default_factory=dict)
    quality_scores: Dict[str, float] = field(default_factory=dict)
    quality_details: Dict[str, Any] = field(default_factory=dict)
    version_id: str = ""
    version_number: int = 0
    checksum: str = ""
    export_format: str = ""
    export_available: bool = False
    started_at: str = ""
    completed_at: str = ""

    @classmethod
    def from_context(cls, ctx: DataPipelineContext) -> "DataPipelineResult":
        return cls(
            dataset_id=ctx.dataset_id,
            name=ctx.name,
            status="completed" if not ctx.stages_failed else "partial",
            stages_completed=ctx.stages_completed,
            stages_failed=ctx.stages_failed,
            row_count=ctx.row_count,
            column_count=ctx.column_count,
            duplicates_removed=ctx.duplicates_removed,
            validation_errors=ctx.validation_errors,
            annotations_count=len(ctx.annotations),
            transformations_applied=ctx.transformations_applied,
            schema_info=ctx.schema_info,
            quality_scores=ctx.quality_scores,
            quality_details=ctx.quality_details,
            version_id=ctx.version_id,
            version_number=ctx.version_number,
            checksum=ctx.checksum,
            export_format=ctx.export_format,
            export_available=ctx.export_content is not None or ctx.export_bytes is not None,
        )