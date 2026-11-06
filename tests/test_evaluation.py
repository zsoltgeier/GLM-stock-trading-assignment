import pandas as pd
import pytest

from glm_trading.evaluation import Portfolio, forward_outcomes, run
from glm_trading.schemas import Decision


def test_buy_sell_costs_and_accounting():
    p = Portfolio(10000)
    p.execute("BUY", 0.25, 100, 10, 0.25)
    assert p.weight(100) == pytest.approx(0.25)
    assert p.cash >= 0 and p.shares > 0
    first_cost = p.costs
    shares = p.shares
    p.execute("NO_TRADE", 0, 101, 10, 0.25)
    p.execute("HOLD", 0, 101, 10, 0.25)
    assert p.shares == shares and p.costs == first_cost and p.trades == 1
    p.execute("SELL", 0, 110, 10, 0.25)
    assert p.shares == pytest.approx(0)
    assert p.costs == pytest.approx(first_cost + shares * 110 * .001)
    assert p.cash == pytest.approx(10000 + shares * 10 - p.costs)
    with pytest.raises(ValueError): p.execute("BUY", 0.5, 100, 10, 0.25)


def test_baseline_next_open_and_holdings(prices, config, tmp_path):
    path = tmp_path / "prices.csv"
    prices.to_csv(path, index_label="date")
    cfg = config.model_copy(update={"prices_path":path, "evaluation_start":"2024-01-02", "evaluation_end":"2024-01-19"})
    decisions, ledger, metrics = run(cfg, None, strategy="buy_hold")
    assert decisions[0].action == "BUY"
    assert ledger.shares.iloc[0] == 0
    expected = Portfolio(10000)
    expected.execute("BUY", .25, prices.loc["2024-01-03", "open"], 10, .25)
    assert ledger.shares.iloc[1] == pytest.approx(expected.shares)
    assert metrics["trade_count"] == 1
    assert ledger.shares.iloc[-1] == ledger.shares.iloc[1]


def test_forward_return_is_ten_sessions_not_calendar_days(prices, config, cal):
    decision = Decision(decision_id="test", ticker="MSFT", decision_time="2024-01-12T21:00:00Z",
        horizon_sessions=10, action="HOLD", rationale="test", uncertainty="high", uncertainty_reason="test",
        evidence_ids=[], indicator_values={}, risk_checks=[], veto_reasons=[], proposed_target_weight=0)
    result = forward_outcomes([decision], prices, cal, config).iloc[0]
    assert result.entry_date == "2024-01-16" # MLK holiday on the 15th
    assert result.outcome_date == "2024-01-30"
    assert result.forward_price_return == pytest.approx(prices.loc["2024-01-30","open"] / prices.loc["2024-01-16","open"] - 1)
