import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import settings
from app.core.error_handler import register_exception_handlers
from app.models.base import Base

logger = settings.log.get_logger(__name__)


@asynccontextmanager
async def lifespan(app_: FastAPI) -> AsyncIterator[None]:
    # Vérifications au démarrage
    logger.info(settings.project_version)
    logger.info(settings.__repr__())

    # Force l'import de tous les modèles (effet de bord = mapping enregistré)
    import app.models as app_models

    _ = app_models

    async with settings.db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Application started successfully")
    yield

    # Cloture de l'application
    logger.info("Shutting down application")


app = FastAPI(
    title=settings.base.project_name,
    version=settings.base.version,
    debug=settings.is_debug,
    lifespan=lifespan,
)

register_exception_handlers(app)


@app.middleware("http")
async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Add request ID to each request for tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    logger.info(
        f"Route: {request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Time: {process_time:.4f}s | "
        f"RequestID: {request_id}"
    )
    return response


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root() -> RedirectResponse:
    return RedirectResponse(url="/docs", status_code=301)
