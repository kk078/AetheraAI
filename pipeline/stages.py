"""
Aethera AI — Pipeline Stage Base Class

Each pipeline stage inherits from PipelineStage and implements execute().
Stages are composable, individually testable, and gracefully handle errors.
"""
import logging
from typing import Optional

from .context import PipelineContext

logger = logging.getLogger("aethera.pipeline")


class PipelineStage:
    """
    Base class for auto-learning pipeline stages.

    Each stage:
    - Has a unique name
    - Reads from and writes to PipelineContext
    - Returns the modified context
    - Wraps execution in try/except for graceful degradation
    """

    name: str = "base"

    @property
    def depends_on(self) -> list:
        """List of stage names that must complete before this stage runs."""
        return []

    @property
    def required_content(self) -> bool:
        """Whether this stage requires extracted text content."""
        return True

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute the pipeline stage.

        Args:
            context: Current pipeline state

        Returns:
            Updated pipeline context
        """
        raise NotImplementedError

    async def run(self, context: PipelineContext) -> PipelineContext:
        """
        Run the stage with error handling and tracking.

        Wraps execute() in try/except. On failure, logs the error
        and records it in context.stages_failed, then returns context
        so the pipeline can continue with other stages.
        """
        # Skip if required content is missing
        if self.required_content and not context.raw_text:
            logger.debug(f"Skipping {self.name}: no text content extracted")
            return context

        # Skip if dependencies failed
        for dep in self.depends_on:
            if dep in context.stages_failed:
                logger.debug(f"Skipping {self.name}: dependency {dep} failed")
                return context

        try:
            context = await self.execute(context)
            context.stages_completed.append(self.name)
            logger.info(f"Pipeline stage completed: {self.name}")
        except Exception as e:
            context.stages_failed[self.name] = str(e)
            logger.error(f"Pipeline stage failed: {self.name} — {e}")
        return context