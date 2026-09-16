"""
Servicio Telegram — envía mensaje al bot cuando se registra una tarea o
cuando vence un recordatorio programado.
Solo se ejecuta si TELEGRAM_HABILITADO=true en .env
Usa urllib (stdlib) para no agregar dependencias extra.
"""

import json
import logging
import urllib.parse
import urllib.request

from backend.config import settings

logger = logging.getLogger("avisador")


def _construir_texto(nota, es_recordatorio: bool = False, tipo: str = "") -> str:
    """Construye el mensaje Markdown para una nota, según el tipo de aviso."""
    deps = []
    try:
        deps = json.loads(nota.dependencias) if nota.dependencias else []
    except Exception:
        deps = [nota.dependencias]

    limite_str = nota.limite.strftime("%d/%m/%Y %H:%M") if nota.limite else "Sin límite"
    deps_str = "\n  • ".join(deps)

    if es_recordatorio:
        titulo = f"⏰ *Recordatorio — falta {tipo} para vencer*"
    else:
        titulo = "*AVISADOR — Nueva tarea*"

    return (
        f"{titulo}\n\n"
        f"*Asunto:* {nota.asunto}\n"
        f"*Motivo:* {nota.motivo}\n"
        f"*Lugar:* {nota.lugar or '—'}\n"
        f"*Límite:* {limite_str}\n"
        f"*Dependencias:*\n  • {deps_str}"
    )


def _enviar_mensaje(texto: str) -> None:
    """Envía `texto` al chat configurado. Lanza excepción si falla."""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    datos = urllib.parse.urlencode({
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown",
    }).encode()

    req = urllib.request.Request(url, data=datos, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        resultado = json.loads(resp.read())
        if not resultado.get("ok"):
            logger.error(f"Telegram respondió con error: {resultado}")
            raise RuntimeError(f"Telegram API: {resultado}")


def _telegram_configurado() -> bool:
    if not settings.TELEGRAM_HABILITADO:
        return False
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.warning("Telegram habilitado pero faltan TOKEN o CHAT_ID en .env")
        return False
    return True


def enviar_telegram_nota(nota) -> None:
    """Envía mensaje de texto al chat de Telegram configurado."""
    if not _telegram_configurado():
        return

    try:
        _enviar_mensaje(_construir_texto(nota, es_recordatorio=False))
        logger.info(f"Telegram enviado para nota {nota.id}")
    except Exception as e:
        logger.error(f"Error al enviar mensaje Telegram: {e}")
        raise


def enviar_telegram_recordatorio(nota, tipo: str) -> None:
    """Envía recordatorio por Telegram con la anticipación indicada (ej. '24h')."""
    if not _telegram_configurado():
        return

    try:
        _enviar_mensaje(_construir_texto(nota, es_recordatorio=True, tipo=tipo))
        logger.info(f"Telegram recordatorio {tipo} enviado para nota {nota.id}")
    except Exception as e:
        logger.error(f"Error al enviar recordatorio Telegram: {e}")
        raise
