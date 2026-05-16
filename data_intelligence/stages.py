"""
Aethera AI — Data Pipeline Stage Base Class

Mirrors the PipelineStage pattern from pipeline/stages.py but operates
on DataPipelineContext instead of PipelineContext.
"""

import logging
from typing import List

from .context import DataPipelineContext

logger = logging.getLogger("aethera.data_intelligence.stages")

# Stage execution order
DATA_PIPELINE_STAGES_ORDER = [
    "curation",
    "annotation",
    "preprocessing",
    "quality",
    "schema_detect",
    "versioning",
    "export",
]


class DataPipelineStage:
    """Base class for data intelligence pipeline stages."""

    name: str = "base"

    @property
    def depends_on(self) -> List[str]:
        """Names of stages that must complete before this one runs."""
        return []

    @property
    def required_content(self) -> bool:
        """Whether cleaned_rows must have data for this stage to run."""
        return True

    async def execute(self, context: DataPipelineContext) -> DataPipelineContext:
        """Execute the stage. Must be overridden by subclasses."""
        raise NotImplementedError

    async def run(self, context: DataPipelineContext) -> DataPipelineContext:
        """Run the stage with error handling and dependency checking."""
        # Check if required content is missing
        if self.required_content and not context.rows and not context.cleaned_rows:
            logger.debug(f"Skipping {self.name}: no data to process")
            return context

        # Check if dependencies failed
        for dep in self.depends_on:
            if dep in context.stages_failed:
                logger.debug(f"Skipping {self.name}: dependency {dep} failed")
                return context

        try:
            context = await self.execute(context)
            context.stages_completed.append(self.name)
            logger.info(f"Data pipeline stage completed: {self.name}")
        except Exception as e:
            context.stages_failed[self.name] = str(e)
            logger.error(f"Data pipeline stage failed: {self.name} — {e}")

        return context