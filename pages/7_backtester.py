"""
🔬 Backtester — Registro y análisis de backtests por estrategia.

Cada estrategia se aloja en un tab horizontal. Dentro:
  • ➕ Nuevo Trade — formulario de backtest
  • 📋 Registro    — tabla filtrable con borrado inline + export CSV
  • 📊 Análisis   — KPIs, impacto por condición, confluencia, desglose
"""

import streamlit as st
import os
import sys
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import (
    obtener_estrategias,
    obtener_condiciones,
    obtener_backtest_trades,
    insertar_backtest_trade,
    eliminar_backtest_trade,
    crear_estrategia,
    load_pares,
)
from core.cuenta_selector import render_cuenta_selector
from core import backtester_stats as bs


st.set_page_config(page_title="Backtester — Trading Journal Pro", layout="wide")

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🔬 Backtester")
st.markdown("Registra trades de backtesting por estrategia y descubre qué condiciones de verdad importan.")
st.markdown("---")

render_cuenta_selector()

# ─── Crear nueva estrategia ───────────────────────────────────────────────────
with st.expander("＋ Nueva estrategia", expanded=False):
    with st.form("form_nueva_estrategia"):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
        with c1:
            n_nombre = st.text_input("Nombre *", placeholder="Mi estrategia")
        with c2:
            n_tipo = st.radio("Tipo *", ["DAY", "SCALPING"], horizontal=True)
        with c3:
            n_color = st.color_picker("Color", value="#58a6ff")
        with c4:
            n_desc = st.text_input("Descripción", placeholder="Resumen breve")
        if st.form_submit_button("Crear estrategia", type="primary"):
            if not n_nombre.strip():
                st.error("El nombre es obligatorio.")
            else:
                try:
                    crear_estrategia(n_nombre.strip(), n_tipo, n_desc, n_color)
                    st.success(f"Estrategia «{n_nombre}» creada.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

estrategias = obtener_estrategias(solo_activas=True)
if not estrategias:
    st.warning("No hay estrategias activas. Crea una arriba.")
    st.stop()

# ─── Tabs horizontales por estrategia ────────────────────────────────────────
nombres = [f"{e['nombre']} · {e['tipo']}" for e in estrategias]
tabs = st.tabs(nombres)

pares_dict = load_pares()
opciones_pares = []
for cat, lista in pares_dict.items():
    opciones_pares.append(f"── {cat} ──")
    opciones_pares.extend(lista)

RESULT_OPTIONS = ["WIN", "LOSS", "BE", "PARTIAL_TP", "PARTIAL_SL"]

for tab, estrategia in zip(tabs, estrategias):
    with tab:
        sid = estrategia["id"]
        st.markdown(
            f"<div style='display:flex;gap:12px;align-items:center;margin-bottom:8px'>"
            f"<div style='width:14px;height:14px;border-radius:50%;background:{estrategia['color']}'></div>"
            f"<div style='font-size:1.4rem;font-weight:800;color:var(--white)'>{estrategia['nombre']}</div>"
            f"<div style='font-size:0.75rem;color:var(--muted);background:var(--bg-3);"
            f"padding:2px 10px;border-radius:12px;border:1px solid var(--border)'>{estrategia['tipo']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if estrategia.get("descripcion"):
            st.caption(estrategia["descripcion"])

        condiciones = obtener_condiciones(sid)
        sub_a, sub_b, sub_c = st.tabs(["➕ Nuevo Trade", "📋 Registro", "📊 Análisis"])

        # ════════════════════════════════════════════════════════════════════
        # SUB-A: Nuevo Trade
        # ════════════════════════════════════════════════════════════════════
        with sub_a:
            with st.form(f"bt_form_{sid}"):
                c1, c2, c3, c4 = st.columns([2, 1.2, 1, 1])
                with c1:
                    instrumento = st.selectbox("Instrumento *", options=opciones_pares,
                                               index=1 if len(opciones_pares) > 1 else 0,
                                               key=f"bt_par_{sid}")
                with c2:
                    fecha_bt = st.date_input("Fecha *", value=date.today(), key=f"bt_fecha_{sid}")
                with c3:
                    direccion_bt = st.radio("Dirección *", ["LONG", "SHORT"], horizontal=True, key=f"bt_dir_{sid}")
                with c4:
                    resultado_bt = st.selectbox("Resultado *", RESULT_OPTIONS, key=f"bt_res_{sid}")

                rr_bt = st.number_input(
                    "R:R conseguido * (negativo = pérdida, 0 = BE)",
                    value=0.0, step=0.1, format="%.2f",
                    key=f"bt_rr_{sid}",
                )

                st.markdown("##### Condiciones presentes en el setup")
                if not condiciones:
                    st.caption("Esta estrategia no tiene condiciones. Añádelas en ⚙️ Configuración → Estrategias.")
                    marcadas = {}
                else:
                    marcadas = {}
                    cols_c = st.columns(2)
                    for i, cond in enumerate(condiciones):
                        with cols_c[i % 2]:
                            on = st.checkbox(cond["nombre"], key=f"bt_cond_{sid}_{cond['id']}")
                            marcadas[str(cond["id"])] = 1 if on else 0

                notas_bt = st.text_area("Notas", height=80, key=f"bt_notas_{sid}")
                screenshot_bt = st.file_uploader(
                    "Screenshot",
                    type=["png", "jpg", "jpeg", "webp"],
                    key=f"bt_img_{sid}",
                )

                if st.form_submit_button("💾 Guardar trade de backtest", type="primary"):
                    if instrumento.startswith("──"):
                        st.error("Selecciona un instrumento válido.")
                    else:
                        path_img = None
                        if screenshot_bt is not None:
                            screenshots_dir = os.path.join(
                                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "data", "screenshots", "backtest",
                            )
                            os.makedirs(screenshots_dir, exist_ok=True)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
                            ext = screenshot_bt.name.rsplit(".", 1)[-1]
                            nombre = f"bt_s{sid}_{timestamp}.{ext}"
                            path_img = os.path.join(screenshots_dir, nombre)
                            with open(path_img, "wb") as f:
                                f.write(screenshot_bt.getbuffer())
                        try:
                            insertar_backtest_trade({
                                "strategy_id": sid,
                                "fecha": fecha_bt.isoformat(),
                                "instrumento": instrumento,
                                "direccion": direccion_bt,
                                "resultado": resultado_bt,
                                "rr": rr_bt,
                                "condiciones": json.dumps(marcadas) if marcadas else None,
                                "notas": notas_bt or None,
                                "screenshot_path": path_img,
                            })
                            st.success(f"✅ Trade backtest guardado en {estrategia['nombre']}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

        # ════════════════════════════════════════════════════════════════════
        # SUB-B: Registro
        # ════════════════════════════════════════════════════════════════════
        with sub_b:
            trades_bt = obtener_backtest_trades(sid)
            if not trades_bt:
                st.info("Aún no hay trades de backtest para esta estrategia.")
            else:
                # Filtros
                fc1, fc2, fc3 = st.columns([1, 1, 1])
                with fc1:
                    f_res = st.multiselect("Resultado", RESULT_OPTIONS, default=RESULT_OPTIONS, key=f"f_res_{sid}")
                with fc2:
                    instrumentos_unicos = sorted({t["instrumento"] for t in trades_bt if t["instrumento"]})
                    f_ins = st.multiselect("Instrumento", instrumentos_unicos, default=instrumentos_unicos, key=f"f_ins_{sid}")
                with fc3:
                    fechas = [t["fecha"] for t in trades_bt if t["fecha"]]
                    fmin = min(fechas) if fechas else date.today().isoformat()
                    fmax = max(fechas) if fechas else date.today().isoformat()
                    rango = st.date_input(
                        "Rango fechas",
                        value=(datetime.fromisoformat(fmin).date(), datetime.fromisoformat(fmax).date()),
                        key=f"f_fecha_{sid}",
                    )

                filtrados = []
                for t in trades_bt:
                    if t["resultado"] not in f_res:
                        continue
                    if t["instrumento"] not in f_ins:
                        continue
                    if isinstance(rango, tuple) and len(rango) == 2 and t["fecha"]:
                        tf = datetime.fromisoformat(t["fecha"]).date()
                        if tf < rango[0] or tf > rango[1]:
                            continue
                    filtrados.append(t)

                st.caption(f"{len(filtrados)} de {len(trades_bt)} trades")

                # Tabla
                cond_map = {c["id"]: c["nombre"] for c in condiciones}
                filas = []
                for t in filtrados:
                    conds = {}
                    if t.get("condiciones"):
                        try:
                            conds = json.loads(t["condiciones"])
                        except Exception:
                            conds = {}
                    fila = {
                        "id": t["id"],
                        "fecha": t["fecha"],
                        "instrumento": t["instrumento"],
                        "dir": t["direccion"],
                        "resultado": t["resultado"],
                        "R:R": f"{(t.get('rr') or 0):+.2f}",
                    }
                    for cid, cnombre in cond_map.items():
                        fila[cnombre[:30]] = "✓" if conds.get(str(cid)) == 1 else "·"
                    filas.append(fila)

                df = pd.DataFrame(filas)

                def color_result(val):
                    color = bs.RESULT_COLORS.get(val, "#8b949e")
                    return f"color: {color}; font-weight: 700;"

                if not df.empty:
                    styler = df.style.applymap(color_result, subset=["resultado"])
                    st.dataframe(styler, use_container_width=True, hide_index=True)

                    # Export CSV
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "⬇️ Exportar CSV",
                        data=csv,
                        file_name=f"backtest_{estrategia['nombre']}_{date.today().isoformat()}.csv",
                        mime="text/csv",
                    )

                    # Borrado inline
                    st.markdown("##### 🗑️ Eliminar trade")
                    col_del1, col_del2 = st.columns([3, 1])
                    with col_del1:
                        ids_filt = [t["id"] for t in filtrados]
                        del_id = st.selectbox(
                            "Selecciona ID",
                            options=ids_filt,
                            key=f"del_{sid}",
                        )
                    with col_del2:
                        if st.button("Eliminar", key=f"del_btn_{sid}"):
                            if eliminar_backtest_trade(del_id):
                                st.success(f"Trade #{del_id} eliminado.")
                                st.rerun()
                            else:
                                st.error("Error eliminando.")

        # ════════════════════════════════════════════════════════════════════
        # SUB-C: Análisis
        # ════════════════════════════════════════════════════════════════════
        with sub_c:
            trades_an = obtener_backtest_trades(sid)
            if not trades_an:
                st.info("Sin datos. Añade trades en la pestaña ➕ Nuevo Trade.")
                continue

            kpis = bs.kpis_globales(sid, trades_an)

            # ── Fila 1: KPIs globales ────────────────────────────────────────
            k1, k2, k3, k4, k5 = st.columns(5)
            for col, label, val, color in [
                (k1, "Total ops", f"{kpis['total']}", "var(--white)"),
                (k2, "Win Rate", f"{kpis['winrate']:.1f}%",
                 "#3fb950" if kpis["winrate"] >= 50 else "#f85149"),
                (k3, "Net R", f"{kpis['net_r']:+.2f}R",
                 "#3fb950" if kpis["net_r"] >= 0 else "#f85149"),
                (k4, "Avg R/trade", f"{kpis['avg_r']:+.2f}R",
                 "#3fb950" if kpis["avg_r"] >= 0 else "#f85149"),
                (k5, "Best streak", f"{kpis['best_streak']}", "#58a6ff"),
            ]:
                with col:
                    st.markdown(
                        f"<div class='kpi-card' style='padding:14px 16px'>"
                        f"<div style='font-size:0.65rem;color:var(--muted-2);text-transform:uppercase;"
                        f"font-weight:700;letter-spacing:0.08em'>{label}</div>"
                        f"<div style='font-size:1.5rem;font-weight:800;color:{color};"
                        f"font-family:JetBrains Mono,monospace'>{val}</div></div>",
                        unsafe_allow_html=True,
                    )

            # ── Fila 2: Impacto por condición ────────────────────────────────
            st.markdown("##### 🎯 Impacto por condición")
            impacto = bs.impacto_condiciones(sid, trades_an)
            if not impacto:
                st.caption("Esta estrategia no tiene condiciones para analizar.")
            else:
                df_imp = pd.DataFrame([{
                    "Condición": r["condicion"],
                    "N cumple": r["n_cumple"],
                    "WR cumple %": f"{r['wr_cumple']:.1f}",
                    "N no cumple": r["n_no_cumple"],
                    "WR no cumple %": f"{r['wr_no_cumple']:.1f}",
                    "Δ WR": f"{r['delta_wr']:+.1f}",
                    "Impacto": f"{r['badge']} {r['impacto']}",
                } for r in impacto])
                st.dataframe(df_imp, use_container_width=True, hide_index=True)

            # ── Fila 3: Confluencia ──────────────────────────────────────────
            st.markdown("##### 🔗 Confluencia de condiciones")
            confl = bs.tabla_confluencia(sid, trades_an)
            if not confl:
                st.caption("Sin datos.")
            else:
                df_c = pd.DataFrame([{
                    "Nº condiciones cumplidas": r["n_condiciones"],
                    "Ops": r["n_ops"],
                    "WR %": f"{r['winrate']:.1f}",
                    "R neto": f"{r['net_r']:+.2f}",
                    "Recomendación": r["recomendacion"],
                } for r in confl])
                st.dataframe(df_c, use_container_width=True, hide_index=True)

            # ── Fila 4: Desglose por tipo de resultado ───────────────────────
            st.markdown("##### 📊 Desglose por tipo de resultado")
            desg = bs.desglose_resultados(sid, trades_an)
            df_d = pd.DataFrame([{
                "Tipo": r["tipo"],
                "N": r["n"],
                "% del total": f"{r['pct']:.1f}%",
                "R medio": f"{r['r_medio']:+.2f}",
                "R neto": f"{r['r_neto']:+.2f}",
            } for r in desg])
            st.dataframe(df_d, use_container_width=True, hide_index=True)

            # Nota sobre PARTIAL_SL
            partial_sl = next((r for r in desg if r["tipo"] == "PARTIAL_SL"), None)
            if partial_sl and partial_sl["n"] > 0:
                ahorro = (-1.0) - partial_sl["r_medio"]
                st.caption(
                    f"💡 PARTIAL_SL: reducción media de pérdida vs -1R completo: "
                    f"**{ahorro:+.2f}R** (ahorrado por gestión)."
                )

            # ── Fila 5: Por instrumento ──────────────────────────────────────
            st.markdown("##### 🌍 Por instrumento")
            por_ins = bs.breakdown_instrumento(sid, trades_an)
            df_i = pd.DataFrame([{
                "Instrumento": r["instrumento"],
                "N": r["n"],
                "WR %": f"{r['winrate']:.1f}",
                "Avg R": f"{r['avg_r']:+.2f}",
                "Net R": f"{r['net_r']:+.2f}",
            } for r in por_ins])
            st.dataframe(df_i, use_container_width=True, hide_index=True)

            # Equity curve
            curva = bs.equity_curve(sid, trades_an)
            if curva:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=[c["fecha"] for c in curva],
                    y=[c["equity_r"] for c in curva],
                    mode="lines+markers",
                    line=dict(color=estrategia["color"], width=2),
                    marker=dict(size=5),
                    name="Equity (R)",
                ))
                fig.update_layout(
                    title="Equity curve (R acumulado)",
                    template="plotly_dark",
                    plot_bgcolor="#0d1117",
                    paper_bgcolor="#0d1117",
                    height=300,
                    margin=dict(l=20, r=20, t=40, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)
