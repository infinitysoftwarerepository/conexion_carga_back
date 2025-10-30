# app/crud.py
from __future__ import annotations
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, literal
from fastapi import HTTPException, status

from . import models, schemas
from .security import get_password_hash


# ---------- USERS ----------
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
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ---------- CARGAS ----------

def _cargo_exists_same_info_active(db: Session, comercial_id: UUID, data: schemas.CargoCreate) -> bool:
    """
    Duplicado EXACTO de viaje ACTIVO, ignorando segundos/milisegundos/offset en fechas:
    - comercial_id
    - origen, destino, tipo_carga (lower + trim)
    - peso, valor (exactos)
    - fecha_salida TRUNCADA A MINUTO
    - fecha_llegada_estimada TRUNCADA A MINUTO (o ambas NULL)
    """
    # fecha_salida: trunc minuto en ambos lados
    salida_eq = func.date_trunc('minute', models.Cargo.fecha_salida) == func.date_trunc('minute', literal(data.fecha_salida))

    # fecha_llegada_estimada: caso NULL vs valor
    if data.fecha_llegada_estimada is None:
        llegada_eq = models.Cargo.fecha_llegada_estimada.is_(None)
    else:
        llegada_eq = func.date_trunc('minute', models.Cargo.fecha_llegada_estimada) == func.date_trunc('minute', literal(data.fecha_llegada_estimada))

    q = (
        db.query(models.Cargo.id)
        .filter(models.Cargo.comercial_id == comercial_id)
        .filter(func.lower(func.btrim(models.Cargo.origen)) == func.lower(func.btrim(data.origen)))
        .filter(func.lower(func.btrim(models.Cargo.destino)) == func.lower(func.btrim(data.destino)))
        .filter(func.lower(func.btrim(models.Cargo.tipo_carga)) == func.lower(func.btrim(data.tipo_carga)))
        .filter(models.Cargo.peso == data.peso)
        .filter(models.Cargo.valor == data.valor)
        .filter(salida_eq)
        .filter(llegada_eq)
        .filter(models.Cargo.activo.is_(True))
    )
    return db.query(q.exists()).scalar()


def create_cargo(db: Session, data: schemas.CargoCreate, comercial_id: UUID):
    # 1) Evitar spam/duplicados: comparar en minuto, no por segundo/ms
    if _cargo_exists_same_info_active(db, comercial_id, data):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tu viaje ya se encuentra creado."
        )

    # 2) Insertar
    obj = models.Cargo(
        empresa_id=data.empresa_id,
        origen=data.origen,
        destino=data.destino,
        tipo_carga=data.tipo_carga,
        peso=data.peso,
        valor=data.valor,
        comercial_id=comercial_id,
        conductor=data.conductor,
        vehiculo_id=data.vehiculo_id,
        tipo_vehiculo=data.tipo_vehiculo,
        fecha_salida=data.fecha_salida,
        fecha_llegada_estimada=data.fecha_llegada_estimada,
        activo=True,
        premium_trip=data.premium_trip,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_my_cargas(db: Session, comercial_id: UUID, skip=0, limit=100):
    return (
        db.query(models.Cargo)
        .filter(models.Cargo.comercial_id == comercial_id)
        .order_by(models.Cargo.created_at.desc())
        .offset(skip).limit(limit).all()
    )
