"""
🔬 Backtester — Registro de trades de backtesting con UX idéntico al
módulo de trading en vivo (nuevo_trade + historial), pero escribiendo
en las tablas backtest_trades / backtest_imagenes.
"""

import streamlit as st
import os
import sys
import json
import pandas as pd
from datetime import date, datetime
from PIL import Image as PILImage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import (
    obtener_estrategias,
    obtener_condiciones,
    insertar_backtest_trade,
    obtener_backtest_trades,
    obtener_backtest_trade_por_id,
    actualizar_backtest_trade,
    eliminar_backtest_trade,
    insertar_imagen_backtest,
    obtener_imagenes_backtest,
    eliminar_imagen_backtest,
)

st.set_page_config(
    page_title="Backtester — Trading Journal Pro",
    layout="wide",
    initial_sidebar_state="expanded",
)

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def _mostrar_imagenes(paths: list, cols: int = 3):
    """Muestra una lista de rutas de imagen en columnas usando st.image."""
    paths_validos = [p for p in paths if p and os.path.isfile(p)]
    paths_invalidos = [p for p in paths if p and not os.path.isfile(p)]
    if not paths_validos:
        if paths_invalidos:
            st.caption("⚠️ Archivo no encontrado")
        else:
            st.caption("📷 Sin capturas adjuntas")
        return
    columnas = st.columns(min(len(paths_validos), cols))
    for i, path in enumerate(paths_validos):
        with columnas[i % cols]:
            try:
                img = PILImage.open(path)
                st.image(img, use_container_width=True,
                         caption=os.path.basename(path))
            except Exception:
                st.caption(f"⚠️ No se pudo cargar: {os.path.basename(path)}")


RESULT_OPTIONS = ["WIN", "LOSS", "BE", "PARTIAL_TP", "PARTIAL_SL"]
DIR_OPTIONS = ["LONG", "SHORT"]
OPERATIVA_OPTIONS = ["DAY", "SCALPING"]
RES_COLORS = {
    "WIN": "#00e676", "LOSS": "#ff3c00", "BE": "#ffc107",
    "PARTIAL_TP": "#00bcd4", "PARTIAL_SL": "#ff9800",
}

st.title("🔬 Backtester")
st.caption("Registra trades de backtesting y consúltalos con el mismo UX que el módulo de trading en vivo.")
st.markdown("---")

estrategias_all = obtener_estrategias(solo_activas=False)
estrategias_activas = [e for e in estrategias_all if e.get("activa")]

if not estrategias_activas:
    st.warning("No hay estrategias activas. Créalas en ⚙️ Configuración → Estrategias.")
    st.stop()

strat_map = {e["id"]: e["nombre"] for e in estrategias_all}

tab_nuevo, tab_registro = st.tabs(["➕ Nuevo Trade Backtest", "📋 Registro Backtest"])

