"""
Entry point de la aplicación AVISADOR.
Ejecutar con: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

import asyncio
import logging
import logging.handlers
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import init_db
from backend.routers import admin, notas
from backend.services.recordatorios import revisar_recordatorios


# ---------------------------------------------------------------------------
# Configuración de logging
# ---------------------------------------------------------------------------

def _configurar_logging():
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler a archivo con rotación (máx 5MB x 3 archivos)
    file_handler = logging.handlers.RotatingFileHandler(
        settings.LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)

    # Handler a consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    root_logger = logging.getLogger("avisador")
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    _configurar_logging()
    logger = logging.getLogger("avisador")
    logger.info("Iniciando AVISADOR...")

    # Crear carpetas de uploads si no existen
    settings.UPLOADS_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    settings.UPLOADS_IMAGENES_DIR.mkdir(parents=True, exist_ok=True)

    # Inicializar base de datos (crea tablas si no existen)
    init_db()
    logger.info("Base de datos lista.")

    # Scheduler de recordatorios (APScheduler)
    scheduler = None
    if settings.RECORDATORIOS_HABILITADO:
        from datetime import datetime

        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        async def _job_recordatorios():
            await asyncio.to_thread(revisar_recordatorios)

        scheduler = AsyncIOScheduler(timezone="UTC")
        scheduler.add_job(
            _job_recordatorios,
            trigger="interval",
            minutes=settings.RECORDATORIO_INTERVALO_MINUTOS,
            id="revisar_recordatorios",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
            next_run_time=datetime.utcnow(),
        )
        scheduler.start()
        logger.info(
            "Scheduler de recordatorios activo — intervalo %s min, avisos %s h",
            settings.RECORDATORIO_INTERVALO_MINUTOS,
            settings.RECORDATORIO_ANTICIPACION_HORAS,
        )

    yield

    if scheduler is not None:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler de recordatorios detenido.")

    logger.info("AVISADOR detenido.")


# ---------------------------------------------------------------------------
# App FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS — permite acceso desde el frontend en desarrollo y desde origen local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción limitar a tu dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Manejador global de errores no controlados
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def manejador_global(request: Request, exc: Exception):
    logger = logging.getLogger("avisador")
    logger.error(f"Error no controlado en {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor. Revisa los logs para más detalles."},
    )


# ---------------------------------------------------------------------------
# Routers de la API
# ---------------------------------------------------------------------------

app.include_router(notas.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


# ---------------------------------------------------------------------------
# Servir archivos estáticos (frontend)
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOADS_DIR = BASE_DIR / "uploads"

if FRONTEND_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# ---------------------------------------------------------------------------
# Arranque directo (python backend/main.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
