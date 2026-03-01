"""
Voice Cloner — FastAPI backend
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
from backend.middleware.rate_limit import limiter
from backend.routers import jobs, outputs, synthesize, voices
from backend.services import job_service

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    ensure_dirs()
    job_service._load_jobs_from_disk()

    # Pre-load model in background (non-blocking for startup, loads on first request if not done)
    import asyncio
    import concurrent.futures

    loop = asyncio.get_event_loop()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    async def _preload_model():
        try:
            await loop.run_in_executor(executor, _load_model_sync)
        except Exception as e:
            logger.warning("Model preload failed (will retry on first request): %s", e)

    asyncio.create_task(_preload_model())

    logger.info(
        "Voice Cloner started | engine=%s | data=%s",
        settings.voice_engine,
        settings.data_dir,
    )
    yield
    # Shutdown
    logger.info("Voice Cloner shutting down")


def _load_model_sync():
    from backend.services.model.factory import get_model
    get_model()


app = FastAPI(
    title="Voice Cloner API",
    description="Local-first voice cloning. MIT/Apache-2.0 code. See README for model weight licenses.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
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
    try:
        import torch
        gpu = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if gpu else None
    except ImportError:
        gpu = False
        gpu_name = None

    from backend.services.model.factory import get_model
    try:
        model = get_model()
        engine_loaded = model.is_loaded
        engine_commercial = model.COMMERCIAL_OK
        engine_license = model.LICENSE
    except Exception:
        engine_loaded = False
        engine_commercial = None
        engine_license = None

    return {
        "status": "ok",
        "engine": settings.voice_engine,
        "engine_loaded": engine_loaded,
        "engine_license": engine_license,
        "commercial_ok": engine_commercial,
        "gpu": gpu,
        "gpu_name": gpu_name,
        "denoise": settings.denoise,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
