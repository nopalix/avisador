"""
Tests del CRUD de notas — endpoint /api/notas/
"""

import json


DATOS_VALIDOS = {
    "asunto": "Comprar tóner",
    "motivo": "Se acabó la tinta de la impresora",
    "dependencias": '["internet", "tarjeta de crédito"]',
}


def _datos(**overrides):
    d = dict(DATOS_VALIDOS)
    d.update(overrides)
    return d


# ---------------------------------------------------------------------------
# POST /api/notas/
# ---------------------------------------------------------------------------

def test_crear_nota_valida(client):
    resp = client.post("/api/notas/", data=DATOS_VALIDOS)
    assert resp.status_code == 201
    body = resp.json()
    assert body["asunto"] == "Comprar tóner"
    assert body["motivo"] == "Se acabó la tinta de la impresora"
    assert body["dependencias"] == ["internet", "tarjeta de crédito"]
    assert body["estado"] == "pendiente"
    assert "id" in body


def test_crear_nota_sin_asunto(client):
    resp = client.post("/api/notas/", data=_datos(asunto="  "))
    assert resp.status_code == 422


def test_crear_nota_sin_motivo(client):
    resp = client.post("/api/notas/", data=_datos(motivo=""))
    assert resp.status_code == 422


def test_crear_nota_dependencias_vacias(client):
    resp = client.post("/api/notas/", data=_datos(dependencias="[]"))
    assert resp.status_code == 422


def test_crear_nota_dependencias_invalidas(client):
    resp = client.post("/api/notas/", data=_datos(dependencias="no-es-json"))
    assert resp.status_code == 422


def test_crear_nota_con_lugar(client):
    resp = client.post(
        "/api/notas/",
        data=_datos(lugar="Papelería del centro"),
    )
    assert resp.status_code == 201
    assert resp.json()["lugar"] == "Papelería del centro"


# ---------------------------------------------------------------------------
# GET /api/notas/
# ---------------------------------------------------------------------------

def test_listar_notas_vacio(client):
    resp = client.get("/api/notas/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_listar_notas_con_datos(client, crear_nota):
    crear_nota()
    crear_nota()
    resp = client.get("/api/notas/?page=1&page_size=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_listar_notas_filtro_buscar(client, crear_nota):
    crear_nota(asunto="Pagar la luz")
    crear_nota(asunto="Ir al gimnasio")
    resp = client.get("/api/notas/?buscar= luz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["asunto"] == "Pagar la luz"


def test_listar_notas_filtro_estado(client, crear_nota):
    crear_nota(estado="completada")
    crear_nota(estado="pendiente")
    resp = client.get("/api/notas/?estado=completada")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["estado"] == "completada"


# ---------------------------------------------------------------------------
# GET /api/notas/{id}
# ---------------------------------------------------------------------------

def test_obtener_nota_existente(client, crear_nota):
    nota_id = crear_nota()
    resp = client.get(f"/api/notas/{nota_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == nota_id


def test_obtener_nota_inexistente(client):
    resp = client.get("/api/notas/9999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/notas/{id}
# ---------------------------------------------------------------------------

def test_actualizar_estado_valido(client, crear_nota):
    nota_id = crear_nota()
    resp = client.patch(
        f"/api/notas/{nota_id}",
        json={"estado": "en_progreso"},
    )
    assert resp.status_code == 200
    assert resp.json()["estado"] == "en_progreso"


def test_actualizar_estado_invalido(client, crear_nota):
    nota_id = crear_nota()
    resp = client.patch(
        f"/api/notas/{nota_id}",
        json={"estado": "estado_inexistente"},
    )
    assert resp.status_code == 422


def test_actualizar_asunto(client, crear_nota):
    nota_id = crear_nota()
    resp = client.patch(
        f"/api/notas/{nota_id}",
        json={"asunto": "Nuevo asunto"},
    )
    assert resp.status_code == 200
    assert resp.json()["asunto"] == "Nuevo asunto"


# ---------------------------------------------------------------------------
# DELETE /api/notas/{id}
# ---------------------------------------------------------------------------

def test_eliminar_nota(client, crear_nota):
    nota_id = crear_nota()
    resp = client.delete(f"/api/notas/{nota_id}")
    assert resp.status_code == 204


def test_eliminar_nota_inexistente(client):
    resp = client.delete("/api/notas/9999")
    assert resp.status_code == 404
