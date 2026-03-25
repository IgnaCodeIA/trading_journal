"""
Estadísticas — Análisis detallado del rendimiento por período, estrategia y contexto.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import obtener_todos_los_trades, obtener_configuracion
from core.stats import (
    calcular_winrate,
    calcular_profit_factor,
    calcular_expectativa,
    calcular_rr_medio,
    calcular_rachas,
    calcular_trades_por_periodo,
    calcular_equity_curve,
    calcular_drawdown_historico,
    calcular_pnl_mensual,
    calcular_pnl_trimestral,
    calcular_stats_por_estrategia,
    calcular_stats_por_sesion,
    calcular_stats_por_tipo_operacion,
    calcular_impacto_trailing_stop,
    calcular_top_pares,
    calcular_rentabilidad_anual,
    calcular_pnl_dia,
    calcular_pnl_semana,
    calcular_pnl_mes,
)

st.set_page_config(page_title="Estadísticas — Trading Journal Pro", layout="wide")

# CSS
css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("📈 Estadísticas")
st.markdown("---")

# ─── Carga de datos ─────────────────────────────────────────────────────────
trades = obtener_todos_los_trades()
config = obtener_configuracion()
trades_validos = [t for t in trades if t.get("resultado") in ("Win", "Loss", "Breakeven", "Parcial")]

if not trades_validos:
    st.info("No hay trades registrados todavía. Ve a **Nuevo Trade** para empezar.")
    st.stop()

capital_inicial = config.get("tamanio_cuenta", 10000.0)
divisa = config.get("divisa", "USD")

# Precalculamos todo
curva = calcular_equity_curve(trades_validos, capital_inicial)
drawdown_info = calcular_drawdown_historico(curva)
winrate = calcular_winrate(trades_validos)
rr_medio = calcular_rr_medio(trades_validos)
profit_factor = calcular_profit_factor(trades_validos)
expectativa = calcular_expectativa(winrate, rr_medio["conseguido"])
rachas = calcular_rachas(trades_validos)
trades_periodo = calcular_trades_por_periodo(trades_validos)
rentabilidad_anual = calcular_rentabilidad_anual(trades_validos)

# ─── Tabs de secciones ────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📅 Rendimiento Temporal",
    "🎯 Métricas de Calidad",
    "📉 Drawdown",
    "🎨 Por Estrategia",
    "🌍 Por Contexto",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: Rendimiento temporal
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Equity Curve Completa")

    if len(curva) >= 2:
        fechas_curva = [p["fecha"] or "Inicio" for p in curva]
        valores_curva = [p["equity"] for p in curva]

        fig_equity = go.Figure()
        fig_equity.add_trace(go.Scatter(
            x=fechas_curva,
            y=valores_curva,
            mode="lines",
            name="Equity",
            line=dict(color="#58a6ff", width=2),
            fill="tozeroy",
            fillcolor="rgba(88, 166, 255, 0.08)",
        ))
        fig_equity.add_hline(
            y=capital_inicial,
            line_dash="dash",
            line_color="#8b949e",
            annotation_text=f"Capital inicial: {capital_inicial:,.0f} {divisa}",
        )
        fig_equity.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=350,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#30363d"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_equity, use_container_width=True)

    # P&L mensual
    st.subheader("P&L Mensual — Últimos 12 Meses")
    pnl_mensual = calcular_pnl_mensual(trades_validos)
    if pnl_mensual:
        df_mensual = pd.DataFrame(pnl_mensual)
        colores = ["#3fb950" if v >= 0 else "#f85149" for v in df_mensual["pnl"]]

        fig_mensual = go.Figure(go.Bar(
            x=df_mensual["mes"],
            y=df_mensual["pnl"],
            marker_color=colores,
            text=[f"{v:+.2f}%" for v in df_mensual["pnl"]],
            textposition="outside",
        ))
        fig_mensual.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=300,
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#30363d", zeroline=True, zerolinecolor="#30363d"),
            showlegend=False,
        )
        st.plotly_chart(fig_mensual, use_container_width=True)

    # P&L trimestral
    st.subheader("P&L Trimestral")
    pnl_trimestral = calcular_pnl_trimestral(trades_validos)
    if pnl_trimestral:
        df_trim = pd.DataFrame(pnl_trimestral)
        colores_trim = ["#3fb950" if v >= 0 else "#f85149" for v in df_trim["pnl"]]

        fig_trim = go.Figure(go.Bar(
            x=df_trim["trimestre"],
            y=df_trim["pnl"],
            marker_color=colores_trim,
            text=[f"{v:+.2f}%" for v in df_trim["pnl"]],
            textposition="outside",
        ))
        fig_trim.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=280,
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#30363d"),
            showlegend=False,
        )
        st.plotly_chart(fig_trim, use_container_width=True)

    # Rentabilidad anual
    st.subheader("Rentabilidad Anual Acumulada")
    if rentabilidad_anual:
        cols_anual = st.columns(len(rentabilidad_anual))
        for i, (anio, pnl) in enumerate(rentabilidad_anual.items()):
            with cols_anual[i]:
                delta_color = "normal" if pnl >= 0 else "inverse"
                st.metric(f"Año {anio}", f"{pnl:+.2f}%", delta=f"{pnl:+.2f}%", delta_color=delta_color)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: Métricas de calidad
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Métricas de Calidad")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Winrate Global", f"{winrate:.1f}%")
    with col2:
        pf_str = f"{profit_factor:.2f}" if profit_factor != float("inf") else "∞"
        st.metric("Profit Factor", pf_str)
    with col3:
        st.metric("Expectativa Matemática", f"{expectativa:.3f}")
    with col4:
        st.metric("Total Trades", len(trades_validos))

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("R:R Medio Planificado", f"{rr_medio['planificado']:.2f}")
    with col6:
        st.metric("R:R Medio Conseguido", f"{rr_medio['conseguido']:.2f}")
    with col7:
        st.metric("Trades/Semana (media)", f"{trades_periodo['por_semana']:.1f}")
    with col8:
        st.metric("Trades/Mes (media)", f"{trades_periodo['por_mes']:.1f}")

    st.markdown("---")
    col9, col10 = st.columns(2)
    with col9:
        st.metric("🏆 Mejor racha ganadora", f"{rachas['max_ganadora']} seguidas")
    with col10:
        st.metric("⚠️ Peor racha perdedora", f"{rachas['max_perdedora']} seguidas")

    st.markdown("---")
    st.subheader("Fórmula: Expectativa Matemática")
    st.latex(r"E = (WR \times \bar{RR}) - (1 - WR)")
    wr_dec = winrate / 100
    st.info(
        f"E = ({wr_dec:.2f} × {rr_medio['conseguido']:.2f}) - (1 - {wr_dec:.2f}) = "
        f"**{expectativa:.3f}**\n\n"
        f"{'✅ Expectativa positiva — sistema rentable.' if expectativa > 0 else '❌ Expectativa negativa — revisar estrategia.'}"
    )

    # Distribución de resultados
    st.markdown("---")
    st.subheader("Distribución de Resultados")
    conteo = {"Win": 0, "Loss": 0, "Breakeven": 0, "Parcial": 0}
    for t in trades_validos:
        r = t.get("resultado", "")
        if r in conteo:
            conteo[r] += 1

    fig_pie = go.Figure(go.Pie(
        labels=list(conteo.keys()),
        values=list(conteo.values()),
        marker_colors=["#3fb950", "#f85149", "#8b949e", "#d29922"],
        hole=0.4,
    ))
    fig_pie.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        height=320,
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: Drawdown
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Análisis de Drawdown")

    col_dd1, col_dd2 = st.columns(2)
    with col_dd1:
        st.metric("Drawdown Máximo Histórico", f"{drawdown_info['max_drawdown_pct']:.2f}%")
    with col_dd2:
        st.metric("Drawdown Actual", f"{drawdown_info['drawdown_actual_pct']:.2f}%")

    # Gráfica de drawdown en el tiempo
    st.markdown("---")
    dd_serie = drawdown_info.get("serie", [])
    if len(dd_serie) >= 2:
        fechas_dd = [p["fecha"] or "Inicio" for p in dd_serie]
        valores_dd = [p["drawdown"] for p in dd_serie]

        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(
            x=fechas_dd,
            y=[-v for v in valores_dd],  # Negativo para que vaya hacia abajo
            mode="lines",
            name="Drawdown",
            line=dict(color="#f85149", width=1.5),
            fill="tozeroy",
            fillcolor="rgba(248, 81, 73, 0.2)",
        ))
        fig_dd.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=320,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#30363d", title="Drawdown (%)"),
            title="Drawdown en el Tiempo",
            hovermode="x unified",
        )
        st.plotly_chart(fig_dd, use_container_width=True)
    else:
        st.info("Se necesitan más trades para visualizar el drawdown en el tiempo.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: Por Estrategia
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    stats_estrategia = calcular_stats_por_estrategia(trades_validos)

    if not stats_estrategia:
        st.info("Sin datos de estrategia.")
    else:
        st.subheader("Comparativa por Estrategia")
        df_estrat = pd.DataFrame(stats_estrategia)

        # Formatear para mostrar
        df_estrat_display = df_estrat.copy()
        df_estrat_display["winrate"] = df_estrat_display["winrate"].apply(lambda x: f"{x:.1f}%")
        df_estrat_display["pnl"] = df_estrat_display["pnl"].apply(lambda x: f"{x:+.2f}%")
        df_estrat_display["rr_medio_conseguido"] = df_estrat_display["rr_medio_conseguido"].apply(lambda x: f"{x:.2f}")
        df_estrat_display["profit_factor"] = df_estrat_display["profit_factor"].apply(
            lambda x: "∞" if x == float("inf") else f"{x:.2f}"
        )
        df_estrat_display.columns = ["Estrategia", "Winrate", "P&L %", "R:R Medio", "Nº Trades", "Profit Factor"]

        st.dataframe(df_estrat_display, use_container_width=True, hide_index=True)

        # Gráfica de barras agrupadas
        st.markdown("---")
        fig_estrat = go.Figure()
        fig_estrat.add_trace(go.Bar(
            name="Winrate (%)",
            x=df_estrat["estrategia"],
            y=df_estrat["winrate"],
            marker_color="#58a6ff",
            yaxis="y",
        ))
        fig_estrat.add_trace(go.Bar(
            name="P&L (%)",
            x=df_estrat["estrategia"],
            y=df_estrat["pnl"],
            marker_color=[("#3fb950" if v >= 0 else "#f85149") for v in df_estrat["pnl"]],
            yaxis="y2",
        ))
        fig_estrat.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=360,
            margin=dict(l=0, r=0, t=30, b=0),
            barmode="group",
            yaxis=dict(title="Winrate (%)", showgrid=True, gridcolor="#30363d"),
            yaxis2=dict(title="P&L (%)", overlaying="y", side="right", showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_estrat, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: Por Contexto
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    col_ctx1, col_ctx2 = st.columns(2)

    # Por sesión
    with col_ctx1:
        st.subheader("Por Sesión")
        stats_sesion = calcular_stats_por_sesion(trades_validos)
        if stats_sesion:
            df_sesion = pd.DataFrame(stats_sesion)
            fig_sesion = go.Figure(go.Bar(
                x=df_sesion["sesion"],
                y=df_sesion["pnl"],
                marker_color=[("#3fb950" if v >= 0 else "#f85149") for v in df_sesion["pnl"]],
                text=[f"{v:+.2f}%" for v in df_sesion["pnl"]],
                textposition="outside",
            ))
            fig_sesion.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=300,
                margin=dict(l=0, r=0, t=20, b=0),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#30363d"),
                showlegend=False,
            )
            st.plotly_chart(fig_sesion, use_container_width=True)

    # Por tipo de operación
    with col_ctx2:
        st.subheader("Por Tipo de Operación")
        stats_tipo = calcular_stats_por_tipo_operacion(trades_validos)
        if stats_tipo:
            df_tipo = pd.DataFrame(stats_tipo)
            fig_tipo = go.Figure(go.Bar(
                x=df_tipo["tipo"],
                y=df_tipo["pnl"],
                marker_color=[("#3fb950" if v >= 0 else "#f85149") for v in df_tipo["pnl"]],
                text=[f"{v:+.2f}%" for v in df_tipo["pnl"]],
                textposition="outside",
            ))
            fig_tipo.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=300,
                margin=dict(l=0, r=0, t=20, b=0),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#30363d"),
                showlegend=False,
            )
            st.plotly_chart(fig_tipo, use_container_width=True)

    # Impacto trailing stop
    st.markdown("---")
    st.subheader("Impacto del Trailing Stop")
    impacto_trailing = calcular_impacto_trailing_stop(trades_validos)
    col_tr1, col_tr2 = st.columns(2)

    with col_tr1:
        datos_con = impacto_trailing["con_trailing"]
        st.markdown("**Con Trailing Stop**")
        st.metric("Nº Trades", datos_con["n_trades"])
        st.metric("Winrate", f"{datos_con['winrate']:.1f}%")
        st.metric("P&L Medio", f"{datos_con['pnl_medio']:+.3f}%")

    with col_tr2:
        datos_sin = impacto_trailing["sin_trailing"]
        st.markdown("**Sin Trailing Stop**")
        st.metric("Nº Trades", datos_sin["n_trades"])
        st.metric("Winrate", f"{datos_sin['winrate']:.1f}%")
        st.metric("P&L Medio", f"{datos_sin['pnl_medio']:+.3f}%")

    # Top 10 pares
    st.markdown("---")
    st.subheader("Top 10 Pares por P&L")
    top_pares = calcular_top_pares(trades_validos, 10)
    if top_pares:
        df_pares = pd.DataFrame(top_pares)
        fig_pares = go.Figure(go.Bar(
            x=df_pares["par"],
            y=df_pares["pnl"],
            marker_color=[("#3fb950" if v >= 0 else "#f85149") for v in df_pares["pnl"]],
            text=[f"{v:+.2f}%" for v in df_pares["pnl"]],
            textposition="outside",
        ))
        fig_pares.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=320,
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#30363d"),
            showlegend=False,
        )
        st.plotly_chart(fig_pares, use_container_width=True)
