"""Deterministic final veto and position rules; models cannot override these."""


def veto(candidate, current_weight, max_weight):
    reasons = []
    if candidate.action == "BUY" and not current_weight < candidate.proposed_target_weight <= max_weight:
        reasons.append("POSITION_LIMIT_OR_NONINCREASING_BUY")
    if candidate.action == "SELL" and (current_weight <= 0 or candidate.proposed_target_weight != 0):
        reasons.append("INVALID_SELL")
    if candidate.action in {"HOLD", "NO_TRADE"} and abs(candidate.proposed_target_weight - current_weight) > 0.001:
        reasons.append("INVALID_HOLD_TARGET")
    return reasons
