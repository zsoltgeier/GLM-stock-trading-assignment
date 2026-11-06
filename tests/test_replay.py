import json

import pandas as pd
import pytest
import requests

from glm_trading.config import load_config
from glm_trading.evaluation import run
from glm_trading.llm import Ollama


def test_distributed_fixture_runs_offline_and_reproduces(monkeypatch):
    def offline(*a, **kw): pytest.fail("Offline fixture attempted network access")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setattr(requests, "post", offline)
    monkeypatch.setattr(requests, "get", offline)
    config = load_config("config/sample.yml")
    first = run(config, Ollama(config.llm, config.cache_dir, replay=True))
    second = run(config, Ollama(config.llm, config.cache_dir, replay=True))
    assert first[0] == second[0]
    pd.testing.assert_frame_equal(first[1], second[1])
    assert first[2] == second[2]
    expected = json.loads((config.prices_path.parent / "expected.json").read_text())
    assert [d.action for d in first[0]] == expected["actions"]
    assert first[2]["net_return"] == pytest.approx(expected["net_return"])


def test_invalid_replay_is_not_treated_as_model_success(tmp_path, config):
    model = Ollama(config.llm, tmp_path, replay=True)
    from glm_trading.llm import ModelFailure
    from glm_trading.schemas import Events
    with pytest.raises(ModelFailure, match="cache miss"):
        model.complete("extract_events", {}, Events, lambda e: None)
