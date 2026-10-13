"""First-pass screening memo shell: facts + gaps only.

Deliberately no investment thesis and no go/no-go — those stay human.
Every figure traces to a cited OM page.
"""

import datetime

from .fields import FIELDS


def _fmt_value(name, value):
    if value is None:
        return "\u26a0 NOT FOUND"
    for f in FIELDS:
        if f["name"] != name:
            continue
        kind = f["kind"]
        if kind == "money":
            return f"${value:,.2f}".rstrip("0").rstrip(".") if isinstance(value, float) else f"${value:,}"
        if kind == "percent":
            return f"{value}%"
        if kind == "number":
            return f"{value:,}"
        if kind == "table" and isinstance(value, list):
            return "; ".join(
                f"{r['unit_type']}: {r['count']} @ ${r['avg_rent']:,.0f}/mo"
                for r in value)
        if kind == "table" and isinstance(value, dict):
            return "; ".join(f"{k}: ${v:,.0f}" for k, v in value.items())
        return str(value)
    return str(value)


def build_memo(result):
    """result: pipeline output dict. Returns markdown string."""
    fields = result["fields"]
    today = datetime.date.today().isoformat()
    prop = fields.get("property_name", {}).get("value") or "Unnamed property"

    lines = [
        f"# First-Pass Screening Memo \u2014 {prop}",
        f"*Generated {today} from {result.get('file', 'uploaded OM')}. "
        "All figures unaudited; verify independently.*",
        "",
        "## Property Snapshot",
        "",
        "| Field | Value | Source |",
        "|---|---|---|",
    ]
    for f in FIELDS:
        name = f["name"]
        r = fields.get(name, {})
        status = r.get("status", "not_found")
        badge = "" if status == "ok" else " \u26a0"
        page = f"p.{r['page']}" if r.get("page") else "\u2014"
        lines.append(f"| {f['label']}{badge} | {_fmt_value(name, r.get('value'))} | {page} |")

    lines += ["", "## Financial Summary", ""]
    for name in ("asking_price", "t12_noi", "proforma_noi", "cap_rate_pct"):
        r = fields.get(name, {})
        label = next(f["label"] for f in FIELDS if f["name"] == name)
        lines.append(f"- **{label}:** {_fmt_value(name, r.get('value'))}")

    lines += ["", "## Gaps & Broker Questions", ""]
    gaps = result.get("gaps", [])
    if gaps:
        for g in gaps:
            flag = "\u26a0 MISSING" if g["status"] == "not_found" else "\u26a0 UNCERTAIN"
            lines.append(f"- [{flag}] **{g['field']}**: {g['question']}")
    else:
        lines.append("- None \u2014 all target fields were extracted with citations.")

    lines += ["", "## Reconciliation Notes", ""]
    for c in result.get("reconciliation", []):
        mark = {"pass": "\u2713", "warn": "\u26a0", "skip": "\u2014"}[c["status"]]
        lines.append(f"- [{mark}] {c['check']}: {c['detail']}")

    lines += [
        "",
        "---",
        "*This is a first-pass screen, not an investment recommendation. "
        "No thesis or go/no-go is included. Every figure above traces to the "
        "cited OM page; \u26a0 marks fields the OM did not state.*",
    ]
    return "\n".join(lines)
