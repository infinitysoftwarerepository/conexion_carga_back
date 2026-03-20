from __future__ import annotations

import base64
import html
import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse


router = APIRouter(tags=["Public Referral"])

APP_NAME = "Conexión Carga"
ANDROID_PACKAGE_NAME = "com.infinitysoftware.conexioncarga"
ANDROID_STORE_URL = (
    "https://play.google.com/store/apps/details?id=com.infinitysoftware.conexioncarga"
)
BRAND_LOGO_PATH = (
    Path(__file__).resolve().parents[1]
    / "static"
    / "branding"
    / "logo-dark-full.png"
)


def _normalizar_ref(ref: str | None) -> str | None:
    valor = (ref or "").strip()
    return valor or None


def _construir_url_web(ref: str | None) -> str:
    if not ref:
        return "https://conexioncarga.com/register"
    return f"https://conexioncarga.com/register?{urlencode({'ref': ref})}"


def _construir_deep_link(ref: str | None) -> str:
    if not ref:
        return "conexioncarga://register"
    return f"conexioncarga://register?{urlencode({'ref': ref})}"


@lru_cache(maxsize=1)
def _cargar_logo_data_url() -> str | None:
    if not BRAND_LOGO_PATH.exists():
        return None

    contenido = BRAND_LOGO_PATH.read_bytes()
    if not contenido:
        return None

    b64 = base64.b64encode(contenido).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _render_register_page(ref: str | None) -> str:
    ref_normalizado = _normalizar_ref(ref)
    deep_link = html.escape(_construir_deep_link(ref_normalizado), quote=True)
    store_url = html.escape(ANDROID_STORE_URL, quote=True)
    brand_logo = _cargar_logo_data_url()
    app_icon_html = ""
    app_button_icon_html = '<span class="btn-icon btn-icon-app" aria-hidden="true">CC</span>'
    referido_html = ""

    if brand_logo:
        app_icon_html = f"""
            <div class="brand-mark">
                <img src="{html.escape(brand_logo, quote=True)}" alt="Conexión Carga" />
            </div>
        """
        app_button_icon_html = f"""
            <span class="btn-icon btn-icon-brand">
                <img src="{html.escape(brand_logo, quote=True)}" alt="" />
            </span>
        """

    if ref_normalizado:
        referido_html = f"""
            <div class="chip">Referido detectado: <strong>{html.escape(ref_normalizado)}</strong></div>
        """

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Registro con referido | {APP_NAME}</title>
    <meta
        name="description"
        content="Abre la app de Conexión Carga o descárgala desde Google Play para continuar el registro con referido."
    />
    <meta name="robots" content="noindex,nofollow" />
    <style>
        :root {{
            color-scheme: light;
            --bg: #f6f7fb;
            --card: #ffffff;
            --text: #172033;
            --muted: #5b6475;
            --line: #e7eaf1;
            --accent: #ff7800;
            --accent-strong: #cc6200;
            --accent-soft: #fff1e4;
            --shadow: 0 24px 60px rgba(23, 32, 51, 0.10);
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            padding: 24px;
            background:
                radial-gradient(circle at top right, rgba(255, 120, 0, 0.10), transparent 24%),
                linear-gradient(180deg, #fffdf9 0%, var(--bg) 100%);
            color: var(--text);
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        }}

        .card {{
            width: min(100%, 680px);
            background: var(--card);
            border: 1px solid rgba(255, 120, 0, 0.14);
            border-radius: 26px;
            padding: 32px 28px;
            box-shadow: var(--shadow);
        }}

        .eyebrow {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: var(--accent-soft);
            color: var(--accent);
            border-radius: 999px;
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }}

        .brand-mark {{
            width: min(100%, 240px);
            min-height: 78px;
            border-radius: 22px;
            overflow: hidden;
            display: grid;
            place-items: center;
            margin-bottom: 18px;
            background: #ffffff;
            border: 1px solid rgba(255, 120, 0, 0.12);
            box-shadow: 0 16px 34px rgba(23, 32, 51, 0.10);
        }}

        .brand-mark img {{
            display: block;
            width: 86%;
            height: auto;
            object-fit: contain;
        }}

        h1 {{
            margin: 18px 0 12px;
            font-size: clamp(2rem, 4vw, 2.8rem);
            line-height: 1.08;
        }}

        p {{
            margin: 0 0 14px;
            color: var(--muted);
            line-height: 1.7;
        }}

        .chip {{
            display: inline-flex;
            flex-wrap: wrap;
            gap: 8px;
            background: #f8fafc;
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 12px 14px;
            margin: 6px 0 18px;
            font-size: 14px;
        }}

        .actions {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 22px;
        }}

        .btn {{
            appearance: none;
            border: 0;
            border-radius: 14px;
            text-decoration: none;
            font-weight: 700;
            padding: 14px 18px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            transition: transform 0.18s ease, opacity 0.18s ease;
        }}

        .btn:hover {{
            transform: translateY(-1px);
        }}

        .btn-primary {{
            background: var(--accent);
            color: #ffffff;
        }}

        .btn-secondary {{
            background: #ffffff;
            color: var(--text);
            border: 1px solid var(--line);
        }}

        .small {{
            margin-top: 18px;
            font-size: 13px;
        }}

        .btn-icon {{
            width: 28px;
            height: 28px;
            flex: 0 0 28px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }}

        .btn-icon img,
        .btn-icon svg {{
            width: 100%;
            height: 100%;
            display: block;
        }}

        .btn-icon-brand {{
            width: 64px;
            height: 36px;
            flex: 0 0 64px;
            padding: 6px 8px;
            border-radius: 12px;
            background: #ffffff;
            box-shadow: inset 0 0 0 1px rgba(23, 32, 51, 0.08);
        }}

        .btn-icon-brand img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
        }}

        .btn-icon-store {{
            width: 36px;
            height: 36px;
            flex: 0 0 36px;
            padding: 6px;
            border-radius: 12px;
            background: #f5f7fb;
            box-shadow: inset 0 0 0 1px rgba(23, 32, 51, 0.06);
        }}

        .btn-label {{
            display: inline-flex;
            flex-direction: column;
            align-items: flex-start;
            line-height: 1.2;
            text-align: left;
        }}

        .btn-label small {{
            font-size: 12px;
            font-weight: 600;
            opacity: 0.84;
        }}

        .btn-icon-app {{
            width: 64px;
            height: 36px;
            flex: 0 0 64px;
            padding: 6px 8px;
            border-radius: 12px;
            background: #ffffff;
            color: var(--accent-strong);
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 0.04em;
            box-shadow: inset 0 0 0 1px rgba(23, 32, 51, 0.08);
        }}
    </style>
