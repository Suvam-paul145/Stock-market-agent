"""Real PostgreSQL integration tests, exclusively in an explicit disposable local database.

All document text is invented test-fixture content; ``origin='live'`` exercises
the live-data gate and does not claim that these fixtures came from a provider.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from stock_agent.db.access import grant_access
from stock_agent.db.connection import database_engine, migrate
from stock_agent.db.contracts import EvidenceInput, Excerpt, ReviewInput
from stock_agent.db.repository import GateError, ResearchRepository
from stock_agent.db.legacy import import_legacy
from stock_agent.core import Store

pytestmark = pytest.mark.postgres
SCHEMA_MARKER = "stock_agent_disposable_integration_tests"


def disposable_url(value):
    """Reject remote or non-test databases before making any connection."""
    try:
        parsed = make_url(value)
        valid = (
            parsed.drivername in {"postgres", "postgresql", "postgresql+psycopg"}
            and parsed.host in {"127.0.0.1", "localhost", "::1"}
            and parsed.database and parsed.database.endswith("_test")
        )
    except Exception:
        valid = False
    if not valid:
        raise ValueError("Integration tests require a loopback PostgreSQL database ending in _test")
    return value


def drop_owned_test_schema(engine):
    with engine.begin() as conn:
        schema = conn.execute(text("""SELECT pg_get_userbyid(nspowner) = current_user,
            obj_description(oid, 'pg_namespace') FROM pg_namespace WHERE nspname='research'""")).first()
        if schema:
            if not schema[0] or schema[1] != SCHEMA_MARKER:
                raise RuntimeError("Refusing to remove research schema without test ownership and marker")
            conn.execute(text("DROP SCHEMA research CASCADE"))


@pytest.fixture
def db():
    value = os.getenv("STOCK_AGENT_TEST_DATABASE_URL")
    if not value:
        pytest.skip("Set STOCK_AGENT_TEST_DATABASE_URL to an explicitly disposable loopback *_test database")
    engine = database_engine(disposable_url(value))
    try:
        drop_owned_test_schema(engine)
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA research"))
            conn.execute(text(f"COMMENT ON SCHEMA research IS '{SCHEMA_MARKER}'"))
        migrate(engine)
        yield engine
    finally:
        try:
            drop_owned_test_schema(engine)
        finally:
            engine.dispose()


@pytest.fixture
def seeded(db):
    repo = ResearchRepository(db)
    company = repo.add_company("TST", "Invented integration test company")
    repo.add_source("test_fixture", storage_allowed=True)
    return repo, company


def evidence(company, **changes):
    now = datetime.now(timezone.utc) - timedelta(minutes=10)
    values = dict(company_id=company, source_id="test_fixture", provider_id="fixture-1",
                  content="TEST FIXTURE: The invented company reports 10 sample units.",
                  url="https://example.com/test-fixture", published_at=now - timedelta(minutes=1),
                  observed_at=now, origin="live")
    values.update(changes)
    return EvidenceInput(**values)


def review(company, evidence_id, **changes):
    values = dict(company_id=company, excerpts=[Excerpt(evidence_id=evidence_id,
                  quote="The invented company reports 10 sample units.")])
    values.update(changes)
    return ReviewInput(**values)


def scalar(db, sql):
    with db.connect() as conn:
        return conn.execute(text(sql)).scalar_one()


@pytest.mark.parametrize("value", [
    "postgresql://user:secret@db.example.com/stock_agent_test",
    "postgresql://user:secret@127.0.0.1/stock_agent",
    "sqlite:///stock_agent_test", "invalid",
])
def test_destructive_target_guard(value):
    with pytest.raises(ValueError, match="loopback"):
        disposable_url(value)


def test_migration_upgrade_idempotent_and_explicit_downgrade(db, seeded):
    migrate(db)
    assert scalar(db, "SELECT count(*) FROM research.companies") == 1
    assert scalar(db, "SELECT version_num FROM research.alembic_version") == "0001_foundation"
    with db.begin() as conn:
        conn.execute(text("CREATE TABLE research.unrelated_test_sentinel (id integer)"))
        cfg = Config()
        cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "migrations"))
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "base")
        assert conn.execute(text("SELECT to_regclass('research.companies')")).scalar_one() is None
        assert conn.execute(text("SELECT to_regclass('research.unrelated_test_sentinel')")).scalar_one()
    migrate(db)
    assert scalar(db, "SELECT count(*) FROM research.companies") == 0


def test_unmarked_schema_is_preserved(db):
    with db.begin() as conn:
        conn.execute(text("COMMENT ON SCHEMA research IS NULL"))
    try:
        with pytest.raises(RuntimeError, match="ownership and marker"):
            drop_owned_test_schema(db)
        assert scalar(db, "SELECT version_num FROM research.alembic_version") == "0001_foundation"
    finally:
        with db.begin() as conn:
            conn.execute(text(f"COMMENT ON SCHEMA research IS '{SCHEMA_MARKER}'"))


def test_ingestion_dedup_revision_and_first_observation(db, seeded):
    repo, company = seeded
    original = evidence(company)
    first = repo.ingest_batch("test_fixture", company, [original], cursor="1")[0]
    refetch = original.model_copy(update={"observed_at": original.observed_at + timedelta(minutes=1)})
    assert repo.ingest_batch("test_fixture", company, [refetch], cursor="2", expected_cursor="1") == [first]
    revised = original.model_copy(update={"content": "TEST FIXTURE: Revised report has 11 sample units."})
    second = repo.ingest_batch("test_fixture", company, [revised], cursor="3", expected_cursor="2")[0]
    assert second != first
    assert scalar(db, "SELECT count(*) FROM research.evidence") == 2
    with db.connect() as conn:
        assert conn.execute(text("SELECT observed_at FROM research.evidence WHERE id=:id"),
                            {"id": first}).scalar_one() == original.observed_at
    assert scalar(db, "SELECT cursor FROM research.watermarks") == "3"


def test_ingestion_batch_rolls_back_before_watermark(db, seeded):
    repo, company = seeded
    original = evidence(company)
    repo.ingest_batch("test_fixture", company, [original], cursor="1")
    fresh = evidence(company, provider_id="fixture-2")
    conflicting = original.model_copy(update={"origin": "synthetic"})
    with pytest.raises(GateError, match="provenance"):
        repo.ingest_batch("test_fixture", company, [fresh, conflicting], cursor="2", expected_cursor="1")
    assert scalar(db, "SELECT count(*) FROM research.evidence") == 1
    assert scalar(db, "SELECT cursor FROM research.watermarks") == "1"
    with pytest.raises(GateError, match="watermark"):
        repo.ingest_batch("test_fixture", company, [fresh], cursor="2", expected_cursor="stale")
    assert scalar(db, "SELECT count(*) FROM research.evidence") == 1


def test_ingestion_identity_and_source_policy(db, seeded):
    repo, company = seeded
    with pytest.raises(GateError, match="identity"):
        repo.ingest_batch("test_fixture", uuid4(), [evidence(company)], cursor="1")
    repo.add_source("blocked_fixture")
    with pytest.raises(GateError, match="policy"):
        repo.ingest_batch("blocked_fixture", company,
                          [evidence(company, source_id="blocked_fixture")], cursor="1")
    assert scalar(db, "SELECT count(*) FROM research.watermarks") == 0


@pytest.mark.parametrize("invalid", ["quote", "company", "synthetic", "cutoff", "missing"])
def test_publication_rejects_invalid_evidence_atomically(db, seeded, invalid):
    repo, company = seeded
    item = evidence(company, origin="synthetic" if invalid == "synthetic" else "live")
    eid = repo.ingest_batch("test_fixture", company, [item], cursor="1")[0]
    changes = {}
    if invalid == "company":
        changes["company_id"] = repo.add_company("OTHER", "Other invented company")
    elif invalid == "quote":
        changes["excerpts"] = [Excerpt(evidence_id=eid, quote="Made-up quotation not in source")]
    elif invalid == "cutoff":
        changes["generated_at"] = item.observed_at - timedelta(seconds=1)
    elif invalid == "missing":
        eid = uuid4()
    candidate = review(company, eid, **changes)
    lease = repo.acquire_lease("publisher", uuid4())
    with pytest.raises(GateError):
        repo.publish_review(candidate, lease)
    assert scalar(db, "SELECT count(*) FROM research.reviews") == 0
    assert scalar(db, "SELECT count(*) FROM research.review_evidence") == 0
    assert repo.published() == []


def test_publication_retry_does_not_rewind_and_changed_id_rejected(db, seeded):
    repo, company = seeded
    eid = repo.ingest_batch("test_fixture", company, [evidence(company)], cursor="1")[0]
    lease = repo.acquire_lease("publisher", uuid4())
    first = review(company, eid, generated_at=datetime.now(timezone.utc) - timedelta(minutes=2))
    second = review(company, eid, generated_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    assert repo.publish_review(first, lease) == first.id
    repo.publish_review(second, lease)
    repo.publish_review(first, lease)
    assert repo.published()[0]["id"] == str(second.id)
    assert scalar(db, "SELECT count(*) FROM research.reviews") == 2
    with pytest.raises(GateError, match="changed content"):
        repo.publish_review(first.model_copy(update={"generated_at": second.generated_at}), lease)
    with pytest.raises(GateError, match="newer or equal"):
        repo.publish_review(first.model_copy(update={"id": uuid4()}), lease)


def test_failure_after_review_insert_rolls_back_all_publication(db, seeded):
    repo, company = seeded
    eid = repo.ingest_batch("test_fixture", company, [evidence(company)], cursor="1")[0]
    lease = repo.acquire_lease("publisher", uuid4())
    with db.begin() as conn:
        conn.execute(text("""CREATE FUNCTION research.test_fail_publication() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'intentional test failure'; END $$"""))
        conn.execute(text("""CREATE TRIGGER test_fail BEFORE INSERT ON research.current_reviews
            FOR EACH ROW EXECUTE FUNCTION research.test_fail_publication()"""))
    with pytest.raises(DBAPIError):
        repo.publish_review(review(company, eid), lease)
    assert scalar(db, "SELECT count(*) FROM research.reviews") == 0
    assert scalar(db, "SELECT count(*) FROM research.review_evidence") == 0
    assert repo.published() == []


def test_expired_replaced_and_wrong_name_leases_cannot_publish(db, seeded):
    repo, company = seeded
    eid = repo.ingest_batch("test_fixture", company, [evidence(company)], cursor="1")[0]
    candidate = review(company, eid)
    old = repo.acquire_lease("publisher", uuid4())
    repo.release_lease(old)
    with pytest.raises(GateError, match="expired or replaced"):
        repo.publish_review(candidate, old)
    replacement = repo.acquire_lease("publisher", uuid4())
    assert replacement.token > old.token
    repo.release_lease(old)  # A stale release must not release the replacement.
    with pytest.raises(GateError, match="already held"):
        repo.acquire_lease("publisher", uuid4())
    with pytest.raises(GateError, match="expired or replaced"):
        repo.publish_review(candidate, old)
    other = repo.acquire_lease("collector", uuid4())
    with pytest.raises(GateError):
        repo.publish_review(candidate, other)
    repo.publish_review(candidate, replacement)


def parallel_calls(db, operation, workers=4):
    """Independent pools are essential: the application pool itself has one connection."""
    barrier = Barrier(workers)

    def run(index):
        engine = database_engine(db.url)
        try:
            repo = ResearchRepository(engine)
            barrier.wait(timeout=10)
            try:
                return operation(repo, index)
            except GateError:
                return None
        finally:
            engine.dispose()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(run, range(workers)))


def test_concurrent_lease_has_one_winner(db):
    results = parallel_calls(db, lambda repo, _: repo.acquire_lease("publisher", uuid4()))
    assert sum(result is not None for result in results) == 1
    assert scalar(db, "SELECT count(*) FROM research.leases") == 1


def test_concurrent_budget_reservations_never_exceed_ceiling(db):
    results = parallel_calls(db, lambda repo, _: repo.reserve_budget("fixture", date.today(), 3, 7, uuid4()))
    assert sorted(result for result in results if result is not None) == [3, 6]
    assert scalar(db, "SELECT used FROM research.budgets") == 6
    assert scalar(db, "SELECT count(*) FROM research.reservations") == 2


def test_concurrent_same_budget_request_is_idempotent(db):
    request = uuid4()
    results = parallel_calls(db, lambda repo, _: repo.reserve_budget("fixture", date.today(), 3, 7, request))
    assert results == [3, 3, 3, 3]
    repo = ResearchRepository(db)
    with pytest.raises(GateError, match="different amount"):
        repo.reserve_budget("fixture", date.today(), 4, 7, request)
    with pytest.raises(GateError, match="ceiling differs"):
        repo.reserve_budget("fixture", date.today(), 3, 8, uuid4())
    assert scalar(db, "SELECT count(*) FROM research.reservations") == 1


def test_reader_writer_privilege_boundaries(db, seeded):
    repo, company = seeded
    suffix = uuid4().hex[:12]
    writer, reader = f"stock_agent_w_{suffix}", f"stock_agent_r_{suffix}"
    engines = []
    try:
        with db.begin() as conn:
            for role in (writer, reader):
                conn.exec_driver_sql(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS")
        grant_access(db, writer, reader)
        for role in (writer, reader):
            engine = database_engine(db.url)

            @event.listens_for(engine, "connect")
            def set_role(connection, record, role=role):
                with connection.cursor() as cursor:
                    cursor.execute(f"SET ROLE {role}")
                connection.commit()

            engines.append(engine)
        write_repo, read_repo = (ResearchRepository(engine) for engine in engines)
        eid = write_repo.ingest_batch("test_fixture", company, [evidence(company)], cursor="1")[0]
        write_repo.publish_review(review(company, eid), write_repo.acquire_lease("publisher", uuid4()))
        assert len(read_repo.published()) == 1
        denied = [
            (engines[1], "SELECT content FROM research.evidence"),
            (engines[1], "SELECT * FROM research.legacy_records"),
            (engines[1], "DELETE FROM research.current_reviews"),
            (engines[1], "DELETE FROM research.published_reviews"),
            (engines[0], "UPDATE research.sources SET storage_allowed=false"),
            (engines[0], "UPDATE research.evidence SET origin='live'"),
            (engines[0], "DELETE FROM research.evidence"),
            (engines[0], "CREATE TABLE research.forbidden (id integer)"),
        ]
        for engine, sql in denied:
            with pytest.raises(DBAPIError):
                with engine.begin() as conn:
                    conn.execute(text(sql))
        with pytest.raises(DBAPIError):
            write_repo.add_source("unauthorized", storage_allowed=True)
        assert len(read_repo.published()) == 1
    finally:
        for engine in engines:
            engine.dispose()
        with db.begin() as conn:
            for role in (writer, reader):
                exists = conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname=:name"), {"name": role}).first()
                if exists:
                    conn.exec_driver_sql(f"DROP OWNED BY {role}")
                    conn.exec_driver_sql(f"DROP ROLE {role}")


def test_legacy_import_idempotent_quarantined_and_atomic(db, tmp_path):
    path = tmp_path / "legacy.sqlite3"
    store = Store(path)
    store.save_report(dict(id="demo", generated_at="2026-01-01T00:00:00+00:00", mode="synthetic_demo"))
    store.save_report(dict(id="unknown", generated_at="2026-01-01T00:00:00+00:00", mode="provider_collection"))
    store.close()
    original = path.read_bytes()
    first = import_legacy(db, path)
    assert first["inserted"] == 2
    assert first["live_records_promoted"] == 0
    assert first["classifications"] == {"synthetic": 1, "quarantined": 1}
    assert import_legacy(db, path)["inserted"] == 0
    assert scalar(db, "SELECT count(*) FROM research.evidence") == 0
    assert path.read_bytes() == original
    with db.begin() as conn:
        conn.execute(text("DELETE FROM research.legacy_records WHERE row_key='1'"))
        conn.execute(text("UPDATE research.legacy_records SET content_hash='tampered' WHERE row_key='2'"))
    with pytest.raises(GateError, match="does not match"):
        import_legacy(db, path)
    assert scalar(db, "SELECT count(*) FROM research.legacy_records") == 1
    assert path.read_bytes() == original
