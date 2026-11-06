# Data and provenance

`sources.json` lists nine dated original Microsoft earnings releases, from October
2022 through October 2024. `glm-trading download` fetches these releases and MSFT
daily OHLCV into the ignored `data/raw/` directory. It saves source identity,
publication/availability/retrieval dates, request parameters and SHA-256 hashes.
The text input is the first 4,000 characters beginning at the release's REDMOND
dateline; at most the two newest eligible releases are supplied to the model.
Date-only releases become eligible at the following exchange session's open.

Prices come from Yahoo via yfinance with `auto_adjust=False`, actions included,
and repair disabled. Vendor OHLC can still incorporate retrospective split
adjustments. This implementation rejects any nonzero split in the experiment
interval. Dividends are excluded; all strategy and benchmark outputs are price
returns, not total returns. Daily session labels use the XNYS regular-session
calendar (the same US holiday/early-close schedule used here for Nasdaq MSFT).
Record the provider/retrieval limitations in the report. Review source usage terms
before redistributing raw downloads; these files are deliberately unversioned.

`sample/` contains **artificial prices, an artificial release and authored model
responses**, distributed solely for network-free reproduction tests. The MSFT
label exercises identity validation; none of the sample values describe actual
Microsoft results or historical performance. Its request caches were built with
the production adapter, but responses are test fixtures, not LLM output.

Sources: [yfinance download parameters](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html),
[Microsoft investor relations](https://www.microsoft.com/en-us/Investor/earnings/FY-2024-Q1/press-release-webcast).
