"""
Aethera AI — Auto-Learning Pipeline

Automatically processes uploaded files through a 10-stage pipeline:
1. Document classification (type, domain, sensitivity)
2. Content extraction (text, tables, images)
3. Entity extraction (people, orgs, codes, dates, amounts)
4. Knowledge indexing (ChromaDB with metadata)
5. Fact extraction (verified facts with source attribution)
6. Profile updating (user preferences from content)
7. Skill detection (workflow/process patterns)
8. Memory updating (knowledge graph nodes + edges)
9. Contradiction checking (validate against existing knowledge)
10. Notification ("I've learned X from this document")
"""

from .pipeline import AutoLearningPipeline, run_pipeline_for_file, run_pipeline_for_url
from .context import PipelineContext, PipelineResult

__all__ = ["AutoLearningPipeline", "PipelineContext", "PipelineResult",
           "run_pipeline_for_file", "run_pipeline_for_url"]