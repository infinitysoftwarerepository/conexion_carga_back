# app/models.py
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    Numeric,
    func,
    text,
    Interval,
)
from sqlalchemy.dialects.postgresql import UUID
from .db import Base
import uuid
from datetime import timedelta  # 🟢 usado en la propiedad duration_hours


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "conexion_carga"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
        nullable=False,
    )
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(120), nullable=False)
    last_name = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=True)

    is_company = Column(Boolean, nullable=False, server_default=text("false"))
    company_name = Column(String(255), nullable=True)
    is_premium = Column(Boolean, nullable=False, server_default=text("false"))
    active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )

    points = Column(Integer, nullable=False, server_default=text("0"))
    referred_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conexion_carga.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    referral_rewarded = Column(Boolean, nullable=False, server_default=text("false"))


class Cargo(Base):
    __tablename__ = "carga"
    __table_args__ = {"schema": "conexion_carga"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    empresa_id = Column(UUID(as_uuid=True), nullable=True)

    origen = Column(String, nullable=False)
    destino = Column(String, nullable=False)
    tipo_carga = Column(String, nullable=False)

    peso = Column(Numeric(10, 2), nullable=False)
    valor = Column(Integer, nullable=False)

    comercial_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conexion_carga.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    comercial = Column(String, nullable=True)
    contacto = Column(String, nullable=True)
    observaciones = Column(String, nullable=True)

    conductor = Column(String, nullable=True)
    # vehiculo_id = Column(String, nullable=True)  # ❌ ELIMINADO
    tipo_vehiculo = Column(String, nullable=True)

    # ↓ Fechas eliminadas previamente
    # fecha_salida
    # fecha_llegada_estimada

    estado = Column(String, nullable=False, server_default=text("'publicado'"))
    activo = Column(Boolean, nullable=False, server_default=text("true"))
    premium_trip = Column(Boolean, nullable=False, server_default=text("false"))

    # horas -> interval
    duracion_publicacion = Column(
        Interval, nullable=True, server_default=text("'24 hours'::interval")
    )

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now())

    # 🟢 NUEVO: propiedad para que Pydantic (CargoOut) vea duration_hours correcto
    @property
    def duration_hours(self) -> int:
        """
        Exponer 'duracion_publicacion' (interval) como entero de horas.
        Se usa solo para serializar respuesta (CargoOut) de forma consistente
        con lo que espera el frontend.
        """
        d = self.duracion_publicacion
        if not d:
            return 24  # mismo default que en el schema
        try:
            # En PostgreSQL Interval -> datetime.timedelta
            return int(d.total_seconds() // 3600)
        except Exception:
            return 24
