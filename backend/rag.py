"""
rag.py — Resource retrieval layer for Compass.

Loads the curated, public resource knowledge base (data/resources.json)
into a FAISS vector index so the Retrieval Agent can pull relevant
resources for a survivor's described situation.

No survivor data is ever written into this index — it is read-only
reference data seeded from public sources (hotlines, legal aid
directories, federal program pages). See data/resources.json for
sourcing notes.
"""

import json
import os
from pathlib import Path
from typing import List, Dict

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

DATA_PATH = Path(__file__).parent / "data" / "resources.json"
_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"


class ResourceIndex:
    """A lightweight FAISS wrapper over the static resource knowledge base."""

    def __init__(self, data_path: Path = DATA_PATH):
        self.resources: List[Dict] = json.loads(data_path.read_text())
        self.model = SentenceTransformer(_EMBED_MODEL_NAME)
        self._build_index()

    def _doc_text(self, r: Dict) -> str:
        return (
            f"{r['name']}. Category: {r['category']}. "
            f"Needs served: {', '.join(r['need_type'])}. "
            f"{r['description']}"
        )

    def _build_index(self):
        texts = [self._doc_text(r) for r in self.resources]
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings.astype(np.float32))

    def search(self, query: str, jurisdiction: str = None, top_k: int = 5) -> List[Dict]:
        """Return the top_k most relevant resources for a free-text query,
        optionally filtered/boosted by jurisdiction."""
        query_vec = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        scores, idxs = self.index.search(query_vec.astype(np.float32), min(top_k * 2, len(self.resources)))

        results = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx == -1:
                continue
            r = dict(self.resources[idx])
            r["relevance_score"] = float(score)
            results.append(r)

        if jurisdiction:
            # Boost exact jurisdiction matches and national resources to the top
            def jurisdiction_rank(r):
                if r["jurisdiction"] == jurisdiction:
                    return 0
                if r["jurisdiction"] in ("US-national",):
                    return 1
                return 2
            results.sort(key=lambda r: (jurisdiction_rank(r), -r["relevance_score"]))
        else:
            results.sort(key=lambda r: -r["relevance_score"])

        return results[:top_k]


# Singleton instance, built once at import time
_index_instance = None


def get_resource_index() -> ResourceIndex:
    global _index_instance
    if _index_instance is None:
        _index_instance = ResourceIndex()
    return _index_instance
