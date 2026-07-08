"""Semantic layer: generation quality, versioning, YAML round-trip, editing."""
from __future__ import annotations

import io

from fastapi.testclient import TestClient

from app.db.duckdb_manager import DuckDBManager
from app.repositories.projects import ProjectRepository
from app.schemas.semantic_layer import SemanticLayerSpec
from app.services.sample_data.seed import seed_sample_data
from app.services.semantic_layer.generator import SemanticLayerGenerator
from app.services.semantic_layer.yaml_io import spec_to_yaml, yaml_to_spec

BASE = "/api/v1"

CSV = (
    "order_date,region,amount,is_priority\n"
    "2025-01-05,North,120.50,true\n"
    "2025-01-06,South,80.00,false\n"
    "2025-02-02,East,45.25,false\n"
)


def _project_with_csv(client: TestClient) -> str:
    pid = client.post(f"{BASE}/projects", json={"name": "Sem", "source": "duckdb"}).json()["id"]
    client.post(
        f"{BASE}/projects/{pid}/uploads",
        files={"file": ("sales.csv", io.BytesIO(CSV.encode()), "text/csv")},
    )
    return pid


def test_generate_creates_active_v1(client: TestClient) -> None:
    pid = _project_with_csv(client)
    r = client.post(f"{BASE}/projects/{pid}/semantic-layer/generate")
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["version"] == 1
    assert out["is_active"] is True
    assert out["yaml"]
    entities = {e["name"]: e for e in out["spec"]["entities"]}
    assert "sales" in entities
    measures = {m["name"] for m in entities["sales"]["measures"]}
    assert "amount" in measures  # numeric → measure


def test_no_layer_yet_returns_404(client: TestClient) -> None:
    pid = client.post(f"{BASE}/projects", json={"name": "Empty", "source": "duckdb"}).json()["id"]
    assert client.get(f"{BASE}/projects/{pid}/semantic-layer").status_code == 404


def test_versioning_via_edit(client: TestClient) -> None:
    pid = _project_with_csv(client)
    v1 = client.post(f"{BASE}/projects/{pid}/semantic-layer/generate").json()

    edited = v1["yaml"].replace(
        "One row per sale.", "One row per sales order line (edited)."
    ) if "One row per sale." in v1["yaml"] else v1["yaml"]
    r = client.put(f"{BASE}/projects/{pid}/semantic-layer", json={"yaml": edited})
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 2
    assert r.json()["created_by"] == "user"

    # Active is now v2; v1 still fetchable and inactive.
    assert client.get(f"{BASE}/projects/{pid}/semantic-layer").json()["version"] == 2
    v1_now = client.get(f"{BASE}/projects/{pid}/semantic-layer?version=1").json()
    assert v1_now["is_active"] is False

    versions = client.get(f"{BASE}/projects/{pid}/semantic-layer/versions").json()
    assert [v["version"] for v in versions] == [2, 1]


def test_put_invalid_yaml_is_422(client: TestClient) -> None:
    pid = _project_with_csv(client)
    client.post(f"{BASE}/projects/{pid}/semantic-layer/generate")
    r = client.put(
        f"{BASE}/projects/{pid}/semantic-layer",
        json={"yaml": "entities: [this is: not valid: schema"},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_yaml_round_trip(client: TestClient) -> None:
    pid = _project_with_csv(client)
    spec_dict = client.post(f"{BASE}/projects/{pid}/semantic-layer/generate").json()["spec"]
    spec = SemanticLayerSpec.model_validate(spec_dict)
    assert yaml_to_spec(spec_to_yaml(spec)) == spec


def test_heuristic_detects_joins_and_revenue(db_session) -> None:
    seed_sample_data(db_session, DuckDBManager())
    ecom = ProjectRepository(db_session).get_by_slug("sample-ecommerce")
    spec = SemanticLayerGenerator(DuckDBManager()).build(ecom.id, dialect="duckdb")

    entities = {e.name: e for e in spec.entities}
    assert {"orders", "customers", "products", "order_items"} <= set(entities)

    orders_join = {(j.to, j.on) for j in entities["orders"].joins}
    assert ("customers", "orders.customer_id = customers.customer_id") in orders_join

    item_measures = {m.name: m for m in entities["order_items"].measures}
    assert item_measures["amount"].agg == "sum"           # revenue
    assert item_measures["amount"].format == "currency"


def test_generation_is_deterministic(db_session) -> None:
    seed_sample_data(db_session, DuckDBManager())
    ecom = ProjectRepository(db_session).get_by_slug("sample-ecommerce")
    gen = SemanticLayerGenerator(DuckDBManager())
    a = gen.build(ecom.id, dialect="duckdb").model_dump()
    b = gen.build(ecom.id, dialect="duckdb").model_dump()
    assert a == b
