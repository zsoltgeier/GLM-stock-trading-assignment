# Verification notes

## Automated verification

Run `python -m pytest -q` from the root in the declared environment. The suite
covers independently calculated SMA/Wilder RSI examples; missing/bad prices;
holidays/early closes; source age/cutoffs; identity/reference/quote validation;
invalid JSON/actions/timestamps; bounded retries/timeouts; allocation/state rules;
cash/share accounting, next-open execution and costs; and a network-disabled
replay with fixed expected results. Changing future prices/documents must not
change earlier decisions. A generated fixture report must contain exactly five
pages and an explicit synthetic-data label.

## Development review — 2023

The first/final scheduled dates (2023-01-03 and 2023-12-15) were selected for manual
inspection before evaluation. Four extracted claims and both synthesis responses
were read against the supplied original-release excerpts. This small descriptive
audit is not a random accuracy estimate.

- The first extraction's two numerical facts agree with the supplied revenue and
  operating-income passages. Synthesis treats reported growth as strong purchase
  support without a calibrated link to subsequent returns.
- The last extraction puts source IDs in both `fact` fields. Supporting quotes
  are present, so mechanical checks pass, but these are not factual statements.
  One interpretation also confuses constant-currency growth with comparison to
  a prior-year growth rate. Exact quote validation misses this semantic failure.
- Final synthesis incorrectly says approximately 34.7% exposure is below 25%
  and proposes a noncompliant purchase. The code vetoes it, retains holdings and
  produces NO_TRADE.
- Low self-reported uncertainty does not establish forecast reliability.

The full development run produced 25 decisions: one BUY, nine HOLD and fifteen
NO_TRADE. All abstentions were risk vetoes. Both LLM stages passed mechanical
checks on all dates, which differs from semantic correctness. One purchase was
executed; its weight drifted above the initial allocation. Settings/prompts were
not tuned to improve historical returns.

## Evaluation interpretation

The 2024 run uses the same numerical settings/prompts after development.
Findings are exploratory: no preregistration, independent asset selection or
confirmatory replication is claimed. The manifest records model digest,
data/prompt hashes and source commit. Timestamp checks cannot eliminate
pretrained future knowledge or retrospective vendor data revisions.

## Completed evaluation and reproduction

- `python -m pytest -q`: **37 passed**. The plotting dependency emits
  pyparsing deprecation warnings; no package requirements are broken.
- Nine original release datelines/ticker identities were checked; historical
  prices contain 585 rows with the expected session coverage.
- Genuine local inference: Qwen 2.5 3B, Ollama 0.40.15. The 2024 run has 26
  decisions, 52 mechanically valid stage calls and no retries. One BUY, one HOLD
  and 24 risk-vetoed NO_TRADE decisions result in one executed purchase.
- Offline replay reproduced every original decision exactly, without contacting
  Ollama, and preserved the original protocol. All 26 forward outcomes are available.
- At 10 bp per side: LLM and allocation-matched buy-and-hold both return 3.53%;
  the rules-only strategy returns −0.29%. This run shows no portfolio advantage
  over matched buy-and-hold. It does not justify a general performance claim.
- Recorded inference totals: 78,858 prompt tokens, 11,892 generated tokens and
  274.7 seconds of summed model-call duration. Local hardware/energy costs are
  not estimated.
- The generated final report contains exactly five pages. Its Markdown and
  machine-readable result snapshot are versioned; the PDF remains ignored.
