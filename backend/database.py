"""
Configuración de la base de datos SQLite con SQLAlchemy.
Se usa SQLite para operación local/offline-first sin necesidad de servidor.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from backend.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # necesario para SQLite con FastAPI
)


# SQLite no aplica FKs por defecto; el listener habilita ON DELETE CASCADE
# para que borrar una nota limpie sus recordatorios_enviados.
@event.listens_for(engine, "connect")
def _activar_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependencia FastAPI para obtener sesión de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Crea todas las tablas si no existen."""
    from backend import models  # noqa: F401 - necesario para registrar modelos
    Base.metadata.create_all(bind=engine)
