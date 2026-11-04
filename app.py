"""
Interfaz web genérica (Streamlit) para conversar con un agente.

- Lo específico del caso de uso (marca, textos, colores, consultas rápidas,
  proveedor) está en config.toml.
- La conexión con el agente está en agentes/ (un conector por proveedor).
- Los gráficos declarativos (```radar {...}```) están en graficos.py.

Uso:  streamlit run app.py
"""

import base64
import html
import logging
import mimetypes
import os
import tomllib
from dataclasses import asdict

import streamlit as st
from dotenv import load_dotenv

from agentes import Actividad, Decision, crear_agente
from graficos import configurar as configurar_graficos, extraer_bloques, pintar_grafico

load_dotenv()
DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(DIR, os.environ.get("APP_CONFIG", "config.toml")), "rb") as _f:
    CFG = tomllib.load(_f)

APP = CFG.get("app", {})
MARCA = CFG.get("marca", {})
COLORES = CFG.get("colores", {})
TIPO = CFG.get("tipografia", {})
AGENTE_CFG = CFG.get("agente", {})
GRAFICOS = CFG.get("graficos", {})
configurar_graficos(GRAFICOS.get("claves_series"))
PROVEEDOR = os.environ.get("AGENT_PROVIDER") or AGENTE_CFG.get("proveedor", "")
NOMBRE_PROVEEDOR = AGENTE_CFG.get("nombre_visible", PROVEEDOR)
CARPETA_SALIDAS = os.path.join(DIR, APP.get("carpeta_salidas", "salidas"))
EXT_IMAGEN = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
AVATAR_AGENTE = APP.get("avatar_agente", "🤖")
AVATAR_USUARIO = APP.get("avatar_usuario", "👤")
FUENTE_TITULOS = TIPO.get("titulos", "Montserrat")
FUENTE_TEXTO = TIPO.get("texto", "Inter")

