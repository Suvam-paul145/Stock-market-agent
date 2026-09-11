"""Short PostgreSQL transactions; no network/model calls inside transactions."""
import hashlib
import json
import re
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .contracts import EvidenceInput, LeaseToken, ReviewInput
from .models import Budget, Company, CurrentReview, Evidence, Lease, Reservation, Review, Source, Watermark


class GateError(ValueError):
    """Safe domain failure, never includes a connection string or provider payload."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class ResearchRepository:
    def __init__(self, engine):
        self.engine = engine

    def add_company(self, symbol, name, currency="USD"):
        if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", symbol):
            raise GateError("Invalid symbol")
        with Session(self.engine) as session, session.begin():
            session.execute(insert(Company).values(id=uuid4(), symbol=symbol, name=name, currency=currency)
                            .on_conflict_do_nothing(index_elements=[Company.symbol]))
            return session.scalar(select(Company.id).where(Company.symbol == symbol))

    def add_source(self, source_id, *, storage_allowed=False, cloud_allowed=False):
        # Policy configuration requires the migration/admin role; ordinary writer cannot grant eligibility.
        with Session(self.engine) as session, session.begin():
            session.execute(insert(Source).values(id=source_id, storage_allowed=storage_allowed,
                            cloud_allowed=cloud_allowed).on_conflict_do_nothing(index_elements=[Source.id]))

    def ingest_batch(self, source_id, company_id, items, *, cursor, expected_cursor=None):
        """Persist a complete acknowledged batch and compare-and-swap its watermark together."""
        validated = [EvidenceInput.model_validate(item) for item in items]
        if any(i.source_id != source_id or i.company_id != company_id for i in validated):
            raise GateError("Batch identity mismatch")
        ids = []
        with Session(self.engine) as session, session.begin():
            source = session.get(Source, source_id)
            if source is None or not source.storage_allowed:
                raise GateError("Source storage policy is not approved")
            # Serialize initial watermark creation as well as updates for this source/company pair.
            lock_key = f"{source_id}:{company_id}"
            session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": lock_key})
            marker = session.get(Watermark, (source_id, company_id))
            current = marker.cursor if marker else None
            if current != expected_cursor:
                raise GateError("Source watermark changed; reload before retry")
            for item in validated:
                existing = session.scalar(select(Evidence).where(
                    Evidence.source_id == source_id, Evidence.company_id == company_id,
                    Evidence.provider_id == item.provider_id, Evidence.content_hash == item.content_hash))
                if existing:
                    # Re-fetching the same content preserves its first-observed time, never promotes a fixture.
                    if (existing.origin != item.origin or existing.url != str(item.url)
                            or existing.published_at != item.published_at):
                        raise GateError("Conflicting evidence provenance for the same content")
                    ids.append(existing.id)
                    continue
                evidence_id = uuid4()
                session.add(Evidence(id=evidence_id, company_id=company_id, source_id=source_id,
                    provider_id=item.provider_id, content_hash=item.content_hash, content=item.content,
                    url=str(item.url), published_at=item.published_at, observed_at=item.observed_at,
                    origin=item.origin))
                ids.append(evidence_id)
            session.flush()
            session.execute(insert(Watermark).values(source_id=source_id, company_id=company_id, cursor=cursor)
                            .on_conflict_do_update(index_elements=[Watermark.source_id, Watermark.company_id],
                                                   set_={"cursor": cursor}))
        return ids

    def acquire_lease(self, name, owner, ttl_seconds=180):
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 600:
            raise GateError("Lease lifetime must be between 1 and 600 seconds")
        with Session(self.engine) as session, session.begin():
            stmt = insert(Lease).values(name=name, owner=owner, token=1,
                expires_at=func.clock_timestamp() + timedelta(seconds=ttl_seconds))
            stmt = stmt.on_conflict_do_update(index_elements=[Lease.name],
                set_={"owner": owner, "token": Lease.token + 1,
                      "expires_at": func.clock_timestamp() + timedelta(seconds=ttl_seconds)},
                where=Lease.expires_at <= func.clock_timestamp()).returning(Lease.token)
            token = session.scalar(stmt)
            if token is None:
                raise GateError("Research worker lease is already held")
            return LeaseToken(name=name, owner=owner, token=token)

    def release_lease(self, lease):
        with Session(self.engine) as session, session.begin():
            session.execute(update(Lease).where(Lease.name == lease.name, Lease.owner == lease.owner,
                Lease.token == lease.token).values(expires_at=func.clock_timestamp()))

    def reserve_budget(self, bucket, day: date, amount, ceiling, request_id):
        if type(amount) is not int or amount <= 0 or type(ceiling) is not int or ceiling < 0:
            raise GateError("Invalid budget amount")
        with Session(self.engine) as session, session.begin():
            session.execute(insert(Budget).values(bucket=bucket, day=day, ceiling=ceiling, used=0)
                            .on_conflict_do_nothing(index_elements=[Budget.bucket, Budget.day]))
            budget = session.scalar(select(Budget).where(Budget.bucket == bucket, Budget.day == day).with_for_update())
            if budget.ceiling != ceiling:
                raise GateError("Budget ceiling differs from its configured value")
            old = session.get(Reservation, (bucket, day, request_id))
            if old:
                if old.amount != amount:
                    raise GateError("Reservation ID reused with a different amount")
                return budget.used
            if budget.used + amount > budget.ceiling:
                raise GateError("Budget exhausted")
            budget.used += amount
            session.add(Reservation(bucket=bucket, day=day, request_id=request_id, amount=amount))
            return budget.used

    def publish_review(self, review: ReviewInput, lease: LeaseToken):
        """v0.2 accepts attributed source excerpts only; no generated analysis is qualified yet."""
        if lease.name != "publisher":
            raise GateError("Publication requires the publisher lease")
        review = ReviewInput.model_validate(review)
        payload = review.model_dump(mode="json")
        content_hash = digest(payload)
        with Session(self.engine) as session, session.begin():
            held = session.scalar(select(Lease).where(Lease.name == lease.name).with_for_update())
            now = session.scalar(select(func.clock_timestamp()))
            if (held is None or held.owner != lease.owner or held.token != lease.token or held.expires_at <= now):
                raise GateError("Worker lease is expired or replaced")
            old = session.get(Review, review.id)
            if old:
                if old.content_hash != content_hash:
                    raise GateError("Review ID reused with changed content")
                return review.id  # Retry is idempotent and never moves the pointer back.
            evidence_ids = set()
            for excerpt in review.excerpts:
                evidence = session.get(Evidence, excerpt.evidence_id)
                if evidence is None or evidence.company_id != review.company_id:
                    raise GateError("Citation missing or belongs to another company")
                if evidence.origin != "live":
                    raise GateError("Synthetic evidence cannot be published as live research")
                if evidence.observed_at > review.generated_at:
                    raise GateError("Evidence was observed after the review cutoff")
                if excerpt.quote not in evidence.content:
                    raise GateError("Cited excerpt does not exist in the evidence")
                source = session.get(Source, evidence.source_id)
                if source is None or not source.storage_allowed:
                    raise GateError("Source storage policy is no longer approved")
                evidence_ids.add(evidence.id)
            current = session.get(CurrentReview, review.company_id)
            if current:
                previous = session.get(Review, current.review_id)
                if review.generated_at <= previous.generated_at:
                    raise GateError("A newer or equal-time review is already published")
            session.add(Review(id=review.id, company_id=review.company_id,
                               generated_at=review.generated_at, content_hash=content_hash, payload=payload))
            session.flush()
            for evidence_id in evidence_ids:
                session.execute(text("INSERT INTO research.review_evidence VALUES (:r,:e,:c)"),
                                {"r": review.id, "e": evidence_id, "c": review.company_id})
            session.execute(insert(CurrentReview).values(company_id=review.company_id, review_id=review.id)
                .on_conflict_do_update(index_elements=[CurrentReview.company_id], set_={"review_id": review.id}))
        return review.id

    def published(self):
        with self.engine.connect() as connection:
            return [row[0] for row in connection.execute(text("SELECT payload FROM research.published_reviews ORDER BY symbol"))]
