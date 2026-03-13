from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["Public Pages"])

APP_NAME = "Conexión Carga"
RESPONSABLE_NOMBRE = "Deibizon Andrés Londoño Gallego"
RESPONSABLE_DOCUMENTO = "98.669.911"
RESPONSABLE_DIRECCION = "Carrera 56A #61-24, Medellín, Colombia"
RESPONSABLE_EMAIL = "conexioncarga@gmail.com"
RESPONSABLE_TELEFONO = "301 904 3971"


def _render_layout(
    *,
    browser_title: str,
    meta_description: str,
    hero_label: str,
    hero_title: str,
    hero_subtitle: str,
    hero_copy: str,
    meta_left: str,
    meta_right: str,
    content_html: str,
) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{browser_title}</title>
    <meta
        name="description"
        content="{meta_description}"
    />
    <style>
        :root {{
            color-scheme: light;
            --bg: #f5f5f2;
            --card: #ffffff;
            --text: #172033;
            --muted: #5b6475;
            --line: #e6e8ee;
            --accent: #ff7800;
            --accent-soft: #fff1e4;
            --accent-strong: #ca5d00;
            --success-soft: #eef8e8;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            background:
                radial-gradient(circle at top right, rgba(255, 120, 0, 0.09), transparent 22%),
                linear-gradient(180deg, #fffdf9 0%, var(--bg) 100%);
            color: var(--text);
            line-height: 1.7;
        }}

        .page {{
            max-width: 980px;
            margin: 0 auto;
            padding: 32px 20px 56px;
        }}

        .hero {{
            background: var(--card);
            border: 1px solid rgba(255, 120, 0, 0.14);
            border-radius: 24px;
            padding: 32px;
            box-shadow: 0 24px 60px rgba(23, 32, 51, 0.08);
        }}

        .eyebrow {{
            display: inline-flex;
            align-items: center;
            gap: 10px;
            background: var(--accent-soft);
            color: var(--accent);
            border-radius: 999px;
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.02em;
            text-transform: uppercase;
        }}

        h1 {{
            margin: 18px 0 12px;
            font-size: clamp(2rem, 4vw, 3.1rem);
            line-height: 1.08;
        }}

        h2 {{
            margin: 0 0 12px;
            font-size: 1.35rem;
            line-height: 1.25;
        }}

        h3 {{
            margin: 22px 0 10px;
            font-size: 1rem;
            color: var(--accent-strong);
        }}

        p {{
            margin: 0 0 14px;
        }}

        .hero-copy {{
            max-width: 76ch;
        }}

        .meta {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 14px;
            margin-top: 24px;
        }}

        .meta-card {{
            background: #fafbfc;
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 16px 18px;
        }}

        .meta-card strong {{
            display: block;
            margin-bottom: 6px;
            font-size: 0.92rem;
        }}

        .legal-nav {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 24px 0 0;
        }}

        .legal-link {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 40px;
            padding: 0 16px;
            border-radius: 999px;
            text-decoration: none;
            border: 1px solid rgba(255, 120, 0, 0.18);
            background: #fff8f0;
            color: var(--accent-strong);
            font-weight: 600;
        }}

        .content {{
            margin-top: 24px;
            display: grid;
            gap: 18px;
        }}

        .section {{
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 26px;
            box-shadow: 0 10px 30px rgba(23, 32, 51, 0.04);
        }}

        .definitions {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 14px;
            margin-top: 18px;
        }}

        .definition {{
            background: #fbfbfd;
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 18px;
        }}

        .definition h3 {{
            margin-top: 0;
            color: var(--accent);
        }}

        ul {{
            margin: 12px 0 0;
            padding-left: 22px;
        }}

        li {{
            margin: 6px 0;
        }}

        .notice {{
            border-left: 4px solid var(--accent);
            background: var(--accent-soft);
            border-radius: 14px;
            padding: 14px 16px;
            margin-top: 14px;
        }}

        .contact {{
            background: var(--success-soft);
            border: 1px solid #dbe9cf;
        }}

        .compact-list {{
            margin-top: 0;
        }}

        a {{
            color: var(--accent);
        }}

        footer {{
            margin-top: 18px;
            color: var(--muted);
            font-size: 0.95rem;
            text-align: center;
        }}

        @media (max-width: 720px) {{
            .hero,
            .section {{
                padding: 22px 18px;
                border-radius: 20px;
            }}
        }}
    </style>
