"""
Nuevo Trade — Formulario integrado con motor de estrategias unificado.
- Operativa tipo (SCALPING / DAY)
- Selector de estrategia + checklist de sus condiciones
- Registro multi-cuenta con preview en vivo
"""

import streamlit as st
import os
import sys
import json
import pandas as pd
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import (
    insertar_trade,
    insertar_imagen_trade,
    load_pares,
    obtener_cuentas,
    obtener_estrategias,
    obtener_condiciones,
    obtener_backtest_trades,
)
from core.cuenta_selector import render_cuenta_selector
from core.backtester_stats import top_condiciones

st.set_page_config(page_title="Nuevo Trade — Trading Journal Pro", layout="wide")

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("➕ Nuevo Trade")
st.markdown("---")

# Sidebar (no se usa la cuenta activa para registrar, pero mantiene coherencia visual)
render_cuenta_selector()

pares_dict = load_pares()
cuentas = obtener_cuentas()

if not cuentas:
    st.error("No hay cuentas configuradas. Crea una cuenta primero en ⚙️ Configuración → Cuentas.")
    st.stop()

# ═════════════════════════════════════════════════════════════════════════════
# Fila 0: Operativa tipo + Estrategia (fuera del form para reactividad)
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("#### Tipo de operativa y estrategia")
col_op, col_strat = st.columns([1, 2])

with col_op:
    operativa_tipo = st.radio(
        "Operativa *",
        options=["DAY", "SCALPING"],
        horizontal=True,
        key="nt_operativa",
    )

with col_strat:
    estrategias_disp = obtener_estrategias(solo_activas=True, tipo=operativa_tipo)
    if not estrategias_disp:
        st.warning(f"No hay estrategias activas de tipo {operativa_tipo}. Créalas en ⚙️ Configuración → Estrategias.")
        st.stop()
    nombres_strat = [e["nombre"] for e in estrategias_disp]
    nombre_sel = st.selectbox("Estrategia *", options=nombres_strat, key="nt_strategy")
    estrategia_sel = next(e for e in estrategias_disp if e["nombre"] == nombre_sel)

# Insight desde backtest (>10 trades)
bt_trades = obtener_backtest_trades(estrategia_sel["id"])
if len(bt_trades) > 10:
    top = top_condiciones(estrategia_sel["id"], n=2, trades=bt_trades)
    if top:
        nombres_top = " · ".join(f"**{c['condicion']}** (Δ {c['delta_wr']:+.1f}%)" for c in top)
        st.info(f"📊 Basado en {len(bt_trades)} backtest trades — condiciones más importantes: {nombres_top}")

# Condiciones de la estrategia (fuera del form para que el usuario las vea siempre)
condiciones_strat = obtener_condiciones(estrategia_sel["id"])

# ═════════════════════════════════════════════════════════════════════════════
# Formulario principal
# ═════════════════════════════════════════════════════════════════════════════
with st.form("form_nuevo_trade", clear_on_submit=False):

    # ─── Fila 1: identificación ───────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 1.5, 1])
    with col1:
        opciones_pares = []
        for categoria, lista in pares_dict.items():
            opciones_pares.append(f"── {categoria} ──")
            opciones_pares.extend(lista)
        par = st.selectbox("Par *", options=opciones_pares, index=1 if len(opciones_pares) > 1 else 0)
    with col2:
        fecha = st.date_input("Fecha *", value=date.today())
    with col3:
        direccion = st.radio("Dirección *", options=["Long", "Short"], horizontal=True)

    # ─── Fila 2: resultado + R:R ──────────────────────────────────────────
    col1, col2 = st.columns([1, 1])
    with col1:
        resultado = st.selectbox("Resultado *", options=["Win", "Loss", "Breakeven", "Parcial"])
    with col2:
        rr_conseguido = st.number_input(
            "R:R conseguido *",
            value=0.0,
            step=0.1,
            format="%.2f",
            help="2.0 = ganaste 2R · -0.4 = perdiste solo 0.4R (parcial SL) · 0 = breakeven",
        )

    # ─── Condiciones de la estrategia ─────────────────────────────────────
    st.markdown("---")
    st.markdown(f"#### Condiciones presentes — _{estrategia_sel['nombre']} ({estrategia_sel['tipo']})_")
    if not condiciones_strat:
        st.caption("Esta estrategia no tiene condiciones configuradas. Añádelas en ⚙️ Configuración → Estrategias.")
        condiciones_marcadas = {}
    else:
        condiciones_marcadas = {}
        cols_cond = st.columns(2)
        for i, cond in enumerate(condiciones_strat):
            with cols_cond[i % 2]:
                marcado = st.checkbox(cond["nombre"], key=f"cond_{cond['id']}")
                condiciones_marcadas[str(cond["id"])] = 1 if marcado else 0

    # ─── Multi-cuenta ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Cuentas en las que registrar el trade")
    cuentas_seleccionadas_ids = []
    cols_cta = st.columns(min(len(cuentas), 4) or 1)
    for i, c in enumerate(cuentas):
        with cols_cta[i % len(cols_cta)]:
            label = f"**{c['nombre']}**\n\n{c['capital']:,.0f} {c['divisa']} · R {c['riesgo_base']:.2f}%"
            if st.checkbox(label, value=True, key=f"cta_{c['id']}"):
                cuentas_seleccionadas_ids.append(c["id"])

    cuentas_seleccionadas = [c for c in cuentas if c["id"] in cuentas_seleccionadas_ids]

    # Preview de impacto por cuenta
    if cuentas_seleccionadas:
        st.markdown("##### Preview de impacto por cuenta")
        preview_rows = []
        for c in cuentas_seleccionadas:
            capital = float(c["capital"])
            riesgo_base = float(c["riesgo_base"])
            arriesgado = capital * riesgo_base / 100.0
            resultado_pct = rr_conseguido * riesgo_base
            resultado_dinero = capital * resultado_pct / 100.0
            preview_rows.append({
                "Cuenta": c["nombre"],
                "Capital": f"{capital:,.2f} {c['divisa']}",
                "Riesgo base": f"{riesgo_base:.2f}%",
                "Arriesgado": f"{arriesgado:,.2f} {c['divisa']}",
                "R:R": f"{rr_conseguido:+.2f}",
                "% Cuenta": f"{resultado_pct:+.2f}%",
                f"Resultado": f"{resultado_dinero:+,.2f} {c['divisa']}",
            })
        df_prev = pd.DataFrame(preview_rows)
        st.dataframe(df_prev, use_container_width=True, hide_index=True)
    else:
        st.caption("Selecciona al menos una cuenta.")

    # ─── Notas e imágenes ─────────────────────────────────────────────────
    with st.expander("📝 Notas e imágenes (opcional)"):
        notas = st.text_area(
            "Notas",
            placeholder="Qué salió bien/mal, contexto, lecciones...",
            height=100,
        )
        screenshots = st.file_uploader(
            "Imágenes del trade",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
        )

    # ─── Análisis ASR ─────────────────────────────────────────────────────
    with st.expander("📝 Análisis ASR (After Session Review)", expanded=False):
        analisis_asr = st.text_area(
            "Análisis post-operación",
            placeholder=(
                "• ¿Qué salió bien / mal?\n"
                "• ¿Se respetó el plan?\n"
                "• Lecciones aprendidas\n"
                "• Contexto macro / sesión\n"
                "• Emociones y disciplina"
            ),
            height=200,
        )

    st.markdown("---")
    submit = st.form_submit_button("💾 Guardar Trade", type="primary")