log = logging.getLogger(APP.get("logger", "app"))
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter(f"%(asctime)s [{log.name}] %(levelname)s %(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)
    log.propagate = False


def _logo_data_uri():
    if MARCA.get("logo_fichero"):
        ruta = os.path.join(DIR, MARCA["logo_fichero"])
        mime = mimetypes.guess_type(ruta)[0] or "image/png"
        with open(ruta, "rb") as f:
            return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"
    if MARCA.get("logo_svg"):
        return "data:image/svg+xml;base64," + base64.b64encode(MARCA["logo_svg"].strip().encode()).decode()
    return None


LOGO_URI = _logo_data_uri()


def logo_img(w, h):
    if not LOGO_URI:
        return ""
    alt = html.escape(MARCA.get("logo_alt", "Logo"))
    return f'<img src="{LOGO_URI}" width="{w}" height="{h}" alt="{alt}"/>'


# ---------------------------------------------------------------- Diseño
st.set_page_config(page_title=APP.get("titulo_pestana", "Agente"), page_icon=APP.get("icono", "🤖"),
                   layout="wide")

_fuentes = "&".join(f"family={f.replace(' ', '+')}:wght@{w}"
                    for f, w in ((FUENTE_TITULOS, "600;700;800"), (FUENTE_TEXTO, "400;500;600")))
_root = (
    f'@import url("https://fonts.googleapis.com/css2?{_fuentes}&display=swap");\n'
    ":root {"
    + "".join(f" --{k.replace('_', '-')}: {v};" for k, v in COLORES.items())
    + f" --fuente-titulos: '{FUENTE_TITULOS}'; --fuente-texto: '{FUENTE_TEXTO}'; }}\n"
)
CSS = """
html, body, .stMarkdown, .stChatMessage, button, input, textarea { font-family: var(--fuente-texto), sans-serif; }
h1, h2, h3, h4 { font-family: var(--fuente-titulos), sans-serif !important; letter-spacing: -.01em; }

/* Ocultar elementos por defecto de Streamlit */
#MainMenu, footer, [data-testid="stMainMenu"], [data-testid="stDecoration"],
[data-testid="stToolbarActions"], [data-testid="stStatusWidget"], [data-testid="stAppDeployButton"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1150px; }

/* Cabecera */
.hero { display: flex; align-items: center; gap: 1.4rem; padding: 1.4rem 1.8rem; border-radius: 18px;
  background: radial-gradient(circle at 85% 20%, color-mix(in srgb, var(--secundario) 55%, transparent), transparent 55%),
              linear-gradient(120deg, var(--primario) 0%, var(--primario-claro) 100%);
  box-shadow: 0 10px 30px color-mix(in srgb, var(--primario) 25%, transparent); margin-bottom: 1.6rem; }
.hero h1 { color: #fff !important; margin: 0; font-size: 2.1rem; font-weight: 800; padding: 0; }
.hero p { color: rgba(255,255,255,.82); margin: .25rem 0 0 0; font-size: .98rem; font-weight: 500; }
.hero .pill { display: inline-block; margin-top: .6rem; padding: .18rem .7rem; border-radius: 99px;
  background: rgba(255,255,255,.14); color: #fff; font-size: .75rem; font-weight: 600; letter-spacing: .04em; }

/* Barra lateral */
section[data-testid="stSidebar"] { background: linear-gradient(180deg, var(--primario-oscuro) 0%, var(--primario) 100%); }
section[data-testid="stSidebar"] * { color: #eef3f8; }
.sb-marca { display: flex; align-items: center; gap: .7rem; margin-bottom: .4rem; }
.sb-marca b { font-family: var(--fuente-titulos), sans-serif; font-size: 1.25rem; }
.sb-sec { font-size: .7rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
  color: rgba(255,255,255,.55) !important; margin: 1.4rem 0 .5rem 0; }
.sb-estado { margin-top: 2rem; padding: .7rem .8rem; border-radius: 10px; background: rgba(255,255,255,.07);
  font-size: .82rem; }
.sb-estado .ok { color: var(--exito) !important; font-weight: 700; }
.sb-estado .ko { color: color-mix(in srgb, var(--peligro) 60%, white) !important; font-weight: 700; }
.sb-estado small { color: rgba(255,255,255,.6) !important; }

/* Botones */
.stButton > button { background: var(--secundario); color: #fff !important; border: none; border-radius: 10px;
  font-weight: 600; width: 100%; transition: all .15s ease; }
.stButton > button:hover { background: var(--secundario-hover); transform: translateY(-1px);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--secundario) 35%, transparent); }
.stButton > button p { color: #fff !important; }
.st-key-rapidas .stButton > button { background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.14);
  text-align: left; justify-content: flex-start; padding: .7rem .85rem; }
.st-key-rapidas .stButton > button:hover { background: color-mix(in srgb, var(--secundario) 35%, transparent);
  border-color: var(--exito); }
.st-key-rapidas .stButton > button div[data-testid="stMarkdownContainer"] { text-align: left; }
.st-key-rapidas .stButton > button p { margin: 0; line-height: 1.3; }
.st-key-rapidas .stButton > button p + p { font-size: .76rem; opacity: .75; font-weight: 400; margin-top: .15rem; }

/* Chat */
[data-testid="stChatMessage"] { padding: 1rem 1.2rem; border-radius: 16px; margin-bottom: 1rem;
  border: 1px solid rgba(128,128,128,.18); box-shadow: 0 2px 10px rgba(0,0,0,.06);
  background: rgba(128,128,128,.04); }
[data-testid="stChatMessageAvatarCustom"], [data-testid="stChatMessage"] > div:first-child { border-radius: 50%; }
.traza { font-size: .85rem; padding: .35rem .8rem; margin: -.4rem 0 1rem 3rem; border-left: 3px solid var(--secundario);
  border-radius: 4px; background: color-mix(in srgb, var(--secundario) 8%, transparent); }
.traza.no { border-left-color: var(--peligro); background: color-mix(in srgb, var(--peligro) 8%, transparent); }

/* Tablas legibles en ambos temas */
.stMarkdown table { border-collapse: collapse; width: 100%; margin: .6rem 0; border-radius: 8px; overflow: hidden; }
.stMarkdown th { background: var(--primario) !important; color: #fff !important; padding: 8px 12px; text-align: left; }
.stMarkdown td { border: 1px solid rgba(128,128,128,.28); padding: 7px 12px; color: inherit !important; background: transparent; }
.stMarkdown tr:nth-child(even) td { background: color-mix(in srgb, var(--secundario) 12%, transparent) !important; }

/* Aprobaciones */
[class*="st-key-aprob_"] { border: 2px solid var(--aviso); border-radius: 14px; padding: 1rem 1.2rem;
  background: color-mix(in srgb, var(--aviso) 7%, transparent);
  box-shadow: 0 4px 16px color-mix(in srgb, var(--aviso) 15%, transparent); margin-bottom: 1rem; }
.aprob-titulo { font-family: var(--fuente-titulos), sans-serif; font-weight: 700; font-size: 1.1rem; }
.aprob-sub { font-size: .85rem; opacity: .8; margin-bottom: .4rem; }
[class*="st-key-rechazar_"] .stButton > button { background: var(--peligro); }
[class*="st-key-rechazar_"] .stButton > button:hover { background: color-mix(in srgb, var(--peligro) 85%, black);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--peligro) 35%, transparent); }

/* Figuras */
.figura { margin: .8rem 0; padding: .7rem; border-radius: 14px; border: 1px solid rgba(128,128,128,.25);
  background: rgba(128,128,128,.05); max-width: 640px; }
.figura img { width: 100%; border-radius: 10px; background: #fff; }
.figura figcaption { font-size: .8rem; opacity: .75; margin-top: .45rem; text-align: center; }
[class*="st-key-figgraf_"] { margin: .8rem 0; padding: .7rem; border-radius: 14px; max-width: 680px;
  border: 1px solid rgba(128,128,128,.25); background: rgba(128,128,128,.05); }
.figura-pie { font-size: .8rem; opacity: .75; text-align: center; margin-top: -.3rem; }

/* Estado vacío */
.vacio { text-align: center; padding: 1.5rem 0 .5rem 0; }
.vacio h3 { margin-bottom: .2rem; }
.vacio-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-top: 1.2rem; }
.vacio-card { padding: 1.1rem; border-radius: 14px; border: 1px solid rgba(128,128,128,.22);
  background: rgba(128,128,128,.04); text-align: left; }
.vacio-card .ic { font-size: 1.6rem; }
.vacio-card b { display: block; margin: .3rem 0 .2rem 0; font-family: var(--fuente-titulos), sans-serif; }
.vacio-card span { font-size: .87rem; opacity: .8; }
"""
st.html(f"<style>{_root}{CSS}</style>")


# ---------------------------------------------------------------- Agente
@st.cache_resource(show_spinner=f"Conectando con {NOMBRE_PROVEEDOR}…")
def get_agente():
    return crear_agente(PROVEEDOR, ajustes=AGENTE_CFG, carpeta_salidas=CARPETA_SALIDAS, log=log)


def nueva_conversacion():
    agente = get_agente()
    if st.session_state.get("conv_id"):
        try:
            agente.cerrar_conversacion(st.session_state.conv_id)
        except Exception:
            pass
    st.session_state.conv_id = agente.nueva_conversacion()
    st.session_state.mensajes = []
    st.session_state.pendientes = []      # aprobaciones (dicts) esperando decisión
    st.session_state.decisiones = {}      # aprobacion_id -> bool
    st.session_state.ficheros_turno = []
    st.session_state.actividad_turno = []


def _cerrar_turno():
    st.session_state.ficheros_turno = []
    st.session_state.actividad_turno = []


def procesar(entrada):
    """Envía texto (str) o decisiones (list[Decision]) al agente y actualiza el historial."""
    agente = get_agente()
    conv_id = st.session_state.conv_id
    try:
        with st.chat_message("assistant", avatar=AVATAR_AGENTE):
            with st.spinner(APP.get("texto_espera", "El agente está pensando…")):
                if isinstance(entrada, str):
                    resp = agente.enviar(conv_id, entrada)
                else:
                    resp = agente.responder_aprobaciones(conv_id, entrada)
        st.session_state.actividad_turno += [asdict(a) for a in resp.actividad]
        for ruta in resp.ficheros:
            if ruta not in st.session_state.ficheros_turno:
                st.session_state.ficheros_turno.append(ruta)

        if resp.aprobaciones:
            st.session_state.pendientes = [asdict(a) for a in resp.aprobaciones]
            st.session_state.decisiones = {}
        else:
            ficheros = st.session_state.ficheros_turno
            texto, graficos, aviso = extraer_bloques(resp.texto or "_(sin texto)_",
                                                     GRAFICOS.get("bloques", {}), log)
            hay_figuras = bool(graficos) or any(r.lower().endswith(EXT_IMAGEN) for r in ficheros)
            st.session_state.mensajes.append({
                "role": "assistant",
                "content": agente.postprocesar_texto(texto, hay_figuras),
                "ficheros": ficheros,
                "graficos": graficos,
                "aviso": aviso,
                "actividad": st.session_state.actividad_turno,
            })
            _cerrar_turno()
    except Exception as e:
        log.exception("Error al hablar con el agente")
        st.session_state.pendientes = []
        st.session_state.decisiones = {}
        st.session_state.mensajes.append({
            "role": "error", "content": f"Error al hablar con el agente: {e}",
            "actividad": st.session_state.actividad_turno,
        })
        _cerrar_turno()
    st.rerun()


# ---------------------------------------------------------------- Pintado
def pintar_figura(ruta):
    with open(ruta, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    mime = mimetypes.guess_type(ruta)[0] or "image/png"
    nombre = os.path.basename(ruta).split("_", 1)[-1]
    st.html(
        f'<figure class="figura"><img src="data:{mime};base64,{b64}"/>'
        f"<figcaption>📊 Figura · {html.escape(nombre)}</figcaption></figure>",
    )


def pintar_actividad(actividad):
    if not actividad:
        return
    with st.expander(f"🔧 Actividad del agente ({len(actividad)})"):
        for a in actividad:
            st.markdown(f"{a['icono']} **{a['nombre']}** — {a['estado']}")
            if a.get("args") not in (None, {}, ""):
                if isinstance(a["args"], (dict, list)):
                    st.json(a["args"], expanded=False)
                else:
                    st.code(str(a["args"]))


def pintar_mensaje(m, idx=0):
    if m["role"] == "error":
        st.error(m["content"])
        pintar_actividad(m.get("actividad"))
        return
    if m["role"] == "approval":
        clase = "traza" if m.get("ok") else "traza no"
        st.html(f'<div class="{clase}">{html.escape(m["content"])}</div>')
        return
    avatar = AVATAR_AGENTE if m["role"] == "assistant" else AVATAR_USUARIO
    with st.chat_message(m["role"], avatar=avatar):
        if m.get("aviso"):
            st.warning(m["aviso"])
        st.markdown(m["content"])
        for k, g in enumerate(m.get("graficos") or []):
            pintar_grafico(g, GRAFICOS.get("paleta", ["#1f77b4"]), f"{idx}_{k}", f"{FUENTE_TEXTO}, sans-serif")
        for ruta in m.get("ficheros") or []:
            if ruta.lower().endswith(EXT_IMAGEN) and os.path.exists(ruta):
                pintar_figura(ruta)
            else:
                st.caption(f"📎 Fichero guardado: {ruta}")
        pintar_actividad(m.get("actividad"))


# ---------------------------------------------------------------- Estado
conectado = True
error_conexion = None
try:
    if "conv_id" not in st.session_state:
        nueva_conversacion()
except Exception as e:
    conectado = False
    error_conexion = e

# ---------------------------------------------------------------- Barra lateral
prompt = None
with st.sidebar:
    st.html(
        f'<div class="sb-marca">{logo_img(40, 46)}'
        f"<div><b>{html.escape(MARCA.get('nombre', ''))}</b><br>"
        f"<small>{html.escape(MARCA.get('subtitulo_lateral', ''))}</small></div></div>",
    )
    st.html('<div class="sb-sec">Conversación</div>')
    if st.button("🔄 Nueva conversación", disabled=not conectado, width="stretch"):
        try:
            nueva_conversacion()
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo crear la conversación: {e}")

    consultas = CFG.get("consultas_rapidas", [])
    if consultas:
        st.html('<div class="sb-sec">Consultas rápidas</div>')
        hay_pendientes = bool(conectado and st.session_state.pendientes)
        with st.container(key="rapidas"):
            for i, c in enumerate(consultas):
                etiqueta = f"{c.get('icono', '')} **{c['titulo']}**"
                if c.get("descripcion"):
                    etiqueta += f"\n\n{c['descripcion']}"
                if st.button(etiqueta, key=f"rap_{i}", help=c["prompt"], width="stretch",
                             disabled=hay_pendientes or not conectado):
                    prompt = c["prompt"]

    nombre_prov = html.escape(NOMBRE_PROVEEDOR)
    etiqueta_agente = html.escape(get_agente().etiqueta) if conectado else html.escape(PROVEEDOR)
    st.html(
        '<div class="sb-estado">'
        + (f'<span class="ok">● Conectado a {nombre_prov}</span>' if conectado
           else f'<span class="ko">● Sin conexión con {nombre_prov}</span>')
        + f"<br><small>Agente: {etiqueta_agente}</small></div>",
    )

# ---------------------------------------------------------------- Principal
_pill = f'<span class="pill">{html.escape(MARCA["etiqueta"])}</span>' if MARCA.get("etiqueta") else ""
st.html(
    f'<div class="hero">{logo_img(78, 90)}<div><h1>{html.escape(MARCA.get("nombre", ""))}</h1>'
    f"<p>{html.escape(MARCA.get('subtitulo', ''))}</p>{_pill}</div></div>",
)

if not conectado:
    st.error(f"No se pudo conectar con {NOMBRE_PROVEEDOR}: {error_conexion}")
    st.stop()

BIENVENIDA = CFG.get("bienvenida", {})
if BIENVENIDA and not st.session_state.mensajes and not st.session_state.pendientes and not prompt:
    tarjetas = "".join(
        f'<div class="vacio-card"><div class="ic">{html.escape(t.get("icono", ""))}</div>'
        f'<b>{html.escape(t.get("titulo", ""))}</b><span>{html.escape(t.get("texto", ""))}</span></div>'
        for t in BIENVENIDA.get("tarjetas", [])
    )
    st.html(
        f'<div class="vacio"><h3>{html.escape(BIENVENIDA.get("titulo", ""))}</h3>'
        f'<span>{html.escape(BIENVENIDA.get("texto", ""))}</span>'
        f'<div class="vacio-grid">{tarjetas}</div></div>'
    )

for i, m in enumerate(st.session_state.mensajes):
    pintar_mensaje(m, i)

# Aprobaciones pendientes (human-in-the-loop)
if st.session_state.pendientes:
    for p in st.session_state.pendientes:
        with st.container(key=f"aprob_{p['id']}"):
            st.html(
                f'<div class="aprob-titulo">⚠️ Solicitud de acción en {html.escape(p["servidor"])}</div>'
                f'<div class="aprob-sub">El agente quiere ejecutar <b>{html.escape(p["herramienta"])}</b> '
                f'en <b>{html.escape(p["servidor"])}</b>. Revisa los argumentos:</div>',
            )
            if isinstance(p["argumentos"], (dict, list)):
                st.json(p["argumentos"])
            else:
                st.code(str(p["argumentos"]))
            decision = st.session_state.decisiones.get(p["id"])
            if decision is None:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Aprobar", key=f"aprobar_{p['id']}", width="stretch"):
                        st.session_state.decisiones[p["id"]] = True
                        st.rerun()
                with c2:
                    with st.container(key=f"rechazar_{p['id']}"):
                        if st.button("❌ Rechazar", key=f"btn_rechazar_{p['id']}", width="stretch"):
                            st.session_state.decisiones[p["id"]] = False
                            st.rerun()
            else:
                st.markdown("✅ Aprobada" if decision else "❌ Rechazada")

    if all(p["id"] in st.session_state.decisiones for p in st.session_state.pendientes):
        decisiones = []
        for p in st.session_state.pendientes:
            ok = st.session_state.decisiones[p["id"]]
            decisiones.append(Decision(aprobacion_id=p["id"], aprobar=ok))
            etiqueta = f"{p['servidor']} · {p['herramienta']}"
            st.session_state.actividad_turno.append(asdict(Actividad(
                "🔐", f"Solicitud de aprobación: {etiqueta}",
                "✅ aprobada" if ok else "❌ rechazada", p["argumentos"])))
            st.session_state.mensajes.append({
                "role": "approval", "ok": ok,
                "content": f"{'✅ Aprobado' if ok else '❌ Rechazado'}: {etiqueta}",
            })
        st.session_state.pendientes = []
        st.session_state.decisiones = {}
        procesar(decisiones)

escrito = st.chat_input(APP.get("placeholder", "Escribe tu mensaje…"),
                        disabled=bool(st.session_state.pendientes))
prompt = prompt or escrito

if prompt:
    st.session_state.mensajes.append({"role": "user", "content": prompt})
    pintar_mensaje(st.session_state.mensajes[-1])
    procesar(prompt)
