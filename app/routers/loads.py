# app/routers/loads.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.security import get_current_user
from app import crud, schemas

router = APIRouter(prefix="/api/loads", tags=["Loads"])

@router.post("", response_model=schemas.CargoOut, status_code=status.HTTP_201_CREATED)
def create_load(payload: schemas.CargoCreate,
                db: Session = Depends(get_db),
                current = Depends(get_current_user)):
    return crud.create_cargo(db, payload, comercial_id=current.id)

@router.get("/mine", response_model=list[schemas.CargoOut])
def list_my_loads(skip: int = 0, limit: int = 100,
                  db: Session = Depends(get_db),
                  current = Depends(get_current_user)):
    return crud.get_my_cargas(db, current.id, skip=skip, limit=limit)
