# Project walkthrough for a live demo or interview

## 60-second explanation

"I built an incident intelligence API in Python using FastAPI and SQLite. When an IT incident is submitted, the API validates and persists the ticket, then queues a background workflow. The workflow retrieves relevant runbook passages, analyzes the incident using an optional LLM provider or a local fallback, validates the result, and recommends a resolver group. High-severity, security-related, unknown, or low-confidence cases are flagged for human review. I added metrics endpoints and automated tests to check the end-to-end workflow. The routing is a recommendation only; this prototype does not change external production systems."

## Live demo sequence

1. Start the service with `uvicorn app.main:app --reload`.
2. Open `http://127.0.0.1:8000/docs`.
3. Run `POST /incidents` with this JSON:

   ```json
   {
     "title": "Production checkout API requests timing out",
     "description": "Since the latest deployment, many users cannot complete checkout. API requests are timing out and error rates are elevated.",
     "service": "checkout-api",
     "source": "live-demo"
   }
   ```

4. Copy the returned incident ID and call `GET /incidents/{incident_id}`. Explain the summary, category, severity, confidence, retrieved runbooks, suggested group, provider, and workflow status.
5. If the status is `needs_review`, call `POST /incidents/{incident_id}/review` with an approve decision and a reviewer name.
6. Call `GET /metrics` to show aggregate incident counts.
7. Run `python -m pytest -q` from the project root to show the end-to-end test.

## One incident's workflow

- **Input:** The caller sends a title, description, service name, and source.
- **Validation and persistence:** Pydantic validates input types/lengths. The API writes a `received` row in SQLite.
- **Background processing:** FastAPI's in-process `BackgroundTasks` starts analysis after the response. The status changes to `processing`.
- **Context retrieval:** `app/retrieval.py` scores runbooks using weighted lexical overlap across title, tags, symptoms, and steps.
- **AI analysis:** `app/analysis.py` optionally calls an OpenAI-compatible Chat Completions API with JSON output; without a key or on provider failure, local rules keep the demo running.
- **Output validation:** Categories, severity, confidence, summaries, and lists are normalized before being stored.
- **Routing decision:** `app/routing.py` maps category to a suggested resolver group. P1, security, unknown-category, and low-confidence incidents require review.
- **Human review and observability:** The review endpoint stores the decision, and metrics aggregate status/category/severity counts.

## Design trade-offs to discuss

- SQLite keeps local setup easy; PostgreSQL is a natural next step for concurrent multi-instance deployment.
- FastAPI background tasks are suitable for a prototype but are not a durable queue. Production should use Celery/RQ or a managed job queue with retries and dead-letter handling.
- The current retrieval is lexical, not embedding/vector search. A next version could use sentence embeddings and a vector index, then evaluate retrieval recall on curated incidents.
- A confidence value returned by an LLM is not a calibrated probability. It should be calibrated against labeled data before being used for important decisions.
- The app recommends a route but does not automatically make production changes. Human review is deliberate for high-impact cases.
- The fallback analysis is rule-based, not a trained ML model. Be clear about whether an interview demo used the configured LLM or local fallback.

## Good next improvements

1. Add authentication and role-based permissions to the review endpoint.
2. Add request IDs, audit event records, idempotency keys, and PII redaction.
3. Switch from SQLite to PostgreSQL and add schema migrations.
4. Add durable job workers, retry policy, and a dead-letter queue.
5. Replace lexical retrieval with embeddings/vector search; measure recall@k and answer groundedness.
6. Create a labeled evaluation set to measure category precision/recall, severity agreement, routing accuracy, API latency, and human override rate.
7. Add a dashboard and optional integration adapter for a ticketing system in a sandbox environment.
