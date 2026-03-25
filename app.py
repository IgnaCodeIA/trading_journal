"""
Trading Journal Pro — Entry point y navegación principal
Arrancar con: streamlit run app.py
"""

import streamlit as st
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.database import inicializar_db

st.set_page_config(
    page_title="Trading Journal Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "style.css")
if os.path.exists(CSS):
    with open(CSS, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

inicializar_db()

from core.database import obtener_todos_los_trades, obtener_configuracion
from core.stats import calcular_winrate, calcular_pnl_mes
from core.risk_engine import calcular_metricas_riesgo, calcular_riesgo_recomendado

trades = obtener_todos_los_trades()
config = obtener_configuracion()
tv = [t for t in trades if t.get("resultado") in ("Win","Loss","Breakeven","Parcial")]
metricas = calcular_metricas_riesgo(trades)
riesgo_info = calcular_riesgo_recomendado(metricas)

# ─── Hero section ─────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:3rem 1rem 2rem">
  <div style="font-size:4rem;margin-bottom:0.5rem">📈</div>
  <h1 style="font-size:2.8rem;font-weight:900;letter-spacing:-0.04em;
             background:linear-gradient(135deg,#58a6ff,#bc8cff,#3fb950);
             -webkit-background-clip:text;-webkit-text-fill-color:transparent;
             background-clip:text;margin:0">
    Trading Journal Pro
  </h1>
  <p style="color:#8b949e;font-size:1rem;margin-top:0.5rem;font-weight:400">
    Tu terminal profesional de análisis y gestión de trades
  </p>
</div>
""", unsafe_allow_html=True)

# ─── Quick stats bar ──────────────────────────────────────────────────────────
nombre = config.get("nombre_trader","Trader")
cuenta = config.get("tamanio_cuenta",10000)
divisa = config.get("divisa","USD")
wr     = calcular_winrate(tv)
pnl_m  = calcular_pnl_mes(tv)

st.markdown(f"""
<div style="background:var(--bg-3);border:1px solid var(--border);border-radius:12px;
            padding:1rem 1.5rem;display:flex;gap:2rem;align-items:center;
            justify-content:center;flex-wrap:wrap;margin-bottom:2rem">
  <div style="text-align:center">
    <div style="font-size:0.65rem;color:var(--muted-2);text-transform:uppercase;letter-spacing:0.1em;font-weight:700">Trader</div>
    <div style="font-size:1rem;font-weight:700;color:var(--white)">{nombre}</div>
  </div>
  <div style="width:1px;background:var(--border);height:30px"></div>
  <div style="text-align:center">
    <div style="font-size:0.65rem;color:var(--muted-2);text-transform:uppercase;letter-spacing:0.1em;font-weight:700">Cuenta</div>
    <div style="font-size:1rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--white)">{cuenta:,.0f} {divisa}</div>
  </div>
  <div style="width:1px;background:var(--border);height:30px"></div>
  <div style="text-align:center">
    <div style="font-size:0.65rem;color:var(--muted-2);text-transform:uppercase;letter-spacing:0.1em;font-weight:700">Trades</div>
    <div style="font-size:1rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--white)">{len(tv)}</div>
  </div>
  <div style="width:1px;background:var(--border);height:30px"></div>
  <div style="text-align:center">
    <div style="font-size:0.65rem;color:var(--muted-2);text-transform:uppercase;letter-spacing:0.1em;font-weight:700">Winrate</div>
    <div style="font-size:1rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:{'#3fb950' if wr>=50 else '#f85149'}">{wr:.1f}%</div>
  </div>
  <div style="width:1px;background:var(--border);height:30px"></div>
  <div style="text-align:center">
    <div style="font-size:0.65rem;color:var(--muted-2);text-transform:uppercase;letter-spacing:0.1em;font-weight:700">P&L Mes</div>
    <div style="font-size:1rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:{'#3fb950' if pnl_m>=0 else '#f85149'}">{pnl_m:+.2f}%</div>
  </div>
  <div style="width:1px;background:var(--border);height:30px"></div>
  <div style="text-align:center">
    <div style="font-size:0.65rem;color:var(--muted-2);text-transform:uppercase;letter-spacing:0.1em;font-weight:700">Riesgo rec.</div>
    <div style="font-size:1rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:#e3a949">{riesgo_info['riesgo']:.2f}%</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── Navigation cards ─────────────────────────────────────────────────────────
PAGES = [
    ("📊","Dashboard","Métricas en tiempo real, semáforo y equity curve","1_dashboard"),
    ("➕","Nuevo Trade","Registra una nueva operación con formulario completo","2_nuevo_trade"),
    ("📋","Historial","Consulta, edita y exporta todos tus trades","3_historial"),
    ("📈","Estadísticas","Análisis avanzado de rendimiento y métricas","4_estadisticas"),
    ("⚡","Motor de Riesgo","Calculadora de posición y gestión dinámica de riesgo","5_motor_riesgo"),
    ("⚙️","Configuración","Parámetros del sistema, pares y backup de datos","6_configuracion"),
]

cols = st.columns(3)
for i, (icon, titulo, desc, _) in enumerate(PAGES):
    with cols[i % 3]:
        st.markdown(f"""
        <div class="kpi-card" style="padding:1.25rem 1.5rem;cursor:pointer;margin-bottom:12px">
          <div class="kpi-card-accent" style="background:linear-gradient(90deg,#58a6ff,transparent)"></div>
          <div style="font-size:1.8rem;margin-bottom:8px">{icon}</div>
          <div style="font-size:1rem;font-weight:700;color:var(--white);margin-bottom:4px">{titulo}</div>
          <div style="font-size:0.8rem;color:var(--muted);line-height:1.4">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

# ─── Sistema status ───────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
col_s1, col_s2 = st.columns([1, 2])
with col_s1:
    st.markdown("""
    <div style="font-size:0.72rem;font-weight:700;text-transform:uppercase;
                letter-spacing:0.1em;color:var(--muted-2);margin-bottom:10px">
      Estado del sistema
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f'<div class="alert-ok">✅ Base de datos conectada · {len(tv)} trades cargados</div>', unsafe_allow_html=True)

with col_s2:
    st.markdown("""
    <div style="font-size:0.72rem;font-weight:700;text-transform:uppercase;
                letter-spacing:0.1em;color:var(--muted-2);margin-bottom:10px">
      Inicio rápido
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex;gap:8px;flex-wrap:wrap;font-size:0.82rem;color:var(--muted)">
      <span>1. Configura tu cuenta en <strong style="color:var(--blue)">Configuración</strong></span>
      <span>·</span>
      <span>2. Registra trades en <strong style="color:var(--blue)">Nuevo Trade</strong></span>
      <span>·</span>
      <span>3. Analiza en <strong style="color:var(--blue)">Estadísticas</strong></span>
    </div>
    """, unsafe_allow_html=True)

st.markdown(f'<div class="app-footer">Trading Journal Pro v2.0 · {date.today().year}</div>', unsafe_allow_html=True)
