"""
Router admin — endpoints para el panel de administración de AVISADOR.

Endpoints:
  GET    /admin/notas/           Listado completo con todos los filtros
  GET    /admin/notas/export     Exportar notas a CSV o JSON
  GET    /admin/stats/           Estadísticas generales
  PATCH  /admin/notas/{id}/estado   Cambiar estado de una nota
  DELETE /admin/notas/bulk       Eliminar múltiples notas
  POST   /admin/log-error        Recibir errores del cliente (JS frontend)
"""

import csv
import io
import json
import logging
import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import Nota
from backend.schemas import NotaListResponse, NotaResponse

logger = logging.getLogger("avisador")

router = APIRouter(prefix="/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Autenticación HTTPBasic para el panel admin
# ---------------------------------------------------------------------------

_security = HTTPBasic()


def _auth_admin(creds: HTTPBasicCredentials = Depends(_security)) -> str:
    """Exige credenciales válidas en los endpoints del panel admin."""
    usuario_ok = secrets.compare_digest(creds.username, settings.ADMIN_USER)
    pass_ok = secrets.compare_digest(creds.password, settings.ADMIN_PASSWORD)
    if not (usuario_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return creds.username


# ---------------------------------------------------------------------------
# GET /admin/stats/ — Estadísticas generales
# ---------------------------------------------------------------------------

@router.get("/stats/")
def obtener_estadisticas(
    db: Session = Depends(get_db),
    _user: str = Depends(_auth_admin),
):
    total = db.query(func.count(Nota.id)).scalar()
    por_estado = (
        db.query(Nota.estado, func.count(Nota.id))
        .group_by(Nota.estado)
        .all()
    )
    con_audio = db.query(func.count(Nota.id)).filter(Nota.ruta_audio.isnot(None)).scalar()
    con_imagen = db.query(func.count(Nota.id)).filter(Nota.ruta_imagen.isnot(None)).scalar()
    vencidas = (
        db.query(func.count(Nota.id))
        .filter(Nota.limite < datetime.utcnow(), Nota.estado.notin_(["completada", "cancelada"]))
        .scalar()
    )

    return {
        "total": total,
        "por_estado": {estado: count for estado, count in por_estado},
        "con_audio": con_audio,
        "con_imagen": con_imagen,
        "vencidas": vencidas,
    }


# ---------------------------------------------------------------------------
# GET /admin/notas/ — Listado completo con todos los filtros
# ---------------------------------------------------------------------------

@router.get("/notas/", response_model=NotaListResponse)
def listar_todas_las_notas(
    db: Session = Depends(get_db),
    _user: str = Depends(_auth_admin),
    estado: Optional[str] = Query(None),
    buscar: Optional[str] = Query(None),
    desde: Optional[datetime] = Query(None, description="Filtrar notas creadas desde esta fecha"),
    hasta: Optional[datetime] = Query(None, description="Filtrar notas creadas hasta esta fecha"),
    con_audio: Optional[bool] = Query(None),
    con_imagen: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    query = db.query(Nota)

    if estado:
        query = query.filter(Nota.estado == estado)
    if buscar:
        t = f"%{buscar}%"
        query = query.filter((Nota.asunto.ilike(t)) | (Nota.motivo.ilike(t)))
    if desde:
        query = query.filter(Nota.creado_en >= desde)
    if hasta:
        query = query.filter(Nota.creado_en <= hasta)
    if con_audio is True:
        query = query.filter(Nota.ruta_audio.isnot(None))
    if con_audio is False:
        query = query.filter(Nota.ruta_audio.is_(None))
    if con_imagen is True:
        query = query.filter(Nota.ruta_imagen.isnot(None))
    if con_imagen is False:
        query = query.filter(Nota.ruta_imagen.is_(None))

    total = query.count()
    items = (
        query.order_by(Nota.creado_en.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return NotaListResponse(total=total, page=page, page_size=page_size, items=items)


# ---------------------------------------------------------------------------
# GET /admin/notas/export — Exportar notas a CSV o JSON
# ---------------------------------------------------------------------------

def _fecha_str(valor) -> str:
    """Convierte un datetime a string legible, o vacío si es None."""
    if not valor:
        return ""
    return valor.strftime("%Y-%m-%d %H:%M")


def _a_fila(nota) -> List[str]:
    """Convierte una Nota a una fila CSV (valores como strings)."""
    try:
        deps = json.loads(nota.dependencias) if nota.dependencias else []
    except Exception:
        deps = [nota.dependencias]
    return [
        str(nota.id),
        nota.asunto,
        nota.motivo,
        "; ".join(deps),
        nota.lugar or "",
        _fecha_str(nota.f_inicio),
        _fecha_str(nota.limite),
        nota.estado,
        _fecha_str(nota.creado_en),
        nota.transcripcion or "",
        nota.ruta_audio or "",
        nota.ruta_imagen or "",
    ]


def _a_dict(nota) -> dict:
    """Convierte una Nota a dict para exportación JSON."""
    try:
        deps = json.loads(nota.dependencias) if nota.dependencias else []
    except Exception:
        deps = [nota.dependencias]
    return {
        "id": nota.id,
        "asunto": nota.asunto,
        "motivo": nota.motivo,
        "dependencias": deps,
        "lugar": nota.lugar,
        "f_inicio": _fecha_str(nota.f_inicio),
        "limite": _fecha_str(nota.limite),
        "estado": nota.estado,
        "creado_en": _fecha_str(nota.creado_en),
        "transcripcion": nota.transcripcion,
        "ruta_audio": nota.ruta_audio,
        "ruta_imagen": nota.ruta_imagen,
    }


@router.get("/notas/export")
def exportar_notas(
    db: Session = Depends(get_db),
    _user: str = Depends(_auth_admin),
    formato: str = Query("csv", pattern="^(csv|json)$", description="Formato de exportación"),
    estado: Optional[str] = Query(None),
    buscar: Optional[str] = Query(None),
    desde: Optional[datetime] = Query(None),
    hasta: Optional[datetime] = Query(None),
):
    """Exporta todas las notas (aplicando filtros si se envían) a CSV o JSON."""
    query = db.query(Nota)

    if estado:
        query = query.filter(Nota.estado == estado)
    if buscar:
        t = f"%{buscar}%"
        query = query.filter((Nota.asunto.ilike(t)) | (Nota.motivo.ilike(t)))
    if desde:
        query = query.filter(Nota.creado_en >= desde)
    if hasta:
        query = query.filter(Nota.creado_en <= hasta)

    notas = query.order_by(Nota.creado_en.desc()).all()

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
    nombre_base = f"avisador_{ts}"

    if formato == "json":
        contenido = json.dumps(
            [_a_dict(n) for n in notas],
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        return Response(
            content=contenido,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{nombre_base}.json"'},
        )

    # CSV — utf-8-sig para compatibilidad con Excel (acentos correctos)
    columnas = [
        "id", "asunto", "motivo", "dependencias", "lugar",
        "f_inicio", "limite", "estado", "creado_en",
        "transcripcion", "ruta_audio", "ruta_imagen",
    ]
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")  # ';' para que Excel lo abra directo en es-ES
    writer.writerow(columnas)
    for nota in notas:
        writer.writerow(_a_fila(nota))

    contenido = ("\ufeff" + buffer.getvalue()).encode("utf-8")  # BOM utf-8-sig
    return Response(
        content=contenido,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nombre_base}.csv"'},
    )


# ---------------------------------------------------------------------------
# PATCH /admin/notas/{id}/estado — Cambiar estado
# ---------------------------------------------------------------------------

@router.patch("/notas/{nota_id}/estado", response_model=NotaResponse)
def cambiar_estado(
    nota_id: int,
    estado: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    _user: str = Depends(_auth_admin),
):
    estados_validos = {"pendiente", "en_progreso", "completada", "cancelada"}
    if estado not in estados_validos:
        raise HTTPException(status_code=422, detail=f"Estado inválido. Valores: {estados_validos}")

    nota = db.query(Nota).filter(Nota.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail=f"Nota {nota_id} no encontrada")

    nota.estado = estado
    nota.actualizado_en = datetime.utcnow()
    db.commit()
    db.refresh(nota)
    return nota


# ---------------------------------------------------------------------------
# DELETE /admin/notas/bulk — Eliminar múltiples notas
# ---------------------------------------------------------------------------

@router.delete("/notas/bulk", status_code=status.HTTP_200_OK)
def eliminar_notas_bulk(
    ids: List[int] = Body(..., embed=True),
    db: Session = Depends(get_db),
    _user: str = Depends(_auth_admin),
):
    if not ids:
        raise HTTPException(status_code=422, detail="Debes enviar al menos un ID")

    notas = db.query(Nota).filter(Nota.id.in_(ids)).all()
    eliminados = []

    for nota in notas:
        for ruta_rel in [nota.ruta_audio, nota.ruta_imagen]:
            if ruta_rel:
                from pathlib import Path
                ruta_abs = settings.UPLOADS_DIR.parent / ruta_rel
                try:
                    Path(ruta_abs).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"No se pudo eliminar archivo {ruta_abs}: {e}")
        db.delete(nota)
        eliminados.append(nota.id)

    db.commit()
    return {"eliminados": eliminados, "total": len(eliminados)}


# ---------------------------------------------------------------------------
# POST /admin/test-telegram — Enviar mensaje de prueba
# ---------------------------------------------------------------------------

@router.post("/test-telegram", status_code=status.HTTP_200_OK)
def test_telegram(
    _user: str = Depends(_auth_admin),
):
    """Envía un mensaje de prueba al chat de Telegram configurado."""
    if not settings.TELEGRAM_HABILITADO:
        raise HTTPException(
            status_code=400,
            detail="Telegram deshabilitado. Pon TELEGRAM_HABILITADO=true en .env",
        )
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        raise HTTPException(
            status_code=400,
            detail="Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en .env",
        )

    try:
        from backend.services.telegram_service import _enviar_mensaje
        _enviar_mensaje("✅ AVISADOR — Prueba de Telegram. La configuración funciona.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Telegram no respondió: {e}")

    return {"ok": True, "detail": "Mensaje de prueba enviado a Telegram"}


# ---------------------------------------------------------------------------
# POST /admin/test-email — Enviar correo de prueba
# ---------------------------------------------------------------------------

@router.post("/test-email", status_code=status.HTTP_200_OK)
def test_email(
    _user: str = Depends(_auth_admin),
):
    """Envía un email de prueba al destinatario configurado."""
    if not settings.EMAIL_HABILITADO:
        raise HTTPException(
            status_code=400,
            detail="Email deshabilitado. Pon EMAIL_HABILITADO=true en .env",
        )
    requeridos = [
        settings.EMAIL_HOST, settings.EMAIL_USER,
        settings.EMAIL_PASSWORD, settings.EMAIL_DESTINATARIO,
    ]
    if not all(requeridos):
        raise HTTPException(
            status_code=400,
            detail="Faltan credenciales de email en .env (HOST, USER, PASSWORD, DESTINATARIO)",
        )

    try:
        from backend.services.email_service import _enviar_html
        _enviar_html(
            "[AVISADOR] Prueba de configuración",
            "<h2 style='color:#2563eb'>AVISADOR</h2><p>✅ El correo funciona. "
            "La configuración de email está lista.</p>",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"No se pudo enviar el email: {e}")

    return {"ok": True, "detail": "Email de prueba enviado correctamente"}


# ---------------------------------------------------------------------------
# POST /admin/test-calendar — Crear evento de prueba en Google Calendar
# ---------------------------------------------------------------------------

@router.post("/test-calendar", status_code=status.HTTP_200_OK)
def test_calendar(
    _user: str = Depends(_auth_admin),
):
    """Crea un evento de prueba en Google Calendar (dispara OAuth la 1ª vez)."""
    if not settings.CALENDAR_HABILITADO:
        raise HTTPException(
            status_code=400,
            detail="Google Calendar deshabilitado. Pon CALENDAR_HABILITADO=true en .env",
        )
    if not settings.GOOGLE_CREDENTIALS_FILE.exists():
        raise HTTPException(
            status_code=400,
            detail=f"No existe credentials.json en {settings.GOOGLE_CREDENTIALS_FILE}",
        )

    try:
        from datetime import datetime, timedelta
        from backend.services.calendar_service import _obtener_servicio

        service = _obtener_servicio()
        inicio = datetime.utcnow() + timedelta(days=1)
        evento = {
            "summary": "AVISADOR — Evento de prueba",
            "description": "Si ves este evento, la integración con Google Calendar funciona.",
            "start": {"dateTime": inicio.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": (inicio + timedelta(minutes=30)).isoformat(), "timeZone": "UTC"},
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 60}],
            },
        }
        resultado = service.events().insert(calendarId="primary", body=evento).execute()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error con Google Calendar: {e}")

    return {
        "ok": True,
        "detail": "Evento de prueba creado en Google Calendar",
        "link": resultado.get("htmlLink", ""),
    }


# ---------------------------------------------------------------------------
# POST /admin/log-error — Registro de errores del cliente JS
# ---------------------------------------------------------------------------

@router.post("/log-error", status_code=status.HTTP_204_NO_CONTENT)
def registrar_error_cliente(
    payload: dict = Body(...),
):
    """
    El frontend JS puede enviar aquí errores capturados para depuración.
    Se registran en el log del servidor.
    """
    mensaje = payload.get("mensaje", "sin mensaje")
    origen = payload.get("origen", "desconocido")
    linea = payload.get("linea", "?")
    ua = payload.get("userAgent", "?")
    logger.error(f"[CLIENT ERROR] {origen}:{linea} — {mensaje} | UA: {ua}")