# ═════════════════════════════════════════════════════════════════════════════
# SECCIÓN A — Nuevo Trade Backtest  (mirrors pages/2_nuevo_trade.py)
# ═════════════════════════════════════════════════════════════════════════════
with tab_nuevo:
    st.markdown("#### Tipo de operativa y estrategia")
    col_op, col_strat = st.columns([1, 2])

    with col_op:
        operativa_tipo = st.radio(
            "Operativa *",
            options=OPERATIVA_OPTIONS,
            horizontal=True,
            key="bt_operativa",
        )

    with col_strat:
        estrategias_disp = estrategias_activas
        if not estrategias_disp:
            st.warning("No hay estrategias activas. Créalas en ⚙️ Configuración → Estrategias.")
            st.stop()
        nombres_strat = [e["nombre"] for e in estrategias_disp]
        nombre_sel = st.selectbox("Estrategia *", options=nombres_strat, key="bt_strategy")
        estrategia_sel = next(e for e in estrategias_disp if e["nombre"] == nombre_sel)

    condiciones_strat = obtener_condiciones(estrategia_sel["id"])

    with st.form("bt_form_nuevo", clear_on_submit=False):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            instrumento = st.text_input("Instrumento *", placeholder="EURUSD, BTCUSD, US30…")
        with col2:
            fecha_bt = st.date_input("Fecha *", value=date.today())
        with col3:
            direccion_bt = st.radio("Dirección *", options=DIR_OPTIONS, horizontal=True)

        col_r1, col_r2 = st.columns([1, 1])
        with col_r1:
            resultado_bt = st.selectbox("Resultado *", options=RESULT_OPTIONS)
            st.caption(
                "**PARTIAL_TP** = trailing SL alcanzado en beneficio (no TP completo)  \n"
                "**PARTIAL_SL** = SL movido para reducir riesgo, alcanzado con pérdida menor"
            )
        with col_r2:
            rr_bt = st.number_input(
                "R:R conseguido *",
                value=0.0, step=0.1, format="%.2f",
                help="2.0 = ganaste 2R · -0.4 = perdiste solo 0.4R · 0 = BE",
            )

        st.markdown("---")
        st.markdown(f"#### Condiciones presentes — _{estrategia_sel['nombre']} ({estrategia_sel['tipo']})_")
        if not condiciones_strat:
            st.caption("Esta estrategia no tiene condiciones. Añádelas en ⚙️ Configuración → Estrategias.")
            condiciones_marcadas = {}
        else:
            condiciones_marcadas = {}
            cols_cond = st.columns(2)
            for i, cond in enumerate(condiciones_strat):
                with cols_cond[i % 2]:
                    marcado = st.checkbox(cond["nombre"], key=f"bt_cond_{cond['id']}")
                    condiciones_marcadas[str(cond["id"])] = 1 if marcado else 0

        st.markdown("---")
        with st.expander("📝 Notas e imágenes (opcional)"):
            notas_bt = st.text_area("Notas", placeholder="Contexto, lecciones, observaciones…", height=100)
            screenshots = st.file_uploader(
                "Imágenes del trade backtest",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
            )

        with st.expander("📝 Análisis ASR (After Session Review)", expanded=False):
            analisis_asr = st.text_area(
                "Análisis post-operación",
                placeholder=(
                    "• ¿Qué salió bien / mal?\n"
                    "• ¿Se respetó el plan?\n"
                    "• Lecciones aprendidas\n"
                    "• Contexto macro / sesión"
                ),
                height=200,
            )

        st.markdown("---")
        submit_nuevo = st.form_submit_button("💾 Guardar Trade Backtest", type="primary")

    if submit_nuevo:
        errores = []
        if not instrumento.strip():
            errores.append("El instrumento es obligatorio")
        if resultado_bt not in RESULT_OPTIONS:
            errores.append("Selecciona un resultado válido")

        if errores:
            for e in errores:
                st.error(f"❌ {e}")
        else:
            try:
                condiciones_json = json.dumps(condiciones_marcadas) if condiciones_marcadas else None
                nuevo_id = insertar_backtest_trade({
                    "strategy_id": estrategia_sel["id"],
                    "fecha": fecha_bt.isoformat(),
                    "instrumento": instrumento.strip(),
                    "direccion": direccion_bt,
                    "resultado": resultado_bt,
                    "rr": rr_bt,
                    "condiciones": condiciones_json,
                    "notas": notas_bt or None,
                    "screenshot_path": None,
                    "analisis_asr": analisis_asr or None,
                    "operativa_tipo": operativa_tipo,
                })

                if screenshots:
                    screenshots_dir = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "screenshots", "backtest",
                    )
                    os.makedirs(screenshots_dir, exist_ok=True)
                    for orden, img_file in enumerate(screenshots):
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
                        ext = img_file.name.rsplit(".", 1)[-1]
                        nombre_archivo = f"bt{nuevo_id}_{timestamp}_{orden}.{ext}"
                        ruta = os.path.join(screenshots_dir, nombre_archivo)
                        with open(ruta, "wb") as f:
                            f.write(img_file.getbuffer())
                        insertar_imagen_backtest(nuevo_id, ruta, orden)

                st.success(
                    f"✅ Trade backtest #{nuevo_id} guardado — "
                    f"{instrumento.strip()} {direccion_bt} {resultado_bt} · {rr_bt:+.2f}R"
                )
                st.toast("✅ Trade guardado", icon="✅")
            except Exception as e:
                st.error(f"❌ Error guardando el trade backtest: {e}")

