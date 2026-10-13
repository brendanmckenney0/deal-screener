"""Target field schema for OM extraction.

Every extracted field carries: value, page (1-indexed), status
(ok | not_found | uncertain), and a short citation snippet.
"""

FIELDS = [
    {"name": "property_name", "kind": "text", "money": False,
     "label": "Property name"},
    {"name": "address", "kind": "text", "money": False,
     "label": "Property address"},
    {"name": "total_units", "kind": "number", "money": False,
     "label": "Total units"},
    {"name": "unit_mix", "kind": "table", "money": True,
     "label": "Unit mix",
     "desc": "List of {unit_type, count, avg_rent} rows"},
    {"name": "avg_rent", "kind": "money", "money": True,
     "label": "Average rent"},
    {"name": "occupancy_pct", "kind": "percent", "money": False,
     "label": "Occupancy %"},
    {"name": "t12_noi", "kind": "money", "money": True,
     "label": "T-12 NOI"},
    {"name": "proforma_noi", "kind": "money", "money": True,
     "label": "Pro forma NOI (Year 1)"},
    {"name": "asking_price", "kind": "money", "money": True,
     "label": "Asking price"},
    {"name": "cap_rate_pct", "kind": "percent", "money": True,
     "label": "Cap rate %"},
    {"name": "expenses_breakdown", "kind": "table", "money": True,
     "label": "Expense breakdown",
     "desc": "Dict of {category: annual amount}"},
    {"name": "total_expenses", "kind": "money", "money": True,
     "label": "Total operating expenses"},
    {"name": "sale_terms", "kind": "text", "money": False,
     "label": "Sale terms"},
]

MONEY_FIELDS = {f["name"] for f in FIELDS if f["money"]}
FIELD_NAMES = [f["name"] for f in FIELDS]


def not_found(name):
    return {"value": None, "page": None, "status": "not_found",
            "citation": ""}


def ok(name, value, page, citation):
    return {"value": value, "page": page, "status": "ok",
            "citation": citation[:160]}
