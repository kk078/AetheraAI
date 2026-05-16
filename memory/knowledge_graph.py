"""
Aethera AI - Knowledge Graph Module

Entity-relationship knowledge graph using SQLite for persistence.
Models healthcare domain entities (people, organizations, conditions, drugs,
procedures, payers, regulations) and their relationships (treats, billed_by,
covered_by, regulated_by, interacts_with, etc.).
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import deque


# Valid entity types
ENTITY_TYPES = {
    "person", "organization", "condition", "drug", "procedure",
    "payer", "regulation", "facility", "device", "test"
}

# Valid relation types
RELATION_TYPES = {
    "treats", "treated_by", "billed_by", "bills",
    "covered_by", "covers", "regulated_by", "regulates",
    "interacts_with", "contraindicated_with",
    "performs", "performed_by",
    "employs", "employed_by",
    "prescribes", "prescribed_by",
    "diagnoses", "diagnosed_by",
    "refers_to", "referred_by",
    "belongs_to", "has_member",
    "located_at", "contains",
    "reimburses", "reimbursed_by",
    "supersedes", "superseded_by",
    "related_to", "part_of", "has_part",
}


class KnowledgeGraph:
    """
    SQLite-backed entity-relationship knowledge graph.

    Schema:
    - nodes: id, type, name, attributes (JSON), created_at, updated_at
    - edges: id, source_id, relation, target_id, attributes (JSON), weight, created_at
    """

    def __init__(self, db_path: str = "/data/aethera.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def initialize(self):
        """Initialize database schema."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS kg_nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                attributes JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS kg_edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                target_id TEXT NOT NULL,
                attributes JSON,
                weight REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES kg_nodes(id),
                FOREIGN KEY (target_id) REFERENCES kg_nodes(id)
            );

            CREATE INDEX IF NOT EXISTS idx_kg_nodes_type
                ON kg_nodes(type);

            CREATE INDEX IF NOT EXISTS idx_kg_nodes_name
                ON kg_nodes(name);

            CREATE INDEX IF NOT EXISTS idx_kg_edges_source
                ON kg_edges(source_id);

            CREATE INDEX IF NOT EXISTS idx_kg_edges_target
                ON kg_edges(target_id);

            CREATE INDEX IF NOT EXISTS idx_kg_edges_relation
                ON kg_edges(relation);
        """)
        self._conn.commit()

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()

    # ---- Entity (Node) Operations ----

    def add_entity(
        self,
        entity_type: str,
        name: str,
        entity_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add an entity node to the knowledge graph.

        Args:
            entity_type: One of the valid ENTITY_TYPES
            name: Human-readable entity name
            entity_id: Optional explicit ID; auto-generated if omitted
            attributes: Arbitrary key-value attributes stored as JSON

        Returns:
            Entity ID
        """
        if entity_type not in ENTITY_TYPES:
            raise ValueError(
                f"Invalid entity type '{entity_type}'. "
                f"Valid types: {sorted(ENTITY_TYPES)}"
            )

        if not entity_id:
            entity_id = f"entity_{uuid.uuid4().hex[:12]}"

        now = datetime.now().isoformat()
        self._conn.execute(
            """INSERT INTO kg_nodes (id, type, name, attributes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   name=excluded.name,
                   type=excluded.type,
                   attributes=excluded.attributes,
                   updated_at=excluded.updated_at""",
            (entity_id, entity_type, name, json.dumps(attributes or {}), now, now)
        )
        self._conn.commit()
        return entity_id

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single entity by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM kg_nodes WHERE id = ?", (entity_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        entity = dict(row)
        entity["attributes"] = json.loads(entity["attributes"]) if entity["attributes"] else {}
        return entity

    def search_entities(
        self,
        entity_type: Optional[str] = None,
        name_query: Optional[str] = None,
        attribute_filter: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search entities by type, name pattern, or attribute values.

        Args:
            entity_type: Filter by entity type
            name_query: Substring match on entity name
            attribute_filter: Key-value pairs that must exist in attributes JSON
            limit: Maximum results

        Returns:
            List of matching entities
        """
        conditions = []
        params: List[Any] = []

        if entity_type:
            conditions.append("type = ?")
            params.append(entity_type)

        if name_query:
            conditions.append("name LIKE ?")
            params.append(f"%{name_query}%")

        # Attribute filtering is done via JSON blob scanning in Python
        # for flexibility across SQLite versions
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        cursor = self._conn.execute(
            f"SELECT * FROM kg_nodes WHERE {where_clause} LIMIT ?",
            params + [limit]
        )

        results = []
        for row in cursor.fetchall():
            entity = dict(row)
            entity["attributes"] = json.loads(entity["attributes"]) if entity["attributes"] else {}

            if attribute_filter:
                attrs = entity["attributes"]
                if not all(attrs.get(k) == v for k, v in attribute_filter.items()):
                    continue

            results.append(entity)

        return results

    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity and all its edges."""
        try:
            self._conn.execute("DELETE FROM kg_edges WHERE source_id = ? OR target_id = ?",
                               (entity_id, entity_id))
            self._conn.execute("DELETE FROM kg_nodes WHERE id = ?", (entity_id,))
            self._conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting entity: {e}")
            return False

    # ---- Relationship (Edge) Operations ----

    def add_relation(
        self,
        source_id: str,
        relation: str,
        target_id: str,
        attributes: Optional[Dict[str, Any]] = None,
        weight: float = 1.0,
        edge_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Add a relationship edge between two entities.

        Args:
            source_id: Source entity ID
            relation: One of the valid RELATION_TYPES
            target_id: Target entity ID
            attributes: Arbitrary key-value edge attributes
            weight: Edge weight / confidence (0.0 to 1.0+)
            edge_id: Optional explicit edge ID

        Returns:
            Edge ID, or None if source/target do not exist
        """
        if relation not in RELATION_TYPES:
            raise ValueError(
                f"Invalid relation type '{relation}'. "
                f"Valid relations: {sorted(RELATION_TYPES)}"
            )

        # Verify both entities exist
        src = self.get_entity(source_id)
        tgt = self.get_entity(target_id)
        if not src or not tgt:
            return None

        if not edge_id:
            edge_id = f"edge_{uuid.uuid4().hex[:12]}"

        self._conn.execute(
            """INSERT INTO kg_edges (id, source_id, relation, target_id, attributes, weight, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (edge_id, source_id, relation, target_id,
             json.dumps(attributes or {}), weight, datetime.now().isoformat())
        )
        self._conn.commit()
        return edge_id

    def get_relation(self, edge_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single edge by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM kg_edges WHERE id = ?", (edge_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        edge = dict(row)
        edge["attributes"] = json.loads(edge["attributes"]) if edge["attributes"] else {}
        return edge

    def delete_relation(self, edge_id: str) -> bool:
        """Delete a single relationship edge."""
        try:
            self._conn.execute("DELETE FROM kg_edges WHERE id = ?", (edge_id,))
            self._conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting relation: {e}")
            return False

    def add_entities_and_relations_batch(
        self,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Add multiple entities and relations in a single transaction.

        Args:
            entities: List of dicts with keys: entity_type, name, entity_id (optional), attributes (optional)
            relations: List of dicts with keys: source_id, relation, target_id, attributes (optional), weight (optional)

        Returns:
            Dict mapping temporary IDs to real IDs for entities
        """
        id_map = {}
        now = datetime.now().isoformat()
        try:
            for ent in entities:
                entity_type = ent.get("entity_type", "organization")
                if entity_type not in ENTITY_TYPES:
                    entity_type = "organization"
                name = ent.get("name", "Unknown")
                eid = ent.get("entity_id") or f"entity_{uuid.uuid4().hex[:12]}"
                attrs = json.dumps(ent.get("attributes") or {})
                self._conn.execute(
                    """INSERT INTO kg_nodes (id, type, name, attributes, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                           name=excluded.name, type=excluded.type,
                           attributes=excluded.attributes, updated_at=excluded.updated_at""",
                    (eid, entity_type, name, attrs, now, now)
                )
                if ent.get("entity_id"):
                    id_map[ent["entity_id"]] = eid

            for rel in relations:
                source_id = rel.get("source_id", "")
                target_id = rel.get("target_id", "")
                relation = rel.get("relation", "related_to")
                if relation not in RELATION_TYPES:
                    relation = "related_to"
                weight = rel.get("weight", 1.0)
                attrs = json.dumps(rel.get("attributes") or {})
                edge_id = f"edge_{uuid.uuid4().hex[:12]}"
                self._conn.execute(
                    """INSERT INTO kg_edges (id, source_id, relation, target_id, attributes, weight, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (edge_id, source_id, relation, target_id, attrs, weight, now)
                )

            self._conn.commit()
        except Exception:
            self._conn.rollback()
        return id_map

    # ---- Graph Traversal Operations ----

    def query_neighbors(
        self,
        entity_id: str,
        relation: Optional[str] = None,
        direction: str = "both",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get neighboring entities connected by edges.

        Args:
            entity_id: Central entity ID
            relation: Filter by relation type
            direction: 'outgoing', 'incoming', or 'both'
            limit: Maximum results

        Returns:
            List of dicts with keys: entity, edge, direction
        """
        results: List[Dict[str, Any]] = []

        if direction in ("outgoing", "both"):
            sql = """SELECT e.*, n.name as target_name, n.type as target_type
                     FROM kg_edges e
                     JOIN kg_nodes n ON e.target_id = n.id
                     WHERE e.source_id = ?"""
            params: List[Any] = [entity_id]
            if relation:
                sql += " AND e.relation = ?"
                params.append(relation)
            sql += " ORDER BY e.weight DESC LIMIT ?"
            params.append(limit)

            cursor = self._conn.execute(sql, params)
            for row in cursor.fetchall():
                edge = dict(row)
                edge["attributes"] = json.loads(edge["attributes"]) if edge["attributes"] else {}
                results.append({
                    "entity": {"id": edge["target_id"], "name": edge["target_name"], "type": edge["target_type"]},
                    "edge": {k: edge[k] for k in ("id", "relation", "weight", "attributes") if k in edge},
                    "direction": "outgoing"
                })

        if direction in ("incoming", "both"):
            sql = """SELECT e.*, n.name as source_name, n.type as source_type
                     FROM kg_edges e
                     JOIN kg_nodes n ON e.source_id = n.id
                     WHERE e.target_id = ?"""
            params = [entity_id]
            if relation:
                sql += " AND e.relation = ?"
                params.append(relation)
            sql += " ORDER BY e.weight DESC LIMIT ?"
            params.append(limit)

            cursor = self._conn.execute(sql, params)
            for row in cursor.fetchall():
                edge = dict(row)
                edge["attributes"] = json.loads(edge["attributes"]) if edge["attributes"] else {}
                results.append({
                    "entity": {"id": edge["source_id"], "name": edge["source_name"], "type": edge["source_type"]},
                    "edge": {k: edge[k] for k in ("id", "relation", "weight", "attributes") if k in edge},
                    "direction": "incoming"
                })

        return results

    def find_paths(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 5,
        relation: Optional[str] = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Find paths between two entities using BFS.

        Args:
            start_id: Starting entity ID
            end_id: Target entity ID
            max_depth: Maximum path length
            relation: Optional relation type filter

        Returns:
            List of paths, where each path is a list of
            {node, edge} steps from start to end
        """
        if not self.get_entity(start_id) or not self.get_entity(end_id):
            return []

        paths: List[List[Dict[str, Any]]] = []
        # BFS queue entries: (current_node_id, path_so_far, visited_set)
        queue: deque[Tuple[str, List[Dict[str, Any]], Set[str]]] = deque()
        queue.append((start_id, [], {start_id}))

        while queue and len(paths) < 10:
            current_id, path, visited = queue.popleft()

            if len(path) >= max_depth * 2:  # each hop = node + edge entry
                continue

            # Get outgoing edges
            sql = "SELECT * FROM kg_edges WHERE source_id = ?"
            params: List[Any] = [current_id]
            if relation:
                sql += " AND relation = ?"
                params.append(relation)
            cursor = self._conn.execute(sql, params)

            for row in cursor.fetchall():
                edge = dict(row)
                edge["attributes"] = json.loads(edge["attributes"]) if edge["attributes"] else {}
                neighbor_id = edge["target_id"]

                if neighbor_id in visited:
                    continue

                neighbor = self.get_entity(neighbor_id)
                if not neighbor:
                    continue

                new_path = path + [
                    {"edge": {k: edge[k] for k in ("id", "relation", "weight") if k in edge}},
                    {"node": {"id": neighbor_id, "name": neighbor["name"], "type": neighbor["type"]}}
                ]

                if neighbor_id == end_id:
                    paths.append(new_path)
                else:
                    new_visited = visited | {neighbor_id}
                    queue.append((neighbor_id, new_path, new_visited))

        return paths

    def get_subgraph(
        self,
        entity_ids: List[str],
        max_depth: int = 1
    ) -> Dict[str, Any]:
        """
        Extract a subgraph around the given entity IDs.

        Args:
            entity_ids: Seed entity IDs
            max_depth: How many hops to expand

        Returns:
            Dict with 'nodes' and 'edges' lists
        """
        collected_nodes: Dict[str, Dict[str, Any]] = {}
        collected_edges: Dict[str, Dict[str, Any]] = {}

        current_ids = set(entity_ids)

        for _ in range(max_depth + 1):
            next_ids: Set[str] = set()

            for eid in current_ids:
                if eid in collected_nodes:
                    continue
                entity = self.get_entity(eid)
                if entity:
                    collected_nodes[eid] = entity

                # Outgoing edges
                cursor = self._conn.execute(
                    "SELECT * FROM kg_edges WHERE source_id = ?", (eid,)
                )
                for row in cursor.fetchall():
                    edge = dict(row)
                    edge["attributes"] = json.loads(edge["attributes"]) if edge["attributes"] else {}
                    collected_edges[edge["id"]] = edge
                    next_ids.add(edge["target_id"])

                # Incoming edges
                cursor = self._conn.execute(
                    "SELECT * FROM kg_edges WHERE target_id = ?", (eid,)
                )
                for row in cursor.fetchall():
                    edge = dict(row)
                    edge["attributes"] = json.loads(edge["attributes"]) if edge["attributes"] else {}
                    collected_edges[edge["id"]] = edge
                    next_ids.add(edge["source_id"])

            current_ids = next_ids - set(collected_nodes.keys())

        return {
            "nodes": list(collected_nodes.values()),
            "edges": list(collected_edges.values())
        }

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        node_cursor = self._conn.execute("SELECT COUNT(*) as count FROM kg_nodes")
        node_count = node_cursor.fetchone()["count"] if node_cursor.fetchone() else 0

        edge_cursor = self._conn.execute("SELECT COUNT(*) as count FROM kg_edges")
        edge_count = edge_cursor.fetchone()["count"] if edge_cursor.fetchone() else 0

        type_cursor = self._conn.execute(
            "SELECT type, COUNT(*) as count FROM kg_nodes GROUP BY type"
        )
        type_counts = {row["type"]: row["count"] for row in type_cursor.fetchall()}

        relation_cursor = self._conn.execute(
            "SELECT relation, COUNT(*) as count FROM kg_edges GROUP BY relation"
        )
        relation_counts = {row["relation"]: row["count"] for row in relation_cursor.fetchall()}

        # Recount after consumption
        node_count = sum(type_counts.values())
        edge_count = sum(relation_counts.values())

        return {
            "total_nodes": node_count,
            "total_edges": edge_count,
            "nodes_by_type": type_counts,
            "edges_by_relation": relation_counts
        }


# Singleton instance
_knowledge_graph: Optional[KnowledgeGraph] = None


def get_knowledge_graph(db_path: str = "/data/aethera.db") -> KnowledgeGraph:
    """Get or create the knowledge graph instance."""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph(db_path)
    return _knowledge_graph