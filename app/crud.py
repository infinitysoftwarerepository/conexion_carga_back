# app/crud.py
from __future__ import annotations
from typing import List, Optional
from uuid import UUID
from datetime import timedelta, datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models, schemas
from .security import get_password_hash

# =====================================================
# Helpers internos
# =====================================================


def _expire_if_needed(db: Session, items: List[models.Cargo]) -> None:
    """
    Recorre la lista de cargas y, si ya se pasó created_at + duracion_publicacion
    para un viaje ACTIVO, lo marca como inactivo (vencido).
    NO toca la columna 'estado' para no violar la constraint ck_carga_estado.
    """
    if not items:
        return

    now = datetime.now(timezone.utc)
    changed = False

    for c in items:
        # si ya está inactivo, no hacemos nada
        if not getattr(c, "activo", True):
            continue

        duration = getattr(c, "duracion_publicacion", None)
        created = getattr(c, "created_at", None)
        if not duration or not created:
            continue

        # normalizar a UTC para comparar
        if created.tzinfo is None:
            created_utc = created.replace(tzinfo=timezone.utc)
        else:
            created_utc = created.astimezone(timezone.utc)

        expires_at = created_utc + duration
        if expires_at <= now:
            # solo cambiamos 'activo'
            c.activo = False
            changed = True

    if changed:
        db.commit()


# =====================================================
# USERS
# =====================================================


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return (
        db.query(models.User)
        .order_by(models.User.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_user(db: Session, user_id: UUID) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return (
        db.query(models.User)
        .filter(func.lower(models.User.email) == func.lower(email.strip()))
        .first()
    )


def create_user(
    db: Session,
    user_in: schemas.UserCreate,
    password_hash: str,
    referred_by_id: Optional[UUID] = None,
) -> models.User:
    u = models.User(
        email=user_in.email.strip(),
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        phone=user_in.phone,
        is_company=user_in.is_company,
        company_name=user_in.company_name if user_in.is_company else None,
        password_hash=password_hash,
        active=False,
        referred_by_id=referred_by_id,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def update_user(
    db: Session, user_id: UUID, user_in: schemas.UserUpdate
) -> Optional[models.User]:
    u = get_user(db, user_id)
    if not u:
        return None
    for attr in ("email", "first_name", "last_name", "phone", "is_company", "company_name"):
        val = getattr(user_in, attr, None)
        if val is not None:
            setattr(u, attr, val)
    if user_in.is_company is False:
        u.company_name = None
    if user_in.password:
        u.password_hash = get_password_hash(user_in.password)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# =====================================================
# CARGAS
# =====================================================


def create_cargo(db: Session, data: schemas.CargoCreate, comercial_id):
    # 🟢 Por si quieres ver en logs qué llegó realmente:
    # print(f"[CREATE_CARGO] duration_hours payload = {data.duration_hours}")

    obj = models.Cargo(
        empresa_id=data.empresa_id,
        origen=data.origen,
        destino=data.destino,
        tipo_carga=data.tipo_carga,
        peso=data.peso,
        valor=data.valor,
        comercial_id=comercial_id,
        comercial=data.comercial,
        contacto=data.contacto,
        observaciones=data.observaciones,
        conductor=data.conductor,
        # vehiculo_id=data.vehiculo_id,  # ❌ ELIMINADO
        tipo_vehiculo=data.tipo_vehiculo,
        duracion_publicacion=timedelta(hours=int(data.duration_hours or 24)),
        activo=True,
        premium_trip=getattr(data, "premium_trip", False),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_cargo(db: Session, cargo_id: UUID) -> Optional[models.Cargo]:
    return db.query(models.Cargo).filter(models.Cargo.id == cargo_id).first()


def get_public_cargas(db: Session, skip=0, limit=100) -> List[models.Cargo]:
    """
    Devuelve solo viajes publicados y ACTIVOS.
    Antes de devolver, revisa si alguno ya venció (created_at + duracion_publicacion)
    y, si es así, lo marca como inactivo.
    """
    items = (
        db.query(models.Cargo)
        .filter(models.Cargo.estado == "publicado", models.Cargo.activo.is_(True))
        .order_by(models.Cargo.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    _expire_if_needed(db, items)

    # filtramos por si alguno cambió a inactivo dentro de esta misma llamada
    return [c for c in items if c.activo]


def get_my_cargas(
    db: Session, comercial_id, status: str = "all", skip=0, limit=100
):
    """
    Viajes del comercial.
    - all: todos (activos + inactivos)
    - published: solo activos
    - expired: solo inactivos (vencidos / eliminados lógicamente)
    """
    items = (
        db.query(models.Cargo)
        .filter(models.Cargo.comercial_id == comercial_id)
        .order_by(models.Cargo.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    _expire_if_needed(db, items)

    if status == "published":
        return [c for c in items if c.activo]
    if status == "expired":
        return [c for c in items if not c.activo]
    return items


def expire_cargo(db: Session, cargo_id: UUID, owner_id: UUID) -> Optional[models.Cargo]:
    """
    Soft-delete / vencimiento manual: marca el viaje como inactivo.
    NO cambia 'estado' para respetar la constraint ck_carga_estado.
    """
    c = get_cargo(db, cargo_id)
    if not c or c.comercial_id != owner_id:
        return None
    c.activo = False
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# 🔵 Reutilizar / republicar viaje (update parcial)
def reactivate_cargo(
    db: Session,
    cargo_id: UUID,
    owner_id: UUID,
    data: schemas.CargoUpdate,
) -> Optional[models.Cargo]:
    c = get_cargo(db, cargo_id)
    if not c or c.comercial_id != owner_id:
        return None

    # actualizar campos si vienen en el payload
    for attr in (
        "empresa_id",
        "origen",
        "destino",
        "tipo_carga",
        "peso",
        "valor",
        "comercial",
        "contacto",
        "observaciones",
        "conductor",
        "tipo_vehiculo",
    ):
        val = getattr(data, attr, None)
        if val is not None:
            setattr(c, attr, val)

    hours = data.duration_hours or 24
    c.duracion_publicacion = timedelta(hours=int(hours))

    # republicar => solo activar de nuevo y refrescar fechas
    c.activo = True
    now = datetime.utcnow()
    c.created_at = now
    c.updated_at = now

    db.add(c)
    db.commit()
    db.refresh(c)
    return c
