"""Small, validated experiment configuration; paths are relative to the repository."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:3b"
    temperature: float = 0
    timeout_seconds: int = Field(default=120, ge=1)
    attempts: int = Field(default=2, ge=1, le=3)


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    company: str
    cik: str
    calendar: str = "XNYS"
    warmup_start: str
    development_start: str
    development_end: str
    evaluation_start: str
    evaluation_end: str
    data_end: str
    decision_interval: int = Field(default=10, ge=1)
    horizon_sessions: int = Field(default=10, ge=1)
    max_source_age_days: int = Field(default=120, ge=1)
    max_weight: float = Field(default=0.25, gt=0, le=1)
    initial_cash: float = Field(default=10000, gt=0)
    cost_bps: float = Field(default=10, ge=0, le=1000)
    prices_path: Path
    evidence_path: Path
    output_dir: Path
    llm: LLMConfig = Field(default_factory=LLMConfig)

    @model_validator(mode="after")
    def chronological(self):
        from datetime import date

        values = [date.fromisoformat(getattr(self, k)) for k in (
            "warmup_start", "development_start", "development_end",
            "evaluation_start", "evaluation_end", "data_end",
        )]
        if not all(a < b for a, b in zip(values, values[1:])):
            raise ValueError("Experiment periods must be strictly chronological")
        return self


def load_config(path: str | Path) -> Config:
    return Config.model_validate(yaml.safe_load(Path(path).read_text()))