</head>
<body>
    <main class="page">
        <header class="hero">
            <div class="eyebrow">{hero_label}</div>
            <h1>{hero_title}</h1>
            <p><strong>{hero_subtitle}</strong></p>
            <div class="hero-copy">{hero_copy}</div>

            <div class="meta">
                <div class="meta-card">
                    <strong>Documento</strong>
                    <span>{meta_left}</span>
                </div>
                <div class="meta-card">
                    <strong>Contacto</strong>
                    <span>{meta_right}</span>
                </div>
            </div>

            <nav class="legal-nav" aria-label="Documentos legales">
                <a class="legal-link" href="/privacidad">Privacidad</a>
                <a class="legal-link" href="/terminos">Términos</a>
                <a class="legal-link" href="/promociones">Promociones</a>
            </nav>
        </header>

        <div class="content">
            {content_html}
        </div>

        <footer>
            Documento público en formato HTML para consulta web y cumplimiento de publicación legal de {APP_NAME}.
        </footer>
    </main>
</body>
</html>
"""


def _render_privacidad() -> str:
    content_html = f"""
        <section class="section">
            <h2>Definiciones</h2>
            <div class="definitions">
                <article class="definition">
                    <h3>Dato personal</h3>
                    <p>Cualquier información vinculada o que pueda asociarse a una o varias personas naturales, determinadas o determinables.</p>
                    <p>Ejemplo: nombre, teléfono, correo electrónico, dirección o documento de identidad.</p>
                </article>
                <article class="definition">
                    <h3>Dato sensible</h3>
                    <p>Información que afecta la intimidad del titular o cuyo uso indebido puede generar discriminación.</p>
                    <p>Incluye, entre otros, origen racial o étnico, orientación política, convicciones religiosas o filosóficas, datos relativos a la salud, vida sexual y datos biométricos.</p>
                </article>
                <article class="definition">
                    <h3>Dato público</h3>
                    <p>Es el dato que no es privado, semiprivado ni sensible.</p>
                    <p>Ejemplos: estado civil, profesión u oficio, datos contenidos en registros públicos o información en medios públicos.</p>
                </article>
                <article class="definition">
                    <h3>Dato privado</h3>
                    <p>Es el dato personal que por su naturaleza íntima o reservada sólo es relevante para el titular.</p>
                    <p>Ejemplo: hábitos de vida o información de carácter personal no divulgada.</p>
                </article>
                <article class="definition">
                    <h3>Dato semiprivado</h3>
                    <p>Dato que no es estrictamente íntimo, pero cuyo conocimiento o divulgación puede interesar no sólo al titular sino a cierto grupo.</p>
                    <p>Ejemplo: información financiera y crediticia.</p>
                </article>
                <article class="definition">
                    <h3>Titular</h3>
                    <p>Persona natural cuyos datos personales son objeto de tratamiento.</p>
                </article>
                <article class="definition">
                    <h3>Responsable del tratamiento</h3>
                    <p>Persona natural o jurídica, pública o privada, que decide sobre la recolección, almacenamiento, uso y circulación de los datos personales.</p>
                </article>
                <article class="definition">
                    <h3>Encargado del tratamiento</h3>
                    <p>Persona natural o jurídica que realiza el tratamiento de datos personales por cuenta del responsable.</p>
                </article>
                <article class="definition">
                    <h3>Autorización</h3>
                    <p>Consentimiento previo, expreso e informado del titular para llevar a cabo el tratamiento de sus datos personales.</p>
                </article>
                <article class="definition">
                    <h3>Tratamiento</h3>
                    <p>Cualquier operación o conjunto de operaciones sobre datos personales, como recolección, almacenamiento, uso, circulación, supresión, transmisión o transferencia.</p>
                </article>
                <article class="definition">
                    <h3>Aviso de privacidad</h3>
                    <p>Comunicación verbal o escrita generada por el responsable que informa al titular sobre la existencia de la política y las finalidades del tratamiento.</p>
                </article>
                <article class="definition">
                    <h3>Base de datos</h3>
                    <p>Conjunto organizado de datos personales que es objeto de tratamiento.</p>
                </article>
                <article class="definition">
                    <h3>Transmisión de datos</h3>
                    <p>Tratamiento por parte de un encargado ubicado dentro o fuera del país en nombre del responsable.</p>
                </article>
                <article class="definition">
                    <h3>Transferencia de datos</h3>
                    <p>Envío de información o datos personales a un receptor que también actúa como responsable del tratamiento dentro o fuera del país.</p>
                </article>
                <article class="definition">
                    <h3>Usuario</h3>
                    <p>Persona natural o jurídica que accede y utiliza la plataforma y los servicios de {APP_NAME}.</p>
                </article>
            </div>
        </section>

        <section class="section contact">
            <h2>1. Responsable del tratamiento de la información</h2>
            <p><strong>Nombre:</strong> {RESPONSABLE_NOMBRE}</p>
            <p><strong>Cédula:</strong> {RESPONSABLE_DOCUMENTO}</p>
            <p><strong>Dirección:</strong> {RESPONSABLE_DIRECCION}</p>
            <p><strong>Correo electrónico:</strong> <a href="mailto:{RESPONSABLE_EMAIL}">{RESPONSABLE_EMAIL}</a></p>
            <p><strong>Teléfono:</strong> <a href="tel:{RESPONSABLE_TELEFONO.replace(" ", "")}">{RESPONSABLE_TELEFONO}</a></p>
        </section>

        <section class="section">
            <h2>2. Alcance</h2>
            <p>Esta política aplica a todos los usuarios de la aplicación móvil {APP_NAME}, incluyendo transportistas, generadores de carga, comisionistas, despachadores y demás personas naturales o jurídicas que hagan uso de sus funcionalidades.</p>
        </section>

        <section class="section">
            <h2>3. Datos personales tratados</h2>
            <h3>3.1 Datos suministrados por el usuario</h3>
            <ul>
                <li>Nombre completo.</li>
                <li>Documento de identidad.</li>
                <li>Correo electrónico.</li>
                <li>Número telefónico.</li>
                <li>Nombre de empresa, si aplica.</li>
            </ul>

            <h3>3.2 Datos recopilados automáticamente por la aplicación</h3>
            <p>La aplicación puede recolectar de forma automática:</p>
            <ul>
                <li>Dirección IP.</li>
                <li>Tipo de dispositivo móvil.</li>
                <li>Sistema operativo y versión.</li>
                <li>Identificadores técnicos de la aplicación.</li>
                <li>Registros de actividad y errores.</li>
            </ul>
            <p>Estos datos se utilizan exclusivamente para fines de seguridad, funcionamiento adecuado de la aplicación, mejora del servicio y soporte técnico.</p>

            <h3>3.3 Datos de ubicación</h3>
            <p>La aplicación puede acceder a datos de ubicación geográfica (GPS):</p>
            <ul>
                <li>Mientras la aplicación está en uso, para facilitar la conexión entre los actores del transporte.</li>
                <li>No se recopila ubicación en segundo plano sin autorización expresa del usuario.</li>
                <li>La ubicación no se utiliza para publicidad ni se comercializa con terceros.</li>
            </ul>
        </section>

        <section class="section">
            <h2>4. Finalidad del tratamiento</h2>
            <p>Los datos personales serán utilizados para:</p>
            <ul>
                <li>Registro, autenticación y administración de cuentas.</li>
                <li>Facilitar la comunicación entre los actores del sector transporte.</li>
                <li>Gestión de operaciones logísticas.</li>
                <li>Seguridad, prevención de fraude y uso indebido de la plataforma.</li>
                <li>Envío de información relacionada con los servicios de {APP_NAME}.</li>
            </ul>
        </section>

        <section class="section">
            <h2>5. Autorización del titular</h2>
            <p>Al aceptar esta política y utilizar la aplicación, el usuario autoriza de forma previa, expresa e informada el tratamiento de sus datos personales conforme a las finalidades aquí descritas.</p>
        </section>

        <section class="section">
            <h2>6. Eliminación de datos personales</h2>
            <p>El usuario podrá solicitar la eliminación de su información personal enviando un correo a <a href="mailto:{RESPONSABLE_EMAIL}">{RESPONSABLE_EMAIL}</a> con el asunto "Eliminación de datos personales".</p>
            <ul>
                <li>La solicitud será atendida en un plazo máximo de 15 días hábiles.</li>
                <li>Se eliminarán todos los datos que no deban conservarse por obligación legal o contractual.</li>
                <li>Algunos datos podrán conservarse de manera anonimizada para fines contables, legales o de seguridad.</li>
                <li>Los datos del usuario se borran automáticamente en un plazo de 90 días.</li>
            </ul>
        </section>

        <section class="section">
            <h2>7. Transferencia y almacenamiento de datos</h2>
            <p>Los datos pueden ser almacenados en servidores ubicados fuera de Colombia, incluyendo servicios en la nube como AWS, garantizando estándares adecuados de seguridad y protección de la información.</p>
            <p>Para más información puede consultarse la política de privacidad de AWS en <a href="https://aws.amazon.com/privacy/" target="_blank" rel="noreferrer noopener">https://aws.amazon.com/privacy/</a>.</p>
            <p>{APP_NAME} no vende ni comercializa datos personales.</p>
        </section>

        <section class="section">
            <h2>8. Uso por menores de edad</h2>
            <p>La aplicación no está dirigida a menores de 18 años. No se recopilan de manera intencional datos de menores. Si se detecta información de un menor, será eliminada inmediatamente.</p>
        </section>

        <section class="section">
            <h2>9. Seguridad de la información</h2>
            <p>{APP_NAME} implementa medidas técnicas, administrativas y organizacionales razonables para proteger la información contra accesos no autorizados, pérdida o uso indebido.</p>
        </section>

        <section class="section">
            <h2>10. Derechos del titular de los datos</h2>
            <p>Los usuarios tienen derecho a:</p>
            <ul>
                <li>Conocer, actualizar y rectificar su información personal.</li>
                <li>Solicitar prueba de la autorización otorgada.</li>
                <li>Ser informados sobre el uso de sus datos.</li>
                <li>Revocar la autorización y solicitar la eliminación de datos personales.</li>
            </ul>
            <div class="notice">
                Para ejercer estos derechos, los usuarios pueden enviar una solicitud a
                <a href="mailto:{RESPONSABLE_EMAIL}">{RESPONSABLE_EMAIL}</a> con el asunto
                "Solicitud de Habeas Data". Las solicitudes serán atendidas en un plazo máximo de 15 días hábiles.
            </div>
        </section>

        <section class="section">
            <h2>11. Modificaciones a la política</h2>
            <p>{APP_NAME} podrá modificar esta política en cualquier momento. Los cambios serán informados a los usuarios mediante la aplicación o correo electrónico.</p>
        </section>

        <section class="section">
            <h2>12. Fecha de vigencia</h2>
            <p>Esta política entra en vigencia a partir del 20 de diciembre de 2025.</p>
        </section>

        <section class="section contact">
            <h2>13. Contacto</h2>
            <p>Para consultas relacionadas con privacidad y datos personales:</p>
            <p><strong>Correo:</strong> <a href="mailto:{RESPONSABLE_EMAIL}">{RESPONSABLE_EMAIL}</a></p>
            <p><strong>Teléfono:</strong> <a href="tel:{RESPONSABLE_TELEFONO.replace(" ", "")}">{RESPONSABLE_TELEFONO}</a></p>
        </section>
    """

    return _render_layout(
        browser_title=f"Política de privacidad | {APP_NAME}",
        meta_description=f"Política de privacidad y tratamiento de datos personales de {APP_NAME}.",
        hero_label="Política pública de privacidad",
        hero_title="Política de privacidad y tratamiento de datos personales",
        hero_subtitle="Aplicable a la aplicación móvil Conexión Carga (Google Play)",
        hero_copy="""
            <p>La presente Política de Privacidad regula el tratamiento de los datos personales de los usuarios que acceden y utilizan la aplicación móvil Conexión Carga, publicada y distribuida a través de Google Play, así como la plataforma tecnológica asociada.</p>
            <p>Su elaboración se ajusta a la Ley 1581 de 2012, el Decreto 1377 de 2013 y a los requisitos de privacidad y seguridad exigidos por Google Play Console.</p>
        """,
        meta_left="Política de privacidad y tratamiento de datos personales",
        meta_right=RESPONSABLE_EMAIL,
        content_html=content_html,
    )


def _render_terminos() -> str:
    content_html = f"""
        <section class="section">
            <h2>1. Introducción</h2>
            <p>Bienvenido a {APP_NAME}. Estos Términos y Condiciones regulan el acceso y uso de la plataforma, el sitio web y la aplicación móvil de {APP_NAME}.</p>
            <p>Al utilizar nuestros servicios, usted acepta cumplir con estos términos. Si no está de acuerdo, por favor no utilice la plataforma.</p>
        </section>

        <section class="section">
            <h2>2. Definiciones</h2>
            <ul class="compact-list">
                <li><strong>Usuario:</strong> Persona natural o jurídica que accede y utiliza la plataforma.</li>
                <li><strong>Plataforma:</strong> Sitio web y aplicación móvil de {APP_NAME}.</li>
                <li><strong>Servicios:</strong> Servicios de logística y transporte ofrecidos a través de la plataforma.</li>
            </ul>
        </section>

        <section class="section">
            <h2>3. Aceptación de términos</h2>
            <p>Al registrarse o utilizar nuestros servicios, el usuario acepta estos Términos y Condiciones, así como nuestra Política de Privacidad, que forma parte integral de este documento.</p>
        </section>

        <section class="section">
            <h2>4. Registro de usuario</h2>
            <p>Para acceder a los servicios, el usuario debe completar el proceso de registro proporcionando información precisa y actualizada según se requiera.</p>
            <p>El usuario es responsable de mantener la confidencialidad de sus credenciales y de todas las actividades que ocurran bajo su cuenta.</p>
        </section>

        <section class="section">
            <h2>5. Obligaciones del usuario</h2>
            <p>El usuario se compromete a:</p>
            <ul>
                <li>Proporcionar información veraz y actualizada durante el proceso de registro y uso de la plataforma.</li>
                <li>No utilizar la plataforma para realizar actividades fraudulentas, ilegales o no autorizadas.</li>
                <li>No interferir con la seguridad, la integridad o el funcionamiento de la plataforma.</li>
                <li>Notificar inmediatamente a {APP_NAME} sobre cualquier uso no autorizado de su cuenta o cualquier otra violación de la seguridad.</li>
            </ul>
        </section>

        <section class="section">
            <h2>6. Servicios ofrecidos</h2>
            <p>{APP_NAME} ofrece servicios de conexión entre transportistas y generadores de carga, así como gestión de logística. Los detalles específicos de los servicios estarán disponibles en la plataforma.</p>
        </section>

        <section class="section">
            <h2>7. Tarifas y pagos</h2>
            <p>Los servicios pueden estar sujetos a tarifas. El usuario acepta pagar todas las tarifas y cargos según lo que se indique en la plataforma.</p>
            <p>{APP_NAME} se reserva el derecho de modificar las tarifas en cualquier momento, notificando adecuadamente a los usuarios.</p>
        </section>

        <section class="section">
            <h2>8. Propiedad intelectual</h2>
            <p>Todos los contenidos, marcas, logos y tecnología presentes en la plataforma son propiedad de {APP_NAME} o de sus respectivos dueños.</p>
            <p>Queda prohibida la reproducción, distribución o uso de cualquier contenido sin autorización previa y por escrito de {APP_NAME}.</p>
        </section>

        <section class="section">
            <h2>9. Limitación de responsabilidad</h2>
            <p>{APP_NAME} no se hace responsable de daños indirectos, incidentales o emergentes que surjan del uso o de la imposibilidad de uso de la plataforma, incluyendo, sin limitación, pérdidas de beneficios, datos o uso.</p>
        </section>

        <section class="section">
            <h2>10. Modificaciones a los términos y condiciones</h2>
            <p>{APP_NAME} se reserva el derecho de modificar estos Términos y Condiciones en cualquier momento. Las modificaciones entrarán en vigencia una vez publicadas en la plataforma.</p>
            <p>Es responsabilidad del usuario revisar periódicamente estos términos.</p>
        </section>

        <section class="section">
            <h2>11. Legislación aplicable y jurisdicción</h2>
            <p>Estos Términos y Condiciones se regirán e interpretarán de acuerdo con las leyes de la República de Colombia.</p>
            <p>Cualquier controversia derivada de estos términos será resuelta ante los tribunales competentes de la ciudad de Medellín.</p>
        </section>

        <section class="section contact">
            <h2>12. Contacto</h2>
            <p>Para cualquier duda, comentario o solicitud relacionada con estos Términos y Condiciones, el usuario puede contactarnos a través de la siguiente dirección de correo electrónico:</p>
            <p><strong>Correo:</strong> <a href="mailto:{RESPONSABLE_EMAIL}">{RESPONSABLE_EMAIL}</a></p>
        </section>

        <section class="section">
            <h2>13. Fecha de entrada en vigencia</h2>
            <p>Estos Términos y Condiciones entran en vigencia a partir del 01 de noviembre de 2025.</p>
        </section>
    """

    return _render_layout(
        browser_title=f"Términos y condiciones | {APP_NAME}",
        meta_description=f"Términos y condiciones de uso de {APP_NAME}.",
        hero_label="Términos de uso",
        hero_title="Términos y condiciones de uso de Conexión Carga",
        hero_subtitle="Aplicables al sitio web, la plataforma y la aplicación móvil",
        hero_copy=f"""
            <p>Este documento resume las reglas de acceso y uso de los servicios de {APP_NAME}. La estructura y el orden siguen el documento oficial cargado en el backend para publicación web.</p>
            <p>Si el usuario no está de acuerdo con estos términos, debe abstenerse de utilizar la plataforma.</p>
        """,
        meta_left="Términos y condiciones de uso",
        meta_right=RESPONSABLE_EMAIL,
        content_html=content_html,
    )


def _render_promociones() -> str:
    content_html = f"""
        <section class="section">
            <h2>1. Objeto de la promoción</h2>
            <p>La presente política regula las condiciones, requisitos, mecanismos de participación y entrega de premios en dinero ofrecidos por la aplicación {APP_NAME}, con ocasión de campañas promocionales basadas en la referenciación de usuarios y el uso activo de la aplicación.</p>
        </section>

        <section class="section">
            <h2>2. Organizador</h2>
            <p>La promoción es organizada por {APP_NAME}, quien se reserva el derecho de verificar, modificar, suspender o cancelar la promoción cuando existan causas justificadas, informándolo oportunamente a través de la aplicación o canales oficiales.</p>
        </section>

        <section class="section">
            <h2>3. Requisitos de participación</h2>
            <p>Podrán participar únicamente las personas que cumplan con las siguientes condiciones:</p>
            <ul>
                <li>Ser mayor de edad conforme a la legislación colombiana.</li>
                <li>Estar registradas en la aplicación {APP_NAME}.</li>
                <li>Pertenecer al sector transporte, en alguno de los siguientes roles:
                    <ul>
                        <li>Conductor.</li>
                        <li>Despachador.</li>
                        <li>Comisionista.</li>
                        <li>Comercial de empresa de transporte.</li>
                    </ul>
                </li>
                <li>Hacer uso frecuente y legítimo de la aplicación.</li>
                <li>Aceptar los Términos y Condiciones, esta Política de Promociones y la Política de Privacidad.</li>
            </ul>
            <div class="notice">
                En caso de detectarse que un usuario referido no pertenece al sector transporte, los puntos asociados a dicho referido serán anulados automáticamente.
            </div>
        </section>

        <section class="section">
            <h2>4. Mecánica de la promoción y sistema de puntos</h2>
            <ul>
                <li>Cada usuario referido que se registre correctamente en la aplicación equivale a un (1) punto.</li>
                <li>Los puntos serán acumulables únicamente durante el período de vigencia de la promoción.</li>
                <li>{APP_NAME} se reserva el derecho de auditar y validar la autenticidad de los registros y del uso real de la aplicación.</li>
            </ul>
        </section>

        <section class="section">
            <h2>5. Premiación y montos</h2>
            <p>Los premios en dinero se asignarán a los tres (3) usuarios con mayor puntaje válido, siempre que cumplan los mínimos establecidos:</p>
            <ul>
                <li><strong>Primer puesto:</strong> Premio de $150.000 COP con puntaje mínimo requerido de 100 puntos.</li>
                <li><strong>Segundo puesto:</strong> Premio de $100.000 COP con puntaje mínimo requerido de 80 puntos.</li>
                <li><strong>Tercer puesto:</strong> Premio de $50.000 COP con puntaje mínimo requerido de 60 puntos.</li>
            </ul>
            <p>Si ninguno de los participantes alcanza los puntajes mínimos establecidos, {APP_NAME} podrá declarar la promoción como desierta.</p>
        </section>

        <section class="section">
            <h2>6. Fecha de entrega del premio</h2>
            <p>La entrega de la premiación se realizará el 27 de febrero de 2026, siempre y cuando los ganadores hayan cumplido con todos los requisitos y validaciones establecidas en esta política.</p>
        </section>

        <section class="section">
            <h2>7. Entrega del incentivo</h2>
            <ul>
                <li>El pago se realizará a través del medio definido por {APP_NAME}.</li>
                <li>Para la entrega del premio, se podrá solicitar información mínima necesaria, por ejemplo datos de transferencia.</li>
                <li>Los premios no son transferibles, canjeables ni acumulables con otras promociones.</li>
                <li>Los incentivos otorgados no constituyen salario, comisión, relación laboral ni vínculo contractual con {APP_NAME}.</li>
            </ul>
        </section>

        <section class="section">
            <h2>8. Prevención de fraude</h2>
            <p>Serán causales de descalificación inmediata, sin derecho a reclamo:</p>
            <ul>
                <li>Registro de usuarios falsos o duplicados.</li>
                <li>Uso de métodos automatizados o engañosos.</li>
                <li>Manipulación del sistema de referidos.</li>
                <li>Incumplimiento de los Términos y Condiciones de la app.</li>
            </ul>
        </section>

        <section class="section">
            <h2>9. Exención de responsabilidad de Google</h2>
            <p>Esta promoción no está patrocinada, avalada, administrada ni asociada con Google ni Google Play, quienes no asumen ninguna responsabilidad frente a la promoción, los premios o su entrega.</p>
        </section>

        <section class="section">
            <h2>10. Tratamiento de datos personales</h2>
            <p>Los datos personales recolectados serán tratados conforme a la Política de Tratamiento de Datos Personales de {APP_NAME}, únicamente para la gestión de la promoción y entrega de premios.</p>
        </section>

        <section class="section">
            <h2>11. Modificaciones</h2>
            <p>{APP_NAME} podrá modificar esta política en cualquier momento. Las modificaciones serán publicadas en la aplicación y entrarán en vigor desde su publicación.</p>
        </section>

        <section class="section">
            <h2>12. Aceptación</h2>
            <p>La participación en la promoción implica la aceptación total e incondicional de la presente Política de Promociones y Premios en Dinero.</p>
        </section>
    """

    return _render_layout(
        browser_title=f"Política de promociones | {APP_NAME}",
        meta_description=f"Política de promociones y premios en dinero de {APP_NAME}.",
        hero_label="Promociones y premios",
        hero_title="Política de promociones",
        hero_subtitle="Condiciones, participación y entrega de premios",
        hero_copy=f"""
            <p>Este documento corresponde a la política de promociones de {APP_NAME} y conserva el orden de los apartados del PDF oficial cargado en el backend.</p>
            <p>Su propósito es dejar visible en la web las reglas de participación, validación y entrega de incentivos promocionales.</p>
        """,
        meta_left="Política de promociones y premios en dinero",
        meta_right=RESPONSABLE_EMAIL,
        content_html=content_html,
    )


@router.get("/privacidad", response_class=HTMLResponse, include_in_schema=False)
@router.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
def politica_privacidad_publica() -> HTMLResponse:
    return HTMLResponse(content=_render_privacidad(), status_code=200)


@router.get("/terminos", response_class=HTMLResponse, include_in_schema=False)
def terminos_uso_publicos() -> HTMLResponse:
    return HTMLResponse(content=_render_terminos(), status_code=200)


@router.get("/promociones", response_class=HTMLResponse, include_in_schema=False)
def politica_promociones_publica() -> HTMLResponse:
    return HTMLResponse(content=_render_promociones(), status_code=200)
