"""Evidence processing → verification → synthesis → final coded risk veto."""

import math

from .evidence import eligible_sources, verify_candidate, verify_events
from .indicators import indicators
from .llm import CacheMiss, ModelFailure
from .risk import veto
from .schemas import Candidate, Decision, Events
from .validation import validate_prices


def decide(prices, sources, session, cal, config, model, current_weight):
    cutoff = cal.session_close(session).to_pydatetime()
    values = {"sma20":None, "sma50":None, "rsi14":None}
    common = dict(decision_id=f"{config.ticker}-{session.date()}", ticker=config.ticker,
                  decision_time=cutoff, horizon_sessions=config.horizon_sessions,
                  uncertainty="high", uncertainty_reason="Insufficient verified evidence",
                  proposed_target_weight=current_weight, evidence_ids=[], indicator_values=values,
                  risk_checks=["POINT_IN_TIME_INPUTS", "IDENTITY_AND_REFERENCES", "MAX_PURCHASE_WEIGHT"])

    def abstain(reason):
        return Decision(**common, action="NO_TRADE", rationale=reason, veto_reasons=[reason])

    try:
        history = prices.loc[config.warmup_start:str(session.date())]
        expected = cal.sessions_in_range(config.warmup_start, session)
        validate_prices(history, config.ticker, expected)
        latest = indicators(history).iloc[-1]
        if not all(math.isfinite(v) for v in latest):
            return abstain("INSUFFICIENT_INDICATOR_HISTORY")
        common["indicator_values"] = {k:float(v) for k, v in latest.items()}
        eligible = eligible_sources(sources, cutoff, config, cal)
        if not eligible:
            return abstain("MISSING_OR_STALE_EVIDENCE")
    except ValueError as exc:
        return abstain("INVALID_DATA: " + str(exc))

    try:
        payload = {"ticker":config.ticker, "company":config.company, "decision_time":cutoff.isoformat(),
                   "sources":[s.model_dump(mode="json") for s in eligible]}
        # Retrieval metadata is provenance, not information available at decision time.
        for source in payload["sources"]:
            source.pop("retrieved_at")
        events = model.complete("extract_events", payload, Events, lambda e: verify_events(e, eligible, config))
        synthesis = {"ticker":config.ticker, "decision_time":cutoff.isoformat(),
                     "verified_events":events.model_dump(mode="json"),
                     "indicators":common["indicator_values"], "current_weight":current_weight,
                     "max_weight":config.max_weight}
        candidate = model.complete("synthesize_decision", synthesis, Candidate,
                                   lambda c: verify_candidate(c, events, cutoff, config))
        reasons = veto(candidate, current_weight, config.max_weight)
        if reasons:
            return abstain("RISK_VETO: " + ",".join(reasons))
        result = {**common, **candidate.model_dump(), "veto_reasons":[]}
        return Decision.model_validate(result)
    except CacheMiss:
        raise
    except ModelFailure as exc:
        return abstain("MODEL_FAILURE: " + str(exc))
