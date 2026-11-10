from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import get_runbooks_path

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "for", "from", "has", "have",
    "i", "in", "into", "is", "it", "of", "on", "or", "our", "the", "this", "to", "was",
    "were", "with", "we", "after", "since", "there", "they", "can", "cannot", "not", "but",
}


def tokenize(text: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", text.lower()) if len(term) > 2 and term not in STOP_WORDS}


def load_runbooks(path: Path | None = None) -> list[dict[str, Any]]:
    source = path or get_runbooks_path()
    with source.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("Runbook file must contain a JSON array.")
    return data


def retrieve_runbooks(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Simple lexical retrieval baseline, suitable for a local demo without vector infrastructure."""
    query_terms = tokenize(query)
    scored: list[tuple[float, dict[str, Any]]] = []

    for runbook in load_runbooks():
        title_terms = tokenize(str(runbook.get("title", "")))
        tag_terms = tokenize(" ".join(runbook.get("tags", [])))
        symptom_terms = tokenize(" ".join(runbook.get("symptoms", [])))
        step_terms = tokenize(" ".join(runbook.get("steps", [])))
        score = (
            3.0 * len(query_terms & title_terms)
            + 2.0 * len(query_terms & tag_terms)
            + 1.5 * len(query_terms & symptom_terms)
            + 0.5 * len(query_terms & step_terms)
        )
        if score > 0:
            result = {
                "id": runbook["id"],
                "title": runbook["title"],
                "category": runbook.get("category", "unknown"),
                "score": round(score / max(len(query_terms), 1), 3),
                "steps": runbook.get("steps", []),
                "symptoms": runbook.get("symptoms", []),
            }
            scored.append((score, result))

    scored.sort(key=lambda item: item[0], reverse=True)
    if scored:
        return [item[1] for item in scored[: max(1, min(top_k, 5))]]

    # Safe generic fallback keeps the analysis workflow useful for unfamiliar issue wording.
    generic = next((item for item in load_runbooks() if item.get("id") == "RB-GEN-001"), None)
    if generic:
        return [{
            "id": generic["id"], "title": generic["title"], "category": "unknown", "score": 0.0,
            "steps": generic.get("steps", []), "symptoms": generic.get("symptoms", []),
        }]
    return []
