from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine, get_db
from . import crud, schemas, models
from .security import get_password_hash

app = FastAPI(
    title="Conexión Carga API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS abierto en desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/api/users", response_model=list[schemas.UserOut])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return [schemas.UserOut.model_validate(u) for u in users]

@app.post("/api/users/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if user.password != user.confirm_password:
        raise HTTPException(status_code=422, detail="Las contraseñas no coinciden")

    if user.is_company and not user.company_name:
        raise HTTPException(status_code=422, detail="company_name es obligatorio cuando is_company=true")

    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=409, detail="El email ya está registrado")

    pw_hash = get_password_hash(user.password)
    created = crud.create_user(db, user, pw_hash)
    return schemas.UserOut.model_validate(created)