</head>
<body>
    <main class="card">
        {app_icon_html}
        <div class="eyebrow">Registro con referido</div>
        <h1>Continúa tu registro en {APP_NAME}</h1>
        <p>Este enlace está optimizado para Android. Si ya tienes la app instalada, intentaremos abrirla directamente en el formulario de registro.</p>
        <p>Si no tienes la app, te llevaremos a Google Play y luego podrás volver a continuar el proceso.</p>
        {referido_html}
        <div class="actions">
            <a class="btn btn-primary" href="{deep_link}">
                {app_button_icon_html}
                <span class="btn-label">
                    <span>Abrir app</span>
                    <small>Conexión Carga</small>
                </span>
            </a>
            <a class="btn btn-secondary" href="{store_url}">
                <span class="btn-icon btn-icon-store" aria-hidden="true">
                    <svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" role="img">
                        <path fill="#EA4335" d="M8 6l22.8 18L8 42z"/>
                        <path fill="#FBBC04" d="M30.8 24l5.8-4.6c2.7-2.1 2.7-4.7 0-6.8L30.8 8z"/>
                        <path fill="#34A853" d="M30.8 24L8 42l28.6-15.7c3.1-1.7 3.1-3 0-4.6z"/>
                        <path fill="#4285F4" d="M8 6l28.6 15.7c3.1 1.7 3.1 3 0 4.6L30.8 24z"/>
                    </svg>
                </span>
                <span class="btn-label">
                    <span>Descargar en Google Play</span>
                    <small>Instalar app</small>
                </span>
            </a>
        </div>
        <p class="small">Si la apertura automática no funciona, toca <strong>Abrir app</strong>. Si aún no la tienes instalada, usa <strong>Descargar en Google Play</strong> y, cuando termine la instalación, vuelve a abrir este mismo enlace para conservar el referido.</p>
    </main>

    <script>
        (function() {{
            var deepLink = "{deep_link}";
            var storeUrl = "{store_url}";
            var isAndroid = /android/i.test(navigator.userAgent || "");

            if (!isAndroid) {{
                return;
            }}

            var fallbackTimer = window.setTimeout(function() {{
                if (document.visibilityState !== "hidden") {{
                    window.location.replace(storeUrl);
                }}
            }}, 1600);

            document.addEventListener("visibilitychange", function() {{
                if (document.visibilityState === "hidden") {{
                    window.clearTimeout(fallbackTimer);
                }}
            }});

            window.location.href = deepLink;
        }})();
    </script>
</body>
</html>
"""


@router.get("/register", response_class=HTMLResponse, include_in_schema=False)
def register_referral_public(ref: str | None = Query(default=None)) -> HTMLResponse:
    return HTMLResponse(content=_render_register_page(ref), status_code=200)


@router.get(
    "/.well-known/assetlinks.json",
    response_class=JSONResponse,
    include_in_schema=False,
)
def android_asset_links() -> JSONResponse:
    raw = os.getenv("ANDROID_APP_SHA256_CERT_FINGERPRINTS", "")
    fingerprints = [item.strip().upper() for item in raw.split(",") if item.strip()]

    if not fingerprints:
        return JSONResponse(content=[], status_code=200)

    return JSONResponse(
        content=[
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                "target": {
                    "namespace": "android_app",
                    "package_name": ANDROID_PACKAGE_NAME,
                    "sha256_cert_fingerprints": fingerprints,
                },
            }
        ],
        status_code=200,
    )
