import pandas as pd
import pytest

from glm_trading.config import load_config
from glm_trading.evidence import available_at, text_hash
from glm_trading.schemas import Source
from glm_trading.validation import calendar


@pytest.fixture
def config():
    return load_config("config/example.yml")


@pytest.fixture
def cal(config):
    return calendar(config)


@pytest.fixture
def source(config, cal):
    text = "Revenue increased by 10 percent."
    return Source(source_id="release", ticker=config.ticker, company=config.company, cik=config.cik,
        url="https://example.org/release", published_at="2024-01-02", timestamp_precision="date",
        available_at=available_at("2024-01-02", "date", cal), retrieved_at="2026-11-06T00:00:00Z",
        text=text, sha256=text_hash(text))


@pytest.fixture
def prices(cal):
    sessions = cal.sessions_in_range("2022-10-03", "2024-03-01")
    close = pd.Series([100 + i / 10 for i in range(len(sessions))], index=sessions)
    return pd.DataFrame({"ticker":"MSFT", "open":close, "high":close+1,
                         "low":close-1, "close":close, "volume":1000., "split":0.})
