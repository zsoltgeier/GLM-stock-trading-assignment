import pandas as pd
import pytest

from glm_trading.evidence import available_at, eligible_sources, verify_events
from glm_trading.schemas import Events, utc
from glm_trading.validation import validate_prices


def test_good_prices(prices):
    validate_prices(prices, "MSFT", prices.index)


@pytest.mark.parametrize("defect", ["missing", "duplicate", "ticker", "ohlc", "nan", "split"])
def test_bad_prices(prices, defect):
    expected = prices.index.copy()
    if defect == "missing": prices = prices.iloc[1:]
    if defect == "duplicate": prices = pd.concat([prices, prices.iloc[-1:]])
    if defect == "ticker": prices.loc[:, "ticker"] = "OTHER"
    if defect == "ohlc": prices.loc[prices.index[0], "high"] = 1
    if defect == "nan": prices.loc[prices.index[0], "close"] = float("nan")
    if defect == "split": prices.loc[prices.index[0], "split"] = 2
    with pytest.raises(ValueError): validate_prices(prices, "MSFT", expected)


def test_date_only_holiday_and_early_close(cal):
    assert available_at("2024-07-03", "date", cal) == utc("2024-07-05T13:30:00Z")
    assert cal.session_close("2024-07-03") == pd.Timestamp("2024-07-03T17:00:00Z")
    assert available_at("2024-01-02T22:00:00-05:00", "datetime", cal) == utc("2024-01-03T03:00:00Z")
    with pytest.raises(ValueError): utc("2024-01-02T22:00:00")


def test_evidence_cutoff_staleness_and_boundary(source, config, cal):
    assert not eligible_sources([source], "2024-01-02T21:00:00Z", config, cal)
    assert eligible_sources([source], source.available_at, config, cal) == [source]
    boundary = source.available_at + pd.Timedelta(days=120)
    assert eligible_sources([source], boundary, config, cal)
    assert not eligible_sources([source], boundary + pd.Timedelta(seconds=1), config, cal)


def test_future_wrong_identity_does_not_affect_past_input(source, config, cal):
    future = source.model_copy(update={"ticker":"OTHER", "available_at":utc("2025-01-01T00:00:00Z")})
    assert eligible_sources([source, future], source.available_at, config, cal) == [source]
    wrong = source.model_copy(update={"ticker":"OTHER"})
    with pytest.raises(ValueError, match="identity"):
        eligible_sources([wrong], source.available_at, config, cal)


@pytest.mark.parametrize("defect", ["reference", "quote", "ticker"])
def test_claim_validation(source, config, defect):
    event = dict(ticker="MSFT", company=config.company, uncertainty="high", claims=[
        dict(fact="Revenue rose", interpretation="Positive", source_id="release", quote="Revenue increased")])
    if defect == "reference": event["claims"][0]["source_id"] = "future"
    if defect == "quote": event["claims"][0]["quote"] = "profit doubled"
    if defect == "ticker": event["ticker"] = "OTHER"
    with pytest.raises(ValueError): verify_events(Events.model_validate(event), [source], config)
