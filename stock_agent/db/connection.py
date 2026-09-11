import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url


class DatabaseConfigurationError(ValueError):
    pass


def engine_from_env(*, migration=False):
    name = "STOCK_AGENT_MIGRATION_URL" if migration else "STOCK_AGENT_DATABASE_URL"
    value = os.getenv(name)
    if not value:
        raise DatabaseConfigurationError(f"Set {name} locally; no SQLite fallback is allowed")
    return database_engine(value, os.getenv("STOCK_AGENT_DB_PROFILE", "local"))


def database_engine(value, profile="local"):
    try:
        url = make_url(value)
        if url.drivername not in ("postgres", "postgresql", "postgresql+psycopg"):
            raise ValueError()
        if not url.host or not url.database or not url.username:
            raise ValueError()
        if set(url.query) - {"sslmode", "sslrootcert", "channel_binding"}:
            raise ValueError()
        if profile == "local":
            if url.host not in ("localhost", "127.0.0.1", "::1"):
                raise ValueError()
        elif profile == "production":
            if url.query.get("sslmode") != "verify-full":
                raise ValueError()
        else:
            raise ValueError()
        url = url.set(drivername="postgresql+psycopg")
    except (ValueError, TypeError):
        raise DatabaseConfigurationError("Invalid PostgreSQL configuration; check profile, host and TLS") from None
    return create_engine(url, pool_size=1, max_overflow=0, pool_pre_ping=True,
                         hide_parameters=True, connect_args={"connect_timeout": 5, "prepare_threshold": None})


def migrate(engine, revision="head"):
    from alembic import command
    from alembic.config import Config

    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "migrations"))
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, revision)
