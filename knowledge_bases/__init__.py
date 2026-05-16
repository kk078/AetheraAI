"""
AetheraAI Knowledge Bases - Download and Index System

Provides downloaders, indexers, and updaters for healthcare, finance,
legal, and technology knowledge bases. Each downloader fetches public
data sources, parses them into structured JSON, and creates manifests
for tracking. The indexer chunks and embeds content into ChromaDB for
retrieval-augmented generation.
"""

__version__ = "1.0.0"

CATEGORIES = ["healthcare", "finance", "legal", "technology"]

import os
DATA_ROOT = os.environ.get("AETHERA_DATA_ROOT", "/data/knowledge")