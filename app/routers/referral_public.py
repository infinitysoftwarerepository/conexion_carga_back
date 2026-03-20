from __future__ import annotations

import html
import os
from urllib.parse import urlencode

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse


router = APIRouter(tags=["Public Referral"])

APP_NAME = "Conexión Carga"
ANDROID_PACKAGE_NAME = "com.infinitysoftware.conexioncarga"
ANDROID_STORE_URL = (
    "https://play.google.com/store/apps/details?id=com.infinitysoftware.conexioncarga"
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


def _render_register_page(ref: str | None) -> str:
    ref_normalizado = _normalizar_ref(ref)
    deep_link = html.escape(_construir_deep_link(ref_normalizado), quote=True)
    store_url = html.escape(ANDROID_STORE_URL, quote=True)
    referido_html = ""

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
    </style>
</head>
<body>
    <main class="card">
        <div class="eyebrow">Registro con referido</div>
        <h1>Continúa tu registro en {APP_NAME}</h1>
        <p>Este enlace está optimizado para Android. Si ya tienes la app instalada, intentaremos abrirla directamente en el formulario de registro.</p>
        <p>Si no tienes la app, te llevaremos a Google Play y luego podrás volver a continuar el proceso.</p>
        {referido_html}
        <div class="actions">
            <a class="btn btn-primary" href="{deep_link}">Abrir app</a>
            <a class="btn btn-secondary" href="{store_url}">Descargar en Google Play</a>
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
