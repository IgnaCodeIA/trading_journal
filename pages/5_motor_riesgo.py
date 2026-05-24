"""
Motor de Riesgo — Panel de estado del sistema y calculadora de posición.
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import obtener_todos_los_trades, obtener_configuracion, load_pares, get_lista_pares_plana
from core.cuenta_selector import render_cuenta_selector
from core.risk_engine import (
    calcular_metricas_riesgo,
    calcular_riesgo_recomendado,
    calcular_tamano_posicion,
    calcular_semaforo,
)

st.set_page_config(page_title="Motor de Riesgo — Trading Journal Pro", layout="wide", initial_sidebar_state="expanded")

# CSS
css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("⚡ Motor de Riesgo")
st.markdown("---")

# ─── Cuenta activa ───────────────────────────────────────────────────────────
cuenta_id, cuenta = render_cuenta_selector()

# ─── Carga de datos ─────────────────────────────────────────────────────────
trades = obtener_todos_los_trades(cuenta_id=cuenta_id)
config = obtener_configuracion()
pares_lista = get_lista_pares_plana()

metricas = calcular_metricas_riesgo(trades)
riesgo_info = calcular_riesgo_recomendado(metricas)
semaforo = calcular_semaforo(metricas, config)

# ─── Layout: Panel izquierdo | Panel derecho ─────────────────────────────────
col_izq, col_der = st.columns([1, 1])

# ══════════════════════════════════════════════════════════════════════════════
# PANEL IZQUIERDO: Estado del sistema
# ══════════════════════════════════════════════════════════════════════════════
with col_izq:
    st.subheader("📊 Estado Actual del Sistema")

    # Semáforo
    color_sem = semaforo["color"]
    msg_sem = f"**{semaforo['texto']}**\n\n{semaforo['descripcion']}"
    if color_sem == "green":
        st.success(msg_sem)
    elif color_sem == "orange":
        st.warning(msg_sem)
    else:
        st.error(msg_sem)
    st.markdown("---")

    # Métricas detalladas
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Winrate últimas 10 ops", f"{metricas['winrate_10']:.1f}%")
        st.metric("Drawdown actual", f"{metricas['drawdown_actual']:.2f}%")
    with c2:
        st.metric("Winrate últimas 20 ops", f"{metricas['winrate_20']:.1f}%")
        pnl_dia = metricas.get("pnl_dia", 0)
        st.metric("P&L del día", f"{pnl_dia:+.2f}%")

    st.markdown("---")

    # Racha actual
    racha = metricas["racha_actual"]
    tipo = metricas["tipo_racha"]
    if racha > 0:
        if tipo == "ganadora":
            st.success(f"🏆 Racha ganadora: **{racha} operaciones** consecutivas")
        elif tipo == "perdedora":
            st.error(f"⚠️ Racha perdedora: **{racha} operaciones** consecutivas")
    else:
        st.info("Sin racha definida (primer trade)")

    st.markdown("---")

    # Riesgo recomendado con justificación
    nivel = riesgo_info["nivel"]
    riesgo = riesgo_info["riesgo"]
    justificacion = riesgo_info["justificacion"]

    st.metric("% Riesgo Recomendado", f"{riesgo:.2f}%")

    if nivel in ("CRITICO", "ALTO"):
        st.error(justificacion)
    elif nivel in ("ELEVADO", "PRECAUCION_DIA", "RACHA_NEGATIVA"):
        st.warning(justificacion)
    else:
        st.success(justificacion)

    if riesgo_info.get("sugerencia_parar"):
        st.error("⛔ Se recomienda encarecidamente NO operar más hoy.")

    # Reglas activas
    st.markdown("---")
    with st.expander("📋 Ver todas las reglas del motor"):
        st.markdown("""
        Las reglas se aplican en este orden de prioridad:

        1. 🚨 DD > 12% → Riesgo 0.25% (CRÍTICO)
        2. ⚠️ DD > 8% → Riesgo 0.5%
        3. ⚠️ DD > 5% → Riesgo 0.75%
        4. ⚠️ Pérdida día > 2% → Riesgo 0.5%
        5. ⚠️ Racha perdedora ≥ 3 → Riesgo × 0.75
        6. ✅ WR-10 > 70% y DD < 3% → Riesgo 1.5%
        7. ✅ WR-10 > 60% y DD < 5% → Riesgo 1.25%
        8. ✅ Racha ganadora ≥ 5 y DD < 3% → Riesgo 1.5%
        9. ℹ️ Caso base → Riesgo base (configuración)
        """)

# ══════════════════════════════════════════════════════════════════════════════
# PANEL DERECHO: Calculadora de posición
# ══════════════════════════════════════════════════════════════════════════════
with col_der:
    st.subheader("🧮 Calculadora de Posición")

    cuenta_actual = config.get("tamanio_cuenta", 10000.0)
    divisa = config.get("divisa", "USD")

    with st.form("calculadora_posicion"):
        c1, c2 = st.columns(2)

        with c1:
            cuenta_input = st.number_input(
                f"Tamaño de cuenta ({divisa})",
                min_value=0.0,
                value=float(cuenta_actual),
                step=100.0,
                format="%.2f",
            )
            par_calc = st.selectbox(
                "Par a operar",
                options=pares_lista,
                index=0,
            )
            tipo_cuenta = st.selectbox(
                "Tipo de cuenta",
                options=["Forex estándar", "Índices", "Metales"],
            )

        with c2:
            riesgo_calc = st.number_input(
                "% Riesgo a aplicar",
                min_value=0.0,
                max_value=10.0,
                value=float(riesgo),
                step=0.05,
                format="%.2f",
                help=f"Motor recomienda: {riesgo:.2f}%",
            )
            precio_calc = st.number_input(
                "Precio de entrada",
                min_value=0.0,
                value=0.0,
                step=0.0001,
                format="%.5f",
            )
            sl_calc = st.number_input(
                "Stop Loss",
                min_value=0.0,
                value=0.0,
                step=0.0001,
                format="%.5f",
            )

        calcular = st.form_submit_button(
            "⚡ Calcular Tamaño de Posición",
            use_container_width=True,
            type="primary",
        )

    if calcular:
        if precio_calc <= 0 or sl_calc <= 0 or cuenta_input <= 0:
            st.error("❌ Completa todos los campos: cuenta, precio de entrada y stop loss.")
        elif precio_calc == sl_calc:
            st.error("❌ El precio de entrada y el stop loss no pueden ser iguales.")
        else:
            resultado_calc = calcular_tamano_posicion(
                cuenta=cuenta_input,
                riesgo_pct=riesgo_calc,
                precio_entrada=precio_calc,
                stop_loss=sl_calc,
                par=par_calc,
                tipo_cuenta=tipo_cuenta,
            )

            if "error" in resultado_calc:
                st.error(f"❌ {resultado_calc['error']}")
            else:
                st.markdown("---")
                st.subheader("Resultado del Cálculo")

                rc1, rc2 = st.columns(2)
                with rc1:
                    st.metric(
                        "Importe a arriesgar",
                        f"{resultado_calc['importe_riesgo']:,.2f} {divisa}",
                        help="Monto máximo a perder en este trade",
                    )
                    st.metric(
                        "Tamaño de posición",
                        f"{resultado_calc['lotes']:.2f} lotes",
                        help="Número de lotes/contratos a operar",
                    )

                with rc2:
                    st.metric(
                        "Valor por pip/punto",
                        f"{resultado_calc['valor_pip']:,.2f} {divisa}",
                    )
                    st.metric(
                        "Margen requerido (estimado)",
                        f"{resultado_calc['margen_estimado']:,.2f} {divisa}",
                        help="Estimación del margen necesario (varía por bróker)",
                    )

                # Resumen visual
                distancia = abs(precio_calc - sl_calc)
                st.markdown("##### Resumen de la operación")
                st.markdown(
                    f"""
| Campo | Valor |
|---|---|
| Par | **{par_calc}** |
| Entrada | **{precio_calc:.5f}** |
| Stop Loss | **{sl_calc:.5f}** |
| Distancia SL | **{distancia:.5f}** |
| Riesgo aplicado | **{riesgo_calc:.2f}%** |
"""
                )

    # ─── Histórico de riesgos (referencia rápida) ─────────────────────────────
    st.markdown("---")
    with st.expander("📊 Referencia rápida de niveles de riesgo"):
        st.markdown("""
        | Nivel | % Riesgo | Condición |
        |-------|----------|-----------|
        | 🚨 Crítico | 0.25% | DD > 12% |
        | 🔴 Alto | 0.50% | DD > 8% o pérdida día > 2% |
        | 🟠 Elevado | 0.75% | DD > 5% |
        | 🟠 Racha negativa | Base × 0.75 | ≥ 3 pérdidas seguidas |
        | 🔵 Base | 1.00% | Condiciones normales |
        | 🟢 Bueno | 1.25% | WR-10 > 60% y DD < 5% |
        | 🟢 Óptimo | 1.50% | WR-10 > 70% y DD < 3% |
        """)
