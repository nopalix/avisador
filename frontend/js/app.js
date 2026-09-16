/**
 * app.js — Lógica principal del formulario AVISADOR
 * Módulo ES2020, sin dependencias externas.
 */

import { sincronizarCola } from "./sync.js";

const API = "/api";

// ---------------------------------------------------------------------------
// Estado
// ---------------------------------------------------------------------------
const estado = {
  dependencias: [],
  audioBlob: null,
  audioMime: "audio/webm",
  imagenFile: null,
  grabando: false,
  mediaRecorder: null,
  chunks: [],
  timerInterval: null,
  segundos: 0,
};

// ---------------------------------------------------------------------------
// Utilidades DOM
// ---------------------------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const err = (id, msg) => { $(id).textContent = msg; };
const limpiarErrores = () => {
  ["#err-asunto", "#err-motivo", "#err-deps"].forEach((s) => err(s, ""));
  ["#asunto", "#motivo"].forEach((s) => $(`${s}`)?.classList.remove("error"));
};

// ---------------------------------------------------------------------------
// Offline banner
// ---------------------------------------------------------------------------
function actualizarBannerOffline() {
  const banner = $("#offline-banner");
  if (!navigator.onLine) banner.removeAttribute("hidden");
  else banner.setAttribute("hidden", "");
}
window.addEventListener("online", async () => {
  actualizarBannerOffline();
  await sincronizarCola();
  cargarRecientes();
});
window.addEventListener("offline", actualizarBannerOffline);
actualizarBannerOffline();

// ---------------------------------------------------------------------------
// Dependencias (tags)
// ---------------------------------------------------------------------------
function renderDeps() {
  const cont = $("#deps-container");
  cont.innerHTML = "";
  estado.dependencias.forEach((dep, i) => {
    const tag = document.createElement("span");
    tag.className = "dep-tag";
    tag.innerHTML = `${dep} <button type="button" aria-label="Eliminar" data-i="${i}">&times;</button>`;
    tag.querySelector("button").addEventListener("click", () => {
      estado.dependencias.splice(i, 1);
      renderDeps();
    });
    cont.appendChild(tag);
  });
}

function agregarDep() {
  const input = $("#dep-input");
  const val = input.value.trim();
  if (!val) return;
  if (!estado.dependencias.includes(val)) {
    estado.dependencias.push(val);
    renderDeps();
  }
  input.value = "";
  input.focus();
}

$("#dep-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); agregarDep(); }
});
$("#btn-add-dep").addEventListener("click", agregarDep);

// ---------------------------------------------------------------------------
// Grabación de audio
// ---------------------------------------------------------------------------
async function toggleGrabacion() {
  if (estado.grabando) {
    detenerGrabacion();
  } else {
    await iniciarGrabacion();
  }
}

async function iniciarGrabacion() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/ogg";
    estado.audioMime = mime;
    estado.chunks = [];
    estado.mediaRecorder = new MediaRecorder(stream, { mimeType: mime });

    estado.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) estado.chunks.push(e.data);
    };
    estado.mediaRecorder.onstop = () => {
      estado.audioBlob = new Blob(estado.chunks, { type: estado.audioMime });
      const url = URL.createObjectURL(estado.audioBlob);
      const audio = $("#preview-audio");
      audio.src = url;
      audio.removeAttribute("hidden");
      $("#btn-limpiar-audio").removeAttribute("hidden");
      stream.getTracks().forEach((t) => t.stop());
    };

    estado.mediaRecorder.start();
    estado.grabando = true;
    estado.segundos = 0;
    actualizarUI_grabando();

    estado.timerInterval = setInterval(() => {
      estado.segundos++;
      const m = Math.floor(estado.segundos / 60);
      const s = String(estado.segundos % 60).padStart(2, "0");
      $("#timer-audio").textContent = `${m}:${s}`;
    }, 1000);
  } catch (e) {
    alert("No se pudo acceder al micrófono: " + e.message);
  }
}

function detenerGrabacion() {
  estado.mediaRecorder?.stop();
  estado.grabando = false;
  clearInterval(estado.timerInterval);
  actualizarUI_grabando();
}

function actualizarUI_grabando() {
  const btn = $("#btn-grabar");
  const timer = $("#timer-audio");
  if (estado.grabando) {
    btn.classList.add("grabando");
    btn.innerHTML = `<span>&#9634;</span> Detener`;
    timer.removeAttribute("hidden");
  } else {
    btn.classList.remove("grabando");
    btn.innerHTML = `<span>&#127908;</span> Grabar`;
    timer.setAttribute("hidden", "");
  }
}

$("#btn-grabar").addEventListener("click", toggleGrabacion);

$("#btn-limpiar-audio").addEventListener("click", () => {
  estado.audioBlob = null;
  const audio = $("#preview-audio");
  audio.src = "";
  audio.setAttribute("hidden", "");
  $("#btn-limpiar-audio").setAttribute("hidden", "");
  $("#audio-file").value = "";
});

// Subida directa de archivo de audio
$("#audio-file").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  estado.audioBlob = file;
  estado.audioMime = file.type;
  const url = URL.createObjectURL(file);
  const audio = $("#preview-audio");
  audio.src = url;
  audio.removeAttribute("hidden");
  $("#btn-limpiar-audio").removeAttribute("hidden");
});

// ---------------------------------------------------------------------------
// Imagen
// ---------------------------------------------------------------------------
$("#imagen-file").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  estado.imagenFile = file;
  const img = $("#preview-imagen");
  img.src = URL.createObjectURL(file);
  img.removeAttribute("hidden");
  $("#btn-limpiar-imagen").removeAttribute("hidden");
});

