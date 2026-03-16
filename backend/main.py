"""
Vuclear — FastAPI backend
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.config import ensure_dirs, settings
from backend.logging_setup import configure_logging
from backend.middleware.rate_limit import limiter
from backend.routers import jobs, outputs, synthesize, voices
from backend.services import job_service

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    import concurrent.futures

    # Startup
    ensure_dirs()
    job_service._load_jobs_from_disk()

    logger.info(
        "Vuclear started | engine=%s | data=%s",
        settings.voice_engine,
        settings.data_dir,
    )

    # Pre-load model in a background thread — non-blocking for startup.
    # The factory singleton is thread-safe; a single load is guaranteed.
    # Health reports engine_loading=true until this finishes.
    loop = asyncio.get_running_loop()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="model-preload")

    async def _preload_model():
        try:
            logger.info("Model preload starting in background thread")
            await loop.run_in_executor(executor, _load_model_sync)
            logger.info("Model preload complete")
        except Exception as e:
            logger.warning(
                "Model preload failed (will retry on first synthesis request): %s", e
            )

    loop.create_task(_preload_model())

    yield
    # Shutdown
    executor.shutdown(wait=False)
    logger.info("Vuclear shutting down")


def _load_model_sync():
    from backend.services.model.factory import get_model
    get_model()


app = FastAPI(
    title="Vuclear API",
    description="Creator-first voice cloning and narration. Local-first, fast, with consent at the center.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Routers
app.include_router(voices.router)
app.include_router(synthesize.router)
app.include_router(jobs.router)
app.include_router(outputs.router)


@app.get("/api/v1/health", tags=["health"])
async def health():
    """
    Liveness + readiness endpoint.

    Always returns HTTP 200 as long as the API process is running.
    engine_loaded / engine_loading reflect background model state without
    blocking the response or triggering a load attempt.
    """
    try:
        import torch
        gpu = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if gpu else None
    except ImportError:
        gpu = False
        gpu_name = None

    from backend.services.model.factory import get_model_status
    ms = get_model_status()

    return {
        "status": "ok",
        "engine": settings.voice_engine,
        "engine_loaded": ms["loaded"],
        "engine_loading": ms["loading"],
        "engine_error": ms["error"],
        "engine_license": ms["license"],
        "commercial_ok": ms["commercial_ok"],
        "gpu": gpu,
        "gpu_name": gpu_name,
        "denoise": settings.denoise,
        "data_dir": str(settings.data_dir.resolve()),
        "voices_dir": str(settings.voices_dir.resolve()),
        "jobs_dir": str(settings.jobs_dir.resolve()),
        "outputs_dir": str(settings.outputs_dir.resolve()),
        "logs_dir": str(settings.logs_dir.resolve()),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
