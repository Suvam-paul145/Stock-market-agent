from datetime import date, datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = {"schema": "research"}
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    symbol: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(Text)


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = {"schema": "research"}
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    storage_allowed: Mapped[bool] = mapped_column(Boolean)
    cloud_allowed: Mapped[bool] = mapped_column(Boolean)


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = {"schema": "research"}
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("research.companies.id"))
    source_id: Mapped[str] = mapped_column(ForeignKey("research.sources.id"))
    provider_id: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    origin: Mapped[str] = mapped_column(Text)


class Watermark(Base):
    __tablename__ = "watermarks"
    __table_args__ = {"schema": "research"}
    source_id: Mapped[str] = mapped_column(ForeignKey("research.sources.id"), primary_key=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("research.companies.id"), primary_key=True)
    cursor: Mapped[str] = mapped_column(Text)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = {"schema": "research"}
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("research.companies.id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB)


class CurrentReview(Base):
    __tablename__ = "current_reviews"
    __table_args__ = {"schema": "research"}
    company_id: Mapped[UUID] = mapped_column(ForeignKey("research.companies.id"), primary_key=True)
    review_id: Mapped[UUID] = mapped_column(ForeignKey("research.reviews.id"))


class Lease(Base):
    __tablename__ = "leases"
    __table_args__ = {"schema": "research"}
    name: Mapped[str] = mapped_column(Text, primary_key=True)
    owner: Mapped[UUID] = mapped_column(Uuid)
    token: Mapped[int] = mapped_column(BigInteger)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = {"schema": "research"}
    bucket: Mapped[str] = mapped_column(Text, primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    ceiling: Mapped[int] = mapped_column(Integer)
    used: Mapped[int] = mapped_column(Integer)


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = {"schema": "research"}
    bucket: Mapped[str] = mapped_column(Text, primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    request_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    amount: Mapped[int] = mapped_column(Integer)


class LegacyRecord(Base):
    __tablename__ = "legacy_records"
    __table_args__ = {"schema": "research"}
    archive_id: Mapped[str] = mapped_column(Text, primary_key=True)
    table_name: Mapped[str] = mapped_column(Text, primary_key=True)
    row_key: Mapped[str] = mapped_column(Text, primary_key=True)
    content_hash: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB)
    classification: Mapped[str] = mapped_column(Text)
