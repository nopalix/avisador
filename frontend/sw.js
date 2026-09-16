/**
 * sw.js — Service Worker AVISADOR
 * Estrategia: Cache-first para assets estáticos, Network-first para API.
 */

const CACHE_VERSION = "avisador-v5";
const ASSETS_ESTATICOS = [
  "/",
  "/index.html",
  "/admin.html",
  "/css/styles.css",
  "/js/app.js",
  "/js/sync.js",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/screenshots/formulario-movil.png",
  "/screenshots/admin-movil.png",
  "/screenshots/admin-desktop.png",
];

// ---------------------------------------------------------------------------
// Install — precachear assets
// ---------------------------------------------------------------------------
self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(ASSETS_ESTATICOS))
  );
  self.skipWaiting();
});

// ---------------------------------------------------------------------------
// Activate — limpiar caches viejos
// ---------------------------------------------------------------------------
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// ---------------------------------------------------------------------------
// Fetch — estrategia según tipo de recurso
// ---------------------------------------------------------------------------
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // Peticiones a la API: Network-first.
  // GET /api/notas/ (lectura de la lista) se guarda en caché para poder
  // ver las notas sin conexión; el resto de la API devuelve 503 offline.
  if (url.pathname.startsWith("/api/")) {
    const esLecturaNotas = e.request.method === "GET" && url.pathname.startsWith("/api/notas/");

    if (!esLecturaNotas) {
      e.respondWith(fetch(e.request).catch(() =>
        new Response(JSON.stringify({ detail: "Sin conexión con el servidor" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        })
      ));
      return;
    }

    e.respondWith(
      fetch(e.request)
        .then((resp) => {
          if (resp.ok) {
            const clone = resp.clone();
            caches.open(CACHE_VERSION).then((cache) => cache.put(e.request, clone));
          }
          return resp;
        })
        .catch(() =>
          caches.match(e.request).then((cached) => {
            if (cached) return cached;
            return new Response(
              JSON.stringify({ detail: "Sin conexión con el servidor" }),
              { status: 503, headers: { "Content-Type": "application/json" } }
            );
          })
        )
    );
    return;
  }

  // Assets estáticos: Cache-first
  e.respondWith(
    caches.match(e.request).then((cached) => {
      if (cached) return cached;
      return fetch(e.request).then((resp) => {
        // Solo cachear respuestas exitosas de origen propio
        if (resp.ok && url.origin === self.location.origin) {
          const clone = resp.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(e.request, clone));
        }
        return resp;
      });
    })
  );
});
