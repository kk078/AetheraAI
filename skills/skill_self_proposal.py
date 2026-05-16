"""
Aethera AI - Skill Self-Proposal Engine

Automatically proposes new skills when knowledge gaps suggest a skill
could fill the gap. Scans KnowledgeGapStore for high-priority gaps,
clusters related gaps, and generates a skill proposal.

Proposal lifecycle:
  proposed -> approved (user accepts) -> generating -> active
            -> rejected (user declines)
            -> failed (generation error)
"""

import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("aethera.skills.proposal")

# Minimum gap priority to trigger proposal
DEFAULT_PRIORITY_THRESHOLD = 7

# Minimum number of related queries before proposing a skill
DEFAULT_MIN_QUERIES = 3

# Maximum auto-proposals per 24-hour window
MAX_PROPOSALS_PER_DAY = 1


class SkillSelfProposalEngine:
    """
    Gap-driven skill auto-creation engine.

    Scans KnowledgeGapStore for high-priority gaps that could be addressed
    by creating a new skill, generates a proposal, and manages the lifecycle
    from proposal through activation.
    """

    def __init__(
        self,
        db_path: str = "/data/aethera.db",
        litellm_url: Optional[str] = None,
        litellm_key: Optional[str] = None,
    ):
        self.db_path = db_path
        self.litellm_url = litellm_url or os.environ.get("LITELLM_URL", "http://litellm:4000")
        self.litellm_key = litellm_key or os.environ.get("LITELLM_MASTER_KEY", "")
        self._conn = None

    def initialize(self):
        """Initialize proposal database schema."""
        import sqlite3
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")

        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS skill_proposals (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT,
                description TEXT,
                category TEXT DEFAULT 'general',
                status TEXT DEFAULT 'proposed',
                gap_ids JSON,
                priority REAL DEFAULT 5.0,
                workflow_spec JSON,
                generated_code TEXT,
                skill_file_path TEXT,
                proposed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                generated_at TIMESTAMP,
                activated_at TIMESTAMP,
                failed_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_proposals_status
                ON skill_proposals(status);

            CREATE INDEX IF NOT EXISTS idx_proposals_category
                ON skill_proposals(category);
        """)
        self._conn.commit()
        logger.info("Skill proposal engine initialized")

    def _get_conn(self):
        if self._conn is None:
            self.initialize()
        return self._conn

    def scan_and_propose(
        self,
        gap_store=None,
        skill_registry=None,
        priority_threshold: int = DEFAULT_PRIORITY_THRESHOLD,
        min_queries: int = DEFAULT_MIN_QUERIES,
    ) -> Optional[Dict]:
        """
        Scan knowledge gaps and propose a new skill if warranted.

        Args:
            gap_store: KnowledgeGapStore instance
            skill_registry: SkillRegistry instance (to check for duplicates)
            priority_threshold: Minimum gap priority to consider
            min_queries: Minimum related queries before proposing

        Returns:
            Proposal dict if created, None otherwise
        """
        # Check daily proposal limit
        if self._proposal_count_today() >= MAX_PROPOSALS_PER_DAY:
            logger.info("Daily proposal limit reached, skipping")
            return None

        if gap_store is None:
            from memory.knowledge_gaps import get_knowledge_gap_store
            gap_store = get_knowledge_gap_store(self.db_path.replace("/aethera.db", "") + "/aethera.db")
            # Fallback: try default path
            try:
                gap_store.initialize()
            except Exception:
                pass

        # Get high-priority gaps
        gaps = gap_store.list_gaps(
            status="detected",
            min_priority=priority_threshold,
        )

        if not gaps:
            gaps = gap_store.list_gaps(
                status="researching",
                min_priority=priority_threshold,
            )

        if not gaps:
            logger.debug("No high-priority gaps found")
            return None

        # Cluster gaps by category
        clusters = self._cluster_gaps(gaps)

        # Check if existing skills already cover these gaps
        if skill_registry is None:
            try:
                from skills.skill_registry import get_registry
                skill_registry = get_registry()
            except Exception:
                pass

        for category, gap_list in clusters.items():
            if len(gap_list) < min_queries:
                continue

            # Check for existing skill coverage
            if skill_registry and self._is_covered_by_existing(gap_list, skill_registry):
                logger.info(f"Gap cluster in '{category}' already covered by existing skills")
                continue

            # Generate proposal
            proposal = self._create_proposal(gap_list, category)
            if proposal:
                return proposal

        return None

    def _cluster_gaps(self, gaps: List[Dict]) -> Dict[str, List[Dict]]:
        """Group gaps by category."""
        clusters: Dict[str, List[Dict]] = {}
        for gap in gaps:
            cat = gap.get("category", "general")
            if cat not in clusters:
                clusters[cat] = []
            clusters[cat].append(gap)
        return clusters

    def _is_covered_by_existing(self, gaps: List[Dict], registry) -> bool:
        """Check if existing skills already cover these gaps."""
        all_skills = registry.list()
        skill_descriptions = " ".join(
            s.get("description", "").lower() for s in all_skills
        )

        for gap in gaps:
            topic = gap.get("topic", "").lower()
            # Simple keyword overlap check
            topic_words = set(topic.split())
            overlap = sum(1 for w in topic_words if w in skill_descriptions)
            if overlap >= len(topic_words) * 0.5:
                return True
        return False

    def _create_proposal(self, gaps: List[Dict], category: str) -> Optional[Dict]:
        """Create a skill proposal from a cluster of gaps."""
        proposal_id = str(uuid.uuid4())

        # Build proposal from gap info
        primary_gap = max(gaps, key=lambda g: g.get("priority", 0))
        topics = [g.get("topic", "") for g in gaps]
        descriptions = [g.get("description", "") for g in gaps if g.get("description")]

        # Generate a skill name from the primary topic
        name = self._generate_name(primary_gap.get("topic", "custom_skill"))
        display_name = name.replace("_", " ").title()
        description = f"Automated processing for: {', '.join(topics[:3])}"
        avg_priority = sum(g.get("priority", 5) for g in gaps) / len(gaps)

        gap_ids = json.dumps([g.get("id", "") for g in gaps])

        conn = self._get_conn()
        conn.execute(
            """INSERT INTO skill_proposals
               (id, name, display_name, description, category, status,
                gap_ids, priority, proposed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (proposal_id, name, display_name, description, category,
             "proposed", gap_ids, avg_priority, datetime.now().isoformat()),
        )
        conn.commit()

        logger.info(f"Created skill proposal: {name} (priority={avg_priority:.1f})")

        return {
            "id": proposal_id,
            "name": name,
            "display_name": display_name,
            "description": description,
            "category": category,
            "status": "proposed",
            "gap_ids": [g.get("id", "") for g in gaps],
            "priority": avg_priority,
            "proposed_at": datetime.now().isoformat(),
        }

    def _generate_name(self, topic: str) -> str:
        """Generate a snake_case skill name from a topic."""
        # Remove common filler words
        fillers = {"the", "a", "an", "how", "to", "for", "of", "in", "on", "with", "and", "or"}
        words = [w.lower() for w in re.findall(r"\w+", topic) if w.lower() not in fillers]
        name = "_".join(words[:4]) if words else "custom_skill"
        return name

    def approve_proposal(self, proposal_id: str) -> Optional[Dict]:
        """Approve a proposal for skill generation."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM skill_proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()

        if not row:
            logger.warning(f"Proposal {proposal_id} not found")
            return None

        if row["status"] != "proposed":
            logger.warning(f"Proposal {proposal_id} is not in 'proposed' state (current: {row['status']})")
            return None

        conn.execute(
            """UPDATE skill_proposals
               SET status = 'approved', approved_at = ?, updated_at = ?
               WHERE id = ?""",
            (datetime.now().isoformat(), datetime.now().isoformat(), proposal_id),
        )
        conn.commit()

        return dict(conn.execute(
            "SELECT * FROM skill_proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone())

    def reject_proposal(self, proposal_id: str, reason: str = "") -> bool:
        """Reject and close a proposal."""
        conn = self._get_conn()
        conn.execute(
            """UPDATE skill_proposals
               SET status = 'rejected', failed_reason = ?, updated_at = ?
               WHERE id = ?""",
            (reason or "User rejected", datetime.now().isoformat(), proposal_id),
        )
        conn.commit()
        return conn.total_changes > 0

    async def generate_skill(self, proposal_id: str) -> Optional[Dict]:
        """
        Generate skill code for an approved proposal.

        Returns the updated proposal with generated_code and skill_file_path.
        """
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM skill_proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()

        if not row or row["status"] != "approved":
            logger.warning(f"Proposal {proposal_id} not approved for generation")
            return None

        from skills.skill_creator import WorkflowSpec, SkillCodeGenerator, SkillValidator

        # Build workflow spec from proposal data
        spec_data = json.loads(row["workflow_spec"]) if row["workflow_spec"] else {}
        spec = WorkflowSpec(
            name=row["name"],
            display_name=row["display_name"],
            description=row["description"],
            category=row["category"],
            inputs=spec_data.get("inputs", [
                {"name": "input", "type": "string", "description": "Input data", "required": True}
            ]),
            outputs=spec_data.get("outputs", [
                {"name": "result", "type": "string", "description": "Processing result"}
            ]),
            steps=spec_data.get("steps", []),
            rules=spec_data.get("rules", []),
            examples=spec_data.get("examples", []),
        )

        # Generate code
        generator = SkillCodeGenerator(litellm_url=self.litellm_url, litellm_key=self.litellm_key)
        generated = await generator.generate(spec)

        # Validate
        validator = SkillValidator()
        validation = validator.validate(generated.code) if generated.code else None

        if not generated.code or (validation and not validation.is_safe):
            # Mark as failed
            errors = generated.validation_errors or (validation.errors if validation else [])
            conn.execute(
                """UPDATE skill_proposals
                   SET status = 'failed', failed_reason = ?,
                       updated_at = ?
                   WHERE id = ?""",
                (f"Code generation/validation failed: {'; '.join(errors)}",
                 datetime.now().isoformat(), proposal_id),
            )
            conn.commit()
            return dict(conn.execute(
                "SELECT * FROM skill_proposals WHERE id = ?", (proposal_id,),
            ).fetchone())

        # Mark as generating -> active
        file_path = str(generated.file_path)
        conn.execute(
            """UPDATE skill_proposals
               SET status = 'active', generated_code = ?,
                   skill_file_path = ?, generated_at = ?,
                   updated_at = ?
               WHERE id = ?""",
            (generated.code, file_path, datetime.now().isoformat(),
             datetime.now().isoformat(), proposal_id),
        )
        conn.commit()

        return {
            "id": proposal_id,
            "name": row["name"],
            "status": "active",
            "generated_code": generated.code,
            "skill_file_path": file_path,
        }

    def write_skill_file(self, proposal_id: str, skills_dir: Optional[str] = None) -> Optional[str]:
        """
        Write the generated skill code to disk and trigger hot-reload.

        Returns the file path where the skill was written.
        """
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM skill_proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()

        if not row or row["status"] != "active":
            return None

        if not row["generated_code"]:
            return None

        # Determine output directory
        if skills_dir is None:
            skills_dir = str(Path(__file__).parent / "user")

        os.makedirs(skills_dir, exist_ok=True)

        file_path = os.path.join(skills_dir, f"{row['name']}.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(row["generated_code"])

        # Update the proposal with the actual file path
        conn.execute(
            "UPDATE skill_proposals SET skill_file_path = ?, updated_at = ? WHERE id = ?",
            (file_path, datetime.now().isoformat(), proposal_id),
        )
        conn.commit()

        logger.info(f"Written skill file: {file_path}")

        # Trigger hot-reload
        try:
            from skills.skill_registry import get_registry
            registry = get_registry()
            registry.hot_reload()
        except Exception as e:
            logger.warning(f"Hot-reload failed after writing skill file: {e}")

        return file_path

    def list_proposals(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """List proposals with optional filtering."""
        conn = self._get_conn()
        query = "SELECT * FROM skill_proposals WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY proposed_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_proposal(self, proposal_id: str) -> Optional[Dict]:
        """Get a single proposal by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM skill_proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()
        return dict(row) if row else None

    def _proposal_count_today(self) -> int:
        """Count proposals created today."""
        conn = self._get_conn()
        today = datetime.now().strftime("%Y-%m-%d")
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM skill_proposals WHERE proposed_at LIKE ?",
            (f"{today}%",),
        ).fetchone()
        return row["cnt"] if row else 0


# Singleton
_proposal_engine: Optional[SkillSelfProposalEngine] = None


def get_proposal_engine(db_path: str = "/data/aethera.db") -> SkillSelfProposalEngine:
    """Get the global proposal engine instance."""
    global _proposal_engine
    if _proposal_engine is None:
        _proposal_engine = SkillSelfProposalEngine(db_path)
        _proposal_engine.initialize()
    return _proposal_engine