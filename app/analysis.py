from __future__ import annotations

import json
import os
import re
from typing import Any

from app.config import get_openai_api_key, get_openai_model

ALLOWED_CATEGORIES = {"network", "database", "application", "authentication", "storage", "security", "hardware", "unknown"}
ALLOWED_SEVERITIES = {"P1", "P2", "P3", "P4"}
CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "network": {"network", "dns", "packet", "latency", "connectivity", "firewall", "timeout", "timeouts"},
    "database": {"database", "postgres", "postgresql", "mysql", "sql", "deadlock", "query", "queries", "connection pool"},
    "application": {"api", "application", "deployment", "deploy", "http", "endpoint", "crash", "exception", "500", "5xx", "checkout"},
    "authentication": {"login", "authentication", "authorization", "sso", "token", "permission", "identity", "credential"},
    "storage": {"storage", "disk", "filesystem", "volume", "capacity", "iops", "space"},
    "security": {"security", "breach", "malware", "suspicious", "unauthorized", "exfiltration", "ransomware"},
    "hardware": {"hardware", "server", "power", "fan", "memory fault", "drive failure"},
}


def _local_analysis(title: str, description: str, runbooks: list[dict[str, Any]]) -> dict[str, Any]:
    text = f"{title} {description}".lower()
    category_scores: list[tuple[int, str]] = []
    for category, phrases in CATEGORY_KEYWORDS.items():
        hits = sum(1 for phrase in phrases if phrase in text)
        category_scores.append((hits, category))
    best_score, category = max(category_scores, default=(0, "unknown"))
    if best_score == 0:
        category = "unknown"
        category_confidence = 0.42
    else:
        category_confidence = min(0.91, 0.58 + best_score * 0.09)

    p1_markers = ("production down", "all users", "complete outage", "data loss", "security breach", "critical outage", "service unavailable")
    p2_markers = ("degraded", "many users", "high latency", "timeouts", "time out", "5xx", "intermittent", "cannot complete")
    p4_markers = ("how do i", "feature request", "question about", "minor issue", "workaround available")
    if any(marker in text for marker in p1_markers):
        severity = "P1"
        severity_confidence = 0.78
    elif any(marker in text for marker in p2_markers):
        severity = "P2"
        severity_confidence = 0.72
    elif any(marker in text for marker in p4_markers):
        severity = "P4"
        severity_confidence = 0.7
    else:
        severity = "P3"
        severity_confidence = 0.60

    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", description.strip()) if part.strip()]
    symptom_candidates = [
        sentence[:240] for sentence in sentences
        if any(term in sentence.lower() for term in ("fail", "error", "slow", "timeout", "unavailable", "cannot", "unable", "latency", "crash", "denied", "down"))
    ]
    key_symptoms = (symptom_candidates or sentences or [description])[:3]

    recommendations: list[str] = []
    for runbook in runbooks[:2]:
        for step in runbook.get("steps", []):
            if step not in recommendations:
                recommendations.append(step)
            if len(recommendations) >= 4:
                break
        if len(recommendations) >= 4:
            break
    if not recommendations:
        recommendations = [
            "Confirm the incident impact and affected users.",
            "Review sanitized logs and recent changes before applying a fix.",
            "Escalate to the appropriate resolver group for production-impacting changes.",
        ]

    summary_body = re.sub(r"\s+", " ", description).strip()
    if len(summary_body) > 220:
        summary_body = summary_body[:217].rsplit(" ", 1)[0] + "..."
    return {
        "summary": f"{title.strip()}: {summary_body}",
        "category": category,
        "severity": severity,
        "confidence": round(min(category_confidence, severity_confidence), 2),
        "key_symptoms": key_symptoms,
        "recommendations": recommendations,
        "provider": "local_rules",
        "provider_note": "Local rules used; set OPENAI_API_KEY to enable LLM analysis.",
    }


def _openai_analysis(title: str, description: str, runbooks: list[dict[str, Any]]) -> dict[str, Any]:
    # Import only when configured, so the project works without an API key or SDK at demo time.
    from openai import OpenAI

    client = OpenAI(api_key=get_openai_api_key())
    context = "\n".join(
        f"{item.get('id')} — {item.get('title')}\nSymptoms: {'; '.join(item.get('symptoms', []))}\nSteps: {'; '.join(item.get('steps', []))}"
        for item in runbooks[:3]
    )
    system_prompt = """You are an IT incident triage assistant. Return one JSON object only with keys: summary (string), category (network|database|application|authentication|storage|security|hardware|unknown), severity (P1|P2|P3|P4), confidence (number 0..1), key_symptoms (array of strings), recommendations (array of strings). Use the supplied runbook context when relevant. Do not claim a root cause is confirmed unless the input proves it. Do not request credentials or recommend dangerous production changes. Severity is a recommendation, not a final operational decision."""
    user_prompt = f"Incident title: {title}\nIncident description: {description}\nRetrieved runbook context:\n{context}\n\nAnalyze this incident. Make the summary concise and recommendations actionable but safe."
    response = client.chat.completions.create(
        model=get_openai_model(),
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    return {**data, "provider": "openai", "provider_note": None}


def analyze_incident(title: str, description: str, runbooks: list[dict[str, Any]]) -> dict[str, Any]:
    """Use a configured LLM when possible; keep a deterministic local fallback for demos/tests."""
    if get_openai_api_key():
        try:
            return _validate_analysis(_openai_analysis(title, description, runbooks), title, description, runbooks)
        except Exception:
            # Keep the workflow available if the provider is temporarily unavailable or misconfigured.
            local = _local_analysis(title, description, runbooks)
            local["provider"] = "local_fallback"
            local["provider_note"] = "LLM request failed; local fallback was used. Check provider configuration and logs."
            return local
    return _validate_analysis(_local_analysis(title, description, runbooks), title, description, runbooks)


def _validate_analysis(data: dict[str, Any], title: str, description: str, runbooks: list[dict[str, Any]]) -> dict[str, Any]:
    category = str(data.get("category", "unknown")).lower()
    if category not in ALLOWED_CATEGORIES:
        category = "unknown"
    severity = str(data.get("severity", "P3")).upper()
    if severity not in ALLOWED_SEVERITIES:
        severity = "P3"
    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    def clean_list(value: Any, maximum: int = 5) -> list[str]:
        if not isinstance(value, list):
            return []
        cleaned = [re.sub(r"\s+", " ", str(item)).strip()[:500] for item in value]
        return [item for item in cleaned if item][:maximum]

    summary = re.sub(r"\s+", " ", str(data.get("summary", "")).strip())[:700]
    if not summary:
        return _local_analysis(title, description, runbooks)
    symptoms = clean_list(data.get("key_symptoms"), 5)
    recommendations = clean_list(data.get("recommendations"), 6)
    fallback = _local_analysis(title, description, runbooks)
    return {
        "summary": summary,
        "category": category,
        "severity": severity,
        "confidence": round(confidence, 2),
        "key_symptoms": symptoms or fallback["key_symptoms"],
        "recommendations": recommendations or fallback["recommendations"],
        "provider": str(data.get("provider", "unknown")),
        "provider_note": data.get("provider_note"),
    }
