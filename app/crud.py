from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from . import models, schemas
from .security import get_password_hash


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
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(
    db: Session,
    user_in: schemas.UserCreate,
    password_hash: str,
    referred_by_id: Optional[UUID] = None,  # ⬅️ NUEVO parámetro
) -> models.User:
    u = models.User(
        email=user_in.email,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        phone=user_in.phone,
        is_company=user_in.is_company,
        company_name=user_in.company_name if user_in.is_company else None,
        password_hash=password_hash,
        active=False,
        referred_by_id=referred_by_id,  # ⬅️ guardar referidor (UUID) si aplica
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

    # Campos planos
    for attr in ("email", "first_name", "last_name", "phone", "is_company", "company_name"):
        value = getattr(user_in, attr)
        if value is not None:
            setattr(u, attr, value)

    # Si pasa is_company = False, company_name debe quedar en None
    if user_in.is_company is False:
        u.company_name = None

    # Cambio de password
    if user_in.password:
        u.password_hash = get_password_hash(user_in.password)

    db.add(u)
    db.commit()
    db.refresh(u)
    return u
