# app/routers/loads.py
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.security import get_current_user
from app import crud, schemas, models

router = APIRouter(prefix="/api/loads", tags=["Loads"])

# Crear
@router.post("", response_model=schemas.CargoOut, status_code=status.HTTP_201_CREATED)
def create_load(payload: schemas.CargoCreate,
                db: Session = Depends(get_db),
                current: models.User = Depends(get_current_user)):
    return crud.create_cargo(db, payload, comercial_id=current.id)

# Listar PÚBLICOS (portada)
@router.get("/public", response_model=List[schemas.CargoOut])
def list_public(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_public_cargas(db, skip=skip, limit=limit)

# Mis viajes (status = all|published|expired)
@router.get("/mine", response_model=List[schemas.CargoOut])
def list_my_loads(status: str = Query("all", pattern="^(all|published|expired)$"),
                  skip: int = 0, limit: int = 100,
                  db: Session = Depends(get_db),
                  current: models.User = Depends(get_current_user)):
    return crud.get_my_cargas(db, current.id, status=status, skip=skip, limit=limit)

# Detalle
@router.get("/{load_id}", response_model=schemas.CargoOut)
def get_one(load_id: str,
            db: Session = Depends(get_db)):
    obj = crud.get_cargo(db, load_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Viaje no encontrado.")
    return obj

# Caducar (eliminar a “historial”)
@router.post("/{load_id}/expire", response_model=schemas.CargoOut)
def expire(load_id: str,
           db: Session = Depends(get_db),
           current: models.User = Depends(get_current_user)):
    obj = crud.expire_cargo(db, load_id, owner_id=current.id)
    if not obj:
        raise HTTPException(status_code=404, detail="No encontrado o sin permisos.")
    return obj
