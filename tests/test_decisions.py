import json

import pandas as pd
import pytest
import requests

from glm_trading.decisions import decide
from glm_trading.llm import ModelFailure, Ollama
from glm_trading.risk import veto
from glm_trading.schemas import Candidate, Events


class FixtureModel:
    """Deterministic test double, never used as historical LLM evidence."""
    def complete(self, stage, payload, schema, verify):
        if stage == "extract_events":
            value = dict(ticker=payload["ticker"], company=payload["company"], uncertainty="high",
                claims=[dict(fact="Revenue increased", source_id=payload["sources"][0]["source_id"],
                    quote="Revenue increased", interpretation="Reported growth, not a prediction")])
        else:
            value = dict(ticker=payload["ticker"], decision_time=payload["decision_time"], action="HOLD",
                rationale="Wait", uncertainty="high", uncertainty_reason="Fixture only",
                evidence_ids=["release"], proposed_target_weight=payload["current_weight"])
        value = schema.model_validate(value)
        verify(value)
        return value


def test_future_inputs_do_not_change_decision(prices, source, config, cal):
    day = pd.Timestamp("2024-01-12")
    before = decide(prices, [source], day, cal, config, FixtureModel(), 0)
    changed = prices.copy()
    changed.loc[changed.index > day, "close"] = 99999
    future = source.model_copy(update={"source_id":"future", "published_at":"2024-02-01",
                                       "available_at":pd.Timestamp("2024-02-02T14:30:00Z").to_pydatetime()})
    after = decide(changed, [source, future], day, cal, config, FixtureModel(), 0)
    assert before == after
    assert before.action == "HOLD"


def test_missing_data_and_stale_evidence_abstain(prices, source, config, cal):
    day = pd.Timestamp("2024-01-12")
    assert decide(prices.iloc[1:], [source], day, cal, config, None, 0).action == "NO_TRADE"
    result = decide(prices, [], day, cal, config, None, 0.2)
    assert result.action == "NO_TRADE" and result.proposed_target_weight == 0.2


@pytest.mark.parametrize("action,weight,current", [("BUY",0.5,0), ("SELL",0,0), ("HOLD",0.1,0.2)])
def test_invalid_position_actions(action, weight, current):
    candidate = Candidate(ticker="MSFT", decision_time="2024-01-02T21:00:00Z", action=action,
        rationale="test", uncertainty="high", uncertainty_reason="test", evidence_ids=["release"],
        proposed_target_weight=weight)
    assert veto(candidate, current, 0.25)


def test_ollama_retries_logs_and_replays_offline(tmp_path, config, monkeypatch):
    good = {"ticker":"MSFT", "company":config.company, "uncertainty":"high", "claims":[
        {"fact":"test", "source_id":"release", "quote":"test", "interpretation":"test"}]}
    responses = iter(["not json", json.dumps(good)])
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"message":{"content":next(responses)}}
    monkeypatch.setattr(requests, "post", lambda *a, **kw: Response())
    model = Ollama(config.llm, tmp_path)
    first = model.complete("extract_events", {"date":"2024-01-02"}, Events, lambda e: None)
    assert model.calls[0]["attempts"] == 2
    monkeypatch.setattr(requests, "post", lambda *a, **kw: pytest.fail("Replay used network"))
    replay = Ollama(config.llm, tmp_path, replay=True)
    assert replay.complete("extract_events", {"date":"2024-01-02"}, Events, lambda e: None) == first
    with pytest.raises(ModelFailure, match="cache miss"):
        replay.complete("extract_events", {"date":"2024-01-03"}, Events, lambda e: None)


def test_timeout_becomes_no_trade(tmp_path, config, prices, source, cal, monkeypatch):
    def fail(*a, **kw): raise requests.Timeout("offline")
    monkeypatch.setattr(requests, "post", fail)
    model = Ollama(config.llm, tmp_path)
    result = decide(prices, [source], pd.Timestamp("2024-01-12"), cal, config, model, 0)
    assert result.action == "NO_TRADE"
    assert result.veto_reasons[0].startswith("MODEL_FAILURE")
    assert model.calls[0]["attempts"] == 2
