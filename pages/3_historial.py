"""
Historial — Tabla completa de trades con filtros, edición, eliminación y exportación.
"""

import streamlit as st
import pandas as pd
import os
import sys
from datetime import date, timedelta, time, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import (
    obtener_todos_los_trades,
    eliminar_trade,
    actualizar_trade,
    load_pares,
    get_lista_pares_plana,
    obtener_imagenes_trade,
    insertar_imagen_trade,
    eliminar_imagen_trade,
)

st.set_page_config(page_title="Historial — Trading Journal Pro", layout="wide")

# CSS
css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("📋 Historial de Trades")
st.markdown("---")

# ─── Carga de datos ─────────────────────────────────────────────────────────
trades = obtener_todos_los_trades()

if not trades:
    st.info("No hay trades registrados todavía. Ve a **Nuevo Trade** para registrar tu primera operación.")
    st.stop()

df_completo = pd.DataFrame(trades)

# Aseguramos que existan las columnas necesarias
columnas_necesarias = [
    "id", "fecha_entrada", "hora_entrada", "par", "direccion", "estrategia",
    "tipo_operacion", "timeframe_entrada", "precio_entrada", "stop_loss",
    "resultado", "pips_resultado", "porcentaje_cuenta", "rr_planificado",
    "rr_conseguido", "sesion", "condicion_mercado", "notas",
]
for col in columnas_necesarias:
    if col not in df_completo.columns:
        df_completo[col] = None

# ─── Filtros en sidebar ───────────────────────────────────────────────────────
st.sidebar.header("🔍 Filtros")

# Rango de fechas
fecha_min = date.today() - timedelta(days=365)
fecha_max = date.today()

if "fecha_entrada" in df_completo.columns and not df_completo["fecha_entrada"].isna().all():
    fechas_validas = df_completo["fecha_entrada"].dropna()
    if not fechas_validas.empty:
        try:
            fecha_min = date.fromisoformat(fechas_validas.min())
            fecha_max = date.fromisoformat(fechas_validas.max())
        except Exception:
            pass

filtro_fecha_inicio = st.sidebar.date_input("Desde", value=fecha_min)
filtro_fecha_fin = st.sidebar.date_input("Hasta", value=fecha_max)

# Estrategia
estrategias_disponibles = ["Todas"] + sorted(df_completo["estrategia"].dropna().unique().tolist())
filtro_estrategia = st.sidebar.selectbox("Estrategia", options=estrategias_disponibles)

# Par
pares_disponibles = ["Todos"] + sorted(df_completo["par"].dropna().unique().tolist())
filtro_par = st.sidebar.selectbox("Par", options=pares_disponibles)

# Resultado
resultados_disponibles = ["Todos", "Win", "Loss", "Breakeven", "Parcial"]
filtro_resultado = st.sidebar.selectbox("Resultado", options=resultados_disponibles)

# Tipo de operación
tipos_disponibles = ["Todos"] + sorted(df_completo["tipo_operacion"].dropna().unique().tolist())
filtro_tipo = st.sidebar.selectbox("Tipo", options=tipos_disponibles)

# ─── Aplicar filtros ──────────────────────────────────────────────────────────
df_filtrado = df_completo.copy()

if "fecha_entrada" in df_filtrado.columns:
    df_filtrado = df_filtrado[
        (df_filtrado["fecha_entrada"].fillna("") >= filtro_fecha_inicio.isoformat()) &
        (df_filtrado["fecha_entrada"].fillna("") <= filtro_fecha_fin.isoformat())
    ]

if filtro_estrategia != "Todas":
    df_filtrado = df_filtrado[df_filtrado["estrategia"] == filtro_estrategia]

if filtro_par != "Todos":
    df_filtrado = df_filtrado[df_filtrado["par"] == filtro_par]

if filtro_resultado != "Todos":
    df_filtrado = df_filtrado[df_filtrado["resultado"] == filtro_resultado]

if filtro_tipo != "Todos":
    df_filtrado = df_filtrado[df_filtrado["tipo_operacion"] == filtro_tipo]

# ─── Resumen del filtro ───────────────────────────────────────────────────────
col_res1, col_res2, col_res3, col_res4 = st.columns(4)
with col_res1:
    st.metric("Trades mostrados", len(df_filtrado))
with col_res2:
    wins = len(df_filtrado[df_filtrado["resultado"] == "Win"])
    losses = len(df_filtrado[df_filtrado["resultado"] == "Loss"])
    wr = round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0
    st.metric("Winrate", f"{wr:.1f}%")
with col_res3:
    pnl_total = df_filtrado["porcentaje_cuenta"].fillna(0).sum()
    st.metric("P&L Total", f"{pnl_total:+.2f}%")
