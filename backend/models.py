"""
Modelos SQLAlchemy para el sistema AVISADOR.
Tabla principal: Nota — representa cada tarea/pendiente registrado.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from backend.database import Base


class Nota(Base):
    __tablename__ = "notas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Campos del formulario
    asunto = Column(String(500), nullable=False, comment="Objetivo de la tarea")
    motivo = Column(Text, nullable=False, comment="Justificación de la tarea")
    dependencias = Column(Text, nullable=False, comment="Lista de dependencias (JSON array como string)")
    lugar = Column(String(500), nullable=True, comment="Nombre o dirección del lugar")

    # Fechas
    f_inicio = Column(DateTime, nullable=False, default=datetime.utcnow, comment="Fecha/hora de inicio")
    limite = Column(DateTime, nullable=True, comment="Fecha/hora límite de la tarea")

    # Archivos adjuntos
    ruta_audio = Column(String(500), nullable=True, comment="Ruta relativa del audio en uploads/audio/")
    ruta_imagen = Column(String(500), nullable=True, comment="Ruta relativa de la imagen en uploads/imagenes/")

    # Transcripción del audio (Whisper, Fase 2 activa si disponible)
    transcripcion = Column(Text, nullable=True, comment="Texto transcrito del audio")

    # Estado de la nota
    estado = Column(String(50), nullable=False, default="pendiente", comment="pendiente | en_progreso | completada | cancelada")

    # Timestamps de auditoría
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Nota id={self.id} asunto='{self.asunto}' estado='{self.estado}'>"


class RecordatorioEnviado(Base):
    """Registro de recordatorios ya enviados por nota para evitar duplicados.

    Un mismo aviso (tipo, ej. '24h' o '1h') solo se envía una vez por nota.
    """

    __tablename__ = "recordatorios_enviados"
    __table_args__ = (
        UniqueConstraint("nota_id", "tipo", name="uq_recordatorio_nota_tipo"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    nota_id = Column(Integer, ForeignKey("notas.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False, comment="Horas de anticipación, ej. '24h' o '1h'")
    enviado_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<RecordatorioEnviado nota_id={self.nota_id} tipo='{self.tipo}'>"
