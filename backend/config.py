"""
Configuración centralizada del sistema AVISADOR.
Usa pydantic-settings para leer variables de entorno desde .env
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # -----------------------------------------------------------------------
    # App
    # -----------------------------------------------------------------------
    APP_TITLE: str = "AVISADOR"
    APP_DESCRIPTION: str = "Sistema de gestión de tareas Local-First / Offline-First"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # -----------------------------------------------------------------------
    # Panel admin — credenciales HTTPBasic (cámbialas en .env)
    # -----------------------------------------------------------------------
    ADMIN_USER: str = "admin"
    ADMIN_PASSWORD: str = "Admin"

    # -----------------------------------------------------------------------
    # Base de datos
    # -----------------------------------------------------------------------
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/avisador.db"

    # -----------------------------------------------------------------------
    # Almacenamiento de archivos
    # -----------------------------------------------------------------------
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    UPLOADS_AUDIO_DIR: Path = BASE_DIR / "uploads" / "audio"
    UPLOADS_IMAGENES_DIR: Path = BASE_DIR / "uploads" / "imagenes"

    # -----------------------------------------------------------------------
    # Logs
    # -----------------------------------------------------------------------
    LOGS_DIR: Path = BASE_DIR / "logs"
    LOG_FILE: Path = BASE_DIR / "logs" / "errores.log"

    # -----------------------------------------------------------------------
    # Email (smtplib) — dejar vacío para deshabilitar
    # -----------------------------------------------------------------------
    EMAIL_HABILITADO: bool = False
    EMAIL_HOST: str = ""
    EMAIL_PORT: int = 587
    EMAIL_USER: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_DESTINATARIO: str = ""

    # -----------------------------------------------------------------------
    # Telegram — dejar TOKEN vacío para deshabilitar
    # -----------------------------------------------------------------------
    TELEGRAM_HABILITADO: bool = False
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # -----------------------------------------------------------------------
    # Google Calendar — dejar vacío para deshabilitar
    # -----------------------------------------------------------------------
    CALENDAR_HABILITADO: bool = False
    GOOGLE_CREDENTIALS_FILE: Path = BASE_DIR / "credentials.json"  # credenciales OAuth2
    GOOGLE_TOKEN_FILE: Path = BASE_DIR / "token.json"              # generado tras autenticar

    # -----------------------------------------------------------------------
    # Recordatorios (scheduler de avisos de tareas próximas a vencer)
    # -----------------------------------------------------------------------
    RECORDATORIOS_HABILITADO: bool = True
    RECORDATORIO_INTERVALO_MINUTOS: int = 5          # frecuencia del job
    RECORDATORIO_ANTICIPACION_HORAS: str = "24,1"    # avisos: lista separada por comas de horas antes del límite

    # -----------------------------------------------------------------------
    # Whisper (transcripción de audio)
    # -----------------------------------------------------------------------
    WHISPER_HABILITADO: bool = False
    WHISPER_MODELO: str = "base"        # tiny | base | small | medium | large

    # -----------------------------------------------------------------------
    # API Keys
    # -----------------------------------------------------------------------
    gemini_api_key: str | None = None
    nvidia_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
