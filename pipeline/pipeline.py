"""
Aethera AI — Auto-Learning Pipeline Orchestrator

Runs the 10-stage document processing pipeline with graceful degradation,
job tracking, and background execution support.
"""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional

from .context import PipelineContext, PipelineResult
from .classifier import DocumentClassifier
from .extractor import ContentExtractor
from .entities import EntityExtractor
from .indexer import KnowledgeIndexer
from .facts import FactExtractor
from .profile import ProfileUpdater
from .skills_detect import SkillDetector
from .memory_update import MemoryUpdater
from .contradictions import ContradictionChecker
from .notification import NotificationBuilder

logger = logging.getLogger("aethera.pipeline")

# Stage execution order
PIPELINE_STAGES = [
    DocumentClassifier,
    ContentExtractor,
    EntityExtractor,
    KnowledgeIndexer,
    FactExtractor,
    ProfileUpdater,
    SkillDetector,
    MemoryUpdater,
    ContradictionChecker,
    NotificationBuilder,
]

# Job tracking (in-memory; persists for session lifetime)
_pipeline_jobs: Dict[str, PipelineResult] = {}


class AutoLearningPipeline:
    """
    Orchestrates the 10-stage auto-learning pipeline.

    Each stage runs in order. Stage failures are logged but don't stop
    the pipeline — later stages that depend on a failed stage are skipped.
    The pipeline returns a PipelineResult with notification and stats.
    """

    def __init__(self):
        self.stages = [stage_cls() for stage_cls in PIPELINE_STAGES]

    async def run(self, context: PipelineContext) -> PipelineResult:
        """
        Run all pipeline stages in sequence.

        Args:
            context: Initial pipeline context with file_path or url

        Returns:
            PipelineResult with notification and statistics
        """
        context.started_at = datetime.now().isoformat()

        # Register job
        result = PipelineResult(job_id=context.job_id, status="processing",
                                started_at=context.started_at)
        _pipeline_jobs[context.job_id] = result

        try:
            for stage in self.stages:
                context = await stage.run(context)
                # Update job status after each stage
                result.stages_completed = context.stages_completed
                result.stages_failed = context.stages_failed

            context.completed_at = datetime.now().isoformat()
            result = PipelineResult.from_context(context)
            result.status = "completed" if not context.stages_failed else "partial"

        except Exception as e:
            logger.error(f"Pipeline fatal error: {e}")
            result.status = "failed"
            context.completed_at = datetime.now().isoformat()

        # Update job tracking
        _pipeline_jobs[context.job_id] = result
        return result

    @staticmethod
    def get_job_status(job_id: str) -> Optional[PipelineResult]:
        """Get the status of a pipeline job."""
        return _pipeline_jobs.get(job_id)

    @staticmethod
    def list_jobs() -> Dict[str, Dict]:
        """List all pipeline jobs and their statuses."""
        return {
            jid: {
                "status": r.status,
                "file_type": r.file_type,
                "domain": r.domain,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
            }
            for jid, r in _pipeline_jobs.items()
        }


async def run_pipeline_for_file(
    file_path: str,
    filename: str = "",
    content_type: str = "",
    job_id: Optional[str] = None,
) -> PipelineResult:
    """
    Convenience function to run the pipeline on a file.

    Args:
        file_path: Path to the uploaded file
        filename: Original filename
        content_type: MIME type
        job_id: Optional job ID (auto-generated if omitted)

    Returns:
        PipelineResult
    """
    if not job_id:
        job_id = str(uuid.uuid4())

    context = PipelineContext(
        job_id=job_id,
        file_path=file_path,
        filename=filename,
        content_type=content_type,
    )

    pipeline = AutoLearningPipeline()
    return await pipeline.run(context)


async def run_pipeline_for_url(
    url: str,
    domain: str = "general",
    job_id: Optional[str] = None,
) -> PipelineResult:
    """
    Convenience function to run the pipeline on a URL.

    Args:
        url: URL to fetch and process
        domain: Optional domain hint
        job_id: Optional job ID

    Returns:
        PipelineResult
    """
    if not job_id:
        job_id = str(uuid.uuid4())

    context = PipelineContext(
        job_id=job_id,
        url=url,
        domain=domain,
    )

    pipeline = AutoLearningPipeline()
    return await pipeline.run(context)