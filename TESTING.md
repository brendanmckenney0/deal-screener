# Testing DealScreener yourself (Mac)

You don't need to be a developer for this — just follow the steps in
order. Each step tells you what success looks like. Everything runs on
your own machine; nothing is uploaded anywhere.

**You will need:** a Mac with Python 3.10+ (check with
`python3 --version` in Terminal), and this repo cloned or downloaded.

---

## 1. Get the code

```bash
git clone <repo-url> deal-screener   # the private GitHub repo URL
cd deal-screener
```

> If you downloaded a ZIP instead: unzip it, then `cd` into the folder.

**Success:** you see files like `app.py`, `requirements.txt`, `README.md`.

## 2. Create a virtual environment and install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

This takes a minute or two. **Success:** the last lines show
"Successfully installed ..." with no red errors. Your prompt now starts
with `(.venv)`.

> If `python3` isn't found, install Python from
> [python.org](https://www.python.org/downloads/) (3.10 or newer) and
> retry.

## 3. Generate the three sample OMs

```bash
python scripts/generate_oms.py
```

**Success:** you see six "wrote ..." lines — three PDFs under
`data/oms/` and three JSON files under `data/ground_truth/`.

## 4. Start the app

```bash
PROVIDER=local uvicorn app:app
```

**Success:** the last lines read something like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Leave that Terminal window running. `PROVIDER=local` means the demo
uses the built-in template extractor — no API key, no cost, no
internet needed.

> **Port already in use?** If you see `address already in use`, either
> stop the other program or run on a different port:
> `PROVIDER=local uvicorn app:app --port 8001` (then use
> `http://127.0.0.1:8001` below).

## 5. Open the demo

In your browser go to **http://127.0.0.1:8000**.

**Success:** a dark page titled "DealScreener" with an upload box and
three "Sample:" buttons.

## 6. Analyze an OM

Click **Sample: maple_grove_apartments.pdf** (or drag in any of the
PDFs from `data/oms/`).

**What you should see, in order:**
1. A spinner: "Analyzing… extracting fields with citations"
2. **Extracted fields** — a table of ~13 fields. Money fields show
   values like `$1,111,680`; each row shows a page number (`p.5`) and a
   green `ok` badge plus the quoted source text.
3. **Reconciliation** — four deterministic checks (unit counts,
   weighted rent, expense sums, cap-rate math), all `[PASS]`.
4. **Gap report** — for Maple Grove: "None — all target fields extracted
   with citations."
5. **First-pass memo shell** — property snapshot table, financial
   summary, gaps, reconciliation notes, and the disclaimer footer.

Now try **Sample: ironworks_industrial.pdf** — this one has deliberate
gaps. **Success looks different here:** `cap_rate_pct` and
`expenses_breakdown` show amber `⚠ not found` badges, the gap report
lists broker questions ("Request a detailed operating expense breakdown
by category."), and the memo marks those fields. That is the system
working as designed — a missing number is a flagged gap, never a guess.

## 7. Run the eval (optional, still no key needed)

In a **new** Terminal window:

```bash
cd deal-screener
source .venv/bin/activate
PROVIDER=local python eval/run_eval.py
```

**Success:** `AGGREGATE 100.0% (87/87 weighted)` — every field across
all three OMs matches ground truth, with money-moving fields weighted
3×. (Scores are against the generated ground truth in
`data/ground_truth/`.)

## 8. Try real LLM extraction (optional, needs an OpenAI key)

The local extractor is deliberately narrow — it only understands the
phrasing of the sample OMs. For real-world PDFs:

```bash
export OPENAI_API_KEY="sk-..."
PROVIDER=openai uvicorn app:app
```

Then upload any OM-style PDF. Expect it to be slower (10–30s) and to
cost a few cents per document. The guardrails (citations, NOT_FOUND
refusal, reconciliation) apply identically — only the extractor changes.

> Never paste your API key into a chat window or commit the `.env`
> file. Keep it in your shell session only.

## Stopping

Press `Ctrl+C` in the Terminal running uvicorn. To leave the virtual
environment: `deactivate`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `python3: command not found` | Install Python 3.10+ from python.org |
| `pip install` fails on Apple Silicon | Make sure you're on Python 3.10+; all packages ship arm64 wheels |
| `address already in use` | Use `--port 8001` (see step 4) |
| Page won't load | Check the uvicorn Terminal is still running; URL must be `http://127.0.0.1:8000` exactly |
| Upload spins forever | The file must be a PDF; try one of the sample buttons instead |
| `OPENAI_API_KEY` errors | You skipped step 8's `export`; or the key is invalid — check it at platform.openai.com |
