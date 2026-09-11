"""Private, versioned PostgreSQL evidence foundation.

Frozen DDL intentionally does not import mutable application models.
"""
from alembic import op

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE research.companies (
      id uuid PRIMARY KEY, symbol text UNIQUE NOT NULL CHECK (symbol ~ '^[A-Z][A-Z0-9.-]{0,9}$'),
      name text NOT NULL, currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'));
    CREATE TABLE research.sources (
      id text PRIMARY KEY, storage_allowed boolean NOT NULL DEFAULT false,
      cloud_allowed boolean NOT NULL DEFAULT false);
    CREATE TABLE research.evidence (
      id uuid PRIMARY KEY, company_id uuid NOT NULL REFERENCES research.companies,
      source_id text NOT NULL REFERENCES research.sources, provider_id text NOT NULL,
      content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
      content text NOT NULL CHECK (length(content) BETWEEN 1 AND 100000), url text NOT NULL,
      published_at timestamptz NOT NULL, observed_at timestamptz NOT NULL,
      origin text NOT NULL CHECK (origin IN ('live', 'synthetic')),
      CHECK (published_at <= observed_at), UNIQUE (source_id, company_id, provider_id, content_hash),
      UNIQUE (id, company_id));
    CREATE INDEX evidence_company_time ON research.evidence(company_id, published_at DESC);
    CREATE TABLE research.watermarks (
      source_id text NOT NULL REFERENCES research.sources, company_id uuid NOT NULL REFERENCES research.companies,
      cursor text NOT NULL, PRIMARY KEY(source_id, company_id));
    CREATE TABLE research.reviews (
      id uuid PRIMARY KEY, company_id uuid NOT NULL REFERENCES research.companies,
      generated_at timestamptz NOT NULL, content_hash text NOT NULL, payload jsonb NOT NULL,
      UNIQUE (id, company_id));
    CREATE INDEX reviews_company_time ON research.reviews(company_id, generated_at DESC);
    CREATE TABLE research.review_evidence (
      review_id uuid NOT NULL, evidence_id uuid NOT NULL, company_id uuid NOT NULL,
      PRIMARY KEY(review_id, evidence_id),
      FOREIGN KEY(review_id, company_id) REFERENCES research.reviews(id, company_id),
      FOREIGN KEY(evidence_id, company_id) REFERENCES research.evidence(id, company_id));
    CREATE TABLE research.current_reviews (
      company_id uuid PRIMARY KEY REFERENCES research.companies, review_id uuid NOT NULL,
      FOREIGN KEY(review_id, company_id) REFERENCES research.reviews(id, company_id));
    CREATE TABLE research.leases (
      name text PRIMARY KEY, owner uuid NOT NULL, token bigint NOT NULL CHECK(token > 0),
      expires_at timestamptz NOT NULL);
    CREATE TABLE research.budgets (
      bucket text NOT NULL, day date NOT NULL, ceiling integer NOT NULL CHECK(ceiling >= 0),
      used integer NOT NULL DEFAULT 0 CHECK(used >= 0 AND used <= ceiling), PRIMARY KEY(bucket, day));
    CREATE TABLE research.reservations (
      bucket text NOT NULL, day date NOT NULL, request_id uuid NOT NULL, amount integer NOT NULL CHECK(amount > 0),
      PRIMARY KEY(bucket, day, request_id), FOREIGN KEY(bucket, day) REFERENCES research.budgets(bucket, day));
    CREATE TABLE research.legacy_records (
      archive_id text NOT NULL, table_name text NOT NULL, row_key text NOT NULL,
      content_hash text NOT NULL, payload jsonb NOT NULL,
      classification text NOT NULL CHECK(classification IN ('synthetic','quarantined')),
      PRIMARY KEY(archive_id, table_name, row_key));
    CREATE VIEW research.published_reviews AS
      SELECT r.id, r.company_id, c.symbol, r.generated_at, r.payload
      FROM research.current_reviews p JOIN research.reviews r ON p.review_id=r.id
      JOIN research.companies c ON c.id=r.company_id;
    REVOKE ALL ON ALL TABLES IN SCHEMA research FROM PUBLIC;
    """)


def downgrade():
    # Explicit downgrade only; no schema-wide CASCADE that could delete unrelated objects.
    op.execute("""
    DROP VIEW research.published_reviews;
    DROP TABLE research.legacy_records, research.reservations, research.budgets,
      research.leases, research.current_reviews, research.review_evidence,
      research.reviews, research.watermarks, research.evidence, research.sources, research.companies;
    """)
