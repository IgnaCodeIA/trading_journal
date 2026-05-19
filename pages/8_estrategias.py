"""
🎯 Strategy Intelligence Dashboard
- A: Deep dive de una estrategia (equity, heatmap, top condiciones)
- B: Comparativa cross-estrategia
- C: "Quick insight" — top condiciones ranking por Δ WR
"""

import streamlit as st
import os
import sys
import json
import pandas as pd
import plotly.graph_objects as go
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import (
    obtener_estrategias,
    obtener_condiciones,
    obtener_backtest_trades,
)
from core.cuenta_selector import render_cuenta_selector
from core import backtester_stats as bs


st.set_page_config(page_title="Estrategias — Trading Journal Pro", layout="wide")

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🎯 Strategy Intelligence")
st.caption("Vista unificada: qué estrategia funciona, qué condiciones de verdad importan y dónde concentrar tu trading.")
st.markdown("---")

render_cuenta_selector()

estrategias = obtener_estrategias(solo_activas=True)
if not estrategias:
    st.warning("No hay estrategias activas. Créalas en ⚙️ Configuración → Estrategias.")
    st.stop()

# ═════════════════════════════════════════════════════════════════════════════
# SECCIÓN A — Deep dive de una estrategia
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("### 🔍 Deep dive por estrategia")
sel_nombre = st.selectbox(
    "Estrategia",
    options=[e["nombre"] for e in estrategias],
    key="dd_strat",
)
estrategia_sel = next(e for e in estrategias if e["nombre"] == sel_nombre)
sid = estrategia_sel["id"]
trades = obtener_backtest_trades(sid)
condiciones = obtener_condiciones(sid)

kpis = bs.kpis_globales(sid, trades)
top = bs.top_condiciones(sid, n=3, trades=trades)

