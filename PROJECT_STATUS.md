# PROJECT_STATUS

_Living handoff doc. Updated at the end of every phase._

**Current phase:** 6 — hardening + launch ✅
**Status: COMPLETE.** All six phases shipped. Portfolio-ready.

---

## Done (Phase 6)

- **Cloudflare R2 storage wired for real** (`services/storage/r2.py`) — boto3
  S3-compatible pull/push/exists/delete with local caching and tolerant
  not-found handling; missing objects let a first ingest create-then-push. The
  `DuckDBManager` already pulls on connect and pushes on persist, so flipping
  `STORAGE_BACKEND=r2` is the only change. Covered by tests with a fake S3 client.
- **Deploy blueprints** — `render.yaml` (API on Render, Docker, `preDeployCommand:
  alembic upgrade head`, all secrets as `sync:false`), `vercel.json` (frontend),
  Dockerfile now copies `migrations/` + `alembic.ini`. API base is configurable
  (`VITE_API_BASE`) with CORS via `CORS_ORIGINS`. All env documented in
  `.env.example` + `frontend/.env.example`. Render cold-start noted in the README.
- **Shareable dashboards + saved layouts** — `PATCH /dashboards/{id}` persists a
  user-adjusted react-grid layout; `GET` returns it; the grid loads a saved layout
  and debounce-saves drags. (Tested end-to-end.)
- **Case-study README** — problem, mermaid architecture, key-tradeoffs table,
  privacy section, eval results table (23/23 gate + Gemini row), planted-insights
  list, demo GIF + live-link placeholders, and a full free-tier deploy guide.
- **Demo script** — `docs/DEMO_SCRIPT.md`, a 60–90s walkthrough of the Tier-2 Q3
  revenue dip and the 92-day churn cliff, with timing, narration, and a shot list.

## Quality (whole project)

- **72 backend tests** pass; ruff + mypy clean (78 files); migrations up/down verified.
- Frontend: `tsc` clean, ESLint 9 flat config clean, **9 vitest** tests, warning-free build.
- CI (mock, $0): backend lint/mypy/pytest + Postgres migration + **eval gate**;
  frontend lint/test/build.
- Eval: **23/23 clear-case regression gate**, 77% execution accuracy, 100% valid-SQL
  on the deterministic planner (Gemini scored separately via `--provider gemini`).

## What ships

Text -> semantic layer (auto-gen, versioned, editable) -> multi-query planning
(structured output, 1–6 typed intents) -> safe SQL (sqlglot guard: SELECT-only,
allowlist, denylist, auto-LIMIT, timeout) -> sandboxed execution + self-correction
-> deterministic chart selection + captions -> interactive dashboard (grid, global
date filter, view-SQL, shareable/reloadable) -> versioned eval suite with a CI
accuracy gate. Free-tier deployable (Vercel + Render + Neon + R2), synthetic-only
hosted demo, BYO paid key for real data.

## Fill-in before publishing

- Record `docs/demo.gif` (resolving-dashboard hero) and set the live URL in the
  README (currently `https://insightiq.vercel.app` placeholder).
- Run `insightiq eval --provider gemini` with a key and drop the number into the
  README eval table's Gemini row.

## Possible follow-ons (not required)

- Multi-tenant auth (isolation is already at `project_id`).
- dbt-metrics importer into the semantic layer (loader is structured for it).
- Grow the eval set; add a cost/usage view from `llm_usage`.
