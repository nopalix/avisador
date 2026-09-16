"""
Router de notas — CRUD completo para el sistema AVISADOR.

Endpoints:
  POST   /notas/           Crear nota (multipart/form-data con audio/imagen opcional)
  GET    /notas/           Listar notas con filtros y paginación
  GET    /notas/{id}       Obtener una nota por ID
  PATCH  /notas/{id}       Actualizar campos de una nota
  DELETE /notas/{id}       Eliminar una nota
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

import aiofiles

from backend.config import settings
from backend.database import get_db
from backend.models import Nota
from backend.schemas import NotaCreate, NotaListResponse, NotaResponse, NotaUpdate

logger = logging.getLogger("avisador")

router = APIRouter(prefix="/notas", tags=["notas"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _timestamp_nombre(nombre_original: str) -> str:
    """Genera nombre único con timestamp para evitar colisiones."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    ext = Path(nombre_original).suffix
    return f"{ts}{ext}"


async def _guardar_archivo(upload: UploadFile, carpeta: Path) -> str:
    """Guarda un UploadFile en disco y devuelve la ruta relativa."""
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = _timestamp_nombre(upload.filename or "archivo")
    ruta_abs = carpeta / nombre
    async with aiofiles.open(ruta_abs, "wb") as f:
        contenido = await upload.read()
        await f.write(contenido)
    return str(ruta_abs.relative_to(settings.UPLOADS_DIR.parent))


def _ejecutar_notificaciones(nota: Nota):
    """
    Ejecuta en BackgroundTask todas las integraciones habilitadas.
    Cada servicio verifica internamente si está habilitado.
    """
    try:
        if settings.EMAIL_HABILITADO:
            from backend.services.email_service import enviar_email_nota
            enviar_email_nota(nota)
    except Exception as e:
        logger.error(f"Error enviando email para nota {nota.id}: {e}")

    try:
        if settings.TELEGRAM_HABILITADO:
            from backend.services.telegram_service import enviar_telegram_nota
            enviar_telegram_nota(nota)
    except Exception as e:
        logger.error(f"Error enviando Telegram para nota {nota.id}: {e}")

    try:
        if settings.CALENDAR_HABILITADO:
            from backend.services.calendar_service import crear_evento_calendario
            crear_evento_calendario(nota)
    except Exception as e:
        logger.error(f"Error creando evento Calendar para nota {nota.id}: {e}")


# ---------------------------------------------------------------------------
# POST /notas/ — Crear nota
# ---------------------------------------------------------------------------

@router.post("/", response_model=NotaResponse, status_code=status.HTTP_201_CREATED)
async def crear_nota(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    asunto: str = Form(..., description="Objetivo de la tarea"),
    motivo: str = Form(..., description="Justificación de la tarea"),
    dependencias: str = Form(..., description="Lista JSON de dependencias, ej: ['internet','laptop']"),
    lugar: Optional[str] = Form(None),
    f_inicio: Optional[datetime] = Form(None),
    limite: Optional[datetime] = Form(None),
    audio: Optional[UploadFile] = File(None),
    imagen: Optional[UploadFile] = File(None),
):
    # Validar campos obligatorios
    asunto = asunto.strip()
    motivo = motivo.strip()

    if not asunto:
        raise HTTPException(status_code=422, detail="El asunto es obligatorio")
    if not motivo:
        raise HTTPException(status_code=422, detail="El motivo es obligatorio")

    # Validar y parsear dependencias
    try:
        deps_lista = json.loads(dependencias)
        if not isinstance(deps_lista, list) or not deps_lista:
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(
            status_code=422,
            detail="'dependencias' debe ser un array JSON válido con al menos un elemento, ej: [\"internet\"]",
        )

    # Guardar archivos
    ruta_audio = None
    ruta_imagen = None

    if audio and audio.filename:
        ruta_audio = await _guardar_archivo(audio, settings.UPLOADS_AUDIO_DIR)

    if imagen and imagen.filename:
        ruta_imagen = await _guardar_archivo(imagen, settings.UPLOADS_IMAGENES_DIR)

    # Transcripción con Whisper (si está habilitado y hay audio)
    transcripcion = None
    if ruta_audio and settings.WHISPER_HABILITADO:
        try:
            from backend.services.transcripcion import transcribir_audio
            ruta_abs_audio = settings.UPLOADS_DIR.parent / ruta_audio
            transcripcion = transcribir_audio(str(ruta_abs_audio))
        except Exception as e:
            logger.warning(f"No se pudo transcribir el audio: {e}")

    # Crear registro
    nota = Nota(
        asunto=asunto,
        motivo=motivo,
        dependencias=json.dumps(deps_lista, ensure_ascii=False),
        lugar=lugar.strip() if lugar else None,
        f_inicio=f_inicio or datetime.utcnow(),
        limite=limite,
        ruta_audio=ruta_audio,
        ruta_imagen=ruta_imagen,
        transcripcion=transcripcion,
    )
    db.add(nota)
    db.commit()
    db.refresh(nota)

    # Notificaciones en segundo plano
    background_tasks.add_task(_ejecutar_notificaciones, nota)

    return nota


