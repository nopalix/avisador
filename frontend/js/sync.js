/**
 * sync.js — Sincronización offline con IndexedDB
 * Guarda tareas en cola cuando no hay red y las reenvía al reconectarse.
 */

const DB_NAME = "avisador-offline";
const STORE = "cola";
const DB_VERSION = 1;

// ---------------------------------------------------------------------------
// Abrir / crear IndexedDB
// ---------------------------------------------------------------------------
function abrirDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
      }
    };
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror = (e) => reject(e.target.error);
  });
}

// ---------------------------------------------------------------------------
// Serializar FormData a objeto JSON (sin archivos binarios por ahora)
// Para blobs de audio/imagen los convertimos a base64.
// ---------------------------------------------------------------------------
async function formDataAObjeto(fd) {
  const obj = {};
  for (const [clave, valor] of fd.entries()) {
    if (valor instanceof Blob) {
      const b64 = await blobABase64(valor);
      obj[clave] = { __blob: true, data: b64, type: valor.type, name: valor.name || clave };
    } else {
      obj[clave] = valor;
    }
  }
  return obj;
}

function blobABase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function objetoAFormData(obj) {
  const fd = new FormData();
  for (const [clave, valor] of Object.entries(obj)) {
    if (valor && typeof valor === "object" && valor.__blob) {
      const arr = dataURLAUint8(valor.data);
      const blob = new Blob([arr], { type: valor.type });
      fd.append(clave, blob, valor.name);
    } else {
      fd.append(clave, valor);
    }
  }
  return fd;
}

function dataURLAUint8(dataURL) {
  const base64 = dataURL.split(",")[1];
  const binario = atob(base64);
  const arr = new Uint8Array(binario.length);
  for (let i = 0; i < binario.length; i++) arr[i] = binario.charCodeAt(i);
  return arr;
}

// ---------------------------------------------------------------------------
// Guardar en cola
// ---------------------------------------------------------------------------
export async function guardarEnCola(fd) {
  const db = await abrirDB();
  const objeto = await formDataAObjeto(fd);
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).add({ datos: objeto, timestamp: Date.now() });
    tx.oncomplete = resolve;
    tx.onerror = (e) => reject(e.target.error);
  });
}

// ---------------------------------------------------------------------------
// Obtener toda la cola
// ---------------------------------------------------------------------------
function obtenerCola(db) {
  return new Promise((resolve, reject) => {
    const req = db.transaction(STORE, "readonly").objectStore(STORE).getAll();
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror = (e) => reject(e.target.error);
  });
}

// ---------------------------------------------------------------------------
// Eliminar elemento de la cola
// ---------------------------------------------------------------------------
function eliminarDeCola(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).delete(id);
    tx.oncomplete = resolve;
    tx.onerror = (e) => reject(e.target.error);
  });
}

// ---------------------------------------------------------------------------
// Sincronizar cola → API
// ---------------------------------------------------------------------------
export async function sincronizarCola() {
  if (!navigator.onLine) return;

  let db;
  try {
    db = await abrirDB();
  } catch {
    return;
  }

  const items = await obtenerCola(db);
  if (items.length === 0) return;

  console.log(`[AVISADOR sync] ${items.length} tareas pendientes en cola...`);

  for (const item of items) {
    try {
      const fd = objetoAFormData(item.datos);
      const resp = await fetch("/api/notas/", { method: "POST", body: fd });
      if (resp.ok) {
        await eliminarDeCola(db, item.id);
        console.log(`[AVISADOR sync] Tarea ${item.id} sincronizada OK`);
      } else {
        console.warn(`[AVISADOR sync] Tarea ${item.id} falló con HTTP ${resp.status}`);
      }
    } catch (e) {
      console.warn(`[AVISADOR sync] Error al sincronizar tarea ${item.id}:`, e);
    }
  }
}
