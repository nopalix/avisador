# CHANGELOG — AVISADOR

## [1.9.0] — 2026-08-13

### Agregado
- Modo offline mejorado para la app principal:
  - `frontend/sw.js`: los GET de `/api/notas/` (lista) ahora son network-first con respaldo en caché → la lista se puede ver sin conexión
  - `frontend/js/app.js`: al reconectar (evento `online`) se sincroniza la cola de IndexedDB y se recarga la lista automáticamente
  - Bump de caché a `avisador-v5`

### Notas
- El panel admin no se cachea (evita servir respuestas autenticadas desde caché)
- Caso no cubierto (futuro): móvil "online" sin acceso al servidor (fuera de la red doméstica) no encola el guardado

## [1.8.0] — 2026-08-12

### Agregado
- Autenticación HTTPBasic para el panel admin:
  - Credenciales configurable en `.env` (`ADMIN_USER` / `ADMIN_PASSWORD`, por defecto `admin` / `Admin`)
  - Dependencia `_auth_admin` protege todos los endpoints `/api/admin/` (stats, notas, estado, bulk, export y test-*)
  - `POST /api/admin/log-error` queda público para reportes de errores del frontend
  - Login en `admin.html` (overlay) con credenciales en `sessionStorage`; todas las llamadas admin usan `Authorization: Basic`
  - Exportación CSV/JSON vía fetch con el header de auth (antes usaba `window.location.href`)
- Tests de autenticación (`tests/test_admin.py`): rechazo sin credenciales, credenciales incorrectas y acceso correcto; fixture `crear_nota` autenticado

### Cambiado
- `frontend/sw.js` — bump de caché a `avisador-v4` (cambió admin.html)
- `.env` / `.env.example` — nuevas variables `ADMIN_USER` y `ADMIN_PASSWORD`

### Pendiente (Fase 2)
- Tests de integraciones externas (Telegram/Email/Calendar con mocks)

## [1.7.0] — 2026-08-12

### Agregado
- Tests del scheduler de recordatorios (`tests/test_recordatorios.py`, 15 casos):
  - `_offsets_horas`: parsing válido, inválido y vacío (fallback a 24h)
  - `_notas_en_ventana`: incluye notas próximas y estados activos; excluye lejanas, vencidas, sin límite y completadas/canceladas
  - `revisar_recordatorios`: marca solo si el envío tuvo éxito, no duplica envíos, doble aviso 24h/1h y comportamiento sin canales (con mocks)

### Pendiente (Fase 2)
- Tests de integraciones externas (Telegram/Email/Calendar con mocks)

## [1.6.0] — 2026-08-12

### Agregado
- Integración Google Calendar activa y verificada (Fase D):
  - Dependencias instaladas: `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`
  - `config.py`: `GOOGLE_CREDENTIALS_FILE`/`GOOGLE_TOKEN_FILE` como rutas absolutas bajo `BASE_DIR`
  - Popups del evento alineados con `RECORDATORIO_ANTICIPACION_HORAS` (1440 y 60 min, máx 3)
  - `POST /api/admin/test-calendar` — crea evento de prueba y dispara el OAuth la primera vez
  - Flujo OAuth2 completado: `credentials.json` del proyecto `avisador-505404` + `token.json` generado
  - Verificado end-to-end: evento de prueba y evento real por cada nota (Email + Telegram + Calendar)

### Pendiente (Fase 2)
- Tests de integraciones externas (Telegram/Email/Calendar con mocks)

## [1.5.0] — 2026-08-12

### Agregado
- Integración Email (Gmail) activa y verificada (Fase C):
  - `POST /api/admin/test-email` — correo de prueba para validar SMTP
  - Refactor de `email_service.py`: `_construir_html` y `_construir_asunto` (alta vs recordatorio) + `enviar_email_recordatorio(nota, tipo)`
  - `EMAIL_HABILITADO=true` en `.env` con credenciales reales
  - Verificado end-to-end: test-email, notificación de alta y recordatorio por correo

### Pendiente (Fase 2)
- Tests de integraciones externas (Telegram/Email/Calendar con mocks)

## [1.4.0] — 2026-08-12

### Agregado
- Scheduler de recordatorios automáticos (Fase A):
  - APScheduler (`AsyncIOScheduler`) en el lifespan de FastAPI
  - Aviso de tareas próximas a vencer con anticipación configurable (`RECORDATORIO_ANTICIPACION_HORAS`, por defecto `24,1`)
  - Tabla `recordatorios_enviados` para evitar envíos duplicados por nota y tipo de aviso
  - `services/recordatorios.py` — consulta de ventana, envío por canales y registro solo en éxito
  - Avisos deshabilitables con `RECORDATORIOS_HABILITADO` e intervalo configurable (`RECORDATORIO_INTERVALO_MINUTOS`)
- Integración Telegram activa (Fase B):
  - Refactor de `telegram_service.py`: `_construir_texto` (alta vs recordatorio), `_enviar_mensaje`, `enviar_telegram_recordatorio(nota, tipo)`
  - `POST /api/admin/test-telegram` — mensaje de prueba para validar la configuración
  - Bot @Avisadorweb_bot configurado (token + chat_id) y verificado end-to-end (alta y recordatorio)
