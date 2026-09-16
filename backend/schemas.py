"""
Schemas Pydantic para validación de entrada/salida de la API AVISADOR.
"""

import json
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Schema de creación (entrada del formulario)
# ---------------------------------------------------------------------------

class NotaCreate(BaseModel):
    asunto: str
    motivo: str
    dependencias: List[str]
    lugar: Optional[str] = None
    f_inicio: Optional[datetime] = None   # si no se envía, se asigna la hora actual en el router
    limite: Optional[datetime] = None

    @field_validator("asunto")
    @classmethod
    def asunto_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El asunto no puede estar vacío")
        return v

    @field_validator("motivo")
    @classmethod
    def motivo_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El motivo no puede estar vacío")
        return v

    @field_validator("dependencias")
    @classmethod
    def dependencias_no_vacias(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Debe indicar al menos una dependencia")
        return [d.strip() for d in v if d.strip()]


# ---------------------------------------------------------------------------
# Schema de actualización (todos los campos opcionales para PATCH)
# ---------------------------------------------------------------------------

class NotaUpdate(BaseModel):
    asunto: Optional[str] = None
    motivo: Optional[str] = None
    dependencias: Optional[List[str]] = None
    lugar: Optional[str] = None
    f_inicio: Optional[datetime] = None
    limite: Optional[datetime] = None
    estado: Optional[str] = None

    @field_validator("estado")
    @classmethod
    def estado_valido(cls, v: Optional[str]) -> Optional[str]:
        estados_validos = {"pendiente", "en_progreso", "completada", "cancelada"}
        if v and v not in estados_validos:
            raise ValueError(f"Estado inválido. Valores permitidos: {estados_validos}")
        return v


# ---------------------------------------------------------------------------
# Schema de respuesta (salida de la API)
# ---------------------------------------------------------------------------

class NotaResponse(BaseModel):
    id: int
    asunto: str
    motivo: str
    dependencias: List[str]
    lugar: Optional[str]
    f_inicio: datetime
    limite: Optional[datetime]
    ruta_audio: Optional[str]
    ruta_imagen: Optional[str]
    transcripcion: Optional[str]
    estado: str
    creado_en: datetime
    actualizado_en: datetime

    @field_validator("dependencias", mode="before")
    @classmethod
    def parse_dependencias(cls, v):
        """El modelo almacena dependencias como JSON string; aquí lo convertimos a lista."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return [v]
        return v

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Schema de respuesta paginada
# ---------------------------------------------------------------------------

class NotaListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[NotaResponse]
