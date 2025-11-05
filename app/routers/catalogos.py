# app/routers/catalogos.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.db import get_db

router = APIRouter(prefix="/api/catalogos", tags=["Catálogos"])

# Utilidad: limpiar nombre
def _norm(s: str) -> str:
    return (s or "").strip()

@router.get("/municipios", response_model=List[str])
def lista_municipios(
    limit: int = Query(10000, ge=1, le=50000),
    db: Session = Depends(get_db),
):
    # Solo necesitamos nombres. Filtramos por activo si existe esa columna.
    sql = text("""
        SELECT nombre
        FROM municipio
        WHERE (activo IS NULL OR activo = TRUE)
        ORDER BY nombre ASC
        LIMIT :limit
    """)
    rows = db.execute(sql, {"limit": limit}).fetchall()
    return [r[0] for r in rows if r[0]]

@router.get("/tipos-carga", response_model=List[str])
def lista_tipos_carga(
    limit: int = Query(10000, ge=1, le=50000),
    db: Session = Depends(get_db),
):
    # Tabla: tipo_carga (columna 'nombre' y opcional 'activo')
    sql = text("""
        SELECT nombre
        FROM tipo_carga
        WHERE (activo IS NULL OR activo = TRUE)
        ORDER BY nombre ASC
        LIMIT :limit
    """)
    rows = db.execute(sql, {"limit": limit}).fetchall()
    return [r[0] for r in rows if r[0]]

@router.get("/tipos-vehiculo", response_model=List[str])
def lista_tipos_vehiculo(
    limit: int = Query(10000, ge=1, le=50000),
    db: Session = Depends(get_db),
):
    # Tabla: tipo_vehiculo (columna 'nombre' y opcional 'activo')
    sql = text("""
        SELECT nombre
        FROM tipo_vehiculo
        WHERE (activo IS NULL OR activo = TRUE)
        ORDER BY nombre ASC
        LIMIT :limit
    """)
    rows = db.execute(sql, {"limit": limit}).fetchall()
    return [r[0] for r in rows if r[0]]

# ─────────────────────────────────────────────────────────
# Altas "silenciosas": si el usuario escribe uno que no existe
# ─────────────────────────────────────────────────────────

@router.post("/tipos-carga", status_code=201)
def crear_tipo_carga(nombre: str, db: Session = Depends(get_db)):
    nombre = _norm(nombre)
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    # upsert simple por nombre
    sql_exists = text("SELECT 1 FROM tipo_carga WHERE LOWER(nombre)=LOWER(:n) LIMIT 1")
    if db.execute(sql_exists, {"n": nombre}).fetchone():
        return {"created": False, "nombre": nombre}  # ya existía
    sql_ins = text("INSERT INTO tipo_carga (nombre, activo) VALUES (:n, TRUE)")
    db.execute(sql_ins, {"n": nombre})
    db.commit()
    return {"created": True, "nombre": nombre}

@router.post("/tipos-vehiculo", status_code=201)
def crear_tipo_vehiculo(nombre: str, db: Session = Depends(get_db)):
    nombre = _norm(nombre)
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    sql_exists = text("SELECT 1 FROM tipo_vehiculo WHERE LOWER(nombre)=LOWER(:n) LIMIT 1")
    if db.execute(sql_exists, {"n": nombre}).fetchone():
        return {"created": False, "nombre": nombre}
    sql_ins = text("INSERT INTO tipo_vehiculo (nombre, activo) VALUES (:n, TRUE)")
    db.execute(sql_ins, {"n": nombre})
    db.commit()
    return {"created": True, "nombre": nombre}
