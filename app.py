"""DealScreener demo UI: upload an OM -> extraction + gap report + memo."""

import os
import tempfile

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.pipeline import analyze_pdf

BASE = os.path.dirname(os.path.abspath(__file__))
# DEALSCREENER_DATA lets serverless deployments point at a writable dir
# (e.g. /tmp/...); local dev uses the repo root as before.
DATA_BASE = os.environ.get("DEALSCREENER_DATA", BASE)
OMS_DIR = os.path.join(DATA_BASE, "data", "oms")


def _ensure_samples():
    """Cold-start bootstrap: generate the fictional sample OMs if missing
    (fresh serverless container)."""
    if os.path.isdir(OMS_DIR) and any(
            f.lower().endswith(".pdf") for f in os.listdir(OMS_DIR)):
        return
    from scripts.generate_oms import main as generate_oms
    generate_oms(DATA_BASE)


_ensure_samples()

app = FastAPI(title="DealScreener")
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")),
          name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(BASE, "static", "index.html"))


@app.get("/health")
def health():
    return {"status": "ok",
            "provider": os.environ.get("PROVIDER", "local")}


@app.get("/samples")
def samples():
    if not os.path.isdir(OMS_DIR):
        return {"samples": []}
    return {"samples": sorted(f for f in os.listdir(OMS_DIR)
                              if f.lower().endswith(".pdf"))}


def _run(pdf_path):
    result = analyze_pdf(pdf_path)
    return JSONResponse(result)


@app.post("/analyze")
def analyze(file: UploadFile = File(...)):
    suffix = ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name
    try:
        return _run(tmp_path)
    finally:
        os.unlink(tmp_path)


@app.post("/analyze_sample")
def analyze_sample(name: str):
    safe = os.path.basename(name)
    path = os.path.join(OMS_DIR, safe)
    if not safe.lower().endswith(".pdf") or not os.path.isfile(path):
        return JSONResponse({"error": "unknown sample"}, status_code=404)
    return _run(path)
