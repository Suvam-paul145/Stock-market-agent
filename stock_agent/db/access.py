"""Explicit admin step: grant privileges to already-created, dedicated roles."""
import re


def grant_access(engine, writer, reader):
    for name in (writer, reader):
        if not re.fullmatch(r"stock_agent_[a-z][a-z0-9_]{0,40}", name):
            raise ValueError("Use a dedicated stock_agent_ role name")
    if writer == reader:
        raise ValueError("Writer and reader must be separate roles")
    with engine.begin() as connection:
        for name in (writer, reader):
            role = connection.exec_driver_sql(
                "SELECT rolsuper, rolcreaterole, rolcreatedb, rolbypassrls FROM pg_roles WHERE rolname=%s", (name,)
            ).first()
            if role is None or any(role):
                raise ValueError("Roles must exist and have no elevated cluster privileges")
            # Avoid implicitly changing an unrelated, privileged/member role into an app credential.
            if connection.exec_driver_sql("SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member WHERE r.rolname=%s", (name,)).first():
                raise ValueError("Dedicated app roles must not inherit other roles")
            if connection.exec_driver_sql("""SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                JOIN pg_roles r ON r.oid=c.relowner WHERE n.nspname='research' AND r.rolname=%s""", (name,)).first():
                raise ValueError("Application roles must not own research tables or views")
        quoted_writer = connection.dialect.identifier_preparer.quote(writer)
        quoted_reader = connection.dialect.identifier_preparer.quote(reader)
        for role in (quoted_writer, quoted_reader):
            connection.exec_driver_sql(f"REVOKE ALL ON ALL TABLES IN SCHEMA research FROM {role}")
            connection.exec_driver_sql(f"REVOKE ALL ON SCHEMA research FROM {role}")
            connection.exec_driver_sql(f"GRANT USAGE ON SCHEMA research TO {role}")
        connection.exec_driver_sql(f"GRANT SELECT ON research.published_reviews TO {quoted_reader}")
        connection.exec_driver_sql(f"""GRANT SELECT ON research.companies, research.sources, research.evidence,
            research.watermarks, research.reviews, research.review_evidence, research.current_reviews,
            research.leases, research.budgets, research.reservations TO {quoted_writer}""")
        connection.exec_driver_sql(f"""GRANT INSERT ON research.companies, research.evidence, research.watermarks,
            research.reviews, research.review_evidence, research.current_reviews,
            research.leases, research.budgets, research.reservations TO {quoted_writer}""")
        connection.exec_driver_sql(f"""GRANT UPDATE ON research.watermarks, research.current_reviews,
            research.leases, research.budgets TO {quoted_writer}""")
        # No owner role, DDL, source-policy changes, DELETE, legacy archives or source-body access for reader.
