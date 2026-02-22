# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

한양대학교 LIONS 학생 관리 대시보드 — a full-stack student management system with AI-powered evaluation, async task processing, and graph-based course similarity analysis.

## Running the System

### Full System (Docker — primary workflow)
```bash
docker-compose up --build          # Build and start all 6 services
docker-compose up -d --build       # Background mode
docker-compose down                # Stop
docker-compose down -v             # Stop and wipe all volumes (full reset)
docker-compose restart backend     # Restart a single service
docker-compose logs -f backend     # Tail logs for a service
```

Service URLs after startup:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8080 | Swagger UI: http://localhost:8080/docs
- Neo4j Browser: http://localhost:7474 (neo4j / password123)
- PostgreSQL: localhost:5432 | Redis: localhost:6379

### Local Development (without Docker)
```bash
# Backend
cd backend && uv sync
uv run fastapi dev main.py --host 0.0.0.0 --port 8080

# Frontend
cd frontend && npm install && npm run dev

# GraphDB (optional — populates Neo4j with course similarity graph)
cd graphDB && uv sync && uv run python quick_start.py
```

### Frontend Build & Lint
```bash
cd frontend
npm run build    # tsc -b && vite build
npm run lint     # eslint
npm run preview  # Preview production build
```

## Architecture

Six Docker containers communicate over a shared network:

```
frontend (React/Vite :5173)
    └─→ backend (FastAPI :8080)
            ├─→ db (PostgreSQL+pgvector :5432)
            ├─→ neo4j (Neo4j :7474/:7687) — course similarity graph
            └─→ redis (:6379) — Celery broker + task state
    └─→ ai (Celery worker)
            ├─→ db (same PostgreSQL)
            └─→ backend/* (imports EvaluationService directly via BACKEND_PATH)
```

### Backend (`backend/`)
FastAPI app with SQLAlchemy ORM on PostgreSQL. Entry point: `backend/main.py`.

Routers in `backend/routers/`:
- `students.py` — CRUD and filtering with pagination
- `courses.py` — course catalog and curriculum data
- `surveys.py` — major preference surveys
- `evaluation.py` — per-student department fitness evaluation
- `admin.py` — bulk CSV/Excel data import, trigger async evaluation jobs
- `dashboard.py` — aggregate statistics
- `graph.py` — Neo4j-backed similarity search and curriculum analysis

Services in `backend/services/`:
- `evaluation_service.py` — **core logic**: 3-metric scoring (entry requirements, recommended courses, curriculum completion). Uses Neo4j similarity at threshold 0.7 to recognize equivalent courses.
- `admin_service.py` — validates and imports uploaded files into DB
- `graph_service.py` — Neo4j driver singleton (`Neo4jConnection`)
- `seed_service.py` — initial DB seeding

Database constants live in `backend/constants.py` (grade thresholds, weights, etc.).

### Frontend (`frontend/src/`)
React 19 + TypeScript + Tailwind CSS. Routing via React Router v7.

- `App.tsx` — Three routes: `/` (DashboardView), `/student/:studentId` (StudentDetailView), `/admin` (AdminView)
- `api.ts` — Centralized API client. All backend calls go through the `api.*` namespace here. Add new endpoints here first.
- `types.ts` — Shared TypeScript interfaces matching backend Pydantic schemas
- `components/student/` — Student list, detail, tabs (courses, surveys, entry requirements, curriculum)

### AI Worker (`ai/`)
Celery worker that runs async tasks triggered from the admin UI:
- `tasks.py::bulk_evaluate_task` — runs EvaluationService for all students × all departments, stores results in `student_requirement_status`, generates AI summary via OpenAI
- `tasks.py::rebuild_graph_task` — re-runs `graphDB/quick_start.py` to rebuild Neo4j graph

The worker imports backend Python modules directly (`sys.path` injection via `BACKEND_PATH=/backend`).

### GraphDB (`graphDB/`)
Standalone Python module that builds the Neo4j course similarity graph using Sentence-BERT embeddings. Produces `SIMILAR_TO` (cosine similarity ≥ 0.8) and `IDENTICAL_ID` relationships between course nodes.

## Database Schema Key Points

11 tables in PostgreSQL. The most important:
- `students` — `student_id` (PK), GPA, track, status
- `student_courses` — enrollment history with grades and completion type
- `department_entry_requirements` + `requirement_courses` — define which courses a department requires/recommends with grade thresholds (A/B/C)
- `student_requirement_status` — **cached evaluation results** per (student × department). Populated by `bulk_evaluate_task`. Stale entries remain until re-evaluated.
- `curriculum` + `course_recommendations` — per-department curriculum and recommended course lists

## Key Conventions

- **Package manager**: `uv` for Python (backend and ai worker); `npm` for frontend. Do not mix.
- **Python version**: 3.12 required.
- **API client pattern**: All frontend API calls must go through `frontend/src/api.ts`. Do not use `fetch` directly in components.
- **Evaluation caching**: `student_requirement_status` is a cache. After changing evaluation logic, trigger a bulk re-evaluation from the admin UI or via the Celery task.
- **Neo4j is optional**: The backend gracefully degrades when Neo4j is unavailable (`_graph_available` flag in `EvaluationService`). Similarity matching is skipped; only exact course code matches are used.
- **Environment variables**: Defined in `.env` at project root and injected by `docker-compose.yml`. The backend reads them via `os.getenv`. Do not hardcode credentials.
- **No test suite**: There are no automated tests. Use Swagger UI at `/docs` for API testing.
