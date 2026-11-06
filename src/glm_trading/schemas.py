"""Records exchanged by the LLM stages; reject extra fields and nonfinite values."""

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Source(Record):
    source_id: str
    ticker: str
    company: str
    cik: str
    url: str
    published_at: str
    available_at: AwareDatetime
    timestamp_precision: Literal["date", "datetime"]
    retrieved_at: AwareDatetime
    text: str = Field(min_length=1)
    sha256: str


class Claim(Record):
    fact: str = Field(min_length=1)
    source_id: str
    quote: str = Field(min_length=1, max_length=180)
    interpretation: str = Field(min_length=1)


class Events(Record):
    ticker: str
    company: str
    claims: list[Claim] = Field(min_length=1, max_length=2)
    uncertainty: Literal["low", "medium", "high"]


class Candidate(Record):
    ticker: str
    decision_time: AwareDatetime
    action: Literal["BUY", "SELL", "HOLD", "NO_TRADE"]
    rationale: str = Field(min_length=1)
    uncertainty: Literal["low", "medium", "high"]
    uncertainty_reason: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    proposed_target_weight: float = Field(ge=0, le=1)


class Decision(Record):
    decision_id: str
    ticker: str
    decision_time: AwareDatetime
    horizon_sessions: int
    action: Literal["BUY", "SELL", "HOLD", "NO_TRADE"]
    rationale: str
    uncertainty: Literal["low", "medium", "high"]
    uncertainty_reason: str
    evidence_ids: list[str]
    indicator_values: dict[str, float | None]
    risk_checks: list[str]
    veto_reasons: list[str]
    proposed_target_weight: float = Field(ge=0, le=1)


def utc(value) -> datetime:
    """Reject ambiguous naive timestamps instead of guessing their timezone."""
    import pandas as pd

    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError("Timestamp must include an explicit timezone")
    return timestamp.tz_convert("UTC").to_pydatetime()
