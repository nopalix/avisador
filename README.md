# AVISADOR

Sistema de gestión de tareas **Local-First / Offline-First / PWA** — descarga la cabeza de una persona con TDAH.

---

## Requisitos

- Python 3.10+
- pip

Para transcripción de audio (opcional):
- `ffmpeg` instalado en el sistema: `sudo apt install ffmpeg`

---

## Instalación y arranque

```bash
# 1. Clona o entra a la carpeta del proyecto
cd avisador

# 2. Crea un entorno virtual
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# 3. Instala dependencias
pip install -r requirements.txt

# 4. Copia el archivo de configuración
cp .env.example .env
# Edita .env y completa solo lo que necesites

# 5. Inicia el servidor
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Abre en el navegador: `http://localhost:8000`

---

## URLs disponibles

| URL | Descripción |
|---|---|
| `http://localhost:8000/` | Formulario para crear tareas (PWA) |
| `http://localhost:8000/admin.html` | Panel de administración |
| `http://localhost:8000/api/docs` | Documentación interactiva (Swagger) |
| `http://localhost:8000/api/redoc` | Documentación alternativa (ReDoc) |

---

## Estructura del proyecto

```
avisador/
├── backend/
│   ├── main.py              # Entry point FastAPI
│   ├── models.py            # Modelos SQLAlchemy
│   ├── schemas.py           # Schemas Pydantic
│   ├── database.py          # Config SQLite
│   ├── config.py            # Variables de entorno
│   └── routers/
│       ├── notas.py         # CRUD notas
│       └── admin.py         # Panel admin
│   └── services/
│       ├── email_service.py
│       ├── telegram_service.py
│       ├── calendar_service.py
│       └── transcripcion.py
├── frontend/
│   ├── index.html           # UI principal (móvil-first)
│   ├── admin.html           # Panel admin
│   ├── sw.js                # Service Worker
│   ├── manifest.json        # PWA manifest
│   ├── css/styles.css
│   └── js/
│       ├── app.js           # Lógica principal
│       └── sync.js          # Cola offline IndexedDB
├── uploads/
│   ├── audio/               # Archivos de audio
│   └── imagenes/            # Imágenes
├── logs/
│   └── errores.log
├── docs/
│   └── CHANGELOG.md
├── .env.example
├── requirements.txt
└── avisador.db              # Base de datos SQLite (se crea al arrancar)
```

---

## Integraciones opcionales

Todas deshabilitadas por defecto. Para activar, editar `.env`:

### Email
```env
EMAIL_HABILITADO=true
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=tu@gmail.com
EMAIL_PASSWORD=contraseña_de_app
EMAIL_DESTINATARIO=destino@ejemplo.com
```

### Telegram
```env
TELEGRAM_HABILITADO=true
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=-100123456789
```

### Google Calendar
```env
CALENDAR_HABILITADO=true
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json
```
La primera ejecución abrirá el navegador para autenticarse con Google.

### Whisper (transcripción de audio)
```bash
pip install openai-whisper
sudo apt install ffmpeg
```
```env
WHISPER_HABILITADO=true
WHISPER_MODELO=base   # tiny | base | small | medium | large
```

---

## Instalar como PWA en el celular

1. Abre `http://<ip-de-tu-computadora>:8000` en Chrome/Safari del celular
2. Toca el menú del navegador → "Agregar a pantalla de inicio"
3. La app funciona sin conexión gracias al Service Worker

> **Nota:** para acceder desde otro dispositivo en la misma red, usa la IP local de tu computadora, no `localhost`.

---

## Fase 2 (pendiente)

- Iconos PWA reales (reemplazar placeholders en `frontend/icons/`)
- Notificaciones push
- Modo oscuro
- Exportar notas a CSV / JSON
- Autenticación básica para el panel admin
- Tests automáticos (pytest)
