# DeepResearch Agent 🔬

> **Multi-agent AI research system** — takes any research question, runs parallel web search across specialized agents, fact-checks claims against multiple sources, and produces a fully cited Markdown report.

[![Phase](https://img.shields.io/badge/Phase-5%20Complete-brightgreen)](#phases)
[![Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20Next.js%20%7C%20LangGraph-blue)](#tech-stack)

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
| Frontend   | Next.js 15 (App Router), Tailwind CSS |
| Backend    | FastAPI (Python), async SQLAlchemy  |
| Agents     | LangGraph, LangChain, Claude Sonnet |
| Search     | Tavily (purpose-built for LLM agents) |
| Database   | PostgreSQL + pgvector               |
| Cache/Queue| Redis                               |
| Container  | Docker Compose                      |

---

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/youruser/DeepResearch-Agent
cd DeepResearch-Agent

# Copy and fill in credentials
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY and TAVILY_API_KEY
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

| Method | Endpoint                        | Description                      |
|--------|---------------------------------|----------------------------------|
| POST   | `/api/v1/research`              | Start a new research run         |
| GET    | `/api/v1/research/{run_id}`     | Poll run status + result         |
| GET    | `/api/v1/research/{run_id}/sources` | Get sources for a run        |
| GET    | `/health`                       | Health check                     |
| GET    | `/docs`                         | Interactive Swagger UI           |

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
| 6     | Synthesis, writing, citations                 | 🔜 Next |
| 7     | Supervisor node + retry logic                 | 🔜     |
| 8     | PDF export + full pipeline UI demo            | 🔜     |

---

## Project Structure

```
DeepResearch-Agent/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   └── phase1_chain.py    # Tavily search + Claude summarise
│   │   ├── routers/
│   │   │   └── research.py        # REST API endpoints
│   │   ├── config.py              # Settings via pydantic-settings
│   │   ├── database.py            # Async SQLAlchemy engine
│   │   ├── main.py                # FastAPI app factory
│   │   ├── models.py              # ORM models (runs/sources/claims)
│   │   ├── schemas.py             # Pydantic request/response schemas
│   │   └── tasks.py               # Background task runner
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── globals.css            # Full design system
│   │   ├── layout.js              # Root layout + SEO metadata
│   │   └── page.jsx               # Main page
│   ├── components/
│   │   ├── QuestionForm.jsx       # Research question input
│   │   ├── StatusTracker.jsx      # Live pipeline progress
│   │   ├── ReportViewer.jsx       # Rendered Markdown report
│   │   └── SourcesList.jsx        # Clickable sources sidebar
│   ├── hooks/
│   │   └── useResearch.js         # Submit + poll lifecycle hook
│   ├── lib/
│   │   └── api.js                 # Backend API client
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
ANTHROPIC_API_KEY=sk-ant-...   # Get from console.anthropic.com
TAVILY_API_KEY=tvly-...         # Get from app.tavily.com

# backend/.env (for local run — same keys plus DB config)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/deepresearch
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:3000
```

---

## Security

- **Never commit real API keys** — `.env` files are in `.gitignore`
- All credentials flow through environment variables only
- CORS is restricted to `CORS_ORIGINS` setting (default: localhost:3000)
