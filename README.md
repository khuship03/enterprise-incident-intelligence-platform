# AI-Powered Enterprise Incident Intelligence & Workflow Automation Platform

An AI-powered IT incident management backend built with **Python, FastAPI, SQLite, and OpenAI integration**. The platform automates incident intake, analyzes incoming tickets, retrieves relevant troubleshooting runbooks, recommends resolver groups, and incorporates human review into incident triage workflows.

The system combines rule-based automation with optional LLM-powered analysis to demonstrate an end-to-end incident intelligence and workflow automation pipeline.

## Key Features

### 1. Automated Incident Intake
- Accepts IT incident tickets through REST APIs.
- Validates incoming incident details using Pydantic schemas.
- Stores incident records and processing statuses in SQLite.
- Initiates incident analysis using FastAPI background tasks.

### 2. AI-Powered Incident Analysis
- Integrates with OpenAI models for contextual incident analysis.
- Generates structured summaries, incident categories, severity classifications, and confidence scores.
- Validates and normalizes model-generated analysis before applying downstream decisions.
- Supports rule-based analysis when an API key is not configured.

### 3. Knowledge Base & Runbook Retrieval
- Maintains a local knowledge base of troubleshooting runbooks.
- Uses lexical retrieval to identify relevant operational documentation.
- Incorporates retrieved runbook context into incident analysis.
- Returns relevant runbook references alongside incident recommendations.

### 4. Intelligent Incident Routing
- Recommends resolver groups based on incident categories and routing policies.
- Applies configurable routing rules to incident analysis results.
- Tracks routing recommendations and incident processing states.

### 5. Human-in-the-Loop Review
- Identifies incidents requiring additional review based on severity, category, or confidence.
- Supports approval and rejection of routing recommendations through dedicated API endpoints.
- Records reviewer information, decisions, and review notes.

### 6. Incident Tracking & Reporting
- Provides APIs to retrieve incident histories and individual incident details.
- Tracks incident severity, category, status, and resolver recommendations.
- Exposes operational metrics for incident distribution and processing states.
- Includes automated workflow tests.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| API Validation | Pydantic |
| Database | SQLite |
| AI Integration | OpenAI API (optional) |
| Knowledge Retrieval | Lexical Runbook Search |
| Workflow Processing | FastAPI Background Tasks |
| API Documentation | Swagger UI / OpenAPI |
| Testing | Pytest |
| Containerization | Docker |

## System Architecture

```text
                Incident Source / Client
                          |
                          v
                FastAPI REST API
                  POST /incidents
                          |
                          v
                Incident Validation
                          |
                          v
                   SQLite Storage
                          |
                          v
                Background Processing
                          |
             +------------+------------+
             |                         |
             v                         v
       Runbook Retrieval        Incident Analysis
       (Knowledge Base)         (OpenAI / Rules)
             |                         |
             +------------+------------+
                          |
                          v
                Structured Analysis
                          |
                          v
                 Routing Engine
                          |
                          v
                Review Policy Engine
                     /          \
                    v            v
                 Triaged     Needs Review
                                  |
                                  v
                           Human Approval
                             /       \
                            v         v
                        Approved   Rejected
                          |
                          v
                   SQLite Database
                          |
                          v
                  Reporting & Metrics
```

## Project Structure

```text
incident-intelligence-platform/
|
|-- app/
|   |-- __init__.py
|   |-- main.py
|   |-- analysis.py
|   |-- config.py
|   |-- database.py
|   |-- retrieval.py
|   |-- routing.py
|   |-- schemas.py
|
|-- data/
|   |-- runbooks.json
|
|-- docs/
|   |-- PROJECT_WALKTHROUGH.md
|
|-- tests/
|   |-- test_workflow.py
|
|-- .env.example
|-- .gitignore
|-- Dockerfile
|-- pyproject.toml
|-- requirements.txt
|-- README.md
```

## Installation & Setup

**Prerequisites:** Python 3.11 or newer and pip.

### 1. Clone the repository

```bash
git clone https://github.com/khuship03/enterprise-incident-intelligence-platform.git
cd enterprise-incident-intelligence-platform
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure OpenAI integration (optional)

The application supports both AI-powered and rule-based incident analysis.

For OpenAI integration, set your API credentials before starting the server.

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY = "your-api-key"
$env:OPENAI_MODEL = "gpt-4o-mini"
```

macOS / Linux:

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="gpt-4o-mini"
```

Without an API key, the application automatically uses its local rule-based analysis.

### 5. Start the application

```bash
uvicorn app.main:app --reload
```

The API will run at:

`http://127.0.0.1:8000`

Interactive Swagger documentation:

`http://127.0.0.1:8000/docs`

The SQLite database is initialized automatically when the application starts.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Application information |
| GET | `/health` | Check service and database health |
| POST | `/incidents` | Submit an incident for analysis |
| GET | `/incidents` | Retrieve incident records |
| GET | `/incidents/{incident_id}` | Retrieve incident details and analysis |
| POST | `/incidents/{incident_id}/review` | Approve or reject an incident recommendation |
| GET | `/runbooks` | Retrieve knowledge base runbooks |
| GET | `/metrics` | Retrieve incident metrics and statistics |

## Example Workflow

### Create an incident

Open the Swagger UI at `http://127.0.0.1:8000/docs`.

Select `POST /incidents`, click **Try it out**, and submit:

```json
{
  "title": "Production checkout API requests timing out",
  "description": "Following a deployment, customers are experiencing elevated API error rates and checkout timeouts.",
  "service": "checkout-api",
  "source": "manual-demo"
}
```

The API returns a unique incident identifier.

### Retrieve incident analysis

Use:

```http
GET /incidents/{incident_id}
```

The incident details include:

- Incident summary and classification
- Severity and confidence score
- Relevant troubleshooting runbooks
- Recommended resolver group
- Analysis provider and processing status
- Human review state

### Review an incident

For incidents requiring human review, use:

```http
POST /incidents/{incident_id}/review
```

Example request:

```json
{
  "decision": "approve",
  "reviewed_by": "demo-reviewer",
  "notes": "Reviewed incident classification and resolver recommendation."
}
```

### View operational metrics

Use:

```http
GET /metrics
```

The reporting endpoint returns aggregated incident information, including distributions by status, category, and severity.

## Running Tests

Execute the automated test suite from the project root:

```bash
python -m pytest -q
```

Tests cover core incident creation, analysis, routing, and review workflows using a temporary SQLite database.

No OpenAI API key is required to execute the tests.