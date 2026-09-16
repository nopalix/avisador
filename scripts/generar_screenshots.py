"""
Genera screenshots de la app AVISADOR para el manifest.json PWA.

Uso:
    .venv/bin/python scripts/generar_screenshots.py

Requisitos:
    - Servidor corriendo en http://localhost:8000
    - playwright instalado (pip install playwright && playwright install chromium)
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL_BASE = "http://localhost:8000"
SALIDA = Path(__file__).resolve().parent.parent / "frontend" / "screenshots"

VISTAS = [
    # (nombre_archivo, ruta, viewport_ancho, viewport_alto, device)
    ("formulario-movil.png", "/", 412, 915, None),
    ("admin-movil.png", "/admin.html", 412, 915, None),
    ("admin-desktop.png", "/admin.html", 1280, 800, None),
]

ESPERA_CARGA_MS = 2500


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for nombre, ruta, ancho, alto, _device in VISTAS:
            context = browser.new_context(
                viewport={"width": ancho, "height": alto},
                device_scale_factor=2,  # alta densidad para nitidez
                color_scheme="light",
            )
            page = context.new_page()
            page.goto(f"{URL_BASE}{ruta}", wait_until="networkidle")
            page.wait_for_timeout(ESPERA_CARGA_MS)

            # Esperar a que cargue la lista de recientes / tabla
            try:
                page.wait_for_selector("#lista-notas .nota-item, #tabla-body tr", timeout=5000)
            except Exception:
                pass  # puede no haber datos; se captura igual

            destino = SALIDA / nombre
            page.screenshot(path=str(destino))
            print(f"OK  {destino} ({ancho}x{alto})")
            context.close()
        browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
