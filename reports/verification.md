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

- `python -m pytest -q`: **38 passed** after the final review. The plotting dependency emits
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

## Final assignment requirements review — 2026-11-06

Checked against the common requirements on page 1 and Pathway C/submission rules
on page 3 of the original assignment brief.

| Requirement | Verified evidence |
| --- | --- |
| Exactly one pathway; real asset, purpose and horizon | Pathway C, MSFT, research objective and ten-session horizon stated in PDF page 1 |
| Dated historical prices and financial text | Yahoo OHLCV, nine original Microsoft earnings releases, publication/availability conventions; dates and direct example URLs now included in PDF |
| At least two technical indicators | SMA20/SMA50 trend plus Wilder RSI14; formulas and verified fixtures |
| At least three identifiable stages | Evidence processing, verification, decision synthesis, then final coded risk veto |
| Structured recommendations, references and uncertainty | Schemas and dated records; PDF distinguishes model interpretations from verified source facts and identifies the source context of a rejected proposal |
| At least two explicit risk rules | Eligibility/validation gate and 25% purchase allocation rule, with no leverage/shorting |
| Multiple historical dates and subsequent outcomes | 26 evaluation decisions; all forward outcomes available; PDF now gives numerical outcomes for three predetermined examples |
| Chronological out-of-sample analysis and baseline | 2023 development, frozen 2024 evaluation, rules and allocation-matched buy-and-hold comparisons |
| Costs, assumptions and limitations | 0/10/25 bp per-side sensitivity; price-return, execution, source-coverage and pretrained-future-knowledge limitations explained |
| Separate programming components and documented local-model interface | Importable ingestion, validation, indicators, evidence, risk, decisions and Ollama components; exact prompts and schemas versioned |
| Reproducible critical/failure tests | 38 passing tests, including missing data, stale sources, NO_TRADE and source-archive reproduction |
| Git code, README, dependencies, example config and fixtures | All present in tracked files; raw/model/helper/PDF files excluded |
| Self-contained 3–5 page English PDF | Regenerated final report has five pages; source facts, dates, URLs and individual outcomes appear in the PDF itself |
| No submitted credentials | Tracked-file credential-pattern scan found no tokens/private keys; environments and local identity/model files are ignored |

The genuine 2024 replay exactly reproduced all original decision records and
portfolio metrics. Report changes add supporting evidence and clarity; they do
not alter decisions, historical returns or the recorded experiment protocol.

An independent source-archive check used only versioned files plus the declared
installed dependencies. Offline sample replay, baseline evaluation and PDF
generation succeeded without raw downloads, Ollama, or `.git`. Review found that
Git metadata was previously assumed present; the small fix now records an honest
unavailable-commit marker for source ZIPs instead of aborting.

The instructor's deadline, submission channel and group policy are communicated
separately and cannot be verified from this brief. Submit the regenerated final
PDF and a repository link containing the final review commit.
