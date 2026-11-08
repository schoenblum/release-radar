"""FastAPI application: the API under ``/api/v1``, brand assets and the built frontend."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app import __version__
from app.config import get_settings
from app.database import SessionLocal
from app.middleware import SecurityHeadersMiddleware
from app.routers import (
    auth,
    brand,
    custom_fields,
    data_export,
    lists,
    release_export,
    releases,
    researchers,
    system,
    users,
    writer_counts,
)
from app.routers import (
    settings as settings_router,
)
from app.services.audit import to_json
from app.services.field_patch import FieldConflict
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("release-radar")

settings = get_settings()

STATIC_DIR = Path(__file__).parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"
API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await start_scheduler()
    try:
        yield
    finally:
        await stop_scheduler()


_docs_enabled = not settings.is_production
app = FastAPI(
    title="Release Radar",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url=None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)
app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Report which fields failed, without echoing their values: one may be a password."""
    fields = [
        {"field": ".".join(str(part) for part in error["loc"][1:]), "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        {"detail": "validation_error", "fields": fields},
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


@app.exception_handler(FieldConflict)
async def field_conflict(_: Request, exc: FieldConflict) -> JSONResponse:
    """Someone else changed this field: show the current value so the person can choose."""
    return JSONResponse(
        {
            "detail": "conflict",
            "field": exc.field,
            "current_value": to_json(exc.current_value),
            "current_version": exc.current_version,
            **exc.extra,
        },
        status_code=status.HTTP_409_CONFLICT,
    )


@app.get(f"{API_PREFIX}/health", tags=["health"])
async def health() -> JSONResponse:
    """Answers 503 if the database is unreachable, so a monitor can see the problem."""
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - any failure here means the same thing
        logger.exception("Health check failed: database unreachable")
        return JSONResponse(
            {"status": "degraded", "version": __version__, "detail": "database unreachable"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return JSONResponse({"status": "ok", "version": __version__})


app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(system.router, prefix=API_PREFIX)
app.include_router(settings_router.router, prefix=API_PREFIX)
app.include_router(lists.router, prefix=API_PREFIX)
app.include_router(researchers.router, prefix=API_PREFIX)
app.include_router(releases.router, prefix=API_PREFIX)
app.include_router(release_export.router, prefix=API_PREFIX)
app.include_router(writer_counts.router, prefix=API_PREFIX)
app.include_router(custom_fields.router, prefix=API_PREFIX)
app.include_router(data_export.router, prefix=API_PREFIX)
app.include_router(brand.api_router, prefix=API_PREFIX)
app.include_router(brand.asset_router)

if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False, response_model=None)
async def frontend(full_path: str) -> FileResponse | JSONResponse:
    """Serve the frontend. Unknown paths get ``index.html``, for client-side routes."""
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "not_found"}, status_code=status.HTTP_404_NOT_FOUND)
    # Confirm the target stays inside the static folder, so a crafted path such as
    # "../../.env" cannot read other files.
    static_root = STATIC_DIR.resolve()
    target = (STATIC_DIR / full_path).resolve()
    if full_path and target.is_file() and target.is_relative_to(static_root):
        return FileResponse(target)
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE, headers={"Cache-Control": "no-cache"})
    return JSONResponse(
        {"detail": "frontend_not_built"}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE
    )
