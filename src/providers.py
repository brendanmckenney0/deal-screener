"""Field extraction providers behind PROVIDER=openai|local.

Local provider: deterministic regex/template extraction tuned to labeled
OM phrasing. Narrow by design — documented as such. It never invents a
value: no match means NOT_FOUND.
"""

import os
import re

from .fields import FIELD_NAMES, not_found, ok

_MONEY = r"\$([\d,]+(?:\.\d{2})?)"


def _parse_money(s):
    return float(s.replace(",", "").replace("$", ""))


def _first_match(pages, patterns, parse=lambda s: s):
    """Try patterns in order across all pages; return (value, page, snippet)."""
    for pat in patterns:
        rx = re.compile(pat)
        for pg in pages:
            m = rx.search(pg["text"])
            if m:
                line = next((ln for ln in pg["text"].splitlines()
                             if m.group(0) in ln), m.group(0))
                return parse(m.group(1)), pg["page"], line.strip()
    return None, None, ""


class LocalProvider:
    """Regex/template extraction. Narrow, deterministic, no API key."""

    name = "local"

    def extract_fields(self, pages):
        out = {}
        out["property_name"] = self._text(pages, "property_name",
                                          [r"Property Name:\s*(.+)"])
        out["address"] = self._text(pages, "address",
                                    [r"Property Address:\s*(.+)"])
        out["total_units"] = self._number(pages, "total_units",
                                          [r"Total Units:\s*(\d+)"])
        out["unit_mix"] = self._unit_mix(pages)
        out["avg_rent"] = self._number(pages, "avg_rent", [
            r"Average Rent:\s*\$([\d,.]+)\s*per month",
            r"Weighted average rent:\s*\$([\d,.]+)\s*per month",
            r"Average rent:\s*\$([\d.]+)\s*per square foot",
        ], parse=_parse_money)
        out["occupancy_pct"] = self._number(pages, "occupancy_pct", [
            r"Occupancy:\s*([\d.]+)%",
            r"\(([\d.]+)% leased\)",
        ], parse=float)
        out["t12_noi"] = self._number(pages, "t12_noi", [
            r"T-?12 Net Operating Income(?:\s*\(NOI\))?:\s*\$([\d,]+)",
        ], parse=_parse_money)
        out["proforma_noi"] = self._number(pages, "proforma_noi", [
            r"[Pp]ro [Ff]orma Net Operating Income \(Year 1\):\s*\$([\d,]+)",
            r"[Pp]ro forma NOI \(Year 1,[^)]*\):\s*\$([\d,]+)",
        ], parse=_parse_money)
        out["asking_price"] = self._number(pages, "asking_price", [
            r"[Aa]sking [Pp]rice:\s*\$([\d,]+)",
            r"[Oo]ffered at\s*\$([\d,]+)",
            r"[Pp]riced at\s*\$([\d,]+)",
        ], parse=_parse_money)
        out["cap_rate_pct"] = self._number(pages, "cap_rate_pct", [
            r"[Cc]ap(?:italization)? [Rr]ate:\s*([\d.]+)%",
        ], parse=float)
        out["expenses_breakdown"] = self._expenses(pages)
        out["total_expenses"] = self._number(pages, "total_expenses", [
            r"[Tt]otal [Oo]perating [Ee]xpenses:\s*\$([\d,]+)",
        ], parse=_parse_money)
        out["sale_terms"] = self._sale_terms(pages)
        # guarantee every schema field is present
        for name in FIELD_NAMES:
            out.setdefault(name, not_found(name))
        return out

    # -- helpers ------------------------------------------------------
    def _text(self, pages, name, patterns):
        for pat in patterns:
            rx = re.compile(pat)
            for pg in pages:
                m = rx.search(pg["text"])
                if m:
                    val = m.group(1).strip()
                    return ok(name, val, pg["page"], m.group(0).strip())
        return not_found(name)

    def _number(self, pages, name, patterns, parse=float):
        val, page, snip = _first_match(pages, patterns, parse)
        if val is None:
            return not_found(name)
        return ok(name, val, page, snip)

    def _unit_mix(self, pages):
        rx = re.compile(
            r"^(.+?)\s*\u2014\s*(\d+)\s*units?\s*\u2014\s*\$([\d,]+)",
            re.MULTILINE)
        rows = []
        hit_page, hit_snip = None, ""
        for pg in pages:
            for m in rx.finditer(pg["text"]):
                # skip scanned rent-roll sample lines ("Unit 101 — ... — Leased")
                if m.group(1).strip().lower().startswith("unit "):
                    continue
                rows.append({"unit_type": m.group(1).strip(),
                             "count": int(m.group(2)),
                             "avg_rent": _parse_money(m.group(3))})
                hit_page = hit_page or pg["page"]
                hit_snip = hit_snip or m.group(0).strip()
        if not rows:
            return not_found("unit_mix")
        return ok("unit_mix", rows, hit_page, hit_snip)

    def _expenses(self, pages):
        # Top-level "Category: $X" lines only: skip indented/bulleted sub-items
        # and known non-expense labels.
        skip_prefixes = (
            "total operating expenses", "effective gross income",
            "gross potential rent", "residential gross potential rent",
            "less:", "other income", "retail income",
            "t-12 net operating income", "pro forma",
            "asking price", "offered at", "priced at",
            "cap rate", "capitalization rate",
            "average rent", "weighted average rent",
            "occupancy", "property name", "property address",
            "total units", "year built",
        )
        cats = {}
        hit_page = None
        for pg in pages:
            for line in pg["text"].splitlines():
                if not line or line[0].isspace():
                    continue
                low = line.strip().lower()
                if low.startswith(skip_prefixes):
                    continue
                m = re.match(r"^([A-Za-z][A-Za-z &/\-()]+):\s*\$([\d,]+)\s*$",
                             line.strip())
                if m:
                    cats[m.group(1).strip()] = _parse_money(m.group(2))
                    hit_page = hit_page or pg["page"]
        if len(cats) < 2:
            # a lone total is not a breakdown
            return not_found("expenses_breakdown")
        snip = "; ".join(f"{k} {v:,.0f}" for k, v in list(cats.items())[:3])
        return ok("expenses_breakdown", cats, hit_page, snip)

    def _sale_terms(self, pages):
        rx = re.compile(r"(?im)^SALE TERMS\s*$")
        for pg in pages:
            m = rx.search(pg["text"])
            if not m:
                continue
            tail = pg["text"][m.end():]
            items = []
            for line in tail.splitlines():
                s = line.strip()
                if not s:
                    if items:
                        break
                    continue
                # extracted bullets carry a bullet/control char prefix
                s = re.sub(r"^[\x00-\x1f\u2022\u2023\u25cf\u00b7\-\*]+\s*", "", s)
                if not s:
                    continue
                # stop at the next heading-like line
                if re.match(r"^[A-Z][A-Z &/()\-]{4,}$", s):
                    break
                items.append(s)
                if len(items) >= 6:
                    break
            if items:
                return ok("sale_terms", " ".join(items), pg["page"],
                          items[0][:120])
        return not_found("sale_terms")


