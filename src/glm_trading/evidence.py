"""Dated evidence selection and mechanical checks on model claims."""

import hashlib
import json

import pandas as pd

from .schemas import Source, utc


def text_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def available_at(published_at, precision, cal):
    if precision == "datetime":
        return utc(published_at)
    day = pd.Timestamp(published_at).normalize().tz_localize(None)
    # Date-only publication: strictly following session, including holidays/weekends.
    next_day = day + pd.Timedelta(days=1)
    return cal.session_open(cal.date_to_session(next_day, direction="next")).to_pydatetime()


def load_sources(path):
    sources = [Source.model_validate(s) for s in json.loads(path.read_text())]
    if len({s.source_id for s in sources}) != len(sources):
        raise ValueError("Duplicate evidence IDs")
    for source in sources:
        if text_hash(source.text) != source.sha256:
            raise ValueError(f"Evidence hash mismatch: {source.source_id}")
    return sources


def eligible_sources(sources, cutoff, config, cal):
    cutoff = utc(cutoff)
    lower = cutoff - pd.Timedelta(days=config.max_source_age_days)
    eligible = []
    for source in sources:
        if not lower <= source.available_at <= cutoff:
            continue
        if source.ticker != config.ticker or source.company != config.company or source.cik != config.cik:
            raise ValueError("Evidence company identity mismatch")
        earliest = available_at(source.published_at, source.timestamp_precision, cal)
        if source.available_at < earliest:
            raise ValueError(f"Evidence available before publication: {source.source_id}")
        eligible.append(source)
    # Fixed newest-first order; at most two releases per prompt, irrespective of outcomes.
    return sorted(eligible, key=lambda s: (s.available_at, s.source_id), reverse=True)[:2]


def verify_events(events, sources, config):
    if events.ticker != config.ticker or events.company != config.company:
        raise ValueError("Extracted company identity mismatch")
    lookup = {s.source_id: s for s in sources}
    for claim in events.claims:
        if claim.source_id not in lookup:
            raise ValueError("Invented or ineligible evidence reference")
        normalize = lambda value: " ".join(value.split())
        if normalize(claim.quote) not in normalize(lookup[claim.source_id].text):
            raise ValueError("Unsupported evidence quote")


def verify_candidate(candidate, events, cutoff, config):
    if candidate.ticker != config.ticker or utc(candidate.decision_time) != utc(cutoff):
        raise ValueError("Decision ticker or timestamp mismatch")
    references = {claim.source_id for claim in events.claims}
    if not set(candidate.evidence_ids) <= references:
        raise ValueError("Decision references unverified evidence")
