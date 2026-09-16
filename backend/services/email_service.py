"""
Servicio de email — envía resumen HTML de la tarea por smtplib.
Cubre dos casos: alta de nueva tarea y recordatorio programado.
Solo se ejecuta si EMAIL_HABILITADO=true en .env
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.config import settings

logger = logging.getLogger("avisador")


def _construir_asunto(nota, es_recordatorio: bool = False, tipo: str = "") -> str:
    if es_recordatorio:
        return f"[AVISADOR] ⏰ Recordatorio — falta {tipo} para vencer: {nota.asunto}"
    return f"[AVISADOR] Nueva tarea: {nota.asunto}"


def _construir_html(nota, es_recordatorio: bool = False, tipo: str = "") -> str:
    limite_str = nota.limite.strftime("%d/%m/%Y %H:%M") if nota.limite else "Sin límite"
    import json
    try:
        deps = json.loads(nota.dependencias) if nota.dependencias else []
    except Exception:
        deps = [nota.dependencias]
    deps_html = "".join(f"<li>{d}</li>" for d in deps)

    if es_recordatorio:
        titulo = f"⏰ Recordatorio — falta {tipo} para vencer"
        color_banner = "#d97706"
    else:
        titulo = "Nueva tarea registrada"
        color_banner = "#2563eb"

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:{color_banner}">AVISADOR — {titulo}</h2>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:8px;font-weight:bold;background:#f1f5f9">Asunto</td>
            <td style="padding:8px">{nota.asunto}</td></tr>
        <tr><td style="padding:8px;font-weight:bold;background:#f1f5f9">Motivo</td>
            <td style="padding:8px">{nota.motivo}</td></tr>
        <tr><td style="padding:8px;font-weight:bold;background:#f1f5f9">Lugar</td>
            <td style="padding:8px">{nota.lugar or '—'}</td></tr>
        <tr><td style="padding:8px;font-weight:bold;background:#f1f5f9">Límite</td>
            <td style="padding:8px">{limite_str}</td></tr>
        <tr><td style="padding:8px;font-weight:bold;background:#f1f5f9">Dependencias</td>
            <td style="padding:8px"><ul>{deps_html}</ul></td></tr>
      </table>
      <p style="color:#64748b;font-size:12px">Enviado por AVISADOR</p>
    </body></html>
    """


def _email_configurado() -> bool:
    if not settings.EMAIL_HABILITADO:
        return False
    requeridos = [settings.EMAIL_HOST, settings.EMAIL_USER, settings.EMAIL_PASSWORD, settings.EMAIL_DESTINATARIO]
    if not all(requeridos):
        logger.warning("Email habilitado pero faltan credenciales en .env")
        return False
    return True


def _enviar_html(asunto: str, html: str) -> None:
    """Envía el HTML al destinatario. Lanza excepción si falla."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = settings.EMAIL_USER
    msg["To"] = settings.EMAIL_DESTINATARIO

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
        server.sendmail(settings.EMAIL_USER, settings.EMAIL_DESTINATARIO, msg.as_string())


def enviar_email_nota(nota) -> None:
    """Envía un email con el resumen de la nota recién creada."""
    if not _email_configurado():
        return

    try:
        _enviar_html(_construir_asunto(nota), _construir_html(nota))
        logger.info(f"Email enviado para nota {nota.id}")
    except Exception as e:
        logger.error(f"Error al enviar email: {e}")
        raise


def enviar_email_recordatorio(nota, tipo: str) -> None:
    """Envía email recordatorio con la anticipación indicada (ej. '24h')."""
    if not _email_configurado():
        return

    try:
        _enviar_html(
            _construir_asunto(nota, es_recordatorio=True, tipo=tipo),
            _construir_html(nota, es_recordatorio=True, tipo=tipo),
        )
        logger.info(f"Email recordatorio {tipo} enviado para nota {nota.id}")
    except Exception as e:
        logger.error(f"Error al enviar email recordatorio: {e}")
        raise
