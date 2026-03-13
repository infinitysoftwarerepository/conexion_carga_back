# app/main.py
"""
Entrypoint principal: inicializa DB, CORS y monta routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import Base, engine
from app.routers import (
    users,
    auth,
    loads,
    catalogos,
    dashboard_admin,
    public_pages,
    recaptcha,
    viajes_admin,
    usuarios_admin,
)  # 👈 router admin agregado sin tocar contratos existentes

# Inicializar tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Conexión Carga - Backend",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True},  # recuerda el Bearer en /docs
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True, "message": "API running"}


# Montar routers
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(loads.router)
app.include_router(catalogos.router)  # 👈 agregado para municipios, tipo_
app.include_router(public_pages.router)  # 👈 pagina publica /privacidad en HTML
app.include_router(recaptcha.router)  # ✅ /recaptcha (checkbox "No soy un robot")
app.include_router(dashboard_admin.router)  # 👈 endpoints admin dashboard (add-only)
app.include_router(viajes_admin.router)  # 👈 endpoints admin viajes (add-only)
app.include_router(usuarios_admin.router)  # 👈 endpoints admin usuarios (add-only)
