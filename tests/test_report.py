import re

import pytest

from glm_trading.config import load_config
from glm_trading.evaluation import compare, save_run
from glm_trading.llm import Ollama
from glm_trading.report import generate_report


def test_sample_report_is_five_pages(tmp_path, monkeypatch):
    cfg = load_config("config/sample.yml")
    cfg = cfg.model_copy(update={"output_dir":tmp_path})
    save_run(cfg, Ollama(cfg.llm, cfg.cache_dir, replay=True), "evaluation", replay=True)
    compare(cfg)
    # Keep generated reports out of the source tree during tests.
    monkeypatch.chdir(tmp_path)
    pdf = generate_report(cfg)
    assert len(re.findall(rb"/Type\s*/Page\b", pdf.read_bytes())) == 5
    assert "SYNTHETIC FIXTURE" in pdf.with_suffix(".md").read_text()
