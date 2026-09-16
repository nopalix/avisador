"""
Obtiene y guarda el TELEGRAM_CHAT_ID en .env consultando la API de Telegram.

El token se lee localmente desde .env y NUNCA se muestra en pantalla ni se
comparte. Solo se imprime el chat_id (que no es secreto).

Uso:
    .venv/bin/python scripts/obtener_chat_id.py

Pasos que realiza:
    1. Valida el token con getMe (muestra el nombre del bot).
    2. Llama a getUpdates; si no hay mensajes, te pide que escribas al bot.
    3. Extrae el primer chat.id y lo escribe en .env como TELEGRAM_CHAT_ID.
"""

import json
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


def _leer_env() -> dict:
    """Devuelve las variables del .env como dict, sin ejecutar nada."""
    vars_env = {}
    if ENV_FILE.exists():
        for linea in ENV_FILE.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                vars_env[clave.strip()] = valor.strip()
    return vars_env


def _escribir_env(vars_env: dict) -> None:
    """Sobrescribe .env con las variables dadas, conservando comentarios."""
    lineas = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    lineas_nuevas = []
    escrita = set()

    for linea in lineas:
        linea_strip = linea.strip()
        if linea_strip and not linea_strip.startswith("#") and "=" in linea_strip:
            clave = linea_strip.split("=", 1)[0].strip()
            if clave in vars_env:
                lineas_nuevas.append(f"{clave}={vars_env[clave]}")
                escrita.add(clave)
                continue
        lineas_nuevas.append(linea)

    # Agregar variables nuevas que no estaban en el archivo
    for clave, valor in vars_env.items():
        if clave not in escrita:
            lineas_nuevas.append(f"{clave}={valor}")

    ENV_FILE.write_text("\n".join(lineas_nuevas) + "\n", encoding="utf-8")


def _get(url: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def main() -> int:
    env = _leer_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "").strip()

    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN está vacío en .env")
        print("Créalo con @BotFather (comando /newbot) y agrégalo a .env")
        return 1

    # 1) Validar token
    try:
        info = _get(f"https://api.telegram.org/bot{token}/getMe")
    except Exception as e:
        print(f"ERROR: no se pudo contactar Telegram: {e}")
        return 1

    if not info.get("ok"):
        print(f"ERROR: token inválido. Respuesta de Telegram: {info}")
        return 1

    print(f"Token válido ✅ — Bot: @{info['result']['username']}")

    # 2) Obtener chat_id vía getUpdates
    intentos = 0
    max_intentos = 3
    while intentos < max_intentos:
        try:
            updates = _get(f"https://api.telegram.org/bot{token}/getUpdates")
        except Exception as e:
            print(f"ERROR consultando getUpdates: {e}")
            return 1

        resultado = updates.get("result", [])
        chat_id = None
        for upd in resultado:
            msg = (
                upd.get("message")
                or upd.get("edited_message")
                or upd.get("channel_post")
                or upd.get("my_chat_member", {}).get("chat")
            )
            if msg:
                chat_id = msg.get("chat", {}).get("id")
                if chat_id is not None:
                    break

        if chat_id is not None:
            env["TELEGRAM_CHAT_ID"] = str(chat_id)
            _escribir_env(env)
            print(f"chat_id obtenido: {chat_id}")
            print("Guardado en .env como TELEGRAM_CHAT_ID.")
            print("Reinicia el servidor y prueba con POST /api/admin/test-telegram")
            return 0

        intentos += 1
        print(
            f"No hay mensajes aún (intento {intentos}/{max_intentos}). "
            "Envía un mensaje al bot en Telegram (pulsa Start si no lo has hecho) "
            "y presiona Enter para reintentar..."
        )
        try:
            input()
        except EOFError:
            break

    print("ERROR: no se recibió ningún mensaje del bot. Abre Telegram, "
          "escribe a tu bot (o pulsa /start) y vuelve a ejecutar el script.")
    return 1


if __name__ == "__main__":
    sys.exit(main())