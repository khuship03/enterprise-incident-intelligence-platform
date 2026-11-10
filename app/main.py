from __future__ import annotations

import uuid
from collections import Counter
from contextlib import asynccontextmanager
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, status

from app.analysis import analyze_incident
from app.database import (
    connect,
    create_incident_record,
    encode_json,
    get_incident,
    initialize_db,
    list_incidents,
    utc_now,
)
from app.retrieval import retrieve_runbooks
from app.routing import ROUTING_TABLE, recommend_route
from app.schemas import IncidentCreate, IncidentView, MetricsView, ReviewRequest

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_db()
    yield


app = FastAPI(
    title="Enterprise Incident Intelligence Platform",
    lifespan=lifespan,
    version="1.0.0",
    description=(
        "A portfolio-grade incident triage API demonstrating Python backend engineering, "
        "runbook retrieval, optional LLM analysis, workflow automation, and human review. "
        "All incident records in this demo are sample data unless you add your own."
    ),
)


def _id() -> str:
    return f"INC-{uuid.uuid4().hex[:8].upper()}"


def process_incident(incident_id: str) -> None:
    """Process a newly received incident; designed to run as a FastAPI background task."""
    incident = get_incident(incident_id)
    if incident is None:
        return

    with connect() as connection:
        connection.execute(
            "UPDATE incidents SET status='processing', updated_at=?, processing_attempts=processing_attempts+1, error_message=NULL WHERE id=?",
            (utc_now(), incident_id),
        )

    try:
        retrieval_query = f"{incident['title']}\n{incident['description']}\n{incident['service']}"
        runbooks = retrieve_runbooks(retrieval_query, top_k=3)
        analysis = analyze_incident(incident["title"], incident["description"], runbooks)
        route = recommend_route(analysis)
        status_value = "needs_review" if route["needs_human_review"] else "triaged"
        now = utc_now()

        with connect() as connection:
            connection.execute(
                """UPDATE incidents SET
                    status=?, updated_at=?, summary=?, category=?, severity=?, confidence=?,
                    key_symptoms=?, recommendations=?, retrieved_runbooks=?, assigned_group=?,
                    needs_human_review=?, analysis_provider=?, triage_notes=?, error_message=NULL
                   WHERE id=?""",
                (
                    status_value,
                    now,
                    analysis.get("summary"),
                    analysis.get("category", "unknown"),
                    analysis.get("severity", "P3"),
                    analysis.get("confidence", 0.0),
                    encode_json(analysis.get("key_symptoms", [])),
                    encode_json(analysis.get("recommendations", [])),
                    encode_json([
                        {key: item.get(key) for key in ("id", "title", "category", "score")}
                        for item in runbooks
                    ]),
                    route["assigned_group"],
                    int(route["needs_human_review"]),
                    analysis.get("provider", "unknown"),
                    " ".join(part for part in (route.get("triage_notes"), analysis.get("provider_note")) if part),
                    incident_id,
                ),
            )
    except Exception as exc:
        # Do not store stack traces or user payloads in the database response.
        with connect() as connection:
            connection.execute(
                "UPDATE incidents SET status='failed', updated_at=?, error_message=? WHERE id=?",
                (utc_now(), f"Processing failed: {type(exc).__name__}", incident_id),
            )


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "name": "Enterprise Incident Intelligence Platform",
        "status": "running",
        "docs": "/docs",
        "workflow": "ingest -> retrieve runbooks -> analyze -> recommend route -> human review when needed",
    }


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    try:
        initialize_db()
        with connect() as connection:
            connection.execute("SELECT 1").fetchone()
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Health check failed: {type(exc).__name__}") from exc


@app.post("/incidents", response_model=IncidentView, status_code=status.HTTP_202_ACCEPTED, tags=["incidents"])
def create_incident(payload: IncidentCreate, background_tasks: BackgroundTasks) -> dict[str, Any]:
    incident = create_incident_record(
        incident_id=_id(),
        title=payload.title,
        description=payload.description,
        service=payload.service,
        source=payload.source,
    )
    background_tasks.add_task(process_incident, incident["id"])
    return incident


@app.get("/incidents", response_model=list[IncidentView], tags=["incidents"])
def get_incidents(
    limit: int = Query(default=50, ge=1, le=200),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[dict[str, Any]]:
    return list_incidents(limit=limit, status=status_filter)


@app.get("/incidents/{incident_id}", response_model=IncidentView, tags=["incidents"])
def get_incident_by_id(incident_id: str) -> dict[str, Any]:
    incident = get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.post("/incidents/{incident_id}/review", response_model=IncidentView, tags=["human review"])
def review_incident(incident_id: str, payload: ReviewRequest) -> dict[str, Any]:
    incident = get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident["status"] not in {"needs_review", "triaged", "rejected"}:
        raise HTTPException(status_code=409, detail=f"Cannot review an incident in status '{incident['status']}'")

    status_value = "triaged" if payload.decision == "approve" else "rejected"
    note = payload.notes.strip() or f"Review decision: {payload.decision}"
    with connect() as connection:
        connection.execute(
            """UPDATE incidents SET status=?, needs_human_review=0, reviewed_by=?, review_notes=?, reviewed_at=?, updated_at=?
               WHERE id=?""",
            (status_value, payload.reviewed_by.strip(), note, utc_now(), utc_now(), incident_id),
        )
    updated = get_incident(incident_id)
    if updated is None:
        raise HTTPException(status_code=500, detail="Incident review was saved but the record could not be read")
    return updated


@app.get("/runbooks", tags=["knowledge base"])
def get_runbooks() -> list[dict[str, Any]]:
    # Do not expose file-system paths; return only the runbook knowledge used by the demo.
    return retrieve_runbooks("network database application authentication storage security", top_k=5)


@app.get("/metrics", response_model=MetricsView, tags=["reporting"])
def get_metrics() -> dict[str, Any]:
    incidents = list_incidents(limit=200)
    status_counts = Counter(item["status"] for item in incidents)
    category_counts = Counter((item.get("category") or "unclassified") for item in incidents)
    severity_counts = Counter((item.get("severity") or "unclassified") for item in incidents)
    return {
        "total_incidents": len(incidents),
        "status_counts": dict(status_counts),
        "category_counts": dict(category_counts),
        "severity_counts": dict(severity_counts),
        "incidents_requiring_review": sum(1 for item in incidents if item["needs_human_review"]),
    }