# ═════════════════════════════════════════════════════════════════════════════
# SECCIÓN B — Registro Backtest  (mirrors pages/3_historial.py)
# ═════════════════════════════════════════════════════════════════════════════
with tab_registro:
    trades_all = obtener_backtest_trades()

    if not trades_all:
        st.info("No hay trades de backtest registrados. Ve a **Nuevo Trade Backtest** para empezar.")
        st.stop()

    df_completo = pd.DataFrame(trades_all)
    if "instrumento" not in df_completo.columns:
        df_completo["instrumento"] = ""
    df_completo["estrategia"] = df_completo["strategy_id"].map(strat_map).fillna("—")

    # ─── Filtros ──────────────────────────────────────────────────────────────
    st.markdown("##### 🔍 Filtros")
    fc1, fc2, fc3, fc4 = st.columns([1.2, 1.2, 1, 1])

    with fc1:
        filtro_res = st.multiselect(
            "Resultado",
            options=RESULT_OPTIONS,
            default=RESULT_OPTIONS,
            key="bt_filt_res",
        )
    with fc2:
        filtro_instr = st.text_input("Instrumento contiene", value="", key="bt_filt_instr")
    with fc3:
        nombres_estr = ["Todas"] + sorted({n for n in df_completo["estrategia"].dropna().unique()})
        filtro_estr = st.selectbox("Estrategia", options=nombres_estr, key="bt_filt_estr")
    with fc4:
        fechas_validas = df_completo["fecha"].dropna() if "fecha" in df_completo else pd.Series(dtype=str)
        try:
            fmin = date.fromisoformat(fechas_validas.min()) if not fechas_validas.empty else date.today()
            fmax = date.fromisoformat(fechas_validas.max()) if not fechas_validas.empty else date.today()
        except Exception:
            fmin = fmax = date.today()
        rango = st.date_input("Rango fechas", value=(fmin, fmax), key="bt_filt_fecha")

    # Aplicar filtros
    df_filt = df_completo.copy()
    if filtro_res:
        df_filt = df_filt[df_filt["resultado"].isin(filtro_res)]
    if filtro_instr.strip():
        df_filt = df_filt[df_filt["instrumento"].fillna("").str.contains(filtro_instr.strip(), case=False, na=False)]
    if filtro_estr != "Todas":
        df_filt = df_filt[df_filt["estrategia"] == filtro_estr]
    if isinstance(rango, tuple) and len(rango) == 2:
        f_ini, f_fin = rango
        df_filt = df_filt[
            (df_filt["fecha"].fillna("") >= f_ini.isoformat()) &
            (df_filt["fecha"].fillna("") <= f_fin.isoformat())
        ]

    # ─── Resumen ─────────────────────────────────────────────────────────────
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    n_total = len(df_filt)
    n_win = int((df_filt["resultado"] == "WIN").sum()) if "resultado" in df_filt else 0
    n_loss = int((df_filt["resultado"] == "LOSS").sum()) if "resultado" in df_filt else 0
    wr = round(n_win / (n_win + n_loss) * 100, 1) if (n_win + n_loss) > 0 else 0.0
    rr_neto = float(df_filt["rr"].fillna(0).sum()) if "rr" in df_filt else 0.0
    col_s1.metric("Trades mostrados", n_total)
    col_s2.metric("Winrate", f"{wr:.1f}%")
    col_s3.metric("R neto", f"{rr_neto:+.2f}R")
    col_s4.metric("R medio", f"{(rr_neto / n_total) if n_total else 0:+.2f}R")

    st.markdown("---")

    # ─── Tabla (overview) ────────────────────────────────────────────────────
    def color_res(val):
        return f"color: {RES_COLORS.get(str(val), '#e6edf3')}; font-weight: 700"

    def color_rr(val):
        try:
            v = float(val)
            if v > 0: return "color: #00e676"
            if v < 0: return "color: #ff3c00"
            return "color: #8b949e"
        except Exception:
            return ""

    cols_tabla = ["id", "fecha", "instrumento", "estrategia", "direccion", "resultado", "rr", "notas"]
    cols_pres = [c for c in cols_tabla if c in df_filt.columns]
    df_tabla = df_filt[cols_pres].copy()
    if "notas" in df_tabla.columns:
        df_tabla["notas"] = df_tabla["notas"].fillna("").astype(str).str.slice(0, 60)
    if "rr" in df_tabla.columns:
        df_tabla = df_tabla.rename(columns={"rr": "R:R"})

    styler = df_tabla.style
    if "resultado" in df_tabla.columns:
        styler = styler.applymap(color_res, subset=["resultado"])
    if "R:R" in df_tabla.columns:
        styler = styler.applymap(color_rr, subset=["R:R"])

    st.dataframe(styler, use_container_width=True, hide_index=True, height=380)

    # ─── Export CSV ──────────────────────────────────────────────────────────
    csv_data = df_filt.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Exportar CSV",
        data=csv_data,
        file_name=f"backtest_trades_{date.today().isoformat()}.csv",
        mime="text/csv",
    )

    # ─── Per-trade expanders (edit / images / delete) ────────────────────────
    st.markdown("---")
    st.subheader("✏️ Editar / Eliminar / Capturas por trade")

    if df_filt.empty:
        st.info("No hay trades con los filtros actuales.")
    else:
        for _, fila in df_filt.iterrows():
            t_id = int(fila["id"])
            imagenes = obtener_imagenes_backtest(t_id)
            legacy_path = fila.get("screenshot_path")
            paths = [img["imagen_path"] for img in imagenes]
            if legacy_path and legacy_path not in paths:
                paths.append(legacy_path)
            n_caps = sum(1 for p in paths if p and os.path.isfile(p))

            header = (
                f"#{t_id} · {fila.get('fecha','')} · {fila.get('instrumento','')} "
                f"{fila.get('direccion','')} · {fila.get('resultado','—')} · "
                f"R {(fila.get('rr') or 0):+.2f} · {fila.get('estrategia','—')}"
            )

            with st.expander(header):
                trade_sel = obtener_backtest_trade_por_id(t_id)
                if not trade_sel:
                    st.error("Trade no encontrado.")
                    continue

                col_edit, col_del = st.columns([4, 1])

                with col_del:
                    st.markdown("##### Eliminar")
                    confirm_del = st.checkbox(
                        "Confirmar eliminación",
                        key=f"bt_confirm_del_{t_id}",
                    )
                    if st.button("🗑️ Eliminar", type="primary", use_container_width=True, key=f"bt_del_btn_{t_id}"):
                        if confirm_del:
                            if eliminar_backtest_trade(t_id):
                                st.warning(f"🗑️ Trade backtest #{t_id} eliminado.")
                                st.toast(f"🗑️ Trade #{t_id} eliminado", icon="🗑️")
                                st.rerun()
                            else:
                                st.error("❌ Error al eliminar.")
                        else:
                            st.warning("Marca la casilla de confirmación.")

                with col_edit:
                    st.markdown("##### Editar")
                    nombres_strat_edit = [e["nombre"] for e in estrategias_all]
                    try:
                        estr_actual_nombre = strat_map.get(trade_sel.get("strategy_id"), nombres_strat_edit[0])
                        estr_idx = nombres_strat_edit.index(estr_actual_nombre)
                    except Exception:
                        estr_idx = 0

                    with st.form(f"bt_edit_form_{t_id}"):
                        ec1, ec2, ec3 = st.columns(3)
                        with ec1:
                            nuevo_estr_nombre = st.selectbox(
                                "Estrategia",
                                options=nombres_strat_edit,
                                index=estr_idx,
                                key=f"bt_ed_estr_{t_id}",
                            )
                            nuevo_estr = next(e for e in estrategias_all if e["nombre"] == nuevo_estr_nombre)
                            nueva_op = st.radio(
                                "Operativa",
                                OPERATIVA_OPTIONS,
                                index=0 if (trade_sel.get("operativa_tipo") or "DAY") == "DAY" else 1,
                                horizontal=True,
                                key=f"bt_ed_op_{t_id}",
                            )
                        with ec2:
                            nuevo_instr = st.text_input(
                                "Instrumento",
                                value=trade_sel.get("instrumento", "") or "",
                                key=f"bt_ed_instr_{t_id}",
                            )
                            try:
                                fecha_default = date.fromisoformat(trade_sel.get("fecha")) if trade_sel.get("fecha") else date.today()
                            except Exception:
                                fecha_default = date.today()
                            nueva_fecha = st.date_input(
                                "Fecha",
                                value=fecha_default,
                                key=f"bt_ed_fecha_{t_id}",
                            )
                        with ec3:
                            nueva_dir = st.radio(
                                "Dirección",
                                DIR_OPTIONS,
                                index=0 if (trade_sel.get("direccion") or "LONG") == "LONG" else 1,
                                horizontal=True,
                                key=f"bt_ed_dir_{t_id}",
                            )
                            res_actual = trade_sel.get("resultado") or "WIN"
                            res_idx = RESULT_OPTIONS.index(res_actual) if res_actual in RESULT_OPTIONS else 0
                            nuevo_res = st.selectbox(
                                "Resultado",
                                RESULT_OPTIONS,
                                index=res_idx,
                                key=f"bt_ed_res_{t_id}",
                            )

                        nuevo_rr = st.number_input(
                            "R:R conseguido",
                            value=float(trade_sel.get("rr") or 0.0),
                            step=0.1, format="%.2f",
                            key=f"bt_ed_rr_{t_id}",
                        )
                        nuevas_notas = st.text_area(
                            "Notas",
                            value=trade_sel.get("notas") or "",
                            key=f"bt_ed_notas_{t_id}",
                        )
                        nuevo_asr = st.text_area(
                            "📝 Análisis ASR",
                            value=trade_sel.get("analisis_asr") or "",
                            height=160,
                            key=f"bt_ed_asr_{t_id}",
                        )

                        guardar_edit = st.form_submit_button(
                            "💾 Guardar cambios", type="primary", use_container_width=True,
                        )

                    if guardar_edit:
                        datos_upd = {
                            "strategy_id":     nuevo_estr["id"],
                            "fecha":           nueva_fecha.isoformat(),
                            "instrumento":     nuevo_instr.strip(),
                            "direccion":       nueva_dir,
                            "resultado":       nuevo_res,
                            "rr":              nuevo_rr,
                            "condiciones":     trade_sel.get("condiciones"),
                            "notas":           nuevas_notas or None,
                            "screenshot_path": trade_sel.get("screenshot_path"),
                            "analisis_asr":    nuevo_asr or None,
                            "operativa_tipo":  nueva_op,
                        }
                        if actualizar_backtest_trade(t_id, datos_upd):
                            st.success(f"✅ Trade backtest #{t_id} actualizado.")
                            st.toast(f"✅ Trade #{t_id} actualizado", icon="✅")
                            st.rerun()
                        else:
                            st.error("❌ Error actualizando el trade.")

                # ─── Capturas asociadas ──────────────────────────────────────
                st.markdown(f"##### 📷 Capturas ({n_caps})")
                _mostrar_imagenes(paths)

                if imagenes:
                    st.markdown("**Eliminar capturas individuales:**")
                    cols_del = st.columns(min(len(imagenes), 4))
                    for i, img in enumerate(imagenes):
                        with cols_del[i % 4]:
                            if st.button(f"🗑️ #{img['id']}", key=f"bt_del_img_{t_id}_{img['id']}"):
                                eliminar_imagen_backtest(img["id"])
                                st.toast("🗑️ Imagen eliminada", icon="🗑️")
                                st.rerun()

                # ─── Subir nuevas imágenes ───────────────────────────────────
                nuevas_imgs = st.file_uploader(
                    "➕ Añadir imágenes",
                    type=["png", "jpg", "jpeg", "webp", "gif"],
                    accept_multiple_files=True,
                    key=f"bt_upload_{t_id}",
                )
                if st.button("📎 Adjuntar imágenes seleccionadas", key=f"bt_adj_{t_id}"):
                    if nuevas_imgs:
                        screenshots_dir = os.path.join(
                            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "data", "screenshots", "backtest",
                        )
                        os.makedirs(screenshots_dir, exist_ok=True)
                        orden_base = len(imagenes)
                        for i, img_file in enumerate(nuevas_imgs):
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
                            ext = img_file.name.rsplit(".", 1)[-1]
                            nombre_archivo = f"bt{t_id}_{timestamp}_{i}.{ext}"
                            ruta = os.path.join(screenshots_dir, nombre_archivo)
                            with open(ruta, "wb") as f:
                                f.write(img_file.getbuffer())
                            insertar_imagen_backtest(t_id, ruta, orden_base + i)
                        st.success(f"✅ {len(nuevas_imgs)} imagen(es) añadida(s).")
                        st.toast(f"✅ {len(nuevas_imgs)} imagen(es) añadida(s)", icon="✅")
                        st.rerun()
                    else:
                        st.warning("Selecciona al menos una imagen primero.")
