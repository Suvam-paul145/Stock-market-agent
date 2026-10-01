"""Read local secrets without logging, shell evaluation, or variable interpolation."""
import os
from pathlib import Path


ENV_NAMES = (
    "SEC_USER_AGENT", "APCA_API_KEY_ID", "APCA_API_SECRET_KEY",
    "STOCK_AGENT_DATABASE_URL", "STOCK_AGENT_MIGRATION_URL", "STOCK_AGENT_DB_PROFILE",
)


def load_local_environment(path=".env"):
    if not Path(path).is_file():
        return
    from dotenv import dotenv_values

    # Shell / deployment secrets always take precedence. Never execute file contents.
    values = dotenv_values(path, interpolate=False, encoding="utf-8-sig")
    for name in ENV_NAMES:
        if name not in os.environ and values.get(name):
            os.environ[name] = values[name]
