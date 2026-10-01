import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal


class ScreenConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    universe_name: str = Field(min_length=1, max_length=160)
    symbols: list[str] = Field(min_length=5, max_length=50)
    benchmark: Literal["SPY"] = "SPY"
    risk_profile: Literal["conservative", "balanced", "aggressive"] = "balanced"
    top_n: Literal[5] = 5
    max_per_sector: int = Field(default=2, ge=1, le=5)
    minimum_price_usd: float = Field(default=5, ge=1, le=1000, allow_inf_nan=False)
    minimum_iex_daily_dollar_volume: float = Field(default=1_000_000, ge=0, allow_inf_nan=False)
    minimum_universe_coverage: float = Field(default=0.8, ge=0.5, le=1, allow_inf_nan=False)
    max_snapshot_age_seconds: int = Field(default=900, ge=60, le=1800)
    sectors: dict[str, str]

    @model_validator(mode="after")
    def validate_symbols(self):
        import re
        if len(set(self.symbols)) != len(self.symbols) or self.benchmark in self.symbols:
            raise ValueError("Unique stock universe excluding the benchmark required")
        if any(not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", s) for s in self.symbols):
            raise ValueError("Invalid stock symbol")
        if set(self.sectors) != set(self.symbols) or any(not v.strip() or len(v) > 80 for v in self.sectors.values()):
            raise ValueError("Every configured stock requires a sector")
        return self


def load_screen_config(path):
    return ScreenConfig.model_validate(json.loads(Path(path).read_text(encoding="utf-8-sig")))