class OpenAIProvider:
    """LLM extraction with structured JSON output and citation discipline."""

    name = "openai"

    SYSTEM = (
        "You extract underwriting fields from a commercial real estate "
        "offering memorandum. Rules:\n"
        "1. Return ONLY JSON: {\"fields\": [{\"name\": str, \"value\": number|string|object|null, "
        "\"page\": int|null, \"status\": \"ok|not_found|uncertain\", \"citation\": str}]}.\n"
        "2. EVERY field needs a page number and a short citation quote, or "
        "status \"not_found\" with value null. NEVER invent a number — a "
        "missing value is not_found, not a guess.\n"
        "3. Do not do arithmetic; report figures exactly as stated.\n"
        "4. unit_mix is a list of {unit_type, count, avg_rent}; "
        "expenses_breakdown is {category: amount} of top-level categories only.\n"
        "Fields: property_name, address, total_units, unit_mix, avg_rent, "
        "occupancy_pct, t12_noi, proforma_noi, asking_price, cap_rate_pct, "
        "expenses_breakdown, total_expenses, sale_terms."
    )

    def extract_fields(self, pages):
        from openai import OpenAI
        client = OpenAI()  # reads OPENAI_API_KEY
        doc = "\n\n".join(
            f"--- PAGE {p['page']} ---\n{p['text'][:4000]}" for p in pages)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self.SYSTEM},
                {"role": "user",
                 "content": f"Extract the underwriting fields.\n\n{doc}"},
            ],
            temperature=0,
        )
        import json as _json
        data = _json.loads(resp.choices[0].message.content)
        out = {}
        for f in data.get("fields", []):
            name = f.get("name")
            if name not in FIELD_NAMES:
                continue
            out[name] = {"value": f.get("value"), "page": f.get("page"),
                         "status": f.get("status", "uncertain"),
                         "citation": str(f.get("citation", ""))[:160]}
        for name in FIELD_NAMES:
            out.setdefault(name, not_found(name))
        return out


def get_provider(name=None):
    name = (name or os.environ.get("PROVIDER", "local")).lower()
    if name == "openai":
        return OpenAIProvider()
    return LocalProvider()
