"""Chronological next-open simulation and cost-matched baseline comparison."""

import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

from .decisions import decide
from .evidence import load_sources, text_hash
from .indicators import indicators
from .schemas import Decision
from .validation import calendar, read_prices, validate_prices


@dataclass
class Portfolio:
    cash: float
    shares: float = 0
    costs: float = 0
    turnover: float = 0
    trades: int = 0

    def equity(self, price):
        return self.cash + self.shares * price

    def weight(self, price):
        return self.shares * price / self.equity(price)

    def execute(self, action, target, price, cost_bps, max_weight):
        if not np.isfinite(price) or price <= 0:
            raise ValueError("Invalid execution price")
        rate = cost_bps / 10000
        stock = self.shares * price
        if action == "BUY":
            if not 0 < target <= max_weight:
                raise ValueError("Purchase allocation exceeds risk limit")
            # Target is a fraction of equity AFTER fees; solve N = w*(E-fee).
            desired = target * (self.equity(price) + rate * stock) / (1 + target * rate)
            notional = max(0., desired - stock)
            notional = min(notional, self.cash / (1 + rate))
        elif action == "SELL":
            notional = -stock
        elif action in {"HOLD", "NO_TRADE"}:
            return
        else:
            raise ValueError("Unknown action")
        if abs(notional) < 1e-8:
            return
        fee = abs(notional) * rate
        self.cash -= notional + fee
        self.shares += notional / price
        self.costs += fee
        self.turnover += abs(notional)
        self.trades += 1
        if self.cash < -1e-8 or self.shares < -1e-8:
            raise ValueError("Portfolio cannot borrow or short")


def period_bounds(config, period):
    if period not in {"development", "evaluation"}:
        raise ValueError("Unknown experiment period")
    return getattr(config, period + "_start"), getattr(config, period + "_end")


def run(config, model, period="evaluation", strategy="llm", frozen=None, cost_bps=None, progress=False):
    prices = read_prices(config.prices_path)
    sources = load_sources(config.evidence_path) if strategy == "llm" and frozen is None else []
    cal = calendar(config)
    start, end = period_bounds(config, period)
    sessions = cal.sessions_in_range(start, end)
    # Abort an invalid valuation interval rather than manufacture portfolio returns.
    validate_prices(prices.loc[start:end], config.ticker, sessions)
    schedule = set(sessions[::config.decision_interval])
    portfolio = Portfolio(config.initial_cash)
    cost = config.cost_bps if cost_bps is None else cost_bps
    decisions, ledger = [], []
    pending = None
    lookup = {pd.Timestamp(d.decision_time).tz_convert("America/New_York").tz_localize(None).normalize(): d for d in (frozen or [])}
    for day in sessions:
        bar = prices.loc[day]
        if pending is not None:
            portfolio.execute(pending.action, pending.proposed_target_weight, bar.open, cost, config.max_weight)
            pending = None
        ledger.append({"date":str(day.date()), "equity":portfolio.equity(bar.close), "cash":portfolio.cash,
                       "shares":portfolio.shares, "exposure":portfolio.weight(bar.close),
                       "cumulative_cost":portfolio.costs, "cumulative_turnover":portfolio.turnover,
                       "cumulative_trades":portfolio.trades})
        if day in schedule:
            weight = portfolio.weight(bar.close)
            if frozen is not None:
                if day not in lookup:
                    raise ValueError("Frozen decisions do not cover the declared schedule")
                decision = lookup[day]
            elif strategy == "llm":
                decision = decide(prices, sources, day, cal, config, model, weight)
            else:
                decision = baseline_decision(prices, day, cal, config, strategy, weight, not decisions)
            decisions.append(decision)
            pending = decision
            if progress:
                print(f"{period} {day.date()} {decision.action}", flush=True)
    frame = pd.DataFrame(ledger)
    equity = pd.Series([config.initial_cash] + frame.equity.tolist())
    metrics = {"net_return":portfolio.equity(prices.loc[sessions[-1], "close"]) / config.initial_cash - 1,
               "max_drawdown":float((equity / equity.cummax() - 1).min()),
               "average_exposure":float(frame.exposure.mean()), "trade_count":portfolio.trades,
               "turnover":portfolio.turnover / config.initial_cash, "transaction_cost":portfolio.costs,
               "cost_bps_per_side":cost, "decision_count":len(decisions),
               "actions":dict(Counter(d.action for d in decisions)),
               "abstention_rate":sum(d.action == "NO_TRADE" for d in decisions) / len(decisions),
               "veto_reasons":dict(Counter(r.split(":")[0] for d in decisions for r in d.veto_reasons)),
               "terminal_policy":"mark to last session close; no forced liquidation",
               "returns":"price returns; dividends excluded"}
    return decisions, frame, metrics


