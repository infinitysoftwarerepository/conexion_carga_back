# app/routers/catalogos.py
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db

router = APIRouter(prefix="/api/catalogos", tags=["Catálogos"])


FALLBACK_COUNTRY_CODES = [
    {"id": 1, "name": "Colombia", "iso2": "CO", "phone_code": "+57", "flag_emoji": "🇨🇴"},
    {"id": 2, "name": "México", "iso2": "MX", "phone_code": "+52", "flag_emoji": "🇲🇽"},
    {"id": 3, "name": "Argentina", "iso2": "AR", "phone_code": "+54", "flag_emoji": "🇦🇷"},
    {"id": 4, "name": "Chile", "iso2": "CL", "phone_code": "+56", "flag_emoji": "🇨🇱"},
    {"id": 5, "name": "Perú", "iso2": "PE", "phone_code": "+51", "flag_emoji": "🇵🇪"},
    {"id": 6, "name": "Ecuador", "iso2": "EC", "phone_code": "+593", "flag_emoji": "🇪🇨"},
    {"id": 7, "name": "Venezuela", "iso2": "VE", "phone_code": "+58", "flag_emoji": "🇻🇪"},
    {"id": 8, "name": "Bolivia", "iso2": "BO", "phone_code": "+591", "flag_emoji": "🇧🇴"},
    {"id": 9, "name": "Paraguay", "iso2": "PY", "phone_code": "+595", "flag_emoji": "🇵🇾"},
    {"id": 10, "name": "Uruguay", "iso2": "UY", "phone_code": "+598", "flag_emoji": "🇺🇾"},
    {"id": 11, "name": "Brasil", "iso2": "BR", "phone_code": "+55", "flag_emoji": "🇧🇷"},
    {"id": 12, "name": "Panamá", "iso2": "PA", "phone_code": "+507", "flag_emoji": "🇵🇦"},
    {"id": 13, "name": "Costa Rica", "iso2": "CR", "phone_code": "+506", "flag_emoji": "🇨🇷"},
    {"id": 14, "name": "Guatemala", "iso2": "GT", "phone_code": "+502", "flag_emoji": "🇬🇹"},
    {"id": 15, "name": "El Salvador", "iso2": "SV", "phone_code": "+503", "flag_emoji": "🇸🇻"},
    {"id": 16, "name": "Honduras", "iso2": "HN", "phone_code": "+504", "flag_emoji": "🇭🇳"},
    {"id": 17, "name": "Nicaragua", "iso2": "NI", "phone_code": "+505", "flag_emoji": "🇳🇮"},
    {"id": 18, "name": "República Dominicana", "iso2": "DO", "phone_code": "+1", "flag_emoji": "🇩🇴"},
    {"id": 19, "name": "Estados Unidos", "iso2": "US", "phone_code": "+1", "flag_emoji": "🇺🇸"},
    {"id": 20, "name": "Canadá", "iso2": "CA", "phone_code": "+1", "flag_emoji": "🇨🇦"},
    {"id": 21, "name": "España", "iso2": "ES", "phone_code": "+34", "flag_emoji": "🇪🇸"},
    {"id": 22, "name": "Francia", "iso2": "FR", "phone_code": "+33", "flag_emoji": "🇫🇷"},
    {"id": 23, "name": "Alemania", "iso2": "DE", "phone_code": "+49", "flag_emoji": "🇩🇪"},
    {"id": 24, "name": "Italia", "iso2": "IT", "phone_code": "+39", "flag_emoji": "🇮🇹"},
    {"id": 25, "name": "Reino Unido", "iso2": "GB", "phone_code": "+44", "flag_emoji": "🇬🇧"},
]


# Utilidad: limpiar nombre
def _norm(s: str) -> str:
    return (s or "").strip()


def _tiene_tabla_country_codes(db: Session) -> bool:
    return bool(
        db.execute(text("SELECT to_regclass('conexion_carga.country_codes') IS NOT NULL")).scalar()
    )


