"""FastAPI application: REST API for procurement portals + the web app."""
import logging
import re
import time
import uuid
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import audit, history, logs
from .config import FRONTEND_DIST, MAX_UPLOAD_BYTES, SAMPLES_DIR
from .engine import get_engine
from .pipeline import evidence, expand
from .pipeline.ingest import FetchError, UnsupportedDocument, fetch_url

logs.setup()
log = logging.getLogger("isre.server")
SNAPSHOT_RE = re.compile(r"^[0-9a-f]{16}-\d{1,3}\.png$")

app = FastAPI(
    title="Indian Standards Recommendation Engine",
    version="0.2.0",
    description="SIH PS 26108 prototype. Recommends applicable Indian Standards, allied standards, "
                "current editions and certification requirements for procurement specifications.",
)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """One structured log line per request; unhandled errors are logged with their traceback."""
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    start = time.perf_counter()
    ctx = {"event": "request", "request_id": request_id, "method": request.method, "path": request.url.path,
           "query": request.url.query or None, "client": request.client.host if request.client else None,
           "user_agent": request.headers.get("user-agent")}
    try:
        response = await call_next(request)
    except Exception:
        ctx |= {"status": 500, "duration_ms": round((time.perf_counter() - start) * 1000, 1)}
        log.exception("%s %s -> 500", request.method, request.url.path, extra={"ctx": ctx})
        return JSONResponse({"detail": "Internal server error", "request_id": request_id}, status_code=500,
                            headers={"X-Request-ID": request_id})
    ctx |= {"status": response.status_code, "duration_ms": round((time.perf_counter() - start) * 1000, 1),
            "bytes": int(response.headers.get("content-length", 0)) or None}
    level = (logging.WARNING if response.status_code >= 400
             else logging.DEBUG if request.url.path == "/api/health"  # Docker healthcheck polls every 30 s
             else logging.INFO)
    log.log(level, "%s %s -> %s (%.1f ms)", request.method, request.url.path, response.status_code,
            ctx["duration_ms"], extra={"ctx": ctx})
    response.headers["X-Request-ID"] = request_id
    return response


class RecommendRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=5000, examples=["LED street light 90 W, IP66"])
    top_k: int = Field(5, ge=1, le=10)
    output_language: Literal["en", "hi"] = "en"


class UrlRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2000, examples=["http://localhost:8000/samples/03_engineering_college_hostel.pdf"])
    output_language: Literal["en", "hi"] = "en"


class FeedbackRequest(BaseModel):
    request_id: str = Field(..., max_length=64)
    standard_id: str = Field(..., max_length=64)
    decision: Literal["accept", "reject"]
    comment: str | None = Field(None, max_length=1000)


@app.get("/api/health")
def health():
    eng = get_engine()
    return {"status": "ok", "retrieval_mode": eng.retriever.mode, "dense": eng.retriever.dense.status,
            "standards": len(eng.kb.standards), "edges": len(eng.kb.edges),
            "data_as_of": eng.kb.meta["as_of"], "data_verified": eng.kb.meta.get("verified", False),
            "notice": eng.kb.meta["notice"]}


@app.post("/api/recommend")
def recommend(req: RecommendRequest):
    return get_engine().recommend(req.query, req.top_k, req.output_language)


@app.post("/api/tender/analyse")
async def analyse_tender(request: Request, file: UploadFile = File(...),
                         output_language: Literal["en", "hi"] = Query("en")):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    ctx = {"event": "upload", "request_id": request.state.request_id, "filename": file.filename,
           "size_bytes": len(data), "content_type": file.content_type}
    if len(data) > MAX_UPLOAD_BYTES:
        log.warning("Upload rejected: larger than 10 MB", extra={"ctx": ctx})
        raise HTTPException(413, "File is larger than 10 MB.")
    try:
        result = get_engine().analyse_tender(file.filename or "upload.txt", data, output_language)
    except UnsupportedDocument as exc:
        log.warning("Upload rejected: %s", exc, extra={"ctx": ctx})
        raise HTTPException(415, str(exc))
    _log_tender(result, ctx)
    return result


def _log_tender(result: dict, ctx: dict) -> None:
    log.info("Tender analysed: %s", result["summary"]["status"],
             extra={"ctx": ctx | {"status": result["summary"]["status"], "items": result["summary"]["items"],
                                 "sha256": result["document"]["sha256"], "audit_id": result["request_id"]}})


