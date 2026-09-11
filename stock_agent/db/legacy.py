"""Read-only legacy inventory; imports go to quarantine, never live research."""
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .models import LegacyRecord
from .repository import GateError, digest

TABLES = {"snapshots", "cache", "seen_filings", "baselines", "events", "reports"}


def inventory(path):
    path = Path(path).resolve(strict=True)
    if path.stat().st_size > 128 * 1024 * 1024:
        raise GateError("Legacy file exceeds the 128 MB import limit")
    wal = Path(str(path) + "-wal")
    if wal.exists() and wal.stat().st_size:
        raise GateError("Checkpoint and close the legacy WAL database before import")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    rows = []
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        available = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"snapshots", "reports"}.issubset(available):
            raise GateError("Not a recognized legacy collector database")
        for table in sorted(TABLES & available):
            for row in connection.execute(f'SELECT rowid AS "_legacy_rowid", * FROM "{table}"'):
                payload = dict(row)
                key = str(payload.pop("_legacy_rowid"))
                classification = "quarantined"
                if table == "reports":
                    try:
                        report = json.loads(payload["payload"])
                        if report.get("mode") == "synthetic_demo":
                            classification = "synthetic"
                    except (ValueError, TypeError, KeyError, AttributeError):
                        pass  # Preserve malformed records in quarantine without promoting them.
                rows.append(dict(archive_id=before, table_name=table, row_key=key,
                                 content_hash=digest(payload), payload=payload, classification=classification))
    finally:
        connection.close()
    if hashlib.sha256(path.read_bytes()).hexdigest() != before:
        raise GateError("Legacy database changed during inventory; close the collector and retry")
    summary = dict(archive_id=before, tables=dict(Counter(r["table_name"] for r in rows)),
                   classifications=dict(Counter(r["classification"] for r in rows)), total=len(rows),
                   live_records_promoted=0)
    return summary, rows


def import_legacy(engine, path):
    summary, rows = inventory(path)
    inserted = 0
    with Session(engine) as session, session.begin():
        for row in rows:
            stmt = insert(LegacyRecord).values(**row).on_conflict_do_nothing().returning(LegacyRecord.row_key)
            if session.scalar(stmt) is not None:
                inserted += 1
            stored = session.scalar(select(LegacyRecord.content_hash).where(
                LegacyRecord.archive_id == row["archive_id"], LegacyRecord.table_name == row["table_name"],
                LegacyRecord.row_key == row["row_key"]))
            if stored != row["content_hash"]:
                raise GateError("Previously imported legacy content does not match")
    return summary | {"inserted": inserted}