@router.get('/country-codes', response_model=List[schemas.CountryCodeOut])
def lista_country_codes(db: Session = Depends(get_db)):
    if not _tiene_tabla_country_codes(db):
        return FALLBACK_COUNTRY_CODES

    rows = db.execute(
        text(
            """
            SELECT id, name, iso2, phone_code, flag_emoji
            FROM conexion_carga.country_codes
            ORDER BY CASE WHEN UPPER(iso2) = 'CO' THEN 0 ELSE 1 END, name ASC
            """
        )
    ).mappings().all()

    if not rows:
        return FALLBACK_COUNTRY_CODES

    return [schemas.CountryCodeOut(**dict(row)) for row in rows]


@router.get("/municipios", response_model=List[str])
def lista_municipios(
    limit: int = Query(10000, ge=1, le=50000),
    db: Session = Depends(get_db),
):
    sql = text(
        """
        SELECT nombre
        FROM conexion_carga.municipio
        WHERE (activo IS NULL OR activo = TRUE)
        ORDER BY nombre ASC
        LIMIT :limit
        """
    )
    rows = db.execute(sql, {"limit": limit}).fetchall()
    return [r[0] for r in rows if r[0]]


@router.get("/tipos-carga", response_model=List[str])
def lista_tipos_carga(
    limit: int = Query(10000, ge=1, le=50000),
    db: Session = Depends(get_db),
):
    sql = text(
        """
        SELECT nombre
        FROM conexion_carga.tipo_carga
        WHERE (activo IS NULL OR activo = TRUE)
        ORDER BY nombre ASC
        LIMIT :limit
        """
    )
    rows = db.execute(sql, {"limit": limit}).fetchall()
    return [r[0] for r in rows if r[0]]


@router.get("/tipos-vehiculo", response_model=List[str])
def lista_tipos_vehiculo(
    limit: int = Query(10000, ge=1, le=50000),
    db: Session = Depends(get_db),
):
    sql = text(
        """
        SELECT nombre
        FROM conexion_carga.tipo_vehiculo
        WHERE (activo IS NULL OR activo = TRUE)
        ORDER BY nombre ASC
        LIMIT :limit
        """
    )
    rows = db.execute(sql, {"limit": limit}).fetchall()
    return [r[0] for r in rows if r[0]]


@router.post("/tipos-carga", status_code=201)
def crear_tipo_carga(nombre: str, db: Session = Depends(get_db)):
    nombre = _norm(nombre)
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre requerido")

    sql_exists = text(
        "SELECT 1 FROM conexion_carga.tipo_carga WHERE LOWER(nombre)=LOWER(:n) LIMIT 1"
    )
    if db.execute(sql_exists, {"n": nombre}).fetchone():
        return {"created": False, "nombre": nombre}

    sql_ins = text(
        "INSERT INTO conexion_carga.tipo_carga (nombre, activo) VALUES (:n, TRUE)"
    )
    db.execute(sql_ins, {"n": nombre})
    db.commit()
    return {"created": True, "nombre": nombre}


@router.post("/tipos-vehiculo", status_code=201)
def crear_tipo_vehiculo(nombre: str, db: Session = Depends(get_db)):
    nombre = _norm(nombre)
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre requerido")

    sql_exists = text(
        "SELECT 1 FROM conexion_carga.tipo_vehiculo WHERE LOWER(nombre)=LOWER(:n) LIMIT 1"
    )
    if db.execute(sql_exists, {"n": nombre}).fetchone():
        return {"created": False, "nombre": nombre}

    sql_ins = text(
        "INSERT INTO conexion_carga.tipo_vehiculo (nombre, activo) VALUES (:n, TRUE)"
    )
    db.execute(sql_ins, {"n": nombre})
    db.commit()
    return {"created": True, "nombre": nombre}