# ═════════════════════════════════════════════════════════════════════════════
# Procesamiento
# ═════════════════════════════════════════════════════════════════════════════
if submit:
    errores = []
    if par.startswith("──"):
        errores.append("Selecciona un par válido")
    if resultado not in ("Win", "Loss", "Breakeven", "Parcial"):
        errores.append("Selecciona un resultado válido")
    if not cuentas_seleccionadas:
        errores.append("Selecciona al menos una cuenta")

    if errores:
        for e in errores:
            st.error(f"❌ {e}")
    else:
        condiciones_json = json.dumps(condiciones_marcadas) if condiciones_marcadas else None
        ids_creados = []

        try:
            # Guardar screenshots una sola vez compartidos por todas las cuentas
            screenshots_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "screenshots",
            )
            if screenshots:
                os.makedirs(screenshots_dir, exist_ok=True)

            for c in cuentas_seleccionadas:
                capital = float(c["capital"])
                riesgo_base = float(c["riesgo_base"])
                resultado_pct = rr_conseguido * riesgo_base
                resultado_dinero = capital * resultado_pct / 100.0

                datos_trade = {
                    "fecha_entrada": fecha.isoformat(),
                    "hora_entrada": None,
                    "fecha_salida": fecha.isoformat(),
                    "hora_salida": None,
                    "par": par,
                    "direccion": direccion,
                    "estrategia": estrategia_sel["nombre"],
                    "tipo_operacion": None,
                    "timeframe_entrada": None,
                    "precio_entrada": None,
                    "stop_loss": None,
                    "tp1": None,
                    "tp2": None,
                    "rr_planificado": None,
                    "trailing_stop": 0,
                    "trailing_base": None,
                    "sl_breakeven": 0,
                    "cierre_parcial": 0,
                    "porcentaje_cierre_parcial": None,
                    "resultado": resultado,
                    "pips_resultado": None,
                    "porcentaje_cuenta": resultado_pct,
                    "importe_dinero": resultado_dinero,
                    "sesion": None,
                    "condicion_mercado": None,
                    "rr_conseguido": rr_conseguido,
                    "notas": notas if notas else None,
                    "screenshot_path": None,
                    "analisis_asr": analisis_asr if analisis_asr else None,
                    "cuenta_id": c["id"],
                    "strategy_conditions": condiciones_json,
                    "operativa_tipo": operativa_tipo,
                    "strategy_id": estrategia_sel["id"],
                }
                nuevo_id = insertar_trade(datos_trade)
                ids_creados.append((nuevo_id, c["nombre"]))

                if screenshots:
                    for orden, img_file in enumerate(screenshots):
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
                        ext = img_file.name.rsplit(".", 1)[-1]
                        nombre = f"trade{nuevo_id}_{timestamp}_{orden}.{ext}"
                        ruta = os.path.join(screenshots_dir, nombre)
                        with open(ruta, "wb") as f:
                            f.write(img_file.getbuffer())
                        insertar_imagen_trade(nuevo_id, ruta, orden)

            resumen = " · ".join(f"#{tid} ({n})" for tid, n in ids_creados)
            st.success(
                f"✅ {len(ids_creados)} trade(s) guardados — {par} {direccion} {resultado} · R:R {rr_conseguido:+.2f}\n\n{resumen}"
            )
            st.balloons()
        except Exception as e:
            st.error(f"Error guardando los trades: {e}")
