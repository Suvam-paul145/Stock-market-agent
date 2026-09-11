import argparse
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .access import grant_access
from .connection import engine_from_env, migrate
from .contracts import EvidenceInput
from .legacy import import_legacy, inventory
from .repository import ResearchRepository


def main():
    parser = argparse.ArgumentParser(description="PostgreSQL foundation; no live providers or model calls")
    parser.add_argument("command", choices=["doctor", "migrate", "grant-access", "demo", "import-legacy", "export"])
    parser.add_argument("--path", help="Legacy SQLite input or JSON export destination")
    parser.add_argument("--apply", action="store_true", help="Import into quarantine; default is read-only inventory")
    parser.add_argument("--writer", default="stock_agent_writer")
    parser.add_argument("--reader", default="stock_agent_reader")
    args = parser.parse_args()
    engine = None
    try:
        if args.command in ("import-legacy", "export") and not args.path:
            parser.error("--path is required")
        if args.command == "import-legacy" and not args.apply:
            summary, _ = inventory(args.path)
            print(json.dumps(summary | {"dry_run": True}, indent=2))
            return 0
        admin = args.command in ("migrate", "grant-access", "demo", "import-legacy")
        engine = engine_from_env(migration=admin)
        if args.command == "migrate":
            migrate(engine)
            print("PostgreSQL migrations applied. No live providers enabled.")
        elif args.command == "grant-access":
            grant_access(engine, args.writer, args.reader)
            print("Dedicated writer and published-review reader privileges applied.")
        elif args.command == "doctor":
            with engine.connect() as connection:
                info = connection.execute(text("SELECT current_database(), current_user, current_setting('server_version')")).first()
                ready = connection.scalar(text("SELECT to_regclass('research.published_reviews') IS NOT NULL"))
            print(json.dumps(dict(database=info[0], role=info[1], postgres=info[2], schema_present=ready,
                                  live_data_verified=False, ai_enabled=False), indent=2))
            return 0 if ready else 2
        elif args.command == "demo":
            repo = ResearchRepository(engine)
            company = repo.add_company("DEMO", "Synthetic database fixture")
            repo.add_source("synthetic-fixture", storage_allowed=True)
            stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
            item = EvidenceInput(company_id=company, source_id="synthetic-fixture", provider_id="demo-1",
                content="Synthetic fixture: not a company filing or market observation.",
                url="https://example.com/synthetic", published_at=stamp, observed_at=stamp + timedelta(seconds=1),
                origin="synthetic")
            with engine.connect() as connection:
                cursor = connection.scalar(text("SELECT cursor FROM research.watermarks WHERE source_id=:s AND company_id=:c"),
                                           {"s": item.source_id, "c": company})
            ids = repo.ingest_batch(item.source_id, company, [item], cursor="demo-1", expected_cursor=cursor)
            print(json.dumps(dict(mode="synthetic_demo", evidence_id=str(ids[0]), published=False, requests=0), indent=2))
        elif args.command == "import-legacy":
            print(json.dumps(import_legacy(engine, args.path), indent=2))
        elif args.command == "export":
            data = ResearchRepository(engine).published()
            # Never overwrite an earlier export or accept a hidden overwrite flag.
            with Path(args.path).open("x", encoding="utf-8") as target:
                json.dump({"schema_version": 2, "reviews": data}, target, indent=2, allow_nan=False)
            print(f"Exported {len(data)} published reviews.")
        return 0
    except SQLAlchemyError:
        print("Database operation failed. Check connectivity, migrations and role privileges; credentials were not printed.")
        return 2
    except (OSError, ValueError, ValidationError, sqlite3.Error):
        print("Configuration, input or access validation failed. Check documented setup; no live fallback was used.")
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