- `scripts/obtener_chat_id.py` — obtiene y guarda `TELEGRAM_CHAT_ID` en `.env` leyendo el token localmente (sin exponerlo)
- `PRAGMA foreign_keys=ON` en SQLite (`database.py`) para que `ON DELETE CASCADE` limpie `recordatorios_enviados` al borrar una nota

### Cambiado
- `requirements.txt` — agregado `apscheduler>=3.10,<4`
- `.env` / `.env.example` — nuevas variables de recordatorios; Telegram habilitado
- `tests/conftest.py` — desactiva scheduler y todas las integraciones externas en tests (evita envíos reales de Telegram/email)

### Pendiente (Fase 2)
- Integración Google Calendar (verificación de eventos y reminders)
- Autenticación básica para el panel admin (`HTTPBasic` en endpoints `/api/admin/`)
- Tests de recordatorios y de integraciones (con mocks)

## [1.3.0] — 2026-08-12

### Agregado
- Iconos PWA con diseño propio validados (ya no son rectángulos azules):
  - `icons/icon-192.png` y `icons/icon-512.png` con diseño a color
  - Fondo claro consistente con `background_color` del manifest
  - `purpose: "any maskable"` correcto en `manifest.json`

### Cambiado
- `sw.js` — bump de caché a `avisador-v3` con precache de `/icons/icon-192.png` y `/icons/icon-512.png` para que los usuarios con la PWA instalada refresquen el icono nuevo

## [1.0.0] — 2026-08-12

### Agregado
- Estructura completa del proyecto (backend + frontend + services + docs)
- API REST con FastAPI:
  - `POST /api/notas/` — crear nota con soporte multipart (audio + imagen)
  - `GET /api/notas/` — listar con filtros por estado y búsqueda, paginado
  - `GET /api/notas/{id}` — obtener nota por ID
  - `PATCH /api/notas/{id}` — actualizar campos de una nota
  - `DELETE /api/notas/{id}` — eliminar nota y sus archivos adjuntos
  - `GET /api/admin/stats/` — estadísticas generales
  - `GET /api/admin/notas/` — listado completo con filtros avanzados
  - `PATCH /api/admin/notas/{id}/estado` — cambio de estado inline
  - `DELETE /api/admin/notas/bulk` — eliminación masiva
  - `POST /api/admin/log-error` — registro de errores del cliente JS
- Base de datos SQLite con SQLAlchemy (offline-first)
- Almacenamiento de archivos en `uploads/audio/` y `uploads/imagenes/`
- Frontend PWA (Vanilla JS, sin frameworks):
  - Formulario móvil-first con grabación de audio en navegador
  - Captura de imagen desde cámara
  - Panel admin con tabla, filtros, estadísticas y modal de detalle
  - Service Worker con estrategia cache-first para assets, network-first para API
  - Cola offline con IndexedDB — sincroniza al reconectarse
  - Registro automático de errores JS al backend
- Servicios opcionales (deshabilitados hasta configurar .env):
  - Email HTML via smtplib
  - Bot Telegram via API REST
  - Google Calendar OAuth2
  - Transcripción de audio con OpenAI Whisper
- Logging con rotación de archivos (logs/errores.log)

## [1.2.0] — 2026-08-12

### Agregado
- Screenshots PWA en `frontend/screenshots/` (formulario móvil, admin móvil, admin desktop)
  - Generados automáticamente con Playwright (`scripts/generar_screenshots.py`)
  - Registrados en `manifest.json` con `form_factor` narrow/wide
  - Cacheados por el Service Worker (v2) para uso offline
- Exportación de notas a CSV y JSON (`GET /api/admin/notas/export`):
  - Respeta los filtros activos (búsqueda y estado)
  - CSV con BOM utf-8-sig y delimitador `;` para abrir directo en Excel
  - JSON estructurado con todos los campos de la nota
  - Descarga automática vía `Content-Disposition`
- Botones "Exportar CSV" y "Exportar JSON" en el panel admin
- Tests de exportación (6 casos nuevos)

## [1.1.0] — 2026-08-12

### Agregado
- Modo oscuro automático según el sistema operativo (`prefers-color-scheme`)
  - Toggle manual 🌙/☀️ en el header con persistencia en `localStorage`
  - Script anti-flash en `<head>` para evitar parpadeo de tema al cargar
  - Variables CSS semánticas migradas (`--fondo`, `--superficie`, `--borde`, `--texto`...)
- Tests automatizados con pytest (29 tests, SQLite en memoria aislada):
  - `tests/conftest.py` — fixtures con base de datos de test y override de `get_db`
  - `tests/test_notas.py` — 16 casos CRUD de notas
  - `tests/test_admin.py` — 12 casos de endpoints admin
- Validación de `asunto` y `motivo` vacíos en `POST /api/notas/` (antes no se validaba)

### Cambiado
- `requirements.txt` — descomentado `openai-whisper`; agregados `pytest`, `httpx`, `pytest-asyncio`
- `WHISPER_HABILITADO=true` en `.env` — transcripción de audio con Whisper activa
- Iconos PWA generados (`icons/icon-192.png`, `icons/icon-512.png`)

### Descartado
- Notificaciones push del navegador (descartado por requerir HTTPS/VAPID en PWA local; los recordatorios se enviarán por Telegram, Gmail o Google Calendar cuando estén configurados).

### Pendiente (Fase 2)
- Activar Google Calendar (deps + credenciales OAuth2)
- Configurar credenciales de email en `.env`
