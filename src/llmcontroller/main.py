from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from llmcontroller.api import admin, routes

app = FastAPI(title="LLMController", version="0.1.0")
app.include_router(admin.router)
app.include_router(routes.router)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
