from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from search_engine import ScianSearchEngine

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
CATALOG_FILE = DATA_DIR / "catalogo_scian_subrama.csv"

app = FastAPI(title="Buscador SAT-SCIAN", version="1.0.0")
engine = ScianSearchEngine(CATALOG_FILE)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=FileResponse)
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/meta")
def meta() -> JSONResponse:
    return JSONResponse(engine.meta)


@app.get("/api/search")
def search(q: str = Query(default="", description="Texto libre del giro SAT o descripción del cliente")) -> JSONResponse:
    return JSONResponse(engine.search(q))
