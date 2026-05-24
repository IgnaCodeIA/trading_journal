"""
Dashboard — Métricas clave, semáforo visual, últimos trades y equity curve.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import obtener_todos_los_trades, obtener_configuracion, obtener_ultimos_trades
from core.stats import (
    calcular_pnl_dia, calcular_pnl_semana, calcular_pnl_mes,
    calcular_equity_curve, calcular_winrate,
)
from core.risk_engine import calcular_metricas_riesgo, calcular_riesgo_recomendado, calcular_semaforo
from core.cuenta_selector import render_cuenta_selector

st.set_page_config(page_title="Dashboard — Trading Journal Pro", layout="wide", initial_sidebar_state="expanded")

CSS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "style.css")
if os.path.exists(CSS):
    with open(CSS, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── Cuenta activa ───────────────────────────────────────────────────────────
cuenta_id, cuenta = render_cuenta_selector()

# ─── Datos ───────────────────────────────────────────────────────────────────
trades       = obtener_todos_los_trades(cuenta_id=cuenta_id)
config       = obtener_configuracion()
tv           = [t for t in trades if t.get("resultado") in ("Win","Loss","Breakeven","Parcial")]
metricas     = calcular_metricas_riesgo(trades)
riesgo_info  = calcular_riesgo_recomendado(metricas)
semaforo     = calcular_semaforo(metricas, config)
pnl_dia      = calcular_pnl_dia(tv)
pnl_sem      = calcular_pnl_semana(tv)
pnl_mes      = calcular_pnl_mes(tv)
dd           = metricas["drawdown_actual"]
wr_global    = calcular_winrate(tv)
capital      = cuenta.get("capital", 10000)
divisa       = cuenta.get("divisa", "USD")
nombre       = config.get("nombre_trader", "Trader")

# ─── Page header ─────────────────────────────────────────────────────────────
st.title("📊 Dashboard")
st.caption(f"Bienvenido, {nombre} · {date.today().strftime('%A, %d de %B de %Y')} · Cuenta: {capital:,.0f} {divisa}")

# ─── KPI Row ─────────────────────────────────────────────────────────────────
usd_dia = capital * pnl_dia / 100
usd_sem = capital * pnl_sem / 100
usd_mes = capital * pnl_mes / 100

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("P&L Hoy",      f"{pnl_dia:+.2f}%", delta=f"{usd_dia:+,.0f} {divisa}")
c2.metric("P&L Semana",   f"{pnl_sem:+.2f}%", delta=f"{usd_sem:+,.0f} {divisa}")
c3.metric("P&L Mes",      f"{pnl_mes:+.2f}%", delta=f"{usd_mes:+,.0f} {divisa}")
c4.metric("Drawdown",     f"{dd:.2f}%",       delta=f"{-capital * dd / 100:,.0f} {divisa}", delta_color="inverse")
c5.metric("Winrate",      f"{wr_global:.1f}%")
c6.metric("Riesgo Rec.",  f"{riesgo_info['riesgo']:.2f}%")

st.divider()

# ─── Semáforo + Motor de riesgo ──────────────────────────────────────────────
col_sem, col_metricas = st.columns([2, 3])

with col_sem:
    color = semaforo["color"]
    titulo_sem = semaforo["texto"]
    descripcion_sem = semaforo["descripcion"]
    if color == "green":
        st.success(f"**{titulo_sem}**\n\n{descripcion_sem}")
    elif color == "orange":
        st.warning(f"**{titulo_sem}**\n\n{descripcion_sem}")
    else:
        st.error(f"**{titulo_sem}**\n\n{descripcion_sem}")

    nivel = riesgo_info["nivel"]
    just = riesgo_info["justificacion"]
    if nivel in ("CRITICO", "ALTO"):
        st.error(just)
    elif nivel in ("ELEVADO", "PRECAUCION_DIA", "RACHA_NEGATIVA"):
        st.warning(just)
    else:
        st.success(just)

with col_metricas:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("WR-10",   f"{metricas['winrate_10']:.0f}%")
    m2.metric("WR-20",   f"{metricas['winrate_20']:.0f}%")
    racha_txt = f"{metricas['racha_actual']} {'🏆' if metricas['tipo_racha']=='ganadora' else '⚠️'}" if metricas['racha_actual'] else "—"
    m3.metric("Racha",   racha_txt)
    m4.metric("P&L hoy", f"{pnl_dia:+.2f}%")

    # Mini gauge drawdown
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=dd,
        number={"suffix":"%","font":{"size":22,"family":"IBM Plex Mono","color":"#e6edf3"}},
        gauge={
            "axis":{"range":[0,15],"tickcolor":"#8b949e","tickfont":{"size":9}},
            "bar":{"color":"#f85149" if dd>8 else "#e3a949" if dd>5 else "#3fb950","thickness":0.25},
            "bgcolor":"rgba(0,0,0,0)",
            "borderwidth":0,
            "steps":[
                {"range":[0,5],"color":"rgba(63,185,80,0.1)"},
                {"range":[5,8],"color":"rgba(227,169,73,0.1)"},
                {"range":[8,15],"color":"rgba(248,81,73,0.1)"},
            ],
            "threshold":{"line":{"color":"#f85149","width":2},"thickness":0.8,"value":12},
        },
        domain={"x":[0,1],"y":[0,1]},
        title={"text":"Drawdown %","font":{"size":11,"color":"#8b949e"}},
    ))
    fig_gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        height=160, margin=dict(l=20,r=20,t=30,b=0),
        font={"color":"#e6edf3"},
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

st.divider()

# ─── Últimos 5 trades + Equity curve ──────────────────────────────────────────
col_trades, col_equity = st.columns([1, 2])

with col_trades:
    st.subheader("Últimas Operaciones")
    ultimos = obtener_ultimos_trades(5, cuenta_id=cuenta_id)
    if not ultimos:
        st.info("Sin trades registrados. Ve a **Nuevo Trade** para empezar.")
    else:
        rows = []
        for t in ultimos:
            pct = t.get("porcentaje_cuenta", 0) or 0
            usd = t.get("importe_dinero") or (capital * pct / 100)
            rows.append({
                "Fecha": (t.get("fecha_entrada", "") or "")[-5:],
                "Par":   t.get("par", "—"),
                "Strat": t.get("estrategia", "—"),
                "Resultado": t.get("resultado", "—"),
                "% Cta": round(pct, 2),
                divisa:  round(usd, 0),
            })
        df_ultimos = pd.DataFrame(rows)
        st.dataframe(df_ultimos, use_container_width=True, hide_index=True)

with col_equity:
    st.subheader("Equity Curve — Últimos 30 días")
    hace_30 = (date.today() - timedelta(days=30)).isoformat()
    tv30 = [t for t in tv if (t.get("fecha_salida") or t.get("fecha_entrada","")) >= hace_30]
    curva = calcular_equity_curve(tv30, capital)

    if len(curva) < 2:
        st.info("Necesitas al menos 2 trades para ver la equity curve.")
    else:
        fechas = [p["fecha"] or "Inicio" for p in curva]
        valores = [p["equity"] for p in curva]
        color_line = "#3fb950" if valores[-1] >= capital else "#f85149"
        fill_color = "rgba(63,185,80,0.08)" if valores[-1] >= capital else "rgba(248,81,73,0.08)"

        fig = go.Figure()
        # Área de fondo
        fig.add_trace(go.Scatter(
            x=fechas, y=valores, mode="none", fill="tozeroy", fillcolor=fill_color, showlegend=False,
        ))
        # Línea principal
        fig.add_trace(go.Scatter(
            x=fechas, y=valores, mode="lines+markers",
            line=dict(color=color_line, width=2.5, shape="spline"),
            marker=dict(size=6, color=color_line, line=dict(width=2, color="#1c2128")),
            name="Equity", showlegend=False,
            hovertemplate="<b>%{x}</b><br>Equity: %{y:,.2f} " + divisa + "<extra></extra>",
        ))
        # Capital inicial
        fig.add_hline(y=capital, line_dash="dot", line_color="#444c56", line_width=1.5,
            annotation_text=f"Capital inicial {capital:,.0f}", annotation_font_size=10,
            annotation_font_color="#6e7681", annotation_position="bottom right")
        # Max
        if valores:
            max_val = max(valores)
            max_idx = valores.index(max_val)
            fig.add_annotation(x=fechas[max_idx], y=max_val, text=f"MAX<br>{max_val:,.0f}",
                showarrow=True, arrowhead=2, arrowcolor="#3fb950", arrowsize=1,
                font=dict(size=9, color="#3fb950"), bgcolor="rgba(27,58,27,0.9)", bordercolor="#3fb950",
                borderwidth=1, borderpad=4)

        fig.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=340, margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=10, color="#6e7681")),
            yaxis=dict(showgrid=True, gridcolor="#21262d", zeroline=False,
                       tickfont=dict(size=10, color="#6e7681"), tickprefix="", tickformat=",.0f"),
            hovermode="x unified",
            hoverlabel=dict(bgcolor="#1c2128", bordercolor="#30363d", font_size=12),
        )
        st.plotly_chart(fig, use_container_width=True)

# ─── Sidebar stats ────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("Resumen Global")
    st.metric("Total trades",  len(tv))
    st.metric("Winrate global", f"{wr_global:.1f}%")
    wins   = sum(1 for t in tv if t.get("resultado") == "Win")
    losses = sum(1 for t in tv if t.get("resultado") == "Loss")
    st.metric("W / L", f"{wins} / {losses}")
    st.divider()
    pnl_total_pct = sum(t.get("porcentaje_cuenta", 0) or 0 for t in tv)
    pnl_total_usd = capital * pnl_total_pct / 100
    st.metric(f"P&L Total ({divisa})", f"{pnl_total_usd:+,.0f}", delta=f"{pnl_total_pct:+.2f}%")
    st.metric(f"P&L Mes ({divisa})",   f"{usd_mes:+,.0f}",       delta=f"{pnl_mes:+.2f}%")
    st.metric(f"P&L Semana ({divisa})", f"{usd_sem:+,.0f}",      delta=f"{pnl_sem:+.2f}%")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown(f'<div class="app-footer">Trading Journal Pro v2.0 · {date.today().year}</div>', unsafe_allow_html=True)
