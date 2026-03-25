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

st.set_page_config(page_title="Dashboard — Trading Journal Pro", layout="wide", initial_sidebar_state="expanded")

CSS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "style.css")
if os.path.exists(CSS):
    with open(CSS, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── Datos ───────────────────────────────────────────────────────────────────
trades       = obtener_todos_los_trades()
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
capital      = config.get("tamanio_cuenta", 10000)
divisa       = config.get("divisa", "USD")
nombre       = config.get("nombre_trader", "Trader")

# ─── Page header ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="page-header">
  <span class="page-header-icon">📊</span>
  <div>
    <div class="page-header-title">Dashboard</div>
    <div class="page-header-sub">Bienvenido, {nombre} · {date.today().strftime("%A, %d de %B de %Y")} · Cuenta: {capital:,.0f} {divisa}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── KPI Row ─────────────────────────────────────────────────────────────────
def kpi(label, value, delta=None, accent="#58a6ff", prefix="", suffix=""):
    delta_html = ""
    if delta is not None:
        cls = "pos" if delta >= 0 else "neg"
        arrow = "▲" if delta >= 0 else "▼"
        delta_html = f'<div class="kpi-card-delta {cls}">{arrow} {abs(delta):.2f}%</div>'
    return f"""
    <div class="kpi-card">
      <div class="kpi-card-accent" style="background:linear-gradient(90deg,{accent},transparent)"></div>
      <div class="kpi-card-label">{label}</div>
      <div class="kpi-card-value">{prefix}{value}{suffix}</div>
      {delta_html}
    </div>"""

c1,c2,c3,c4,c5,c6 = st.columns(6)
COLS = [c1,c2,c3,c4,c5,c6]
kpis = [
    ("P&L Hoy",    f"{pnl_dia:+.2f}%",  pnl_dia,  "#58a6ff"),
    ("P&L Semana", f"{pnl_sem:+.2f}%",  pnl_sem,  "#bc8cff"),
    ("P&L Mes",    f"{pnl_mes:+.2f}%",  pnl_mes,  "#39d0d8"),
    ("Drawdown",   f"{dd:.2f}%",         -dd,      "#f85149"),
    ("Winrate",    f"{wr_global:.1f}%",  None,     "#3fb950"),
    ("Riesgo Rec.",f"{riesgo_info['riesgo']:.2f}%",None,"#e3a949"),
]
for col, (label, val, delta, accent) in zip(COLS, kpis):
    with col:
        st.markdown(kpi(label, val, delta, accent), unsafe_allow_html=True)

st.markdown("<div style='margin:1.5rem 0 0'></div>", unsafe_allow_html=True)

# ─── Semáforo + Motor de riesgo ──────────────────────────────────────────────
col_sem, col_metricas = st.columns([2, 3])

with col_sem:
    color = semaforo["color"]
    cls = {"green":"semaforo-verde","orange":"semaforo-amarillo","red":"semaforo-rojo"}.get(color,"semaforo-verde")
    st.markdown(f"""
    <div class="semaforo {cls}">
      <span style="font-size:2.5rem;line-height:1">{semaforo['texto'].split()[0]}</span>
      <div>
        <div style="font-size:1rem;font-weight:800">{' '.join(semaforo['texto'].split()[1:])}</div>
        <div style="font-size:0.78rem;font-weight:400;opacity:0.85;margin-top:4px">{semaforo['descripcion']}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin-top:12px" class="alert-{'critica' if riesgo_info['nivel'] in ('CRITICO','ALTO') else 'precaucion' if riesgo_info['nivel'] in ('ELEVADO','PRECAUCION_DIA','RACHA_NEGATIVA') else 'ok'}">
      {riesgo_info['justificacion']}
    </div>
    """, unsafe_allow_html=True)

with col_metricas:
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("WR-10",   f"{metricas['winrate_10']:.0f}%")
    m2.metric("WR-20",   f"{metricas['winrate_20']:.0f}%")
    racha_txt = f"{metricas['racha_actual']} {'🏆' if metricas['tipo_racha']=='ganadora' else '⚠️'}" if metricas['racha_actual'] else "—"
    m3.metric("Racha",   racha_txt)
    m4.metric("P&L hoy", f"{pnl_dia:+.2f}%")

    # Mini gauge drawdown
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=dd,
        number={"suffix":"%","font":{"size":22,"family":"JetBrains Mono","color":"#e6edf3"}},
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

st.markdown("<hr>", unsafe_allow_html=True)

# ─── Últimos 5 trades ─────────────────────────────────────────────────────────
col_trades, col_equity = st.columns([1, 2])

STRAT_COLORS = {"Blue":"#58a6ff","Red":"#f85149","Pink":"#ff7eb6","White":"#c9d1d9","Black":"#8b949e","Green":"#3fb950"}
RES_COLORS   = {"Win":"#3fb950","Loss":"#f85149","Breakeven":"#8b949e","Parcial":"#e3a949"}

with col_trades:
    st.subheader("Últimas Operaciones")
    ultimos = obtener_ultimos_trades(5)
    if not ultimos:
        st.markdown('<div class="alert-info">Sin trades registrados. Ve a <strong>Nuevo Trade</strong> para empezar.</div>', unsafe_allow_html=True)
    else:
        # Header
        st.markdown("""
        <div style="background:var(--bg-4);border-radius:10px 10px 0 0;border:1px solid var(--border);border-bottom:0">
          <div style="display:grid;grid-template-columns:70px 75px 60px 65px 70px 65px;gap:0;padding:8px 12px">
            <span style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted-2)">Fecha</span>
            <span style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted-2)">Par</span>
            <span style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted-2)">Strat</span>
            <span style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted-2)">Result.</span>
            <span style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted-2)">Pips</span>
            <span style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted-2)">% Cta</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        rows_html = '<div style="border:1px solid var(--border);border-radius:0 0 10px 10px;overflow:hidden">'
        for i, t in enumerate(ultimos):
            bg = "var(--bg-3)" if i % 2 == 0 else "var(--bg-4)"
            res  = t.get("resultado","—")
            stra = t.get("estrategia","—")
            pips = t.get("pips_resultado",0) or 0
            pct  = t.get("porcentaje_cuenta",0) or 0
            rc   = RES_COLORS.get(res,"#8b949e")
            sc   = STRAT_COLORS.get(stra,"#8b949e")
            pips_c = "#3fb950" if pips > 0 else "#f85149" if pips < 0 else "#8b949e"
            pct_c  = "#3fb950" if pct  > 0 else "#f85149" if pct  < 0 else "#8b949e"
            fecha  = (t.get("fecha_entrada","") or "")[-5:]
            rows_html += f"""
            <div style="display:grid;grid-template-columns:70px 75px 60px 65px 70px 65px;gap:0;
                        padding:9px 12px;background:{bg};border-bottom:1px solid var(--border);
                        font-family:'JetBrains Mono',monospace;font-size:0.8rem;transition:background 0.1s">
              <span style="color:var(--muted)">{fecha}</span>
              <span style="color:var(--white);font-weight:600">{t.get('par','—')}</span>
              <span style="color:{sc};font-weight:700">{stra}</span>
              <span style="color:{rc};font-weight:700">{res}</span>
              <span style="color:{pips_c}">{pips:+.1f}</span>
              <span style="color:{pct_c};font-weight:600">{pct:+.2f}%</span>
            </div>"""
        rows_html += "</div>"
        st.markdown(rows_html, unsafe_allow_html=True)

# ─── Equity curve ────────────────────────────────────────────────────────────
with col_equity:
    st.subheader("Equity Curve — Últimos 30 días")
    hace_30 = (date.today() - timedelta(days=30)).isoformat()
    tv30 = [t for t in tv if (t.get("fecha_salida") or t.get("fecha_entrada","")) >= hace_30]
    curva = calcular_equity_curve(tv30, capital)

    if len(curva) < 2:
        st.markdown('<div class="alert-info">Necesitas al menos 2 trades para ver la equity curve.</div>', unsafe_allow_html=True)
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
            marker=dict(size=6, color=color_line, line=dict(width=2, color=var if (var:="var(--bg-3)") else "")),
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
    st.markdown(f"""
    <div style="padding:12px 0 8px">
      <div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted-2);margin-bottom:8px">Resumen Global</div>
    </div>
    """, unsafe_allow_html=True)
    st.metric("Total trades",  len(tv))
    st.metric("Winrate global", f"{wr_global:.1f}%")
    wins   = sum(1 for t in tv if t.get("resultado")=="Win")
    losses = sum(1 for t in tv if t.get("resultado")=="Loss")
    st.metric("W / L", f"{wins} / {losses}")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown('<div class="app-footer">Trading Journal Pro v2.0 · {}</div>'.format(date.today().year), unsafe_allow_html=True)