@app.post("/api/tender/analyse-url")
def analyse_tender_url(req: UrlRequest, request: Request):
    ctx = {"event": "upload", "request_id": request.state.request_id, "url": req.url}
    try:
        name, data = fetch_url(req.url)
        result = get_engine().analyse_tender(name, data, req.output_language, source="link")
    except FetchError as exc:
        log.warning("Link rejected: %s", exc, extra={"ctx": ctx})
        raise HTTPException(422, str(exc))
    except UnsupportedDocument as exc:
        log.warning("Link rejected: %s", exc, extra={"ctx": ctx})
        raise HTTPException(415, str(exc))
    _log_tender(result, ctx | {"filename": name, "size_bytes": len(data)})
    return result


@app.get("/api/stats")
def stats():
    return history.stats()


@app.get("/api/history")
def list_history(limit: int = Query(50, ge=1, le=500), kind: Literal["tender", "search"] | None = None):
    return {"checks": history.list_checks(limit, kind)}


@app.get("/api/history/{entry_id}")
def get_history(entry_id: str):
    result = history.load(entry_id)
    if not result:
        raise HTTPException(404, f"No saved result for check '{entry_id}'.")
    return result


@app.get("/api/snapshots/{name}", include_in_schema=False)
def snapshot(name: str):
    path = evidence.SNAPSHOTS / name
    if not SNAPSHOT_RE.match(name) or not path.exists():
        raise HTTPException(404, "Snapshot not found.")
    # Same name is re-rendered when the document is checked again, so revalidate (ETag) instead of caching blindly.
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-cache"})


DEMO_SAMPLES = ["01_office_complex_construction.pdf", "02_district_hospital_electrification.docx",
                "03_engineering_college_hostel.pdf", "04_regional_office_facility_services.pdf",
                "05_government_school_building.docx", "06_engineering_college_hostel_scanned.pdf",
                "07_district_hospital_presentation.pptx"]
DEMO_QUERIES = ["TMT reinforcement bars Fe 500D for building construction",
                "LED street light 90 W, IP66, aluminium housing",
                "PVC insulated cable as per IS 694:1990",
                "22 carat gold jewellery bangles",
                "Housekeeping services for office building"]


@app.post("/api/demo/seed")
def seed_demo():
    """Run the bundled sample tenders and example searches so the dashboard has real history."""
    eng, done = get_engine(), []
    for name in DEMO_SAMPLES:
        path = SAMPLES_DIR / name
        if path.exists():
            done.append(eng.analyse_tender(name, path.read_bytes(), source="sample")["request_id"])
    for q in DEMO_QUERIES:
        done.append(eng.recommend(q)["request_id"])
    return {"checks_added": len(done)}


@app.get("/api/standards")
def list_standards(domain: str | None = None, category: str | None = None):
    kb = get_engine().kb
    rows = [expand.summary(kb, s) | {"domain": s["domain"]} for s in kb.standards.values()
            if (not domain or s["domain"] == domain) and (not category or s["category"] == category)]
    return {"meta": {k: kb.meta[k] for k in ("as_of", "verified", "domains", "categories")}, "standards": rows}


def _get(sid: str) -> dict:
    s = get_engine().kb.get(sid)
    if not s:
        raise HTTPException(404, f"Unknown standard '{sid}'.")
    return s


@app.get("/api/standards/{standard_id}")
def get_standard(standard_id: str):
    kb, s = get_engine().kb, _get(standard_id)
    return s | {"label": kb.label(s), "version": expand.version(kb, s), "certification": expand.certification(kb, s)}


@app.get("/api/standards/{standard_id}/allied")
def get_allied(standard_id: str):
    s = _get(standard_id)
    return {"standard": standard_id, "allied": expand.allied(get_engine().kb, s["id"])}


@app.post("/api/feedback")
def feedback(req: FeedbackRequest):
    _get(req.standard_id)
    entry = audit.record("feedback", req.model_dump())
    return {"recorded": entry}


@app.get("/api/audit/verify")
def audit_verify():
    return {"intact": audit.verify()}


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Unknown API endpoint.")
        target = (FRONTEND_DIST / path).resolve()
        if path and target.is_file() and FRONTEND_DIST.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")
