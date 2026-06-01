"""FastAPI application entrypoint (§4.3, §5.3)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from app import __version__
from app.config import settings
from app.database import create_db_and_tables
from app.errors import register_error_handlers
from app.routers import brands, cpus, gpus, meta, smartphones, socs

PREFIX = settings.api_version_prefix

DESCRIPTION = (
    "Open data platform for consumer electronics specs. "
    "Free and open-source. "
    f"Data licensed CC-BY-SA 4.0. Try `GET {PREFIX}/smartphones`."
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Phase 0: create tables directly. Phase 1+ moves to Alembic migrations (§0.5.4).
    create_db_and_tables()
    yield


app = FastAPI(
    title="TechAPI",
    version=__version__,
    description=DESCRIPTION,
    lifespan=lifespan,
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    contact={"name": "TechAPI", "url": "https://techapi.dev"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Attach a request id used in error envelopes and the X-Request-ID header (§17.1)."""
    request_id = f"req_{uuid.uuid4().hex[:16]}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


register_error_handlers(app)

# Versioned resource + operational routers (§7.2).
app.include_router(meta.router, prefix=PREFIX)
app.include_router(brands.router, prefix=PREFIX)
app.include_router(socs.router, prefix=PREFIX)
app.include_router(smartphones.router, prefix=PREFIX)
app.include_router(gpus.router, prefix=PREFIX)
app.include_router(cpus.router, prefix=PREFIX)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "name": "TechAPI",
        "version": __version__,
        "docs": "/scalar",
        "health": f"{PREFIX}/health",
    }


@app.get("/scalar", include_in_schema=False)
def scalar_docs() -> Response:
    """Modern OpenAPI reference UI (§4.1 Scalar)."""
    return get_scalar_api_reference(openapi_url=app.openapi_url or "/openapi.json", title="TechAPI")
