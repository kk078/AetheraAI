"""
Aethera AI — Data Intelligence Layer

Processes datasets through a 7-stage pipeline:
1. Curation: collect, clean, deduplicate, validate
2. Annotation: label data for categories, sentiment, entities, relationships
3. Preprocessing: normalize, transform, feature engineering
4. Quality scoring: completeness, accuracy, consistency, timeliness
5. Auto-schema detection: infer structure from unstructured data
6. Versioning: track changes to datasets over time
7. Export: generate clean datasets in CSV, JSON, Parquet, XLSX
"""

from .store import DatasetStore, get_dataset_store
from .context import DataPipelineContext, DataPipelineResult
from .pipeline import DataIntelligencePipeline

__all__ = [
    "DataIntelligencePipeline",
    "DatasetStore",
    "DataPipelineContext",
    "DataPipelineResult",
    "get_dataset_store",
]