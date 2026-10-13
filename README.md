# DealScreener — OM Intake & First-Pass Screening Demo

Upload an offering memorandum (OM) PDF. Watch it become structured
underwriting data: every field extracted **with a page citation**, gaps
flagged instead of hallucinated, numbers cross-checked **in code**
(never by the LLM), and a cited first-pass memo shell out the other end.

Built as a portfolio piece demonstrating production-shaped document AI:
extraction → deterministic validation → evaluated behavior, including
deliberate gap cases.

> **All data is fictional.** The three sample OMs are generated from
> constants in `scripts/generate_oms.py`. No real property, broker, or
> market data is used anywhere.

## Architecture

```
┌──────────┐   ┌──────────────┐   ┌──────────────────┐   ┌──────────────┐
│ OM PDF   │──▶│ pypdf text   │──▶│ field extraction │──▶│  guardrails  │
│ (upload) │   │ extraction   │   │ openai | local   │   │  validate +  │
│          │   │ w/ page nos. │   │ JSON + citations │   │  reconcile   │
└──────────┘   └──────────────┘   └──────────────────┘   └──────┬───────┘
                                                              ▼
                                              ┌───────────────────────────┐
                                              │ outputs: normalized JSON, │
                                              │ gap report, memo shell    │
                                              └───────────────────────────┘
```

**Guardrail design** (the core of the concept):
1. **Structured output, NOT_FOUND refusal** — the extractor must return a
   page citation per field or explicitly `not_found`. A missing number is
   a gap, never a guess.
2. **No LLM arithmetic** — reconciliation (unit counts sum, weighted rents,
   expense totals, cap-rate math) runs deterministically in
   `src/guardrails.py`. Mismatches are flagged, never silently fixed.
3. **Amber unsourced fields** — anything without a citation is marked in
   every output surface (UI, JSON, memo).
4. **Memo discipline** — the memo shell contains facts + gaps + broker
   questions only. No thesis, no go/no-go; those stay human.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_oms.py     # build the 3 fictional OMs
PROVIDER=local uvicorn app:app      # no API key needed
# open http://127.0.0.1:8000 — upload a sample OM or use the sample buttons
```

For real extraction quality:
```bash
export OPENAI_API_KEY=...
PROVIDER=openai uvicorn app:app
```

Eval (local mode, no key):
```bash
PROVIDER=local python eval/run_eval.py
```
Current result: **100% weighted field accuracy** across the 3 OMs
(87/87), money-moving fields weighted 3×. The industrial OM's deliberate
gaps (no expense breakdown, no stated cap rate) are correctly returned as
`not_found` — a passing behavior, not a miss.

## The three sample OMs

| OM | Type | Character |
|---|---|---|
| Maple Grove Apartments | 120-unit multifamily, Dayton OH | Clean digital — the happy path |
| Harbor Point | 48-unit + retail mixed-use, Tampa FL | Messy: nested expense table, one scanned-style page |
| Ironworks Industrial Park | 84k SF industrial, Gary IN | Gaps: no expense breakdown, no stated cap rate |

## For clients

This demo is the kernel of a paid pilot: OM + rent roll + T-12 in,
populated Excel in *your* template, gap report, and cited memo shell out
— with every number traceable to a page and a named human reviewer in
the loop. The research behind the design (process, competition, failure
modes) is documented separately; ask about the viability brief.

## Repo layout

```
scripts/generate_oms.py  fictional OM PDFs + ground truth (reproducible)
src/extract.py           PDF -> pages
src/fields.py            target schema
src/providers.py         openai | local extraction
src/guardrails.py        validation + deterministic reconciliation
src/memo.py              first-pass memo shell
src/pipeline.py          orchestration
app.py / static/         FastAPI demo UI
eval/run_eval.py         field-level eval vs ground truth
docs/                    (reserved for client-facing design docs)
```
