import json

import pandas as pd
import pytest
import requests

from glm_trading.config import load_config
from glm_trading.evaluation import run, save_run
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


def test_replay_keeps_original_protocol_and_detects_changed_decisions(tmp_path, monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    cfg = load_config("config/sample.yml").model_copy(update={"output_dir":tmp_path})
    save_run(cfg, Ollama(cfg.llm, cfg.cache_dir, replay=True), "evaluation", replay=True)
    path = tmp_path / "evaluation" / "manifest.json"
    original = json.loads(path.read_text())
    save_run(cfg, Ollama(cfg.llm, cfg.cache_dir, replay=True), "evaluation", replay=True)
    replayed = json.loads(path.read_text())
    assert replayed["created_at"] == original["created_at"]
    assert replayed["git_commit"] == original["git_commit"]
    assert "last_replay_at" in replayed
    decisions_path = path.parent / "decisions.json"
    changed = json.loads(decisions_path.read_text())
    changed[0]["rationale"] = "Deliberately altered saved result"
    decisions_path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="differ"):
        save_run(cfg, Ollama(cfg.llm, cfg.cache_dir, replay=True), "evaluation", replay=True)
    assert json.loads(decisions_path.read_text()) == changed


def test_source_archive_replay_does_not_require_git(tmp_path, monkeypatch):
    import subprocess

    def no_repository(*args, **kwargs):
        raise subprocess.CalledProcessError(128, args[0])

    monkeypatch.setattr(subprocess, "check_output", no_repository)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    cfg = load_config("config/sample.yml").model_copy(update={"output_dir":tmp_path})
    metrics = save_run(cfg, Ollama(cfg.llm, cfg.cache_dir, replay=True), "evaluation", replay=True)
    assert metrics["actions"] == {"BUY":1, "HOLD":2}
    manifest = json.loads((tmp_path / "evaluation" / "manifest.json").read_text())
    assert manifest["git_commit"] == "unavailable (source archive)"
