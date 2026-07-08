# InsightIQ — Backend

FastAPI service. Clean architecture: `routers → services → repositories`, all typed.

## Run (local, no Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head        # create metadata tables (or use `insightiq seed`)
insightiq seed                  # load sample-ecommerce + sample-saas
uvicorn app.main:app --reload
# → http://localhost:8000/health   http://localhost:8000/docs
```

## Test / lint

```bash
pytest
ruff check .
mypy app
```

## Layout

| Path | Purpose |
|------|---------|
| `app/main.py` | App factory, middleware (request-id + structured logging), CORS |
| `app/core/` | config, logging, error envelope, crypto (Fernet), security (access gate) |
| `app/api/v1/` | routers (thin; no business logic) |
| `app/db/` | ORM models, engine/session, DuckDB manager |
| `app/repositories/` | data access (projects, data sources) |
| `app/services/ingestion/` | CSV/XLSX → DuckDB, read-only Postgres connector |
| `app/services/profiling/` | per-column profiling + semantic-type inference |
| `app/services/sample_data/` | deterministic synthetic datasets + `seed` |
| `app/services/llm/` | swappable provider adapter (mock / gemini / anthropic) |
| `app/services/storage/` | `StorageBackend` (local ↔ R2) for DuckDB files |
| `migrations/` | Alembic (initial schema; checked on real Postgres in CI) |

The mock LLM provider (`LLM_PROVIDER=mock`) lets the app and tests run with no API key.
