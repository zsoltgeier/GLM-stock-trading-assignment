# LLM-assisted stock analysis — Pathway C

A modular Python program for historical MSFT analysis: dated financial evidence
→ LLM event extraction → verification → synthesis → coded risk veto → simulation.
It produces BUY, SELL, HOLD or NO_TRADE records, baseline comparisons and a
self-contained five-page report. There is no live order execution.

## Setup

From the repository root:

```bash
conda env create -f environment.yml
conda activate glm-trading
python -m pip install --no-deps --no-build-isolation -e .
python -m pytest -q
```

For the environment already created in this checkout, use `conda activate ./.conda`
instead. You can also invoke `.conda/bin/python -m glm_trading.cli …` directly.
No agent framework, database, notebook server or web application is required.

## Offline reproduction

These commands need neither Ollama nor network access:

```bash
glm-trading replay --config config/sample.yml
glm-trading evaluate --config config/sample.yml
glm-trading report --config config/sample.yml
```

Distributed prices, release and responses are **synthetic test fixtures**, not
historical findings or LLM outputs. Fixed expected actions/returns and
network-disabled tests verify reproduction. Results go to `results/sample/`;
the labeled report goes to `reports/sample_report.pdf`.

## Local Ollama and historical analysis

Install [Ollama](https://docs.ollama.com/linux), start `ollama serve` in another
terminal if no server is running, then download the default CPU-friendly model:

```bash
ollama pull qwen2.5:3b
```

This checkout also has an unversioned local Ollama installation/model directory.
To start it after the current server stops, from the repository root:

```bash
OLLAMA_MODELS="$PWD/.local/models" .local/ollama/bin/ollama serve
```

`config/example.yml` records server/model, retries and experiment settings.
Optional `LLM_BASE_URL` and `LLM_MODEL` environment variables override the endpoint
and model; `.env.example` shows their names. The app does not implicitly load
`.env` files. It uses Ollama's native `/api/chat` with JSON schemas, no API key and
no tools. Runs record the actual model digest and Ollama server version.

```bash
glm-trading check
glm-trading download
glm-trading run --period development
# Review development outputs and freeze prompts/config before evaluation.
glm-trading run --period evaluation
glm-trading evaluate --period evaluation
glm-trading report --period evaluation
```

`download` acquires Yahoo/yfinance OHLCV and nine Microsoft earnings releases;
see [data provenance](data/README.md). Reuse existing local downloads by skipping
this command. A live run reuses validated cached calls. Use a different
`output_dir` for independent experiments; do not replace weights under a model
tag mid-run. Retain inputs, manifest and cache together to reproduce a real run:

```bash
glm-trading replay --period evaluation
```

Replay checks recorded config/input hashes, revalidates responses, never contacts
Ollama and fails if a required cache entry is missing. Raw downloads are
unversioned; review source terms before distribution. A local environment export
can be saved with `conda env export --no-builds > environment.resolved.yml`.

## Experiment and assumptions

- MSFT/Microsoft Corporation, CIK 0000789019. The curated source registry must
  match all three identifiers. Release datelines and original-HTML ticker are checked.
- Warm-up from October 2022, development in 2023 and evaluation in 2024, every
  ten exchange sessions. January 2025 prices score late-2024 outcomes only.
- Decisions use the regular-session close, fills the following session's open.
  XNYS handles US holidays/early closes for this US-stock experiment. Date-only
  releases become eligible at the next session's open. Future or older-than-120-day
  sources are excluded before prompts; at most two releases, newest first, with
  fixed 4,000-character excerpts are supplied.
- SMA20/SMA50 use trailing closes. RSI14 uses Wilder smoothing seeded by the first
  14 changes' mean gains/losses: all gains = 100, all losses = 0, flat = 50.
- Data/evidence/schema failures force NO_TRADE. The final gate enforces action
  semantics and a 25% purchase-time allocation limit. No borrowing/shorting;
  HOLD/NO_TRADE retain holdings, whose exposure may drift after purchase.
- Start with $10,000; fractional shares, zero cash interest, no forced final sale.
  Cost: 10 bp per executed side (5 bp fees + 5 bp slippage). Sensitivity uses
  0/10/25 bp and frozen LLM actions/targets rather than new model decisions.
- Rules baseline: buy when SMA20>SMA50 and RSI14<70, sell an existing position
  when SMA20<SMA50, otherwise hold. Buy-and-hold begins with 25% stock/75% cash.
  Both share price/execution/allocation conventions; neither requires text.
- Explicit vendor adjustment flags, no dividends: all figures are price returns.
  Splits inside the interval require manual review and are rejected. Missing
  valuation sessions abort evaluation rather than inventing flat returns.

The subsequent ten-session open-to-open stock return in `outcomes.csv` is a
diagnostic, separate from portfolio returns. Facts, interpretations and uncertainty
have separate fields. Exact quotes do not prove semantic correctness; manual
review remains necessary. Dated inputs cannot remove future knowledge already
present in pretrained weights. Findings are exploratory, not a claim of clean
historical model knowledge or general trading performance.

## Outputs and submission

`results/historical/{development,evaluation}/` holds the pre-run manifest,
decisions, daily cash/share ledger, outcomes, call index, metrics, baseline/cost
comparisons and chart. `results/historical/cache/` preserves rendered prompts,
schemas, raw responses and attempt errors. Keys include model identity and the
complete dated request.

The report command builds `reports/final_report.pdf` and its Markdown content,
`reports/report.md`. Its five pages include the objective, sources/dates, method,
prompts, indicators, risk controls, examples, evaluation, tests, results and
limitations. [Verification notes](reports/verification.md) record test/audit
observations. Review the PDF and the instructor's separate deadline, channel and
group policy before submitting.

Git contains assignment source, dependencies, config, prompts, tests, artificial
fixtures and report text. PDFs, the brief/plan, environments, model files,
credentials, raw downloads and generated run caches stay unversioned.

## Source layout

`ingestion.py`, `validation.py`, `indicators.py`, `evidence.py`, `llm.py`, `risk.py`
and `decisions.py` implement separate components. `evaluation.py` implements
portfolio/baseline analysis, `report.py` creates reports, and `cli.py` exposes the
commands. Tests cover calculations, failures, cutoffs, accounting and reproduction.

Interface references: [Ollama chat](https://docs.ollama.com/api/chat),
[structured outputs](https://docs.ollama.com/capabilities/structured-outputs),
[exchange calendars](https://github.com/gerrymanoim/exchange_calendars),
[yfinance download](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html).
