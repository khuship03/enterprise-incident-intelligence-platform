# AI-Powered Enterprise Incident Intelligence & Workflow Automation Platform

A practical portfolio project demonstrating how a Python backend can accept IT incident tickets, retrieve relevant runbooks, analyze the incident with an optional LLM, suggest a resolver group, and send uncertain/high-impact cases for human review.

> This is an independent demo project. It is not represented as Dell Technologies' internal software or a production incident-management system. Use synthetic or sanitized incident data only.

## What it does

1. **Ingest:** `POST /incidents` validates an incoming ticket and saves it to SQLite.
2. **Retrieve:** a lightweight lexical retrieval baseline searches the local runbook library for troubleshooting context.
3. **Analyze:** when `OPENAI_API_KEY` is configured, an LLM produces structured incident analysis. Without a key, local rules keep the demo runnable.
4. **Route:** configurable rules suggest a resolver group based on category; the app does not dispatch work to an external ticketing system.
5. **Review:** P1, security, unknown-category, or low-confidence cases are flagged for a human to approve or reject.
6. **Observe:** endpoints expose incident history and simple metrics; automated tests cover the main workflow.

## Architecture

```text
Client / source system
        |
        v
FastAPI POST /incidents -----> SQLite incident record (received)
        |
        v
Background task
        |
        +----> Runbook retrieval (data/runbooks.json)
        |             |
        |             v
        +------> LLM analysis (optional) / local fallback
                      |
                      v
             Validate analysis output
                      |
                      v
           Routing and review policy
                 /           \
          triaged             needs_review
                                  |
                                  v
                      POST /incidents/{id}/review
```

## Run locally

Requires Python 3.11 or newer.

### 1. Create a virtual environment

**macOS/Linux**

```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows PowerShell**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the API

From the project root:

```bash
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/docs> for the interactive API explorer. SQLite is initialized automatically at `data/incidents.db`.

The app works without an LLM API key. For live LLM analysis, set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in your shell before starting the service. Never commit a real API key to source control.

**Windows PowerShell:**

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_MODEL = "gpt-4o-mini"
uvicorn app.main:app --reload
```

**macOS/Linux:**

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_MODEL="gpt-4o-mini"
uvicorn app.main:app --reload
```

## Try the workflow

### Submit a sample incident

```bash
curl -X POST "http://127.0.0.1:8000/incidents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Production checkout API requests timing out",
    "description": "Since the latest deployment, many users cannot complete checkout. API requests are timing out and error rates are elevated.",
    "service": "checkout-api",
    "source": "manual-demo"
  }'
```

The response includes an incident ID such as `INC-1A2B3C4D`. Copy it for the next request.

### Check processing output

```bash
curl "http://127.0.0.1:8000/incidents/INC-1A2B3C4D"
```

Inspect `summary`, `category`, `severity`, `confidence`, `retrieved_runbooks`, `assigned_group`, `analysis_provider`, and `status`.

### Approve a flagged recommendation

If the record is in `needs_review`, approve it after examining the analysis. Replace the ID with your actual incident ID.

```bash
curl -X POST "http://127.0.0.1:8000/incidents/INC-1A2B3C4D/review" \
  -H "Content-Type: application/json" \
  -d '{"decision":"approve","reviewed_by":"demo-reviewer","notes":"Reviewed suggested category and resolver group."}'
```

### List incidents and inspect metrics

```bash
curl "http://127.0.0.1:8000/incidents?limit=20"
curl "http://127.0.0.1:8000/metrics"
curl "http://127.0.0.1:8000/health"
```

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Check API and database connectivity |
| `POST` | `/incidents` | Create an incident and queue triage |
| `GET` | `/incidents` | List recent incidents; optional `limit` and `status` filters |
| `GET` | `/incidents/{id}` | Get analysis, route recommendation, and review state |
| `POST` | `/incidents/{id}/review` | Approve or reject a reviewable recommendation |
| `GET` | `/runbooks` | View retrieved runbook entries |
| `GET` | `/metrics` | Basic counts by status, category, and severity |

## Test

```bash
pytest -q
```

The tests use a temporary SQLite database and do not require an external LLM API key.

## What to explain in an interview

- **Why FastAPI:** typed request validation and automatically generated OpenAPI documentation.
- **Why background tasks:** the create endpoint can acknowledge receipt before processing finishes. This demo uses FastAPI's in-process background task mechanism; for durable production jobs, use a queue such as Celery/RQ with Redis or a managed queue.
- **Why retrieval before an LLM:** retrieved runbooks provide relevant operational context rather than asking the model to answer from general knowledge alone. The current retrieval implementation is a transparent lexical baseline, not a vector database.
- **Why structured output validation:** model responses are untrusted input; category, severity, confidence, and arrays are normalized before downstream logic uses them.
- **Why human review:** incident severity and resolver assignment can have operational consequences, so the application recommends a route rather than automatically changing a production system.
- **Why a local fallback:** developers can run and test the workflow without a paid API key; report the provider used so demo results are not confused with LLM results.

## Honest limitations and next improvements

This is a runnable prototype, not a production service-management product. Before production use, add authentication/authorization, secrets management, PII redaction, rate limits, durable background workers, audit retention policies, migrations, a proper vector search index, monitoring, and integration tests against the chosen model provider. Evaluate classification and routing against a labeled dataset; do not claim accuracy or time savings until measured.