def baseline_decision(prices, day, cal, config, strategy, weight, first):
    history = prices.loc[config.warmup_start:str(day.date())]
    values = {"sma20":None, "sma50":None, "rsi14":None}
    action, reason = "HOLD", "Maintain position"
    try:
        validate_prices(history, config.ticker, cal.sessions_in_range(config.warmup_start, day))
        latest = indicators(history).iloc[-1]
        if not np.isfinite(latest).all():
            raise ValueError("Insufficient indicator history")
        values = latest.to_dict()
        if strategy == "buy_hold":
            action = "BUY" if first else "HOLD"
            reason = "Fixed initial allocation, then hold"
        elif latest.sma20 > latest.sma50 and latest.rsi14 < 70 and weight < config.max_weight:
            action, reason = "BUY", "SMA20 > SMA50 and RSI14 < 70"
        elif latest.sma20 < latest.sma50 and weight > 0:
            action, reason = "SELL", "SMA20 < SMA50"
    except ValueError as exc:
        action, reason = "NO_TRADE", str(exc)
    return Decision(decision_id=f"{config.ticker}-{day.date()}", ticker=config.ticker,
        decision_time=cal.session_close(day).to_pydatetime(), horizon_sessions=config.horizon_sessions,
        action=action, rationale=reason, uncertainty="high", uncertainty_reason="Deterministic comparison, no predicted probability",
        evidence_ids=[], indicator_values=values, risk_checks=["VALID_MARKET_DATA", "MAX_PURCHASE_WEIGHT"],
        veto_reasons=[reason] if action == "NO_TRADE" else [],
        proposed_target_weight=config.max_weight if action == "BUY" else (0 if action == "SELL" else weight))


def forward_outcomes(decisions, prices, cal, config):
    rows = []
    for decision in decisions:
        day = pd.Timestamp(decision.decision_time).tz_convert("America/New_York").tz_localize(None).normalize()
        sessions = cal.sessions[cal.sessions > day]
        horizon = decision.horizon_sessions
        row = {"decision_id":decision.decision_id, "entry_date":None, "outcome_date":None,
               "forward_price_return":None, "status":"MISSING_OUTCOME"}
        if len(sessions) > horizon:
            entry, exit = sessions[0], sessions[horizon]
            dates = sessions[:horizon + 1]
            try:
                validate_prices(prices.reindex(dates), config.ticker, dates)
                row.update(entry_date=str(entry.date()), outcome_date=str(exit.date()),
                           forward_price_return=float(prices.loc[exit, "open"] / prices.loc[entry, "open"] - 1), status="OK")
            except ValueError:
                pass
        rows.append(row)
    return pd.DataFrame(rows)


def save_run(config, model, period, replay=False):
    output = config.output_dir / period
    output.mkdir(parents=True, exist_ok=True)
    prompt_dir = Path(__file__).parent / "prompts"
    manifest = {"created_at":datetime.now(timezone.utc).isoformat(), "period":period,
        "mode":"cached historical replay" if replay else "local Ollama historical replay",
        "config":config.model_dump(mode="json"), "model":model.identity,
        "config_hash":text_hash(config.model_dump_json()),
        "prompts":{p.name:text_hash(p.read_text()) for p in sorted(prompt_dir.glob("*.txt"))},
        "prices_sha256":text_hash(config.prices_path.read_text()),
        "evidence_sha256":text_hash(config.evidence_path.read_text()),
        "git_commit":subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "versions":{p:version(p) for p in ["glm-trading", "pandas", "numpy", "pydantic", "exchange-calendars"]},
        "limitations":["Pretrained future knowledge cannot be excluded", "Retrospectively downloaded vendor data",
                       "One selected stock/year, exploratory results", "Price returns exclude dividends"]}
    # Save protocol before executing any model calls.
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    decisions, ledger, metrics = run(config, model, period, progress=True)
    (output / "decisions.json").write_text(json.dumps([d.model_dump(mode="json") for d in decisions], indent=2))
    ledger.to_csv(output / "ledger.csv", index=False)
    (output / "calls.json").write_text(json.dumps(model.calls, indent=2))
    metrics["llm_calls"] = len(model.calls)
    metrics["valid_llm_calls"] = sum(c["valid"] for c in model.calls)
    metrics["extra_attempts"] = sum(c["attempts"] - 1 for c in model.calls)
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2))
    forward_outcomes(decisions, read_prices(config.prices_path), calendar(config), config).to_csv(output / "outcomes.csv", index=False)
    return metrics


def compare(config, period="evaluation"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output = config.output_dir / period
    decisions = [Decision.model_validate(d) for d in json.loads((output / "decisions.json").read_text())]
    comparisons = []
    fig, ax = plt.subplots(figsize=(8, 3.5), layout="constrained")
    for cost in [0, 10, 25]:
        for name in ["llm", "rules", "buy_hold"]:
            _, ledger, metrics = run(config, None, period, strategy=name,
                frozen=decisions if name == "llm" else None, cost_bps=cost)
            comparisons.append({"strategy":name, **metrics})
            if cost == 10:
                ax.plot(pd.to_datetime(ledger.date), ledger.equity, label=name)
                ledger.to_csv(output / f"{name}_ledger.csv", index=False)
    ax.set(ylabel="Portfolio value ($)", title=f"{config.ticker}: price returns, 10 bp per side")
    ax.legend()
    fig.savefig(output / "comparison.png", dpi=160)
    plt.close(fig)
    (output / "comparison.json").write_text(json.dumps(comparisons, indent=2))
    pd.DataFrame([{k:v for k,v in m.items() if not isinstance(v, (dict, list))} for m in comparisons]).to_csv(output / "comparison.csv", index=False)
    return comparisons
