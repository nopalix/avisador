"""
Fixtures de test para AVISADOR.

Usa una base de datos SQLite en memoria (aislada de la real avisador.db)
y sobreescribe la dependencia `get_db` de FastAPI para que todos los
endpoints de los tests apunten a esa base aislada.
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Permite importar `backend.*` desde cualquier cwd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Desactiva el scheduler y las integraciones externas en los tests
# para que no arranque el job ni se envíen mensajes/emails reales.
os.environ.setdefault("RECORDATORIOS_HABILITADO", "false")
os.environ.setdefault("TELEGRAM_HABILITADO", "false")
os.environ.setdefault("EMAIL_HABILITADO", "false")
os.environ.setdefault("CALENDAR_HABILITADO", "false")
os.environ.setdefault("WHISPER_HABILITADO", "false")

from backend.database import Base, get_db  # noqa: E402
from backend.main import app  # noqa: E402


@pytest.fixture(scope="session")
def test_engine():
    """Motor SQLite en memoria compartido por toda la sesión de test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def limpiar_tablas(test_engine):
    """Limpia todas las tablas antes de cada test (aislamiento entre tests)."""
    with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    yield


@pytest.fixture
def db_session(test_engine):
    """Sesión de base de datos de test (SQLite en memoria)."""
    SessionTest = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionTest()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_engine):
    """
    Cliente de test de FastAPI con `get_db` sobreescrito
    para usar la base en memoria.
    """
    SessionTest = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        session = SessionTest()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def crear_nota(client):
    """Helper: crea una nota vía API y devuelve su id."""
    def _crear(asunto="Comprar tóner", motivo="Se acabó la tinta", estado=None, buscar_extra=""):
        datos = {
            "asunto": asunto,
            "motivo": motivo,
            "dependencias": '["internet", "tarjeta"]',
        }
        resp = client.post("/api/notas/", data=datos)
        assert resp.status_code == 201, f"Error creando nota: {resp.text}"
        nota_id = resp.json()["id"]
        if estado:
            r = client.patch(
                f"/api/admin/notas/{nota_id}/estado",
                json={"estado": estado},
                auth=("admin", "Admin"),
            )
            assert r.status_code == 200
        return nota_id

    return _crear
