from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud, schemas, models
from .db import Base, engine, get_db
from .security import get_password_hash

# Crea tablas si hiciera falta
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Conexion Carga - Backend", openapi_url="/openapi.json")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajusta si quieres restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------ Health -------------
@app.get("/health")
def health():
    return {"ok": True}


# ------------ Users -------------
@app.get("/api/users", response_model=list[schemas.UserOut])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)


@app.post("/api/users/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Email único
    existing = crud.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    pw_hash = get_password_hash(user.password)
    created = crud.create_user(db, user, pw_hash)
    return created


@app.put("/api/users/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: UUID, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    # Si quiere cambiar el email, validar que no esté en uso por otro
    if user.email:
        existing = crud.get_user_by_email(db, user.email)
        if existing and existing.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use by another user",
            )

    updated = crud.update_user(db, user_id, user)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return updated
