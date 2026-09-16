"""
Servicio de transcripción de audio con OpenAI Whisper.
Solo activo si WHISPER_HABILITADO=true en .env

Requiere:
  pip install openai-whisper
  (también necesita ffmpeg instalado en el sistema: apt install ffmpeg)

El modelo se carga en memoria la primera vez y se reutiliza.
Advertencia: el modelo 'base' requiere ~150MB en disco; 'large' ~3GB.
"""

import logging
from functools import lru_cache

from backend.config import settings

logger = logging.getLogger("avisador")


@lru_cache(maxsize=1)
def _cargar_modelo():
    """Carga el modelo Whisper una sola vez y lo mantiene en caché."""
    try:
        import whisper
    except ImportError:
        raise ImportError(
            "Whisper no está instalado. Ejecuta: pip install openai-whisper\n"
            "También necesitas ffmpeg: sudo apt install ffmpeg"
        )
    logger.info(f"Cargando modelo Whisper '{settings.WHISPER_MODELO}'...")
    modelo = whisper.load_model(settings.WHISPER_MODELO)
    logger.info("Modelo Whisper cargado.")
    return modelo


def transcribir_audio(ruta_archivo: str) -> str:
    """
    Transcribe un archivo de audio a texto usando Whisper.

    Args:
        ruta_archivo: Ruta absoluta al archivo de audio (mp3, wav, ogg, m4a, webm...)

    Returns:
        Texto transcrito como string. Vacío si falla.
    """
    if not settings.WHISPER_HABILITADO:
        logger.debug("Whisper deshabilitado, omitiendo transcripción")
        return ""

    try:
        modelo = _cargar_modelo()
        logger.info(f"Transcribiendo: {ruta_archivo}")
        resultado = modelo.transcribe(ruta_archivo)
        texto = resultado.get("text", "").strip()
        logger.info(f"Transcripción completada ({len(texto)} caracteres)")
        return texto
    except Exception as e:
        logger.error(f"Error al transcribir audio '{ruta_archivo}': {e}")
        return ""
