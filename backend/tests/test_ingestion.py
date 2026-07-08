"""CSV upload → DuckDB → list tables → profile."""
from __future__ import annotations

import io
import uuid

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.repositories.data_sources import DataSourceRepository

BASE = "/api/v1"

CSV = (
    "order_date,region,amount,is_priority\n"
    "2025-01-05,North,120.50,true\n"
    "2025-01-06,South,80.00,false\n"
    "2025-02-01,North,,true\n"
    "2025-02-02,East,45.25,false\n"
)


def _new_project(client: TestClient) -> str:
    return client.post(f"{BASE}/projects", json={"name": "Upload Test", "source": "duckdb"}).json()[
        "id"
    ]


def test_upload_list_profile(client: TestClient) -> None:
    pid = _new_project(client)

    files = {"file": ("sales.csv", io.BytesIO(CSV.encode()), "text/csv")}
    r = client.post(f"{BASE}/projects/{pid}/uploads", files=files)
    assert r.status_code == 200, r.text
    tables = r.json()["tables"]
    assert tables[0]["name"] == "sales"
    assert tables[0]["row_count"] == 4
    assert tables[0]["column_count"] == 4

    r = client.get(f"{BASE}/projects/{pid}/tables")
    assert r.status_code == 200
    assert {t["name"] for t in r.json()} == {"sales"}

    r = client.get(f"{BASE}/projects/{pid}/tables/sales/profile")
    assert r.status_code == 200
    prof = r.json()
    assert prof["row_count"] == 4
    cols = {c["name"]: c for c in prof["columns"]}
    assert cols["order_date"]["semantic_type"] == "time"
    assert cols["region"]["semantic_type"] == "categorical"
    assert cols["amount"]["semantic_type"] == "numeric"
    assert cols["amount"]["null_count"] == 1          # the blank amount row
    assert cols["is_priority"]["semantic_type"] == "boolean"


def test_unsupported_file_type(client: TestClient) -> None:
    pid = _new_project(client)
    files = {"file": ("notes.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")}
    r = client.post(f"{BASE}/projects/{pid}/uploads", files=files)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_profile_missing_table_404(client: TestClient) -> None:
    pid = _new_project(client)
    files = {"file": ("sales.csv", io.BytesIO(CSV.encode()), "text/csv")}
    client.post(f"{BASE}/projects/{pid}/uploads", files=files)
    r = client.get(f"{BASE}/projects/{pid}/tables/nope/profile")
    assert r.status_code == 404


def test_postgres_connection_endpoint(client: TestClient, monkeypatch) -> None:
    """Connecting a PG source introspects, stores an ENCRYPTED dsn, returns tables."""
    from app.api.v1.routers import data_sources as ds_mod
    from app.services.ingestion.postgres_connector import PgColumn, PgTable

    class _FakeConnector:
        def __init__(self, dsn: str) -> None:
            self.dsn = dsn

        def introspect(self):
            return [PgTable("public", "orders", [PgColumn("id", "integer", False)])]

    monkeypatch.setattr(ds_mod, "PostgresConnector", _FakeConnector)

    pid = client.post(
        f"{BASE}/projects", json={"name": "PG", "source": "postgres"}
    ).json()["id"]
    dsn = "postgresql://u:p@host:5432/db"
    r = client.post(f"{BASE}/projects/{pid}/connections", json={"connection_string": dsn})
    assert r.status_code == 200, r.text
    assert r.json()["tables"][0]["name"] == "public.orders"

    # The stored credential is encrypted, not the plaintext DSN.
    with SessionLocal() as s:
        sources = DataSourceRepository(s).list_for_project(uuid.UUID(pid))
        pg = [d for d in sources if d.kind == "postgres"][0]
        assert pg.config_encrypted is not None
        assert dsn.encode() not in pg.config_encrypted
