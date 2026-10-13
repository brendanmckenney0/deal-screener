#!/usr/bin/env python3
"""Field-level eval vs ground truth, money fields weighted 3x.

Usage:  PROVIDER=local python eval/run_eval.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fields import MONEY_FIELDS
from src.pipeline import analyze_pdf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OM_PDFS = {
    "maple_grove": "maple_grove_apartments.pdf",
    "harbor_point": "harbor_point_mixed_use.pdf",
    "ironworks": "ironworks_industrial.pdf",
}

# sale_terms is prose: check key phrases instead of exact match
KEY_PHRASES = {
    "maple_grove": ["$500,000", "60-day", "1031"],
    "harbor_point": ["40%", "$250,000", "45-day"],
    "ironworks": ["$200,000", "30-day", "estoppels"],
}


def norm_text(s):
    return "".join(c.lower() for c in str(s) if c.isalnum())


def num_close(a, b):
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return abs(a - b) <= max(abs(b) * 0.01, 2.0)


def table_close(kind, a, b):
    if isinstance(a, list):  # unit_mix
        if not isinstance(b, list) or len(a) != len(b):
            return False
        return all(
            norm_text(x["unit_type"]) == norm_text(y["unit_type"])
            and x["count"] == y["count"] and num_close(x["avg_rent"], y["avg_rent"])
            for x, y in zip(a, b))
    if isinstance(a, dict):  # expenses
        if not isinstance(b, dict) or set(a) != set(b):
            return False
        return all(num_close(a[k], b[k]) for k in a)
    return False


def field_pass(name, expected, got, om_id):
    """expected: ground-truth entry; got: pipeline field dict."""
    exp_val = expected["value"] if expected else None
    if exp_val is None:
        return got.get("status") == "not_found"
    if got.get("status") != "ok":
        return False
    gv = got["value"]
    if name == "sale_terms":
        blob = norm_text(gv or "")
        return all(norm_text(k) in blob for k in KEY_PHRASES[om_id])
    if isinstance(exp_val, (list, dict)):
        return table_close(name, exp_val, gv)
    if isinstance(exp_val, (int, float)):
        return num_close(exp_val, gv)
    return norm_text(exp_val) == norm_text(gv or "")


def main():
    per_om, misses = {}, []
    tot_w, tot_ok = 0, 0
    for om_id, pdf in OM_PDFS.items():
        gt_path = os.path.join(BASE, "data", "ground_truth", f"{om_id}.json")
        with open(gt_path) as f:
            gt = json.load(f)["fields"]
        res = analyze_pdf(os.path.join(BASE, "data", "oms", pdf))
        w_sum, w_ok = 0, 0
        for name, exp in gt.items():
            w = 3 if name in MONEY_FIELDS else 1
            w_sum += w
            ok_ = field_pass(name, exp, res["fields"].get(name, {}), om_id)
            if ok_:
                w_ok += w
            else:
                misses.append(
                    f"{om_id}.{name}: expected={exp['value']} "
                    f"got={res['fields'].get(name, {}).get('value')} "
                    f"(status={res['fields'].get(name, {}).get('status')})")
        score = w_ok / w_sum if w_sum else 0
        per_om[om_id] = round(score * 100, 1)
        tot_w += w_sum
        tot_ok += w_ok
        print(f"{om_id:14s} {per_om[om_id]:5.1f}%  ({w_ok}/{w_sum} weighted)")
        # reconciliation sanity: print warnings
        for c in res["reconciliation"]:
            if c["status"] == "warn":
                print(f"    WARN {c['check']}: {c['detail']}")
    print(f"{'AGGREGATE':14s} {round(tot_ok/tot_w*100,1):5.1f}%  ({tot_ok}/{tot_w} weighted)")
    if misses:
        print("\nMISSES:")
        for m in misses:
            print("  -", m)
    return 0 if not misses else 1


if __name__ == "__main__":
    sys.exit(main())
