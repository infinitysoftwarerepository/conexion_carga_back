# app/routers/recaptcha.py
from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse
import os
import html as html_lib

router = APIRouter()

@router.get("/recaptcha", response_class=HTMLResponse)
def recaptcha_page(response: Response):
    # Acepta ambos nombres por compatibilidad (por si luego renombraras)
    sitekey = os.getenv("SITEKEY") or os.getenv("RECAPTCHA_SITEKEY") or ""
    sitekey = html_lib.escape(sitekey, quote=True)

    # Evita cache (mejor para tokens)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"

    if not sitekey:
        return """
<!doctype html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <style>
      body { font-family: Arial; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; padding:16px; }
      .box { max-width: 520px; border:1px solid #ddd; border-radius:12px; padding:16px; }
      code { background:#f4f4f4; padding:2px 6px; border-radius:6px; }
    </style>
  </head>
  <body>
    <div class="box">
      <h3>reCAPTCHA no configurado</h3>
      <p>No se encontró <code>SITEKEY</code> en el entorno.</p>
      <p>Configura <code>SITEKEY</code> en el archivo <code>.env</code> y reinicia el servicio.</p>
    </div>
  </body>
</html>
"""

    return f"""
<!doctype html>
<html lang="es">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <script src="https://www.google.com/recaptcha/api.js" async defer></script>
    <style>
      body {{
        font-family: Arial;
        display:flex;
        justify-content:center;
        align-items:center;
        height:100vh;
        margin:0;
        background:#fff;
      }}
      .wrap {{
        padding: 12px;
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="g-recaptcha"
           data-sitekey="{sitekey}"
           data-callback="onSolved"
           data-expired-callback="onExpired"></div>
    </div>

    <script>
      function onSolved(token) {{
        try {{
          // ✅ webview_flutter: coincide con addJavaScriptChannel('Recaptcha', ...)
          Recaptcha.postMessage(token);

          // Opcional: reset por si re-abren la pantalla
          setTimeout(function() {{
            try {{ grecaptcha.reset(); }} catch(e) {{}}
          }}, 150);
        }} catch (e) {{
          // fallback: no debería pasar, pero evita que quede “colgado”
          window.location.hash = "token=" + encodeURIComponent(token);
        }}
      }}

      function onExpired() {{
        try {{
          Recaptcha.postMessage("");
        }} catch (e) {{}}
      }}
    </script>
  </body>
</html>
"""
