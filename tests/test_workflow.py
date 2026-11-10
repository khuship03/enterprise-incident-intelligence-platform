from __future__ import annotations

from fastapi.testclient import TestClient

from app.database import initialize_db
from app.main import app, process_incident


def test_complete_incident_workflow(monkeypatch, tmp_path):
    monkeypatch.setenv("INCIDENT_DB_PATH", str(tmp_path / "test_incidents.db"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    initialize_db()

    with TestClient(app) as client:
        response = client.post(
            "/incidents",
            json={
                "title": "Production checkout API requests timing out",
                "description": "Since the latest deployment, many users cannot complete checkout. API requests are timing out and error rates are elevated.",
                "service": "checkout-api",
                "source": "automated-test",
            },
        )
        assert response.status_code == 202
        created = response.json()
        assert created["id"].startswith("INC-")

        # The TestClient runs FastAPI background tasks before returning from the request.
        incident_response = client.get(f"/incidents/{created['id']}")
        assert incident_response.status_code == 200
        incident = incident_response.json()
        assert incident["status"] in {"triaged", "needs_review"}
        assert incident["summary"]
        assert incident["category"] in {
            "network", "database", "application", "authentication", "storage", "security", "hardware", "unknown"
        }
        assert incident["severity"] in {"P1", "P2", "P3", "P4"}
        assert incident["assigned_group"]
        assert incident["retrieved_runbooks"]

        if incident["status"] == "needs_review":
            review = client.post(
                f"/incidents/{created['id']}/review",
                json={"decision": "approve", "reviewed_by": "test-reviewer", "notes": "Reviewed test recommendation"},
            )
            assert review.status_code == 200
            assert review.json()["status"] == "triaged"

        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert metrics.json()["total_incidents"] == 1


def test_unknown_incident_returns_404(monkeypatch, tmp_path):
    monkeypatch.setenv("INCIDENT_DB_PATH", str(tmp_path / "test_incidents_404.db"))
    initialize_db()
    with TestClient(app) as client:
        response = client.get("/incidents/INC-DOESNOTEXIST")
        assert response.status_code == 404
