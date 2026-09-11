import hashlib
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceInput(StrictModel):
    company_id: UUID
    source_id: str = Field(min_length=1, max_length=100)
    provider_id: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=100_000)
    url: HttpUrl
    published_at: datetime
    observed_at: datetime
    origin: Literal["live", "synthetic"]

    @field_validator("published_at", "observed_at")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timezone-aware dates required")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def chronology(self):
        if self.published_at > self.observed_at or self.observed_at > datetime.now(timezone.utc):
            raise ValueError("Invalid evidence chronology")
        if self.url.scheme != "https" or self.url.username or self.url.password or self.url.query:
            raise ValueError("Evidence URLs must be HTTPS without credentials or query secrets")
        return self

    @property
    def content_hash(self):
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()


class Excerpt(StrictModel):
    evidence_id: UUID
    quote: str = Field(min_length=1, max_length=4000)


class ReviewInput(StrictModel):
    schema_version: Literal[2] = 2
    id: UUID = Field(default_factory=uuid4)
    company_id: UUID
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    kind: Literal["source_excerpts"] = "source_excerpts"
    excerpts: list[Excerpt] = Field(min_length=1, max_length=20)
    conclusion: Literal["Research evidence only; no investment recommendation."] = (
        "Research evidence only; no investment recommendation."
    )

    @field_validator("generated_at")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timezone-aware date required")
        if value > datetime.now(timezone.utc):
            raise ValueError("Future review time")
        return value.astimezone(timezone.utc)


class LeaseToken(StrictModel):
    name: str
    owner: UUID
    token: int
