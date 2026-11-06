# AGENTS.md — System Instructions & AI Architecture Setup

## Project Overview
- **Project Name:** YouTube Copy
- **Goal:** Single-command full-stack backend service mimicking core YouTube features.
- **Tech Stack:** Python 3.12+, FastAPI, PostgreSQL, MinIO, Docker Compose.

## AI Execution Rules
1. **Zero Placeholders:** Code generated must be production-ready and fully written. No `# TODO` or shortened snippet functions.
2. **Strict Typing:** Explicit Python Type Hints across all layers (routers, schemas, ORM models).
3. **Pydantic v2 & SQLAlchemy 2.0:** All data validation must use Pydantic v2 schemas; DB interactions must use SQLAlchemy 2.0 async sessions.
4. **Modularity:** 
   - `app/api/` — API routers
   - `app/core/` — DB, security, and environment configs
   - `app/models/` — DB models
   - `app/schemas/` — Request/Response validation schemas
   - `app/services/` — MinIO S3 integration and business logic

## Target Deployment
- **Deployment:** Single command via `docker compose up --build` targeting clean Ubuntu environment.