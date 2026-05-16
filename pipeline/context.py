"""
Aethera AI — Pipeline Context

Dataclasses that carry state through the 10-stage auto-learning pipeline.
PipelineContext accumulates outputs; PipelineResult tracks job progress.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExtractedEntity:
    """An entity extracted from document content."""
    entity_type: str  # person, organization, condition, drug, procedure, payer, etc.
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    source_snippet: str = ""


@dataclass
class ExtractedFact:
    """A fact extracted from document content."""
    fact_text: str
    category: str = "general"
    confidence: float = 0.5
    tags: List[str] = field(default_factory=list)
    source: str = ""
    source_type: str = "document"


@dataclass
class Contradiction:
    """A detected contradiction between a new fact and existing knowledge."""
    new_fact: str
    existing_fact: str
    reason: str
    severity: str = "review"  # review, conflict, override


@dataclass
class PipelineContext:
    """
    Accumulates state as a document passes through the pipeline.
    Each stage reads from and writes to this object.
    """
    # Input
    job_id: str = ""
    file_path: str = ""
    filename: str = ""
    content_type: str = ""
    url: str = ""  # For URL-based learning

    # Stage 1: DocumentClassifier
    file_type: str = ""  # pdf, docx, xlsx, csv, txt, html, json, xml, image, email, url
    domain: str = "general"  # healthcare, finance, legal, technology, general
    sensitivity: str = "public"  # public, internal, phi, pii
    contains_phi: bool = False
    contains_pii: bool = False

    # Stage 2: ContentExtractor
    raw_text: str = ""
    tables: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    page_count: int = 0

    # Stage 3: EntityExtractor
    entities: List[ExtractedEntity] = field(default_factory=list)

    # Stage 4: KnowledgeIndexer
    indexed_chunks: int = 0
    chunk_ids: List[str] = field(default_factory=list)

    # Stage 5: FactExtractor
    extracted_facts: List[ExtractedFact] = field(default_factory=list)
    fact_ids: List[str] = field(default_factory=list)

    # Stage 6: ProfileUpdater
    preferences_updated: List[str] = field(default_factory=list)

    # Stage 7: SkillDetector
    detected_skills: List[str] = field(default_factory=list)
    detected_processes: List[str] = field(default_factory=list)

    # Stage 8: MemoryUpdater
    entity_ids: List[str] = field(default_factory=list)
    relation_ids: List[str] = field(default_factory=list)

    # Stage 9: ContradictionChecker
    contradictions: List[Contradiction] = field(default_factory=list)

    # Stage 10: NotificationBuilder
    notification: str = ""

    # Internal tracking
    stages_completed: List[str] = field(default_factory=list)
    stages_failed: Dict[str, str] = field(default_factory=dict)
    started_at: str = ""
    completed_at: str = ""


@dataclass
class PipelineResult:
    """Result returned from a completed pipeline run."""
    job_id: str = ""
    status: str = "pending"  # pending, processing, completed, failed
    stages_completed: List[str] = field(default_factory=list)
    stages_failed: Dict[str, str] = field(default_factory=dict)
    notification: str = ""
    file_type: str = ""
    domain: str = ""
    sensitivity: str = ""
    entity_count: int = 0
    fact_count: int = 0
    chunk_count: int = 0
    contradiction_count: int = 0
    started_at: str = ""
    completed_at: str = ""

    @classmethod
    def from_context(cls, ctx: PipelineContext) -> "PipelineResult":
        return cls(
            job_id=ctx.job_id,
            status="completed" if not ctx.stages_failed else "partial",
            stages_completed=ctx.stages_completed,
            stages_failed=ctx.stages_failed,
            notification=ctx.notification,
            file_type=ctx.file_type,
            domain=ctx.domain,
            sensitivity=ctx.sensitivity,
            entity_count=len(ctx.entities),
            fact_count=len(ctx.extracted_facts),
            chunk_count=ctx.indexed_chunks,
            contradiction_count=len(ctx.contradictions),
            started_at=ctx.started_at,
            completed_at=ctx.completed_at,
        )