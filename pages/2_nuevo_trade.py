"""
Nuevo Trade — Formulario completo para registrar una nueva operación.
"""

import streamlit as st
import os
import sys
from datetime import date, time, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import insertar_trade, insertar_imagen_trade, load_pares, obtener_configuracion
from core.risk_engine import calcular_rr

st.set_page_config(page_title="Nuevo Trade — Trading Journal Pro", layout="wide")

# CSS
css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("➕ Nuevo Trade")
st.markdown("---")

# Carga pares desde archivo
pares_dict = load_pares()
config = obtener_configuracion()

# ─── Formulario principal ─────────────────────────────────────────────────────
with st.form("form_nuevo_trade", clear_on_submit=False):

    # ─── Sección: Identificación ─────────────────────────────────────────────
    with st.expander("📌 Identificación", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            # Construir opciones agrupadas para selectbox
            opciones_pares = []
            for categoria, lista in pares_dict.items():
                opciones_pares.append(f"── {categoria} ──")
                opciones_pares.extend(lista)

            par_seleccionado = st.selectbox(
                "Par *",
                options=opciones_pares,
                index=1 if len(opciones_pares) > 1 else 0,
                help="Selecciona el par operado",
            )
            # Filtrar si seleccionaron un separador de categoría
            if par_seleccionado.startswith("──"):
                st.warning("Selecciona un par válido, no una categoría.")

        with col2:
            fecha_entrada = st.date_input("Fecha entrada *", value=date.today())
            hora_entrada = st.time_input("Hora entrada *", value=time(9, 0))

        with col3:
            direccion = st.radio("Dirección *", options=["Long", "Short"], horizontal=True)

    # ─── Sección: Estrategia ─────────────────────────────────────────────────
    with st.expander("🎯 Estrategia", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            estrategia = st.selectbox(
                "Estrategia *",
                options=["Blue", "Red", "Pink", "White", "Black", "Green"],
                help="Estrategia utilizada en esta operación",
            )

        with col2:
            tipo_operacion = st.selectbox(
                "Tipo de operación *",
                options=["Day Trading", "Swing", "Scalping"],
            )

        with col3:
            timeframe_entrada = st.selectbox(
                "Timeframe entrada *",
                options=["1m", "2m", "5m", "15m", "30m", "1H", "4H", "D"],
            )

    # ─── Sección: Niveles ─────────────────────────────────────────────────────
    with st.expander("📐 Niveles de precio", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            precio_entrada = st.number_input(
                "Precio entrada *",
                min_value=0.0,
                value=0.0,
                step=0.0001,
                format="%.5f",
            )
            stop_loss = st.number_input(
                "Stop Loss *",
                min_value=0.0,
                value=0.0,
                step=0.0001,
                format="%.5f",
            )

        with col2:
            tp1 = st.number_input(
                "TP1 (opcional)",
                min_value=0.0,
                value=0.0,
                step=0.0001,
                format="%.5f",
            )
            tp2 = st.number_input(
                "TP2 (opcional)",
                min_value=0.0,
                value=0.0,
                step=0.0001,
                format="%.5f",
            )

        # Cálculo automático del R:R
        rr_planificado = 0.0
        if precio_entrada > 0 and stop_loss > 0 and tp1 > 0:
            rr_planificado = calcular_rr(precio_entrada, stop_loss, tp1)

        if rr_planificado > 0:
            color_rr = "#3fb950" if rr_planificado >= 2 else "#d29922" if rr_planificado >= 1 else "#f85149"
            st.markdown(
                f'<div style="background:#1c2128; border:1px solid #30363d; border-radius:8px; '
                f'padding:10px 16px; margin-top:8px;">'
                f'<span style="color:#8b949e; font-size:0.85rem;">R:R Planificado</span><br>'
                f'<span style="color:{color_rr}; font-size:1.4rem; font-weight:bold;">{rr_planificado:.2f}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ─── Sección: Gestión del trade ───────────────────────────────────────────
    with st.expander("⚙️ Gestión del trade"):
        col1, col2 = st.columns(2)

        with col1:
            trailing_stop = st.checkbox("¿Trailing stop aplicado?")
            trailing_base = None
            if trailing_stop:
                trailing_base = st.selectbox(
                    "Base del trailing stop",
                    options=["MM50 2m", "MM50 5m", "MM50 15m", "MM50 1H", "MM50 4H", "MM50 D"],
                )

        with col2:
            sl_breakeven = st.checkbox("¿SL movido a breakeven?")
            cierre_parcial = st.checkbox("¿Cierre parcial en TP1?")
            porcentaje_cierre_parcial = None
            if cierre_parcial:
                porcentaje_cierre_parcial = st.select_slider(
                    "% cerrado en TP1",
                    options=[25, 50, 75],
                    value=50,
                    format_func=lambda x: f"{x}%",
                )

    # ─── Sección: Resultado ───────────────────────────────────────────────────
    with st.expander("✅ Resultado", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            fecha_salida = st.date_input("Fecha salida *", value=date.today())
            hora_salida = st.time_input("Hora salida *", value=time(17, 0))
            resultado = st.selectbox(
                "Resultado *",
                options=["Win", "Loss", "Breakeven", "Parcial"],
            )

        with col2:
            pips_resultado = st.number_input(
                "Pips resultado *",
                value=0.0,
                step=0.1,
                format="%.1f",
                help="Positivo para ganancia, negativo para pérdida",
            )
            porcentaje_cuenta = st.number_input(
                "% de cuenta *",
                value=0.0,
                step=0.01,
                format="%.2f",
                help="Porcentaje ganado/perdido respecto al tamaño de cuenta",
            )
            importe_dinero = st.number_input(
                "Importe en dinero (opcional)",
                value=0.0,
                step=1.0,
                format="%.2f",
            )

        # R:R conseguido automático
        rr_conseguido = 0.0
        if precio_entrada > 0 and stop_loss > 0 and pips_resultado != 0:
            distancia_sl = abs(precio_entrada - stop_loss)
            if distancia_sl > 0:
                distancia_resultado = abs(pips_resultado) / 10000 if "JPY" not in par_seleccionado.upper() else abs(pips_resultado) / 100
                rr_conseguido = round(distancia_resultado / distancia_sl, 2) if pips_resultado > 0 else 0.0

        if porcentaje_cuenta != 0 and config.get("riesgo_base", 1.0) > 0:
            riesgo_usado = config.get("riesgo_base", 1.0)
            rr_conseguido = round(porcentaje_cuenta / riesgo_usado, 2) if pips_resultado > 0 else 0.0

        st.markdown(
            f'<div style="background:#1c2128; border:1px solid #30363d; border-radius:8px; '
            f'padding:10px 16px; margin-top:8px;">'
            f'<span style="color:#8b949e; font-size:0.85rem;">R:R Conseguido (estimado)</span><br>'
            f'<span style="color:#58a6ff; font-size:1.4rem; font-weight:bold;">{max(0, rr_conseguido):.2f}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ─── Sección: Contexto ────────────────────────────────────────────────────
    with st.expander("🌍 Contexto del mercado"):
        col1, col2 = st.columns(2)

        with col1:
            sesion = st.selectbox(
                "Sesión",
                options=["Londres", "Nueva York", "Asiática", "Solapamiento"],
            )
            condicion_mercado = st.selectbox(
                "Condición de mercado",
                options=["Tendencia", "Rango", "Alta Volatilidad"],
            )

        with col2:
            notas = st.text_area(
                "Notas",
                placeholder="Escribe aquí tus observaciones sobre el trade...",
                height=120,
            )

    # ─── Sección: Análisis ASR ────────────────────────────────────────────────
    with st.expander("📝 Análisis ASR (After Session Review)", expanded=False):
        analisis_asr = st.text_area(
            "Análisis post-operación",
            placeholder=(
                "Escribe aquí tu análisis detallado del trade:\n"
                "• ¿Qué salió bien / mal?\n"
                "• ¿Se respetó el plan?\n"
                "• Lecciones aprendidas\n"
                "• Contexto macro / sesión\n"
                "• Emociones y disciplina"
            ),
            height=220,
            help="Este campo queda guardado junto al trade para revisión posterior.",
        )
        screenshots = st.file_uploader(
            "Imágenes del trade (opcional — múltiples permitidas)",
            type=["png", "jpg", "jpeg", "webp", "gif"],
            accept_multiple_files=True,
            help="Sube los gráficos, capturas de entrada/salida, etc.",
        )

    # ─── Botón de guardar ─────────────────────────────────────────────────────
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 3])

    with col_btn1:
        submit = st.form_submit_button(
            "💾 Guardar Trade",
            use_container_width=True,
            type="primary",
        )

    with col_btn2:
        limpiar = st.form_submit_button(
            "🗑️ Limpiar",
            use_container_width=True,
        )

# ─── Procesamiento del formulario ─────────────────────────────────────────────
if submit:
    # Validación de campos obligatorios
    errores = []

    if par_seleccionado.startswith("──"):
        errores.append("Selecciona un par válido")
    if precio_entrada <= 0:
        errores.append("El precio de entrada debe ser mayor a 0")
    if stop_loss <= 0:
        errores.append("El stop loss debe ser mayor a 0")
    if resultado not in ("Win", "Loss", "Breakeven", "Parcial"):
        errores.append("Selecciona un resultado válido")

    if errores:
        for error in errores:
            st.error(f"❌ {error}")
    else:
        # Preparar datos
        datos_trade = {
            "fecha_entrada": fecha_entrada.isoformat(),
            "hora_entrada": hora_entrada.strftime("%H:%M:%S"),
            "fecha_salida": fecha_salida.isoformat(),
            "hora_salida": hora_salida.strftime("%H:%M:%S"),
            "par": par_seleccionado,
            "direccion": direccion,
            "estrategia": estrategia,
            "tipo_operacion": tipo_operacion,
            "timeframe_entrada": timeframe_entrada,
            "precio_entrada": precio_entrada,
            "stop_loss": stop_loss,
            "tp1": tp1 if tp1 > 0 else None,
            "tp2": tp2 if tp2 > 0 else None,
            "rr_planificado": rr_planificado,
            "trailing_stop": 1 if trailing_stop else 0,
            "trailing_base": trailing_base,
            "sl_breakeven": 1 if sl_breakeven else 0,
            "cierre_parcial": 1 if cierre_parcial else 0,
            "porcentaje_cierre_parcial": porcentaje_cierre_parcial,
            "resultado": resultado,
            "pips_resultado": pips_resultado,
            "porcentaje_cuenta": porcentaje_cuenta,
            "importe_dinero": importe_dinero if importe_dinero != 0 else None,
            "sesion": sesion,
            "condicion_mercado": condicion_mercado,
            "rr_conseguido": max(0, rr_conseguido),
            "notas": notas if notas else None,
            "screenshot_path": None,
            "analisis_asr": analisis_asr if analisis_asr else None,
        }

        try:
            nuevo_id = insertar_trade(datos_trade)

            # Guardar imágenes adjuntas
            if screenshots:
                screenshots_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "data", "screenshots",
                )
                os.makedirs(screenshots_dir, exist_ok=True)
                for orden, img_file in enumerate(screenshots):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
                    ext = img_file.name.rsplit(".", 1)[-1]
                    nombre_archivo = f"trade{nuevo_id}_{timestamp}_{orden}.{ext}"
                    ruta = os.path.join(screenshots_dir, nombre_archivo)
                    with open(ruta, "wb") as f:
                        f.write(img_file.getbuffer())
                    insertar_imagen_trade(nuevo_id, ruta, orden)

            st.success(
                f"✅ Trade #{nuevo_id} guardado — {par_seleccionado} {direccion} {resultado}"
                + (f" · {len(screenshots)} imagen(es) adjunta(s)" if screenshots else "")
            )
            st.balloons()
        except Exception as e:
            st.error(f"Error guardando el trade: {e}")