with col_res4:
    pips_total = df_filtrado["pips_resultado"].fillna(0).sum()
    st.metric("Pips Totales", f"{pips_total:+.1f}")

st.markdown("---")

# ─── Tabla principal ──────────────────────────────────────────────────────────
COLOR_MAP = {
    "Win": "#3fb950",
    "Loss": "#f85149",
    "Breakeven": "#8b949e",
    "Parcial": "#d29922",
}

columnas_tabla = [
    "id", "fecha_entrada", "par", "direccion", "estrategia", "tipo_operacion",
    "resultado", "pips_resultado", "porcentaje_cuenta", "rr_planificado", "rr_conseguido",
]
columnas_presentes = [c for c in columnas_tabla if c in df_filtrado.columns]
df_tabla = df_filtrado[columnas_presentes].copy()

def colorear_resultado(val):
    color = COLOR_MAP.get(str(val), "#e6edf3")
    return f"color: {color}; font-weight: bold"

def colorear_pnl(val):
    try:
        v = float(val)
        if v > 0:
            return "color: #3fb950"
        elif v < 0:
            return "color: #f85149"
        return "color: #8b949e"
    except Exception:
        return ""

df_styled = df_tabla.style
if "resultado" in df_tabla.columns:
    df_styled = df_styled.applymap(colorear_resultado, subset=["resultado"])
if "porcentaje_cuenta" in df_tabla.columns:
    df_styled = df_styled.applymap(colorear_pnl, subset=["porcentaje_cuenta"])
if "pips_resultado" in df_tabla.columns:
    df_styled = df_styled.applymap(colorear_pnl, subset=["pips_resultado"])

st.dataframe(df_styled, use_container_width=True, hide_index=True, height=400)

# ─── Exportar CSV ─────────────────────────────────────────────────────────────
st.markdown("---")
col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 3])

with col_exp1:
    csv_data = df_filtrado.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Exportar CSV",
        data=csv_data,
        file_name=f"trades_exportados_{date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ─── Panel de edición y eliminación ──────────────────────────────────────────
st.markdown("---")
st.subheader("✏️ Editar / Eliminar Trade")

if df_filtrado.empty:
    st.info("No hay trades con los filtros actuales.")
