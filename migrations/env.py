from alembic import context

from stock_agent.db.connection import engine_from_env


def run(connection):
    context.configure(connection=connection, version_table_schema="research")
    # Bootstrap only the private schema; all domain changes are versioned below.
    connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS research")
    connection.exec_driver_sql("REVOKE ALL ON SCHEMA research FROM PUBLIC")
    with context.begin_transaction():
        context.run_migrations()


connection = context.config.attributes.get("connection")
if connection is not None:
    run(connection)
else:
    engine = engine_from_env(migration=True)
    try:
        with engine.begin() as connection:
            run(connection)
    finally:
        engine.dispose()
