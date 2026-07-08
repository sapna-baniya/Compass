"""
rag.py — Resource retrieval layer for Compass.
Uses TF-IDF (scikit-learn) instead of neural embeddings to stay within
free-tier hosting memory limits.
"""

import json
from pathlib import Path
from typing import List, Dict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_PATH = Path(__file__).parent / "data" / "resources.json"


class ResourceIndex:
    def __init__(self, data_path: Path = DATA_PATH):
        self.resources: List[Dict] = json.loads(data_path.read_text())
        self._build_index()

    def _doc_text(self, r: Dict) -> str:
        return (
            f"{r['name']}. Category: {r['category']}. "
            f"Needs served: {', '.join(r['need_type'])}. "
            f"{r['description']}"
        )

    def _build_index(self):
        texts = [self._doc_text(r) for r in self.resources]
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.doc_matrix = self.vectorizer.fit_transform(texts)

    def search(self, query: str, jurisdiction: str = None, top_k: int = 5) -> List[Dict]:
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.doc_matrix)[0]

        results = []
        for idx, score in enumerate(scores):
            r = dict(self.resources[idx])
            r["relevance_score"] = float(score)
            results.append(r)

        results.sort(key=lambda r: -r["relevance_score"])
        results = results[: top_k * 2]

        if jurisdiction:
            def jurisdiction_rank(r):
                if r["jurisdiction"] == jurisdiction:
                    return 0
                if r["jurisdiction"] in ("US-national",):
                    return 1
                return 2
            results.sort(key=lambda r: (jurisdiction_rank(r), -r["relevance_score"]))

        return results[:top_k]


_index_instance = None


def get_resource_index() -> ResourceIndex:
    global _index_instance
    if _index_instance is None:
        _index_instance = ResourceIndex()
    return _index_instance