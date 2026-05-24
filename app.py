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
tv = [t for t in trades if t.get("resultado") in ("Win", "Loss", "Breakeven", "Parcial")]
metricas = calcular_metricas_riesgo(trades)
riesgo_info = calcular_riesgo_recomendado(metricas)

nombre = config.get("nombre_trader", "Trader")
cuenta = config.get("tamanio_cuenta", 10000)
divisa = config.get("divisa", "USD")
wr = calcular_winrate(tv)
pnl_m = calcular_pnl_mes(tv)

# ─── Hero ─────────────────────────────────────────────────────────────────────
st.title("📈 Trading Journal Pro")
st.caption(f"Tu terminal profesional de análisis y gestión de trades · Bienvenido, {nombre}")

# ─── Métricas globales ────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total trades", len(tv))
m2.metric("Winrate", f"{wr:.1f}%")
m3.metric("P&L Mes", f"{pnl_m:+.2f}%")
m4.metric("Riesgo recomendado", f"{riesgo_info['riesgo']:.2f}%")

st.divider()

# ─── Nav cards ────────────────────────────────────────────────────────────────
st.subheader("Secciones")

pages_config = [
    ("📊", "Dashboard", "Métricas en tiempo real, semáforo y equity curve", "pages/1_dashboard.py"),
    ("➕", "Nuevo Trade", "Registra una nueva operación", "pages/2_nuevo_trade.py"),
    ("📋", "Historial", "Consulta, edita y exporta todos tus trades", "pages/3_historial.py"),
    ("📈", "Estadísticas", "Análisis avanzado de rendimiento", "pages/4_estadisticas.py"),
    ("⚡", "Motor de Riesgo", "Calculadora de posición y riesgo dinámico", "pages/5_motor_riesgo.py"),
    ("⚙️", "Configuración", "Parámetros del sistema y backup", "pages/6_configuracion.py"),
    ("🔬", "Backtester", "Backtest por estrategia: condiciones, R y análisis de impacto", "pages/7_backtester.py"),
    ("🎯", "Estrategias", "Strategy Intelligence: deep dive y comparativa cross-estrategia", "pages/8_estrategias.py"),
]

cols = st.columns(3)
for i, (icon, title, desc, page_path) in enumerate(pages_config):
    with cols[i % 3]:
        st.subheader(f"{icon} {title}")
        st.caption(desc)
        st.page_link(page_path, label=f"Abrir {title}", icon=icon)

# ─── Estado del sistema ───────────────────────────────────────────────────────
st.divider()
st.success(f"✅ Base de datos conectada · {len(tv)} trades cargados")
st.info("**Inicio rápido:** 1) Configura tu cuenta en Configuración · 2) Registra trades en Nuevo Trade · 3) Analiza en Estadísticas")

st.markdown(f'<div class="app-footer">Trading Journal Pro v2.0 · {date.today().year}</div>', unsafe_allow_html=True)
