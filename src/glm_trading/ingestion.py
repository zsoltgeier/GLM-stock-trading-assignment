"""Download prices and dated original releases, preserving hashes and requests."""

import importlib.metadata
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests

from .evidence import available_at, text_hash
from .schemas import Source
from .validation import calendar, validate_prices


class ReleaseText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.ignored += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignored = max(0, self.ignored - 1)

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def release_excerpt(html):
    parser = ReleaseText()
    parser.feed(html)
    text = " ".join(" ".join(parser.parts).split())
    start = re.search(r"REDMOND,?\s+Wash", text, re.IGNORECASE)
    if not start:
        raise ValueError("Cannot locate dated release body; inspect source HTML")
    # Fixed opening segment; never select excerpts using price outcomes.
    excerpt = text[start.start():start.start() + 4000]
    if "Microsoft" not in excerpt or "revenue" not in excerpt.lower():
        raise ValueError("Release does not identify Microsoft and revenue")
    return excerpt


def download(config, source_file=Path("data/sources.json")):
    import yfinance as yf

    cal = calendar(config)
    config.prices_path.parent.mkdir(parents=True, exist_ok=True)
    params = dict(tickers=config.ticker, start=config.warmup_start, end=config.data_end,
                  auto_adjust=False, back_adjust=False, actions=True, repair=False,
                  keepna=True, progress=False, threads=False, multi_level_index=False)
    prices = yf.download(**params)
    if prices.empty:
        raise ValueError("Price provider returned no data")
    prices.index = prices.index.tz_localize(None).normalize()
    prices = prices.rename(columns={"Open":"open", "High":"high", "Low":"low",
                                   "Close":"close", "Volume":"volume", "Stock Splits":"split"})
    prices["ticker"] = config.ticker
    prices = prices[["ticker", "open", "high", "low", "close", "volume", "split"]]
    expected = cal.sessions_in_range(config.warmup_start, str(__import__('pandas').Timestamp(config.data_end).date() - __import__('datetime').timedelta(days=1)))
    validate_prices(prices, config.ticker, expected)
    prices.to_csv(config.prices_path, index_label="date")
    now = datetime.now(timezone.utc)
    manifest = {"provider":"Yahoo via yfinance", "retrieved_at":now.isoformat(),
                "parameters":params, "yfinance_version":importlib.metadata.version("yfinance"),
                "sha256":text_hash(config.prices_path.read_text()),
                "price_convention":"Vendor split-adjusted OHLC, no dividend adjustment; price returns only; reject splits in interval"}
    config.prices_path.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2))
    sources = []
    for spec in json.loads(source_file.read_text()):
        response = requests.get(spec["url"], headers={"User-Agent":"GLM-Trading educational research"}, timeout=45)
        response.raise_for_status()
        raw_path = config.evidence_path.parent / f"{spec['source_id']}.html"
        raw_path.write_text(response.text)
        text = release_excerpt(response.text)
        sources.append(Source(**spec, ticker=config.ticker, company=config.company, cik=config.cik,
            available_at=available_at(spec["published_at"], "date", cal), timestamp_precision="date",
            retrieved_at=now, text=text, sha256=text_hash(text)).model_dump(mode="json"))
    config.evidence_path.parent.mkdir(parents=True, exist_ok=True)
    config.evidence_path.write_text(json.dumps(sources, indent=2))
    return len(prices), len(sources)