else:
    ids_disponibles = df_filtrado["id"].tolist()
    trade_id_seleccionado = st.selectbox(
        "Selecciona el ID del trade a editar/eliminar",
        options=ids_disponibles,
        format_func=lambda x: f"#{x} — {df_filtrado[df_filtrado['id']==x]['par'].values[0]} "
                              f"{df_filtrado[df_filtrado['id']==x]['resultado'].values[0] if 'resultado' in df_filtrado.columns else ''}",
    )

    trade_sel = df_filtrado[df_filtrado["id"] == trade_id_seleccionado].iloc[0].to_dict()

    col_edit, col_del = st.columns([4, 1])

    with col_del:
        st.markdown("#### Eliminar")
        confirmar_eliminacion = st.checkbox(f"Confirmar eliminación del trade #{trade_id_seleccionado}")
        if st.button("🗑️ Eliminar", type="primary", use_container_width=True):
            if confirmar_eliminacion:
                if eliminar_trade(trade_id_seleccionado):
                    st.success(f"Trade #{trade_id_seleccionado} eliminado correctamente.")
                    st.rerun()
                else:
                    st.error("Error al eliminar el trade.")
            else:
                st.warning("Marca la casilla de confirmación para eliminar.")

    with col_edit:
        st.markdown("#### Editar")
        pares_lista = get_lista_pares_plana()

        with st.form(f"form_editar_{trade_id_seleccionado}"):
            ec1, ec2, ec3 = st.columns(3)

            with ec1:
                par_idx = pares_lista.index(trade_sel.get("par", "")) if trade_sel.get("par", "") in pares_lista else 0
                nuevo_par = st.selectbox("Par", options=pares_lista, index=par_idx)
                nueva_direccion = st.radio("Dirección", ["Long", "Short"],
                    index=0 if trade_sel.get("direccion", "Long") == "Long" else 1, horizontal=True)

            with ec2:
                nueva_estrategia = st.selectbox("Estrategia", ["Blue", "Red", "Pink", "White", "Black", "Green"],
                    index=["Blue", "Red", "Pink", "White", "Black", "Green"].index(trade_sel.get("estrategia", "Blue"))
                    if trade_sel.get("estrategia") in ["Blue", "Red", "Pink", "White", "Black", "Green"] else 0)
                nuevo_resultado = st.selectbox("Resultado", ["Win", "Loss", "Breakeven", "Parcial"],
                    index=["Win", "Loss", "Breakeven", "Parcial"].index(trade_sel.get("resultado", "Win"))
                    if trade_sel.get("resultado") in ["Win", "Loss", "Breakeven", "Parcial"] else 0)

            with ec3:
                nuevos_pips = st.number_input("Pips", value=float(trade_sel.get("pips_resultado", 0) or 0), format="%.1f")
                nuevo_pct = st.number_input("% Cuenta", value=float(trade_sel.get("porcentaje_cuenta", 0) or 0), format="%.2f")

            nuevas_notas = st.text_area("Notas", value=trade_sel.get("notas", "") or "")

            nuevo_asr = st.text_area(
                "📝 Análisis ASR (After Session Review)",
                value=trade_sel.get("analisis_asr", "") or "",
                height=200,
                placeholder=(
                    "• ¿Qué salió bien / mal?\n"
                    "• ¿Se respetó el plan?\n"
                    "• Lecciones aprendidas\n"
                    "• Contexto macro / sesión"
                ),
            )

            guardar_edicion = st.form_submit_button("💾 Guardar cambios", use_container_width=True, type="primary")

        if guardar_edicion:
            datos_actualizados = {**trade_sel}
            datos_actualizados["par"] = nuevo_par
            datos_actualizados["direccion"] = nueva_direccion
            datos_actualizados["estrategia"] = nueva_estrategia
            datos_actualizados["resultado"] = nuevo_resultado
            datos_actualizados["pips_resultado"] = nuevos_pips
            datos_actualizados["porcentaje_cuenta"] = nuevo_pct
            datos_actualizados["notas"] = nuevas_notas
            datos_actualizados["analisis_asr"] = nuevo_asr if nuevo_asr else None
            # Asegurar que analisis_asr existe aunque no estuviera en el trade antiguo
            if "analisis_asr" not in datos_actualizados:
                datos_actualizados["analisis_asr"] = None

            if actualizar_trade(trade_id_seleccionado, datos_actualizados):
                st.success(f"Trade #{trade_id_seleccionado} actualizado correctamente.")
                st.rerun()
            else:
                st.error("Error actualizando el trade.")

    # ─── Imágenes del trade seleccionado ──────────────────────────────────────
    st.markdown("---")
    st.markdown(f"#### 🖼️ Imágenes del Trade #{trade_id_seleccionado}")

    imagenes = obtener_imagenes_trade(trade_id_seleccionado)

    # Mostrar imagen legada (screenshot_path antiguo) si existe
    legacy_path = trade_sel.get("screenshot_path")
    if legacy_path and os.path.isfile(legacy_path):
        st.caption("Screenshot original")
        st.image(legacy_path, use_container_width=True)

    if imagenes:
        cols_img = st.columns(min(len(imagenes), 3))
        for i, img in enumerate(imagenes):
            path = img.get("imagen_path", "")
            if os.path.isfile(path):
                with cols_img[i % 3]:
                    st.image(path, use_container_width=True)
                    if st.button(f"🗑️ Eliminar imagen #{img['id']}", key=f"del_img_{img['id']}"):
                        eliminar_imagen_trade(img["id"])
                        st.rerun()
    elif not legacy_path:
        st.caption("No hay imágenes adjuntas para este trade.")

    # Subir nuevas imágenes
    with st.expander("➕ Añadir imágenes al trade"):
        nuevas_imgs = st.file_uploader(
            "Selecciona una o varias imágenes",
            type=["png", "jpg", "jpeg", "webp", "gif"],
            accept_multiple_files=True,
            key=f"upload_imgs_{trade_id_seleccionado}",
        )
        if st.button("📎 Adjuntar imágenes seleccionadas", key=f"adjuntar_{trade_id_seleccionado}"):
            if nuevas_imgs:
                screenshots_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "data", "screenshots",
                )
                os.makedirs(screenshots_dir, exist_ok=True)
                orden_base = len(imagenes)
                for i, img_file in enumerate(nuevas_imgs):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
                    ext = img_file.name.rsplit(".", 1)[-1]
                    nombre = f"trade{trade_id_seleccionado}_{timestamp}_{i}.{ext}"
                    ruta = os.path.join(screenshots_dir, nombre)
                    with open(ruta, "wb") as f:
                        f.write(img_file.getbuffer())
                    insertar_imagen_trade(trade_id_seleccionado, ruta, orden_base + i)
                st.success(f"{len(nuevas_imgs)} imagen(es) añadida(s).")
                st.rerun()
            else:
                st.warning("Selecciona al menos una imagen primero.")
