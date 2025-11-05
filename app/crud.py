# app/crud.py
from __future__ import annotations
from typing import List, Optional
from uuid import UUID
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from . import models, schemas
from .security import get_password_hash

# ---------- USERS ----------
def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return (
        db.query(models.User)
        .order_by(models.User.created_at.desc())
        .offset(skip).limit(limit).all()
    )

def get_user(db: Session, user_id: UUID) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return (
        db.query(models.User)
        .filter(func.lower(models.User.email) == func.lower(email.strip()))
        .first()
    )

def create_user(db: Session, user_in: schemas.UserCreate, password_hash: str,
                referred_by_id: Optional[UUID] = None) -> models.User:
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
    db.add(u); db.commit(); db.refresh(u)
    return u

def update_user(db: Session, user_id: UUID, user_in: schemas.UserUpdate) -> Optional[models.User]:
    u = get_user(db, user_id)
    if not u:
        return None
    for attr in ("email","first_name","last_name","phone","is_company","company_name"):
        val = getattr(user_in, attr, None)
        if val is not None:
            setattr(u, attr, val)
    if user_in.is_company is False:
        u.company_name = None
    if user_in.password:
        u.password_hash = get_password_hash(user_in.password)
    db.add(u); db.commit(); db.refresh(u)
    return u

# ---------- CARGAS ----------
def create_cargo(db: Session, data: schemas.CargoCreate, comercial_id):
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
        vehiculo_id=data.vehiculo_id,
        tipo_vehiculo=data.tipo_vehiculo,
        # ❌ fechas removidas
        # ⏱️ guardar como INTERVAL
        duracion_publicacion=timedelta(hours=int(data.duration_hours or 24)),
        activo=True,
        premium_trip=data.premium_trip if hasattr(data, "premium_trip") else False,
    )
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

def get_cargo(db: Session, cargo_id: UUID) -> Optional[models.Cargo]:
    return db.query(models.Cargo).filter(models.Cargo.id == cargo_id).first()

def get_public_cargas(db: Session, skip=0, limit=100) -> List[models.Cargo]:
    return (
        db.query(models.Cargo)
        .filter(models.Cargo.estado == "publicado", models.Cargo.activo.is_(True))
        .order_by(models.Cargo.created_at.desc())
        .offset(skip).limit(limit).all()
    )

def get_my_cargas(db: Session, comercial_id, status: str = "all", skip=0, limit=100):
    q = db.query(models.Cargo).filter(models.Cargo.comercial_id == comercial_id)
    if status == "published":
        q = q.filter(models.Cargo.estado == "publicado", models.Cargo.activo.is_(True))
    elif status == "expired":
        q = q.filter(or_(models.Cargo.estado == "caducado",
                         models.Cargo.estado == "eliminado",
                         models.Cargo.activo.is_(False)))
    return (
        q.order_by(models.Cargo.created_at.desc())
         .offset(skip).limit(limit).all()
    )

def expire_cargo(db: Session, cargo_id: UUID, owner_id: UUID) -> Optional[models.Cargo]:
    c = get_cargo(db, cargo_id)
    if not c or c.comercial_id != owner_id:
        return None
    c.estado = "caducado"
    c.activo = False
    db.add(c); db.commit(); db.refresh(c)
    return c
