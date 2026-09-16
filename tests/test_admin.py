"""
Tests de los endpoints del panel admin — /api/admin/

El panel está protegido con HTTPBasic (usuario 'admin' / clave 'Admin').
Los endpoints del admin requieren `auth=(ADMIN_USER, ADMIN_PASS)`.
"""

ADMIN_USER = "admin"
ADMIN_PASS = "Admin"
AUTH = (ADMIN_USER, ADMIN_PASS)


# ---------------------------------------------------------------------------
# Autenticación HTTPBasic
# ---------------------------------------------------------------------------

def test_admin_sin_auth_rechazado(client):
    resp = client.get("/api/admin/stats/")
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers


def test_admin_auth_incorrecta_rechazada(client):
    resp = client.get("/api/admin/stats/", auth=("admin", "clave_incorrecta"))
    assert resp.status_code == 401


def test_log_error_publico_sin_auth(client):
    """log-error queda público para poder reportar errores del frontend."""
    resp = client.post(
        "/api/admin/log-error",
        json={"mensaje": "Error de prueba", "origen": "admin.html", "linea": "12"},
    )
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# GET /api/admin/stats/
# ---------------------------------------------------------------------------

def test_stats_vacio(client):
    resp = client.get("/api/admin/stats/", auth=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["por_estado"] == {}
    assert body["vencidas"] == 0


def test_stats_con_datos(client, crear_nota):
    crear_nota(estado="pendiente")
    crear_nota(estado="pendiente")
    crear_nota(estado="completada")
    resp = client.get("/api/admin/stats/", auth=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert body["por_estado"]["pendiente"] == 2
    assert body["por_estado"]["completada"] == 1


# ---------------------------------------------------------------------------
# GET /api/admin/notas/
# ---------------------------------------------------------------------------

def test_listar_admin_vacio(client):
    resp = client.get("/api/admin/notas/", auth=AUTH)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_listar_admin_con_datos(client, crear_nota):
    crear_nota()
    crear_nota()
    resp = client.get("/api/admin/notas/", auth=AUTH)
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_admin_filtro_estado(client, crear_nota):
    crear_nota(estado="pendiente")
    crear_nota(estado="cancelada")
    resp = client.get("/api/admin/notas/?estado=cancelada", auth=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["estado"] == "cancelada"


def test_admin_filtro_buscar(client, crear_nota):
    crear_nota(asunto="Renovar pasaporte")
    crear_nota(asunto="Cenar con amigos")
    resp = client.get("/api/admin/notas/?buscar=pasaporte", auth=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert "pasaporte" in body["items"][0]["asunto"].lower()


# ---------------------------------------------------------------------------
# PATCH /api/admin/notas/{id}/estado
# ---------------------------------------------------------------------------

def test_cambiar_estado_valido(client, crear_nota):
    nota_id = crear_nota()
    resp = client.patch(
        f"/api/admin/notas/{nota_id}/estado",
        json={"estado": "completada"},
        auth=AUTH,
    )
    assert resp.status_code == 200
    assert resp.json()["estado"] == "completada"


def test_cambiar_estado_invalido(client, crear_nota):
    nota_id = crear_nota()
    resp = client.patch(
        f"/api/admin/notas/{nota_id}/estado",
        json={"estado": "no_existe"},
        auth=AUTH,
    )
    assert resp.status_code == 422


def test_cambiar_estado_nota_inexistente(client):
    resp = client.patch(
        "/api/admin/notas/9999/estado",
        json={"estado": "completada"},
        auth=AUTH,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/admin/notas/bulk
# ---------------------------------------------------------------------------

def test_bulk_delete(client, crear_nota):
    id1 = crear_nota()
    id2 = crear_nota()
    resp = client.request("DELETE", "/api/admin/notas/bulk", json={"ids": [id1, id2]}, auth=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert set(body["eliminados"]) == {id1, id2}


def test_bulk_delete_sin_ids(client):
    resp = client.request("DELETE", "/api/admin/notas/bulk", json={"ids": []}, auth=AUTH)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/admin/log-error (público)
# ---------------------------------------------------------------------------

def test_log_error_cliente(client):
    resp = client.post(
        "/api/admin/log-error",
        json={
            "mensaje": "Error de prueba",
            "origen": "admin.html",
            "linea": "12",
            "userAgent": "pytest",
        },
    )
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# GET /api/admin/notas/export
# ---------------------------------------------------------------------------

def test_export_csv_vacio(client):
    resp = client.get("/api/admin/notas/export?formato=csv", auth=AUTH)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert "asunto" in resp.text  # encabezado de columnas


def test_export_csv_con_datos(client, crear_nota):
    crear_nota(asunto="Comprar leche")
    crear_nota(asunto="Pagar luz")
    resp = client.get("/api/admin/notas/export?formato=csv", auth=AUTH)
    assert resp.status_code == 200
    assert "Comprar leche" in resp.text
    assert "Pagar luz" in resp.text


def test_export_json(client, crear_nota):
    crear_nota(asunto="Renovar pasaporte")
    resp = client.get("/api/admin/notas/export?formato=json", auth=AUTH)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    datos = resp.json()
    assert isinstance(datos, list)
    assert len(datos) == 1
    assert datos[0]["asunto"] == "Renovar pasaporte"
    assert "dependencias" in datos[0]


def test_export_json_respeta_filtro_estado(client, crear_nota):
    crear_nota(asunto="Tarea pendiente", estado="pendiente")
    crear_nota(asunto="Tarea completada", estado="completada")
    resp = client.get("/api/admin/notas/export?formato=json&estado=completada", auth=AUTH)
    assert resp.status_code == 200
    datos = resp.json()
    assert len(datos) == 1
    assert datos[0]["estado"] == "completada"


def test_export_csv_respeta_filtro_buscar(client, crear_nota):
    crear_nota(asunto="Mercado semanal")
    crear_nota(asunto="Pagar impuestos")
    resp = client.get("/api/admin/notas/export?formato=csv&buscar=mercado", auth=AUTH)
    assert resp.status_code == 200
    assert "Mercado semanal" in resp.text
    assert "Pagar impuestos" not in resp.text


def test_export_formato_invalido(client):
    resp = client.get("/api/admin/notas/export?formato=pdf", auth=AUTH)
    assert resp.status_code == 422
