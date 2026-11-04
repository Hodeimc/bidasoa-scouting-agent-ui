"""
Gráficos declarativos dentro de la respuesta del agente.

El agente escribe un bloque de código cuya etiqueta está configurada en
config.toml ([graficos.bloques], p. ej. ```radar), con un JSON. La interfaz lo
quita del texto y lo dibuja con plotly. Formato común:

    {"titulo": "...", "ejes": ["A", "B", ...],
     "series": [{"nombre": "...", "valores": [1, 2, ...]}, ...]}

Para añadir un tipo nuevo: escribe una función `_mi_tipo(spec, paleta)` que
devuelva una figura de plotly y regístrala en RENDERIZADORES.
"""

import html
import json
import re

import streamlit as st

CLAVES_SERIES = ["series"]  # claves aceptadas para la lista de series (ampliable con configurar())


def configurar(claves_series=None):
    """Añade alias para la lista de series (p. ej. los que use el agente en su JSON)."""
    for c in claves_series or []:
        if c not in CLAVES_SERIES:
            CLAVES_SERIES.append(c)


def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def _normalizar(datos):
    """Valida el JSON y lo lleva al formato común {titulo, ejes, series}."""
    ejes = [str(e) for e in datos["ejes"]]
    crudas = next((datos[k] for k in CLAVES_SERIES if k in datos), None)
    if crudas is None:
        raise ValueError(f"falta la lista de series (una de: {', '.join(CLAVES_SERIES)})")
    series = []
    for s in crudas:
        valores = [float(v) for v in s["valores"]]
        if len(valores) != len(ejes):
            raise ValueError(f"'{s.get('nombre', '?')}' tiene {len(valores)} valores para {len(ejes)} ejes")
        series.append({"nombre": str(s["nombre"]), "valores": valores})
    if not ejes or not series:
        raise ValueError("faltan ejes o series")
    spec = {"titulo": str(datos.get("titulo", "Gráfico")), "ejes": ejes, "series": series}
    if "rango" in datos:
        spec["rango"] = [float(x) for x in datos["rango"]]
    return spec


def extraer_bloques(texto, bloques, log=None):
    """Quita del texto los bloques de gráfico válidos.

    `bloques` mapea etiqueta del bloque -> tipo de gráfico (p. ej. {"radar": "radar"}).
    Devuelve (texto, graficos, aviso). Un bloque mal formado se deja en el texto y
    genera un aviso.
    """
    if not bloques:
        return texto, [], None
    etiquetas = "|".join(re.escape(e) for e in bloques)
    patron = re.compile(rf"```({etiquetas})[ \t]*\r?\n(.*?)```", re.S)
    graficos, errores = [], []

    def sustituir(m):
        try:
            spec = _normalizar(json.loads(m.group(2)))
            graficos.append({"tipo": bloques[m.group(1)], "spec": spec})
            return ""
        except Exception as e:
            if log:
                log.warning("Bloque de gráfico '%s' mal formado: %s", m.group(1), e)
            errores.append(str(e))
            return m.group(0)

    texto = patron.sub(sustituir, texto).strip()
    aviso = (f"No se pudo dibujar el gráfico (JSON mal formado: {'; '.join(errores)}). "
             "Se muestra el texto original.") if errores else None
    return texto, graficos, aviso


# ---------------------------------------------------------------- Renderizadores
REJILLA = "rgba(128,128,128,0.35)"


def _radar(spec, paleta):
    import plotly.graph_objects as go

    ejes = spec["ejes"] + spec["ejes"][:1]  # cerrar el polígono
    fig = go.Figure()
    for i, s in enumerate(spec["series"]):
        color = paleta[i % len(paleta)]
        fig.add_trace(go.Scatterpolar(
            r=s["valores"] + s["valores"][:1], theta=ejes, name=s["nombre"],
            fill="toself", fillcolor=_rgba(color, 0.22),
            line=dict(color=color, width=2.5), marker=dict(size=6, color=color),
            hovertemplate="<b>%{fullData.name}</b><br>%{theta}: %{r:.0f}<extra></extra>",
        ))
    fig.update_layout(polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(range=spec.get("rango", [0, 100]), gridcolor=REJILLA, linecolor=REJILLA,
                        tickfont=dict(size=10), angle=90, tickangle=90),
        angularaxis=dict(gridcolor=REJILLA, linecolor=REJILLA, tickfont=dict(size=12)),
    ))
    return fig


def _barras(spec, paleta):
    import plotly.graph_objects as go

    fig = go.Figure()
    for i, s in enumerate(spec["series"]):
        fig.add_trace(go.Bar(x=spec["ejes"], y=s["valores"], name=s["nombre"],
                             marker_color=paleta[i % len(paleta)]))
    fig.update_layout(barmode="group", xaxis=dict(gridcolor=REJILLA), yaxis=dict(gridcolor=REJILLA))
    return fig


RENDERIZADORES = {"radar": _radar, "barras": _barras}


def pintar_grafico(grafico, paleta, key, fuente="sans-serif"):
    """Dibuja un gráfico dentro del marco de figura (contenedor con clave figgraf_*)."""
    spec = grafico["spec"]
    fig = RENDERIZADORES[grafico["tipo"]](spec, paleta)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="top", y=-0.08, xanchor="center", x=0.5),
        margin=dict(l=50, r=50, t=30, b=40), height=460, font=dict(family=fuente),
    )
    with st.container(key=f"figgraf_{key}"):
        st.plotly_chart(fig, key=f"plot_{key}", theme="streamlit", width="stretch",
                        config={"displaylogo": False})
        st.html(f'<div class="figura-pie">📊 Figura · {html.escape(spec["titulo"])}</div>')