# ---------------------------------------------------------------------------
# GET /notas/ — Listar con filtros y paginación
# ---------------------------------------------------------------------------

@router.get("/", response_model=NotaListResponse)
def listar_notas(
    db: Session = Depends(get_db),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    buscar: Optional[str] = Query(None, description="Búsqueda en asunto y motivo"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(Nota)

    if estado:
        query = query.filter(Nota.estado == estado)

    if buscar:
        termino = f"%{buscar}%"
        query = query.filter(
            (Nota.asunto.ilike(termino)) | (Nota.motivo.ilike(termino))
        )

    total = query.count()
    items = (
        query.order_by(Nota.creado_en.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return NotaListResponse(total=total, page=page, page_size=page_size, items=items)


# ---------------------------------------------------------------------------
# GET /notas/{id} — Obtener una nota
# ---------------------------------------------------------------------------

@router.get("/{nota_id}", response_model=NotaResponse)
def obtener_nota(nota_id: int, db: Session = Depends(get_db)):
    nota = db.query(Nota).filter(Nota.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail=f"Nota {nota_id} no encontrada")
    return nota


# ---------------------------------------------------------------------------
# PATCH /notas/{id} — Actualizar campos
# ---------------------------------------------------------------------------

@router.patch("/{nota_id}", response_model=NotaResponse)
def actualizar_nota(
    nota_id: int,
    datos: NotaUpdate,
    db: Session = Depends(get_db),
):
    nota = db.query(Nota).filter(Nota.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail=f"Nota {nota_id} no encontrada")

    update_data = datos.model_dump(exclude_unset=True)

    if "dependencias" in update_data:
        update_data["dependencias"] = json.dumps(update_data["dependencias"], ensure_ascii=False)

    for campo, valor in update_data.items():
        setattr(nota, campo, valor)

    nota.actualizado_en = datetime.utcnow()
    db.commit()
    db.refresh(nota)
    return nota


# ---------------------------------------------------------------------------
# DELETE /notas/{id} — Eliminar nota
# ---------------------------------------------------------------------------

@router.delete("/{nota_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_nota(nota_id: int, db: Session = Depends(get_db)):
    nota = db.query(Nota).filter(Nota.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail=f"Nota {nota_id} no encontrada")

    # Eliminar archivos adjuntos del disco si existen
    for ruta_rel in [nota.ruta_audio, nota.ruta_imagen]:
        if ruta_rel:
            ruta_abs = settings.UPLOADS_DIR.parent / ruta_rel
            try:
                Path(ruta_abs).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo {ruta_abs}: {e}")

    db.delete(nota)
    db.commit()
