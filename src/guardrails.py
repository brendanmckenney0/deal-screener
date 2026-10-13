"""Guardrails: validation + deterministic reconciliation.

Principles (from the research brief):
- Structured output with NOT_FOUND refusal; never hallucinate a number.
- Every extracted field needs a page citation.
- The LLM never does arithmetic: all cross-checks run here, in code.
- Mismatches are flagged, never silently "fixed".
- Unsourced fields are marked amber in downstream output.
"""

from .fields import FIELD_NAMES


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def validate(fields):
    """Check structural integrity of an extraction result.

    Returns a list of {"severity": "error|warn", "message": str}.
    """
    issues = []
    for name in FIELD_NAMES:
        f = fields.get(name)
        if not isinstance(f, dict):
            issues.append({"severity": "error",
                           "message": f"field '{name}' missing from result"})
            continue
        if f.get("status") not in ("ok", "not_found", "uncertain"):
            issues.append({"severity": "error",
                           "message": f"field '{name}' has invalid status"})
        if f.get("status") == "ok" and not f.get("page"):
            issues.append({"severity": "warn",
                           "message": f"field '{name}' ok but has no page citation"})
    return issues


def reconcile(fields):
    """Deterministic cross-checks. Returns list of check dicts.

    Each: {"check": str, "status": "pass|warn|skip", "detail": str}.
    """
    checks = []

    def val(name):
        f = fields.get(name, {})
        return f.get("value") if f.get("status") == "ok" else None

    # 1. unit mix counts sum to total units
    mix, total = val("unit_mix"), val("total_units")
    if isinstance(mix, list) and total is not None:
        s = sum(r.get("count", 0) for r in mix)
        checks.append({
            "check": "unit_mix_counts_sum",
            "status": "pass" if s == total else "warn",
            "detail": f"mix sums to {s} units vs stated total {total}",
        })
    else:
        checks.append({"check": "unit_mix_counts_sum", "status": "skip",
                       "detail": "unit mix or total units not available"})

    # 2. weighted avg rent from mix vs stated avg rent (1% tolerance)
    avg = val("avg_rent")
    if isinstance(mix, list) and mix and avg is not None and avg > 100:
        # avg_rent is monthly $/unit here (industrial $/SF excluded by >100 gate)
        w = sum(r["count"] * r["avg_rent"] for r in mix)
        n = sum(r["count"] for r in mix)
        implied = w / n if n else 0
        ok_ = abs(implied - avg) / max(avg, 1) <= 0.01
        checks.append({
            "check": "weighted_avg_rent",
            "status": "pass" if ok_ else "warn",
            "detail": f"mix implies ${implied:,.2f}/mo vs stated ${avg:,.2f}/mo",
        })
    else:
        checks.append({"check": "weighted_avg_rent", "status": "skip",
                       "detail": "not applicable (no unit mix or non-monthly rent)"})

    # 3. expense categories sum to stated total ($1 tolerance)
    brk, tot = val("expenses_breakdown"), val("total_expenses")
    if isinstance(brk, dict) and brk and tot is not None:
        s = sum(brk.values())
        ok_ = abs(s - tot) <= 1.0
        checks.append({
            "check": "expenses_sum",
            "status": "pass" if ok_ else "warn",
            "detail": f"categories sum to ${s:,.0f} vs stated total ${tot:,.0f}",
        })
    else:
        checks.append({"check": "expenses_sum", "status": "skip",
                       "detail": "expense breakdown or total not available"})

    # 4. cap rate vs NOI / price (0.15pp tolerance)
    noi, price, cap = val("t12_noi"), val("asking_price"), val("cap_rate_pct")
    if all(v is not None for v in (noi, price, cap)) and price:
        implied = noi / price * 100
        ok_ = abs(implied - cap) <= 0.15
        checks.append({
            "check": "cap_rate_math",
            "status": "pass" if ok_ else "warn",
            "detail": f"NOI/price implies {implied:.2f}% vs stated {cap:.2f}%",
        })
    else:
        checks.append({"check": "cap_rate_math", "status": "skip",
                       "detail": "NOI, price, or cap rate not available"})

    return checks


BROKER_QUESTIONS = {
    "property_name": "Confirm the legal property name.",
    "address": "Confirm the full property address.",
    "total_units": "Confirm the unit count.",
    "unit_mix": "Request the current unit mix with in-place rents.",
    "avg_rent": "Confirm average in-place rent.",
    "occupancy_pct": "Confirm current occupancy and the as-of date.",
    "t12_noi": "Request the trailing-twelve-month operating statement.",
    "proforma_noi": "Ask for the broker's pro forma assumptions in writing.",
    "asking_price": "Confirm the asking price and whether it is firm.",
    "cap_rate_pct": "Ask what cap rate the pricing is based on (T-12 or pro forma NOI?).",
    "expenses_breakdown": "Request a detailed operating expense breakdown by category.",
    "total_expenses": "Confirm total annual operating expenses.",
    "sale_terms": "Confirm sale terms: earnest money, diligence period, closing timeline.",
}


def gap_report(fields):
    """Missing/uncertain fields -> broker questions."""
    gaps = []
    for name in FIELD_NAMES:
        f = fields.get(name, {})
        if f.get("status") in ("not_found", "uncertain"):
            gaps.append({
                "field": name,
                "status": f.get("status"),
                "question": BROKER_QUESTIONS.get(
                    name, f"Confirm {name} — not stated in the OM."),
            })
    return gaps