# Header con color
st.markdown(
    f"<div style='display:flex;align-items:center;gap:14px;margin:8px 0 14px'>"
    f"<div style='width:20px;height:20px;border-radius:50%;background:{estrategia_sel['color']};"
    f"box-shadow:0 0 16px {estrategia_sel['color']}40'></div>"
    f"<div style='font-size:1.6rem;font-weight:800;color:var(--white)'>{estrategia_sel['nombre']}</div>"
    f"<div style='font-size:0.7rem;color:var(--muted);background:var(--bg-3);"
    f"padding:3px 10px;border-radius:12px;border:1px solid var(--border)'>{estrategia_sel['tipo']}</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# KPIs deep dive
dc1, dc2, dc3, dc4 = st.columns(4)
for col, label, val, color in [
    (dc1, "Trades backtest", str(kpis["total"]), "var(--white)"),
    (dc2, "Win Rate", f"{kpis['winrate']:.1f}%",
     "#3fb950" if kpis["winrate"] >= 50 else "#f85149"),
    (dc3, "Net R", f"{kpis['net_r']:+.2f}",
     "#3fb950" if kpis["net_r"] >= 0 else "#f85149"),
    (dc4, "Avg R", f"{kpis['avg_r']:+.2f}",
     "#3fb950" if kpis["avg_r"] >= 0 else "#f85149"),
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

st.markdown("##### 🏆 Top 3 condiciones (por Δ WR)")
if not top:
    st.caption("Sin datos suficientes (necesitas condiciones marcadas en trades).")
else:
    for c in top:
        st.markdown(
            f"<div style='background:var(--bg-3);border:1px solid var(--border);border-radius:8px;"
            f"padding:10px 14px;margin:6px 0;display:flex;justify-content:space-between;align-items:center'>"
            f"<div><strong>{c['badge']} {c['condicion']}</strong></div>"
            f"<div style='font-family:JetBrains Mono,monospace;color:var(--white)'>"
            f"Δ WR <strong>{c['delta_wr']:+.1f}%</strong> "
            f"<span style='color:var(--muted)'>(cumple {c['wr_cumple']:.0f}% · no {c['wr_no_cumple']:.0f}%)</span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

# Equity curve + Heatmap
g1, g2 = st.columns([3, 2])
with g1:
    curva = bs.equity_curve(sid, trades)
    if curva:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[c["fecha"] for c in curva],
            y=[c["equity_r"] for c in curva],
            mode="lines+markers",
            line=dict(color=estrategia_sel["color"], width=2),
            marker=dict(size=5),
        ))
        fig.update_layout(
            title="Equity curve (R acumulado)",
            template="plotly_dark",
            plot_bgcolor="#0d1117",
            paper_bgcolor="#0d1117",
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin trades de backtest registrados.")

with g2:
    if condiciones and trades:
        # Heatmap condición x resultado
        tipos = ["WIN", "PARTIAL_TP", "BE", "PARTIAL_SL", "LOSS"]
        matriz = []
        y_labels = []
        for cond in condiciones:
            cid = str(cond["id"])
            fila = []
            for tipo in tipos:
                n = sum(
                    1 for t in trades
                    if t.get("resultado") == tipo
                    and bs._parse_conditions(t.get("condiciones")).get(cid) == 1
                )
                fila.append(n)
            matriz.append(fila)
            y_labels.append(cond["nombre"][:35])

        fig_h = go.Figure(data=go.Heatmap(
            z=matriz,
            x=tipos,
            y=y_labels,
            colorscale="Viridis",
            showscale=True,
            hovertemplate="<b>%{y}</b><br>%{x}: %{z}<extra></extra>",
        ))
        fig_h.update_layout(
            title="Heatmap condición × resultado (n)",
            template="plotly_dark",
            plot_bgcolor="#0d1117",
            paper_bgcolor="#0d1117",
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig_h, use_container_width=True)

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# SECCIÓN B — Comparativa cross-estrategia
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("### ⚖️ Comparativa cross-estrategia")

filas_comp = []
curvas = []
for e in estrategias:
    eid = e["id"]
    ts = obtener_backtest_trades(eid)
    k = bs.kpis_globales(eid, ts)
    impacto = bs.impacto_condiciones(eid, ts)
    impacto_val = [c for c in impacto if c["n_cumple"] > 0 and c["n_no_cumple"] > 0]
    best = impacto_val[0]["condicion"] if impacto_val else "—"
    worst = impacto_val[-1]["condicion"] if impacto_val else "—"
    filas_comp.append({
        "Estrategia": e["nombre"],
        "Tipo": e["tipo"],
        "Trades": k["total"],
        "WR %": f"{k['winrate']:.1f}",
        "Net R": f"{k['net_r']:+.2f}",
        "Avg R": f"{k['avg_r']:+.2f}",
        "Mejor condición": best,
        "Peor condición": worst,
    })
    curvas.append((e, bs.equity_curve(eid, ts)))

df_comp = pd.DataFrame(filas_comp)
st.dataframe(df_comp, use_container_width=True, hide_index=True)

# Overlay equity curves
fig_overlay = go.Figure()
hay_datos = False
for e, curva in curvas:
    if curva:
        hay_datos = True
        fig_overlay.add_trace(go.Scatter(
            x=[c["fecha"] for c in curva],
            y=[c["equity_r"] for c in curva],
            mode="lines",
            name=e["nombre"],
            line=dict(color=e["color"], width=2),
        ))
if hay_datos:
    fig_overlay.update_layout(
        title="Equity curves comparadas (R acumulado)",
        template="plotly_dark",
        plot_bgcolor="#0d1117",
        paper_bgcolor="#0d1117",
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    st.plotly_chart(fig_overlay, use_container_width=True)

# Bar chart WR
fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    x=[e["nombre"] for e in estrategias],
    y=[bs.kpis_globales(e["id"])["winrate"] for e in estrategias],
    marker_color=[e["color"] for e in estrategias],
    text=[f"{bs.kpis_globales(e['id'])['winrate']:.1f}%" for e in estrategias],
    textposition="outside",
))
fig_bar.update_layout(
    title="WR por estrategia",
    template="plotly_dark",
    plot_bgcolor="#0d1117",
    paper_bgcolor="#0d1117",
    height=320,
    margin=dict(l=20, r=20, t=40, b=20),
    yaxis=dict(range=[0, 110], title="WR %"),
)
st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# SECCIÓN C — Condition Intelligence (quick insight)
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("### 💡 Condition Intelligence")
st.caption("Para cada estrategia: top 3 condiciones por Δ WR + peor condición + confluencia óptima.")

for e in estrategias:
    eid = e["id"]
    resumen = bs.resumen_estrategia(eid)
    n_trades = resumen["n_trades"]

    bloque = []
    bloque.append(
        f"<div style='background:var(--bg-2);border:1px solid var(--border);border-left:4px solid {e['color']};"
        f"border-radius:8px;padding:14px 18px;margin:12px 0'>"
    )
    bloque.append(
        f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>"
        f"<div style='font-size:1.15rem;font-weight:800;color:var(--white)'>{e['nombre']} <span style='color:var(--muted);font-weight:400;font-size:0.8rem'>({e['tipo']})</span></div>"
        f"<div style='font-size:0.8rem;color:var(--muted);font-family:JetBrains Mono,monospace'>{n_trades} ops</div>"
        f"</div>"
    )

    top_e = resumen["top_condiciones"]
    if not top_e and n_trades == 0:
        bloque.append("<div style='color:var(--muted);font-size:0.85rem'>Sin trades de backtest aún.</div>")
    elif not top_e:
        bloque.append("<div style='color:var(--muted);font-size:0.85rem'>Sin suficiente variación en las condiciones.</div>")
    else:
        for i, c in enumerate(top_e, 1):
            bloque.append(
                f"<div style='font-family:JetBrains Mono,monospace;font-size:0.85rem;color:var(--white);margin:3px 0'>"
                f"{c['badge']} #{i}  <strong>{c['condicion']}</strong>"
                f"<span style='float:right;color:var(--muted)'>Δ WR <strong style='color:var(--white)'>{c['delta_wr']:+.1f}%</strong>  "
                f"(cumple: {c['wr_cumple']:.0f}% | no: {c['wr_no_cumple']:.0f}%)</span></div>"
            )

    peor = resumen["peor_condicion"]
    if peor:
        bloque.append(
            f"<div style='font-family:JetBrains Mono,monospace;font-size:0.85rem;color:#f85149;margin-top:6px'>"
            f"🔴 ⚠️  <strong>{peor['condicion']}</strong>"
            f"<span style='float:right;color:var(--muted)'>Δ WR <strong style='color:#f85149'>{peor['delta_wr']:+.1f}%</strong>  "
            f"(CONDICIÓN QUE PERJUDICA)</span></div>"
        )

    confl = resumen["confluencia_optima"]
    if confl:
        bloque.append(
            f"<div style='border-top:1px solid var(--border);margin-top:10px;padding-top:8px;color:var(--muted);font-size:0.85rem'>"
            f"Confluencia óptima: <strong style='color:var(--white)'>{confl['n_condiciones']}+ condiciones</strong> → "
            f"WR <strong style='color:#3fb950'>{confl['winrate']:.0f}%</strong> "
            f"({confl['n_ops']} ops)</div>"
        )

    bloque.append("</div>")
    st.markdown("".join(bloque), unsafe_allow_html=True)
