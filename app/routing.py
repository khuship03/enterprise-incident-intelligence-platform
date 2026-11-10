from __future__ import annotations

from typing import Any

ROUTING_TABLE = {
    "network": "Network Operations",
    "database": "Database Operations",
    "application": "Application Support",
    "authentication": "Identity and Access Management",
    "storage": "Storage Operations",
    "security": "Security Operations",
    "hardware": "Infrastructure Support",
    "unknown": "Service Desk",
}


def recommend_route(analysis: dict[str, Any]) -> dict[str, Any]:
    category = analysis.get("category", "unknown")
    severity = analysis.get("severity", "P3")
    confidence = float(analysis.get("confidence", 0.0))
    # Routing is a recommendation only; a human reviews high-impact or uncertain cases.
    needs_review = severity == "P1" or category == "security" or confidence < 0.62 or category == "unknown"
    reasons = []
    if severity == "P1":
        reasons.append("P1 severity recommendation requires human confirmation.")
    if category == "security":
        reasons.append("Security incidents require review by the authorized response team.")
    if confidence < 0.62:
        reasons.append("Analysis confidence is below the review threshold.")
    if category == "unknown":
        reasons.append("No confident issue category was identified.")
    return {
        "assigned_group": ROUTING_TABLE.get(category, ROUTING_TABLE["unknown"]),
        "needs_human_review": needs_review,
        "triage_notes": " ".join(reasons) if reasons else "Routing suggested by category rules; validate against team ownership policies.",
    }
