"""
Servicio Google Calendar — crea un evento cuando se registra una tarea.
Solo se ejecuta si CALENDAR_HABILITADO=true en .env

Requiere:
  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

Flujo OAuth2:
  1. Descarga credentials.json desde Google Cloud Console.
  2. La primera vez que se ejecute generará token.json (autenticación interactiva).
  3. Las siguientes ejecuciones usan el token guardado.
"""

import logging
from datetime import timedelta

from backend.config import settings

logger = logging.getLogger("avisador")

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def _obtener_servicio():
    """Construye y devuelve el servicio de Google Calendar autenticado."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "Instala las dependencias de Google Calendar: "
            "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
        )

    creds = None
    token_file = settings.GOOGLE_TOKEN_FILE
    creds_file = settings.GOOGLE_CREDENTIALS_FILE

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def _overrides_reminders() -> list:
    """Popups alineados con RECORDATORIO_ANTICIPACION_HORAS (máx 3)."""
    try:
        from backend.services.recordatorios import _offsets_horas
        offsets = _offsets_horas()
    except Exception:
        offsets = [24.0, 1.0]

    overrides = []
    for horas in offsets[:3]:
        minutos = max(1, int(round(horas * 60)))
        overrides.append({"method": "popup", "minutes": minutos})
    return overrides


def crear_evento_calendario(nota) -> None:
    """Crea un evento en Google Calendar con los datos de la nota."""
    if not settings.CALENDAR_HABILITADO:
        return

    if not settings.GOOGLE_CREDENTIALS_FILE.exists():
        logger.warning(
            "Google Calendar habilitado pero no existe %s",
            settings.GOOGLE_CREDENTIALS_FILE,
        )
        return

    try:
        service = _obtener_servicio()

        inicio = nota.f_inicio
        fin = nota.limite if nota.limite else (inicio + timedelta(hours=1))

        import json
        try:
            deps = json.loads(nota.dependencias) if nota.dependencias else []
        except Exception:
            deps = [nota.dependencias]

        descripcion = (
            f"Motivo: {nota.motivo}\n\n"
            f"Dependencias:\n" + "\n".join(f"  - {d}" for d in deps) +
            (f"\n\nLugar: {nota.lugar}" if nota.lugar else "")
        )

        evento = {
            "summary": nota.asunto,
            "description": descripcion,
            "location": nota.lugar or "",
            "start": {"dateTime": inicio.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": fin.isoformat(), "timeZone": "UTC"},
            "reminders": {
                "useDefault": False,
                "overrides": _overrides_reminders(),
            },
        }

        resultado = service.events().insert(calendarId="primary", body=evento).execute()
        logger.info(f"Evento Calendar creado: {resultado.get('htmlLink')} para nota {nota.id}")

    except Exception as e:
        logger.error(f"Error al crear evento en Google Calendar: {e}")
        raise
