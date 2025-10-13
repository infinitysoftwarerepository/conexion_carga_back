from sqlalchemy.orm import Session
from . import models

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.User)
        .order_by(models.User.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user_in, password_hash: str):
    u = models.User(
        email=user_in.email,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        phone=user_in.phone,
        is_company=user_in.is_company,
        company_name=user_in.company_name,
        # 👇 este campo debe llamarse igual que en el modelo/DB
        password_hash=password_hash,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u
