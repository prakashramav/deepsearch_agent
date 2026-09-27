# DeepResearch Agent 🔬

> **Multi-agent AI research system** — takes any research question, runs parallel web search across specialized agents, fact-checks claims against multiple sources, and produces a fully cited Markdown report.

[![Phase](https://img.shields.io/badge/All%20Phases-Complete-brightgreen)](#phases)
[![Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20Next.js%20%7C%20LangGraph-blue)](#tech-stack)

---

## 📌 About The Project

Standard conversational AI search tools often fall short when tasked with comprehensive, publication-grade research:
- **Hallucinations & Speculation**: Single-prompt LLMs generate convincing answers but often invent details or cite non-existent publications.
- **Narrow Research Breadth**: A single search query only touches the surface, missing orthogonal angles like pricing, regulatory shifts, tech architecture, and market fragmentation.
- **Unverified Contradictions**: Information across the web is frequently inconsistent or conflicting without any mechanism to identify discrepancies.
- **Superficial Synthesis**: Output usually lacks structured data tables, verified hard figures, and verifiable source attribution.

**DeepResearch Agent** solves this by recreating an entire corporate research organization as an autonomous multi-agent pipeline. It ingests complex questions, methodically deconstructs them, searches the web in parallel across dozens of sources, extracts discrete factual assertions, cross-checks claims for agreement or divergence, synthesizes competitive matrices, and outputs an executive Markdown report with full source citations and one-click PDF export.

---

## 💡 How We Solved It

Rather than relying on one massive, monolithic LLM prompt, we architected a modular multi-agent system powered by **LangGraph**, **Google Gemini 2.5 Flash**, and **Tavily Search**:

1. **Agent Specialization over Monoliths**:
   Each agent has a strictly bounded persona, distinct schema constraints, and isolated failure modes. If an extraction step fails, the pipeline isolates the error and executes fallback heuristics rather than collapsing the entire run.

2. **Stateful Graph Orchestration (LangGraph)**:
   The orchestration graph is governed by a **Supervisor Agent** state machine that manages checkpoint transitions in PostgreSQL, inspects intermediate artifact quality, and dynamically triggers self-correcting retry/refinement loops when source counts or citation coverage drop below predefined quality thresholds.

3. **Multi-Source Fact Verification & Conflict Detection**:
   The `Extractor` parses numbers, dates, and claims into structured records. Then the `FactChecker` cross-references these claims against all gathered sources to compute an agreement score, flag conflicting data points, and append audit notes.

4. **Guaranteed Citation Auditing**:
   The `CitationAgent` matches every inline bracketed citation (`[1]`, `[2]`) in the written report against the actual verified URL catalog, eliminating phantom sources and ensuring a 100% auditable references section.

5. **Production Full-Stack Architecture**:
   - **Backend**: FastAPI with async SQLAlchemy, connection pooling via `psycopg`, background worker execution, and automated table initialization.
   - **Frontend**: Next.js 15 dark-mode application featuring live stage-by-stage status tracking, sub-question visualization, claims verification tables, run lookup by ID, and native browser print-to-PDF export.

---

## ⚙️ How It Works (End-to-End Workflow)

```mermaid
flowchart TD
    User([User Question]) --> API[FastAPI /api/v1/research]
    API --> Supervisor[Supervisor Agent StateGraph]
    
    subgraph MultiAgentPipeline [Orchestrated Research Graph]
        Supervisor --> Planner[1. Planner Agent]
        Planner -->|3-6 Sub-Questions| Researcher[2. Parallel Research Agent]
        Researcher -->|Concurrent Tavily Queries| Dedup[Source Deduplication & Normalization]
        
        Dedup --> Gate{Source Adequacy Threshold >= 3?}
        Gate -- No (Sparse Sources) --> Refine[Dynamic Refinement Loop]
        Refine --> Researcher
        Gate -- Yes --> Extractor[3. Data Extractor Agent]
        
        Extractor -->|Factual Claims & Quotes| FactChecker[4. Fact-Checker Agent]
        FactChecker -->|Verified Claims & Conflict Flags| Analyst[5. Strategic Analyst Agent]
        Analyst -->|Comparative Insights & Trends| Writer[6. Report Writer Agent]
        Writer -->|Draft Report with Citations| Citation[7. Citation Auditor Agent]
        Citation -->|Audited Report + References| Delivery[8. PostgreSQL DB Checkpoint]
    end
    
    Delivery --> UI[Next.js Interactive Dashboard]
    UI --> Export[Printable HTML & PDF Export Engine]
```

### Detailed Pipeline Stages

| Stage | Agent / Module | Responsibility |
|---|---|---|
| **1. Planning** | `PlannerAgent` | Deconstructs the user prompt into 3–6 distinct, non-overlapping sub-questions across distinct research angles (e.g., market size, technical specs, competitive landscape, regulations). |
| **2. Retrieval** | `ResearchAgent` | Dispatches concurrent Tavily web queries with concurrency limits (`asyncio.Semaphore`), normalizes URLs, strips tracking params, and removes duplicate sources. |
| **3. Quality Gate** | `SupervisorAgent` | Evaluates collected source volume. If fewer than 3 sources are found, it generates a refined broad search strategy and re-runs retrieval. |
| **4. Extraction** | `ExtractorAgent` | Extracts key verifiable factual claims, numbers, dates, and direct supporting quotes into structured claim records. |
| **5. Verification** | `FactCheckerAgent` | Cross-checks extracted claims across all retrieved sources, verifying multi-source consensus and flagging data discrepancies or conflicting numbers. |
| **6. Analysis** | `AnalystAgent` | Transforms raw data into strategic insights: identifies macro trends, compares key players/technologies, and resolves contested claims. |
| **7. Writing** | `WriterAgent` | Formats an executive-ready Markdown report with deep-dive sections, comparative Markdown tables, and mandatory inline citations (`[1]`, `[2]`). |
| **8. Audit & Export** | `CitationAgent` & `ExportEngine` | Validates every in-text citation against the source catalog, verifies URLs, saves checkpoints to PostgreSQL, and provides styled PDF / Markdown export endpoints. |

---

## Architecture

```
User (question)
  │
  ▼
Next.js UI ──── REST API ────► FastAPI Backend
                                    │
                                    ▼
                             Supervisor Agent (LangGraph)
                            ┌───────────────────────────┐
                            │  Planner → Research (×N)  │
                            │  → DataAgent → FactChecker │
                            │  → Analyst → Writer        │
                            │  → CitationAgent           │
                            └───────────────────────────┘
                                    │
                                    ▼
                            PostgreSQL (runs/sources/claims)
                            Redis (job queue / cache)
```

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Frontend   | Next.js 15 (App Router), Vanilla CSS |
| Backend    | FastAPI (Python), async SQLAlchemy  |
| Agents     | LangGraph, Google Gemini 2.5 Flash  |
| Search     | Tavily (purpose-built for LLM agents) |
| Database   | PostgreSQL + pgvector               |
| Cache/Queue| Redis                               |
| Container  | Docker Compose                      |

---

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/prakashramav/deepsearch_agent
cd DeepResearch-Agent

# Copy and fill in credentials
cp .env.example .env
# Edit .env — add your GEMINI_API_KEY and TAVILY_API_KEY
```

### 2. Run with Docker Compose (recommended)

```bash
docker compose up --build
```

- Frontend → http://localhost:3000
- Backend API → http://localhost:8000
- API Docs → http://localhost:8000/docs

### 3. Run locally (development)

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
cp .env.example .env          # fill in API keys
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

> **Pre-requisites (local run):** PostgreSQL 15+ and Redis 7+ must be running and accessible at the URLs in `.env`.

---

## API Reference

| Method | Endpoint                             | Description                            |
|--------|--------------------------------------|----------------------------------------|
| POST   | `/api/v1/research`                   | Start a new research run               |
| GET    | `/api/v1/research/{run_id}`          | Poll run status + result               |
| GET    | `/api/v1/research/{run_id}/sources`  | Get sources for a run                  |
| GET    | `/api/v1/research/{run_id}/claims`   | Get extracted & verified factual claims|
| GET    | `/api/v1/research/{run_id}/export/markdown` | Download raw report as Markdown (.md) |
| GET    | `/api/v1/research/{run_id}/export/html`     | Printable HTML report view             |
| GET    | `/api/v1/research/{run_id}/export/pdf`      | Browser-printable PDF layout endpoint  |
| GET    | `/health`                            | Health check                           |
| GET    | `/docs`                              | Interactive Swagger UI                 |

**Start research:**
```bash
curl -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"question": "Analyze the EV market in India — major manufacturers and trends"}'

# → {"run_id": "abc-123", "status": "pending", "message": "Research started"}
```

**Poll for result:**
```bash
curl http://localhost:8000/api/v1/research/abc-123
# → {"status": "complete", "result": "# Research Report\n...", ...}
```

---

## Phases

| Phase | Description                                   | Status |
|-------|-----------------------------------------------|--------|
| 1     | Core scaffold: question → search → report     | ✅ Done |
| 2     | Planner: decompose into sub-questions          | ✅ Done |
| 3     | Parallel research + source collection         | ✅ Done |
| 4     | Data extraction (claims table)                | ✅ Done |
| 5     | Conflict detection + fact verification        | ✅ Done |
| 6     | Synthesis, writing, citations                 | ✅ Done |
| 7     | Supervisor node + retry logic                 | ✅ Done |
| 8     | PDF export + full pipeline UI demo            | ✅ Done |

---

## Project Structure

```
DeepResearch-Agent/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── planner.py         # Sub-question decomposition
│   │   │   ├── researcher.py      # Concurrent Tavily search + deduplication
│   │   │   ├── extractor.py       # Factual claims & stats extraction
│   │   │   ├── fact_checker.py    # Cross-source verification & conflict flags
│   │   │   ├── analyst.py         # Synthesis, trend analysis, comparisons
│   │   │   ├── writer.py          # Markdown executive report formatting
│   │   │   ├── citation_agent.py  # Source reference audit & link validation
│   │   │   └── supervisor.py      # LangGraph state machine & retry loop
│   │   ├── routers/
│   │   │   └── research.py        # REST API endpoints + export routes
│   │   ├── config.py              # Settings via pydantic-settings
│   │   ├── database.py            # Async SQLAlchemy engine
│   │   ├── export.py              # Printable HTML & PDF export renderer
│   │   ├── main.py                # FastAPI app factory
│   │   ├── models.py              # ORM models (runs/sources/claims)
│   │   ├── schemas.py             # Pydantic request/response schemas
│   │   └── tasks.py               # Background task runner & orchestrator
│   ├── tests/                     # 33 unit & integration tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── globals.css            # Dark-theme design system & print styles
│   │   ├── layout.js              # Root layout + SEO metadata
│   │   └── page.jsx               # Main page with Run ID lookup & query params
│   ├── components/
│   │   ├── QuestionForm.jsx       # Research question input
│   │   ├── PlanViewer.jsx         # Research plan & sub-questions view
│   │   ├── ClaimsTable.jsx        # Verified claims & conflict indicators
│   │   ├── StatusTracker.jsx      # Live pipeline progress & supervisor audit
│   │   ├── ReportViewer.jsx       # Rendered report with PDF / MD exports
│   │   └── SourcesList.jsx        # Clickable sources sidebar
│   ├── hooks/
│   │   └── useResearch.js         # Submit, poll, and load run hook
│   ├── lib/
│   │   └── api.js                 # Backend API client + export URLs
│   └── Dockerfile
├── docker-compose.yml
├── .env.example                   # Copy → .env, fill in secrets
└── README.md
```

---

## Worked Example (EV Market India)

```
Question: "Analyze the current EV market in India — major manufacturers,
           pricing, battery technology trends, and competitive landscape"

Pipeline:
  1. Tavily search (7 sources, advanced depth)
  2. Claude Sonnet: structured Markdown synthesis with [1][2][3] citations
  3. Sources saved to DB for audit trail

Result: ~1500-word Markdown report with:
  - Overview of Indian EV market
  - Comparison table: Tata Motors, Ola Electric, MG, Hyundai
  - Price ranges by segment
  - Battery/charging technology trends
  - ## References section with all source URLs
```

---

## Environment Variables

```env
# Root .env (for Docker Compose)
GEMINI_API_KEY=AIzaSy...        # Get from aistudio.google.com
TAVILY_API_KEY=tvly-...         # Get from app.tavily.com

# backend/.env (for local run — same keys plus DB config)
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/deepresearch
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:3000
```

---

## Security

- **Never commit real API keys** — `.env` files are in `.gitignore`
- All credentials flow through environment variables only
- CORS is restricted to `CORS_ORIGINS` setting (default: localhost:3000)
