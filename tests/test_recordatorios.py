"""
Tests del scheduler de recordatorios — backend/services/recordatorios.py

Se centran en la lógica de negocio (ventana de aviso, anti-duplicados y
registro solo en éxito). Los envíos por canales se simulan con monkeypatch:
en los tests los canales externos están deshabilitados (conftest).
"""

from datetime import datetime, timedelta

import pytest

from backend.config import settings
from backend.models import Nota, RecordatorioEnviado
from backend.services import recordatorios


def _crear_nota_db(db, *, asunto="Tarea", estado="pendiente", limite=None, offset_horas=0):
    """Crea una Nota directamente en la sesión de test con el límite deseado."""
    if limite is None:
        limite = datetime.utcnow() + timedelta(hours=offset_horas)
    nota = Nota(
        asunto=asunto,
        motivo="Motivo de prueba",
        dependencias='["a"]',
        f_inicio=datetime.utcnow(),
        limite=limite,
        estado=estado,
    )
    db.add(nota)
    db.commit()
    db.refresh(nota)
    return nota


def _filas_recordatorios(db):
    return db.query(RecordatorioEnviado).all()


# ---------------------------------------------------------------------------
# _offsets_horas
# ---------------------------------------------------------------------------

def test_offsets_horas_valido(monkeypatch):
    monkeypatch.setattr(settings, "RECORDATORIO_ANTICIPACION_HORAS", "24,1")
    assert recordatorios._offsets_horas() == [24.0, 1.0]


def test_offsets_horas_invalidos_caen_a_default(monkeypatch):
    monkeypatch.setattr(settings, "RECORDATORIO_ANTICIPACION_HORAS", "abc,,!")
    assert recordatorios._offsets_horas() == [24.0]


def test_offsets_horas_vacio_cae_a_default(monkeypatch):
    monkeypatch.setattr(settings, "RECORDATORIO_ANTICIPACION_HORAS", "")
    assert recordatorios._offsets_horas() == [24.0]


# ---------------------------------------------------------------------------
# _notas_en_ventana
# ---------------------------------------------------------------------------

def test_ventana_incluye_nota_proxima(db_session):
    nota = _crear_nota_db(db_session, offset_horas=2)
    en_ventana = recordatorios._notas_en_ventana(db_session, 24.0)
    assert [n.id for n in en_ventana] == [nota.id]


def test_ventana_excluye_nota_lejos(db_session):
    nota = _crear_nota_db(db_session, offset_horas=30)
    en_ventana = recordatorios._notas_en_ventana(db_session, 24.0)
    assert nota.id not in [n.id for n in en_ventana]


def test_ventana_excluye_nota_vencida(db_session):
    nota = _crear_nota_db(db_session, offset_horas=-2)
    en_ventana = recordatorios._notas_en_ventana(db_session, 24.0)
    assert nota.id not in [n.id for n in en_ventana]


def test_ventana_excluye_sin_limite(db_session):
    nota = _crear_nota_db(db_session, limite=None)
    en_ventana = recordatorios._notas_en_ventana(db_session, 24.0)
    assert nota.id not in [n.id for n in en_ventana]


@pytest.mark.parametrize("estado", ["completada", "cancelada"])
def test_ventana_excluye_estados_inactivos(db_session, estado):
    nota = _crear_nota_db(db_session, estado=estado, offset_horas=2)
    en_ventana = recordatorios._notas_en_ventana(db_session, 24.0)
    assert nota.id not in [n.id for n in en_ventana]


def test_ventana_incluye_estados_activos(db_session):
    nota = _crear_nota_db(db_session, estado="en_progreso", offset_horas=2)
    en_ventana = recordatorios._notas_en_ventana(db_session, 24.0)
    assert [n.id for n in en_ventana] == [nota.id]


# ---------------------------------------------------------------------------
# revisar_recordatorios — registro solo en éxito y anti-duplicados
# ---------------------------------------------------------------------------

def test_revisar_marca_solo_si_envio_ok(db_session, monkeypatch):
    monkeypatch.setattr(settings, "RECORDATORIO_ANTICIPACION_HORAS", "24")
    monkeypatch.setattr(recordatorios, "_enviar_por_canales", lambda nota, tipo: True)
    _crear_nota_db(db_session, offset_horas=2)

    resumen = recordatorios.revisar_recordatorios(db_session)

    assert resumen == {"revisados": 1, "enviados": 1}
    filas = _filas_recordatorios(db_session)
    assert len(filas) == 1
    assert filas[0].tipo == "24h"


def test_revisar_no_marca_si_envio_falla(db_session, monkeypatch):
    monkeypatch.setattr(settings, "RECORDATORIO_ANTICIPACION_HORAS", "24")
    monkeypatch.setattr(recordatorios, "_enviar_por_canales", lambda nota, tipo: False)
    _crear_nota_db(db_session, offset_horas=2)

    resumen = recordatorios.revisar_recordatorios(db_session)

    assert resumen == {"revisados": 1, "enviados": 0}
    assert _filas_recordatorios(db_session) == []


def test_revisar_no_duplica_envios(db_session, monkeypatch):
    monkeypatch.setattr(settings, "RECORDATORIO_ANTICIPACION_HORAS", "24")
    monkeypatch.setattr(recordatorios, "_enviar_por_canales", lambda nota, tipo: True)
    _crear_nota_db(db_session, offset_horas=2)

    primera = recordatorios.revisar_recordatorios(db_session)
    segunda = recordatorios.revisar_recordatorios(db_session)

    assert primera["enviados"] == 1
    assert segunda == {"revisados": 1, "enviados": 0}
    assert len(_filas_recordatorios(db_session)) == 1


def test_revisar_doble_aviso_24h_y_1h(db_session, monkeypatch):
    """Una nota dentro de ambas ventanas recibe un aviso por cada tipo."""
    monkeypatch.setattr(settings, "RECORDATORIO_ANTICIPACION_HORAS", "24,1")
    monkeypatch.setattr(recordatorios, "_enviar_por_canales", lambda nota, tipo: True)
    nota = _crear_nota_db(db_session, offset_horas=0.5)  # dentro de 24h y de 1h

    resumen = recordatorios.revisar_recordatorios(db_session)

    assert resumen == {"revisados": 2, "enviados": 2}
    tipos = sorted(r.tipo for r in _filas_recordatorios(db_session))
    assert tipos == ["1h", "24h"]
    assert all(r.nota_id == nota.id for r in _filas_recordatorios(db_session))


def test_revisar_sin_canales_no_envia(db_session, monkeypatch):
    """Sin canales habilitados _enviar_por_canales devuelve False siempre."""
    monkeypatch.setattr(settings, "RECORDATORIO_ANTICIPACION_HORAS", "24")
    _crear_nota_db(db_session, offset_horas=2)

    resumen = recordatorios.revisar_recordatorios(db_session)

    assert resumen == {"revisados": 1, "enviados": 0}
    assert _filas_recordatorios(db_session) == []