$("#btn-limpiar-imagen").addEventListener("click", () => {
  estado.imagenFile = null;
  const img = $("#preview-imagen");
  img.src = "";
  img.setAttribute("hidden", "");
  $("#btn-limpiar-imagen").setAttribute("hidden", "");
  $("#imagen-file").value = "";
});

// ---------------------------------------------------------------------------
// Validación del formulario
// ---------------------------------------------------------------------------
function validar() {
  let ok = true;
  limpiarErrores();

  const asunto = $("#asunto").value.trim();
  if (!asunto) {
    err("#err-asunto", "El asunto es obligatorio");
    $("#asunto").classList.add("error");
    ok = false;
  }

  const motivo = $("#motivo").value.trim();
  if (!motivo) {
    err("#err-motivo", "El motivo es obligatorio");
    $("#motivo").classList.add("error");
    ok = false;
  }

  if (estado.dependencias.length === 0) {
    err("#err-deps", "Agrega al menos una dependencia");
    ok = false;
  }

  return ok;
}

// ---------------------------------------------------------------------------
// Construcción del FormData
// ---------------------------------------------------------------------------
function construirFormData() {
  const fd = new FormData();
  fd.append("asunto", $("#asunto").value.trim());
  fd.append("motivo", $("#motivo").value.trim());
  fd.append("dependencias", JSON.stringify(estado.dependencias));

  const lugar = $("#lugar").value.trim();
  if (lugar) fd.append("lugar", lugar);

  const fInicio = $("#f_inicio").value;
  if (fInicio) fd.append("f_inicio", new Date(fInicio).toISOString());

  const limite = $("#limite").value;
  if (limite) fd.append("limite", new Date(limite).toISOString());

  if (estado.audioBlob) {
    const ext = estado.audioMime.includes("ogg") ? "ogg" : "webm";
    fd.append("audio", estado.audioBlob, `audio.${ext}`);
  }

  if (estado.imagenFile) {
    fd.append("imagen", estado.imagenFile, estado.imagenFile.name);
  }

  return fd;
}

// ---------------------------------------------------------------------------
// Mostrar resultado
// ---------------------------------------------------------------------------
function mostrarResultado(msg, tipo = "ok") {
  const div = $("#resultado");
  div.textContent = msg;
  div.className = `resultado ${tipo}`;
  div.removeAttribute("hidden");
  setTimeout(() => div.setAttribute("hidden", ""), 5000);
}

// ---------------------------------------------------------------------------
// Resetear formulario
// ---------------------------------------------------------------------------
function resetearFormulario() {
  $("#form-nota").reset();
  estado.dependencias = [];
  estado.audioBlob = null;
  estado.imagenFile = null;
  renderDeps();
  $("#preview-audio").setAttribute("hidden", "");
  $("#btn-limpiar-audio").setAttribute("hidden", "");
  $("#preview-imagen").setAttribute("hidden", "");
  $("#btn-limpiar-imagen").setAttribute("hidden", "");
  limpiarErrores();
}

// ---------------------------------------------------------------------------
// Envío del formulario
// ---------------------------------------------------------------------------
$("#form-nota").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!validar()) return;

  const btn = $("#btn-submit");
  btn.disabled = true;
  btn.textContent = "Guardando...";

  const fd = construirFormData();

  if (!navigator.onLine) {
    // Guardar en cola offline (IndexedDB via sync.js)
    const { guardarEnCola } = await import("./sync.js");
    await guardarEnCola(fd);
    mostrarResultado("Sin conexión — tarea guardada localmente. Se enviará al reconectarse.", "ok");
    resetearFormulario();
    btn.disabled = false;
    btn.textContent = "Guardar tarea";
    return;
  }

  try {
    const resp = await fetch(`${API}/notas/`, { method: "POST", body: fd });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.detail || `Error ${resp.status}`);
    }
    mostrarResultado("Tarea guardada correctamente.", "ok");
    resetearFormulario();
    cargarRecientes();
  } catch (ex) {
    mostrarResultado(`Error al guardar: ${ex.message}`, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "Guardar tarea";
  }
});

// ---------------------------------------------------------------------------
// Lista de notas recientes
// ---------------------------------------------------------------------------
async function cargarRecientes() {
  const cont = $("#lista-notas");
  cont.innerHTML = `<p class="placeholder">Cargando...</p>`;

  try {
    const resp = await fetch(`${API}/notas/?page=1&page_size=10`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    if (!data.items || data.items.length === 0) {
      cont.innerHTML = `<p class="placeholder">No hay tareas registradas aún.</p>`;
      return;
    }

    cont.innerHTML = "";
    data.items.forEach((nota) => {
      const item = document.createElement("div");
      item.className = "nota-item";
      const fecha = new Date(nota.creado_en).toLocaleDateString("es-ES", {
        day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
      });
      item.innerHTML = `
        <div class="nota-item-left">
          <div class="nota-item-asunto">${nota.asunto}</div>
          <div class="nota-item-motivo">${nota.motivo}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:.3rem">
          <span class="badge badge-${nota.estado}">${nota.estado.replace("_", " ")}</span>
          <span class="nota-item-fecha">${fecha}</span>
        </div>
      `;
      cont.appendChild(item);
    });
  } catch (ex) {
    cont.innerHTML = `<p class="placeholder" style="color:var(--rojo)">Error al cargar: ${ex.message}</p>`;
  }
}

$("#btn-refresh").addEventListener("click", cargarRecientes);

// ---------------------------------------------------------------------------
// Registro de errores JS no controlados → backend
// ---------------------------------------------------------------------------
window.addEventListener("error", (e) => {
  fetch(`${API}/admin/log-error`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mensaje: e.message,
      origen: e.filename,
      linea: e.lineno,
      userAgent: navigator.userAgent,
    }),
  }).catch(() => {});
});

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
renderDeps();
cargarRecientes();

// Registrar Service Worker
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
