"""
Helper para renderizar el selector de cuenta en el sidebar de cualquier página.
"""

import streamlit as st
from core.database import obtener_cuentas


def render_cuenta_selector() -> tuple:
    """
    Renderiza el selector de cuenta activa en el sidebar.
    Devuelve (cuenta_id: int, cuenta: dict).
    La cuenta contiene: nombre, broker, capital, divisa, riesgo_base.
    """
    cuentas = obtener_cuentas()

    if not cuentas:
        # Fallback si por algún motivo no hay cuentas
        return 1, {"id": 1, "nombre": "Cuenta Principal", "broker": "", "capital": 10000.0, "divisa": "USD", "riesgo_base": 1.0}

    ids = [c["id"] for c in cuentas]

    # Inicializar session_state con la primera cuenta disponible
    if "cuenta_activa_id" not in st.session_state or st.session_state.cuenta_activa_id not in ids:
        st.session_state.cuenta_activa_id = ids[0]

    def _label(c):
        broker = f" · {c['broker']}" if c.get("broker") else ""
        return f"{c['nombre']}{broker} ({c['capital']:,.0f} {c['divisa']})"

    idx = ids.index(st.session_state.cuenta_activa_id)

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Cuenta activa**")
    seleccionada = st.sidebar.selectbox(
        "Cuenta",
        options=cuentas,
        format_func=_label,
        index=idx,
        key="cuenta_selector_widget",
        label_visibility="collapsed",
    )
    st.session_state.cuenta_activa_id = seleccionada["id"]
    st.sidebar.markdown("---")

    return seleccionada["id"], seleccionada
