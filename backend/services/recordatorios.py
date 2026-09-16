"""
Servicio de recordatorios — revisa periódicamente las notas próximas a vencer
y envía avisos por los canales habilitados (Telegram, Email, Calendar).

El job lo dispara APScheduler desde el lifespan de FastAPI. Cada aviso
(tipo '24h', '1h' según RECORDATORIO_ANTICIPACION_HORAS) se envía una sola vez
por nota: queda registrado en la tabla recordatorios_enviados para evitar duplicados.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import SessionLocal
from backend.models import Nota, RecordatorioEnviado

logger = logging.getLogger("avisador")

ESTADOS_ACTIVOS = ("pendiente", "en_progreso")


def _offsets_horas() -> List[float]:
    """Convierte '24,1' de .env en [24.0, 1.0], en orden descendente."""
    try:
        offsets = [
            float(x) for x in settings.RECORDATORIO_ANTICIPACION_HORAS.split(",") if x.strip()
        ]
    except (AttributeError, TypeError, ValueError):
        offsets = []
    return sorted(offsets, reverse=True) or [24.0]


def _aviso_ya_enviado(db: Session, nota_id: int, tipo: str) -> bool:
    return (
        db.query(RecordatorioEnviado)
        .filter(RecordatorioEnviado.nota_id == nota_id, RecordatorioEnviado.tipo == tipo)
        .first()
        is not None
    )


def _marcar_enviado(db: Session, nota_id: int, tipo: str) -> None:
    db.add(RecordatorioEnviado(nota_id=nota_id, tipo=tipo))
    db.commit()


def _notas_en_ventana(db: Session, offset_horas: float) -> List[Nota]:
    """Notas activas cuyo límite cae entre ahora y ahora+offset."""
    ahora = datetime.utcnow()
    fin = ahora + timedelta(hours=offset_horas)
    return (
        db.query(Nota)
        .filter(
            Nota.estado.in_(ESTADOS_ACTIVOS),
            Nota.limite.isnot(None),
            Nota.limite >= ahora,
            Nota.limite <= fin,
        )
        .all()
    )


def _enviar_por_canales(nota: Nota, tipo: str) -> bool:
    """Envía el recordatorio por cada canal habilitado.

    Devuelve True si al menos un canal confirmó el envío. Cada servicio
    verifica internamente si está habilitado y es idempotente ante fallos.
    """
    enviados = 0

    if settings.TELEGRAM_HABILITADO:
        try:
            from backend.services.telegram_service import enviar_telegram_recordatorio
            enviar_telegram_recordatorio(nota, tipo)
            enviados += 1
        except Exception as e:
            logger.error(f"Error Telegram en recordatorio de nota {nota.id}: {e}")

    if settings.EMAIL_HABILITADO:
        try:
            from backend.services.email_service import enviar_email_recordatorio
            enviar_email_recordatorio(nota, tipo)
            enviados += 1
        except Exception as e:
            logger.error(f"Error Email en recordatorio de nota {nota.id}: {e}")

    return enviados > 0


def revisar_recordatorios(db: Optional[Session] = None) -> dict:
    """Revisa las ventanas de aviso y envía los recordatorios pendientes.

    Si no se recibe una sesión, abre una propia (uso desde APScheduler).
    Devuelve un resumen con avisos revisados y enviados (útil en tests).
    """
    cerrar = db is None
    db = db or SessionLocal()
    resumen = {"revisados": 0, "enviados": 0}

    try:
        for offset in _offsets_horas():
            tipo = f"{offset:g}h"
            for nota in _notas_en_ventana(db, offset):
                resumen["revisados"] += 1
                if _aviso_ya_enviado(db, nota.id, tipo):
                    continue
                if _enviar_por_canales(nota, tipo):
                    _marcar_enviado(db, nota.id, tipo)
                    resumen["enviados"] += 1
                    logger.info(f"Recordatorio {tipo} enviado para nota {nota.id}")
    finally:
        if cerrar:
            db.close()

    return resumen