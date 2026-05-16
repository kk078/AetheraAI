"""
Aethera AI — Data Intelligence Pipeline Orchestrator

Runs the 7-stage data processing pipeline with graceful degradation.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from .context import DataPipelineContext, DataPipelineResult
from .curation import DatasetCurationStage
from .annotation import DataAnnotationStage
from .preprocessing import DataPreprocessingStage
from .quality import DataQualityScoringStage
from .schema_detect import AutoSchemaDetectionStage
from .versioning import DataVersioningStage
from .export import DataExportStage

logger = logging.getLogger("aethera.data_intelligence.pipeline")

# All stages in execution order
DATA_PIPELINE_STAGES = [
    DatasetCurationStage,
    DataAnnotationStage,
    DataPreprocessingStage,
    DataQualityScoringStage,
    AutoSchemaDetectionStage,
    DataVersioningStage,
    DataExportStage,
]

# Pipeline job tracking (in-memory)
_pipeline_jobs: Dict[str, DataPipelineResult] = {}


class DataIntelligencePipeline:
    """
    Orchestrates the 7-stage data intelligence pipeline.

    Each stage runs in order. Stage failures are logged but don't stop
    the pipeline — later stages that depend on a failed stage are skipped.
    """

    def __init__(self):
        self.stages = [stage_cls() for stage_cls in DATA_PIPELINE_STAGES]

    async def run(
        self,
        context: DataPipelineContext,
        stages: Optional[List[str]] = None,
    ) -> DataPipelineResult:
        """
        Run the data intelligence pipeline.

        Args:
            context: Initial pipeline context with dataset info
            stages: Optional list of stage names to run (runs all if None)

        Returns:
            DataPipelineResult with processing summary
        """
        context.started_at = datetime.now().isoformat() if hasattr(context, 'started_at') else datetime.now().isoformat()

        # Register job
        job_id = context.dataset_id or str(uuid.uuid4())
        result = DataPipelineResult(
            dataset_id=job_id,
            name=context.name,
            status="processing",
            started_at=context.started_at if hasattr(context, 'started_at') else datetime.now().isoformat(),
        )
        _pipeline_jobs[job_id] = result

        try:
            # Filter stages if specific ones requested
            stages_to_run = self.stages
            if stages:
                stages_to_run = [s for s in self.stages if s.name in stages]

            for stage in stages_to_run:
                context = await stage.run(context)
                result.stages_completed = context.stages_completed
                result.stages_failed = context.stages_failed

            context.completed_at = datetime.now().isoformat() if hasattr(context, 'completed_at') else None
            result = DataPipelineResult.from_context(context)
            result.status = "completed" if not context.stages_failed else "partial"

        except Exception as e:
            logger.error(f"Data pipeline fatal error: {e}")
            result.status = "failed"
            result.stages_failed = {"pipeline": str(e)}

        _pipeline_jobs[job_id] = result
        return result

    @staticmethod
    def get_job_status(job_id: str) -> Optional[DataPipelineResult]:
        """Get the status of a pipeline job."""
        return _pipeline_jobs.get(job_id)

    @staticmethod
    def list_jobs() -> Dict[str, Dict]:
        """List all pipeline jobs."""
        return {
            jid: {
                "dataset_id": r.dataset_id,
                "name": r.name,
                "status": r.status,
                "stages_completed": r.stages_completed,
                "stages_failed": r.stages_failed,
            }
            for jid, r in _pipeline_jobs.items()
        }


async def run_data_pipeline(
    dataset_id: str = "",
    name: str = "",
    source_type: str = "inline",
    source_path: str = "",
    format: str = "csv",
    data: Optional[List[Dict]] = None,
    options: Optional[Dict] = None,
    stages: Optional[List[str]] = None,
) -> DataPipelineResult:
    """
    Convenience function to run the data intelligence pipeline.

    Args:
        dataset_id: Existing dataset ID (for re-processing)
        name: Dataset name
        source_type: 'file', 'inline', or 'url'
        source_path: File path or URL
        format: Data format ('csv', 'json', 'xlsx', 'parquet')
        data: Inline data (list of dicts)
        options: Processing options
        stages: Optional list of stage names to run

    Returns:
        DataPipelineResult
    """
    context = DataPipelineContext(
        dataset_id=dataset_id or f"ds_{uuid.uuid4().hex[:12]}",
        name=name,
        source_type=source_type,
        source_path=source_path,
        format=format,
        options=options or {},
        rows=data or [],
    )

    pipeline = DataIntelligencePipeline()
    return await pipeline.run(context, stages=stages)