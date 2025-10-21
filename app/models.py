from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import UUID
from .db import Base
import uuid

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "conexion_carga"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,                         # default en la app
        server_default=text("uuid_generate_v4()"),  # default en la BD
        nullable=False,
    )
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(120), nullable=False)
    last_name = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=True)

    is_company = Column(Boolean, nullable=False, server_default=text("false"))
    company_name = Column(String(255), nullable=True)

    active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())

    # ⬇️ NUEVO: sistema de referidos
    points = Column(Integer, nullable=False, server_default=text("0"))
    referred_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conexion_carga.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    referral_rewarded = Column(Boolean, nullable=False, server_default=text("false"))
