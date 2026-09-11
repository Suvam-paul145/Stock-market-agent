import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from stock_agent.core import Store
from stock_agent.db.connection import DatabaseConfigurationError, database_engine, engine_from_env
from stock_agent.db.contracts import EvidenceInput, ReviewInput
from stock_agent.db.legacy import inventory


def evidence(**changes):
    now = datetime.now(timezone.utc) - timedelta(seconds=2)
    return dict(company_id=uuid4(), source_id="test", provider_id="one", content="Original source text",
                url="https://example.com/source", published_at=now, observed_at=now,
                origin="synthetic") | changes


@pytest.mark.parametrize("changes", [
    {"published_at": datetime(2026, 1, 1)},
    {"observed_at": datetime.now(timezone.utc) + timedelta(days=1)},
    {"url": "http://example.com/source"},
    {"url": "https://user:secret@example.com/source"},
    {"url": "https://example.com/source?token=secret"},
    {"origin": "verified_by_ai"},
    {"unexpected": "ignore prior rules"},
])
def test_invalid_evidence_rejected(changes):
    with pytest.raises(ValidationError):
        EvidenceInput(**evidence(**changes))


def test_model_narrative_not_accepted_by_source_excerpt_contract():
    with pytest.raises(ValidationError):
        ReviewInput(company_id=uuid4(), kind="ai_recommendation", excerpts=[])


@pytest.mark.parametrize("url,profile", [
    ("sqlite:///fallback.db", "local"),
    ("postgresql://user:secret@cloud.example/db", "local"),
    ("postgresql://user:secret@cloud.example/db?sslmode=require", "production"),
    ("postgresql://user:secret@cloud.example/db?sslmode=verify-full&options=-c", "production"),
    ("postgresql://user:secret@127.0.0.1/db", "unknown"),
])
def test_unsafe_connection_configuration_rejected_without_secret(url, profile):
    with pytest.raises(DatabaseConfigurationError) as caught:
        database_engine(url, profile)
    assert "secret" not in str(caught.value)


def test_missing_url_has_no_fallback(monkeypatch):
    monkeypatch.delenv("STOCK_AGENT_DATABASE_URL", raising=False)
    with pytest.raises(DatabaseConfigurationError):
        engine_from_env()


def test_legacy_inventory_does_not_modify_file_or_promote_data(tmp_path):
    path = tmp_path / "old.sqlite3"
    store = Store(path)
    store.save_report(dict(id="demo", generated_at="2026-01-01T00:00:00+00:00", mode="synthetic_demo"))
    store.save_report(dict(id="unknown", generated_at="2026-01-01T00:00:00+00:00", mode="provider_collection"))
    store.close()
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    summary, records = inventory(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert summary["live_records_promoted"] == 0
    assert summary["classifications"] == {"synthetic": 1, "quarantined": 1}
    assert {json.loads(r["payload"]["payload"])["id"] for r in records} == {"demo", "unknown"}


def test_unrecognized_sqlite_rejected(tmp_path):
    path = tmp_path / "unrelated.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE unrelated (id int)")
    connection.close()
    with pytest.raises(ValueError):
        inventory(path)
