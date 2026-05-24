"""
Configuración — Parámetros del sistema, pares, backup y reseteo.
"""

import streamlit as st
import os
import sys
import json
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import (
    obtener_configuracion,
    actualizar_configuracion,
    load_pares,
    exportar_todo_json,
    importar_desde_json,
    resetear_base_datos,
    obtener_cuentas,
    crear_cuenta,
    actualizar_cuenta,
    eliminar_cuenta,
    obtener_estrategias,
    crear_estrategia,
    actualizar_estrategia,
    eliminar_estrategia,
    contar_trades_estrategia,
    obtener_condiciones,
    crear_condicion,
    actualizar_condicion,
    eliminar_condicion,
    reordenar_condiciones,
    PARES_PATH,
    BASE_DIR,
)

st.set_page_config(page_title="Configuración — Trading Journal Pro", layout="wide", initial_sidebar_state="expanded")

# CSS
css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("⚙️ Configuración")
st.markdown("---")

config = obtener_configuracion()

# ─── Tabs de configuración ─────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏦 Cuentas",
    "👤 Perfil y Riesgo",
    "📊 Motor de Riesgo",
    "📁 Pares",
    "🎯 Estrategias",
    "💾 Backup y Reseteo",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: Cuentas
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Gestión de Cuentas de Trading")
    cuentas = obtener_cuentas()

    # ─── Lista de cuentas existentes ────────────────────────────────────────
    st.markdown("#### Cuentas configuradas")
    for c in cuentas:
        with st.expander(f"**{c['nombre']}** — {c['capital']:,.0f} {c['divisa']}" + (f" · {c['broker']}" if c.get("broker") else "")):
            with st.form(f"editar_cuenta_{c['id']}"):
                cc1, cc2, cc3 = st.columns(3)
                with cc1:
                    nombre_c = st.text_input("Nombre", value=c["nombre"], key=f"n_{c['id']}")
                    broker_c = st.text_input("Broker", value=c.get("broker", "") or "", key=f"b_{c['id']}")
                with cc2:
                    capital_c = st.number_input("Capital", min_value=0.0, value=float(c["capital"]), step=100.0, format="%.2f", key=f"cap_{c['id']}")
                    divisa_c  = st.selectbox("Divisa", ["USD", "EUR", "GBP"],
                        index=["USD", "EUR", "GBP"].index(c.get("divisa", "USD")), key=f"div_{c['id']}")
                with cc3:
                    riesgo_c  = st.number_input("Riesgo base (%)", min_value=0.1, max_value=5.0,
                        value=float(c.get("riesgo_base", 1.0)), step=0.1, format="%.1f", key=f"r_{c['id']}")
                col_g, col_e = st.columns([3, 1])
                with col_g:
                    if st.form_submit_button("💾 Guardar", use_container_width=True, type="primary"):
                        if actualizar_cuenta(c["id"], {"nombre": nombre_c, "broker": broker_c, "capital": capital_c, "divisa": divisa_c, "riesgo_base": riesgo_c}):
                            st.success("✅ Cuenta actualizada.")
                            st.toast("✅ Cuenta actualizada", icon="✅")
                            st.rerun()
                        else:
                            st.error("❌ Error guardando.")
                with col_e:
                    if st.form_submit_button("🗑️ Eliminar", use_container_width=True):
                        if eliminar_cuenta(c["id"]):
                            st.warning("🗑️ Cuenta eliminada.")
                            st.toast("🗑️ Cuenta eliminada", icon="🗑️")
                            st.rerun()
                        else:
                            st.warning("No puedes eliminar la única cuenta.")

    # ─── Crear nueva cuenta ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Añadir nueva cuenta")
    with st.form("nueva_cuenta"):
        nc1, nc2, nc3 = st.columns(3)
        with nc1:
            new_nombre = st.text_input("Nombre *", placeholder="Prop Firm A")
            new_broker = st.text_input("Broker", placeholder="FTMO, MyForexFunds...")
        with nc2:
            new_capital = st.number_input("Capital *", min_value=0.0, value=10000.0, step=500.0, format="%.2f")
            new_divisa  = st.selectbox("Divisa", ["USD", "EUR", "GBP"])
        with nc3:
            new_riesgo  = st.number_input("Riesgo base (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1, format="%.1f")
        if st.form_submit_button("➕ Crear cuenta", use_container_width=True, type="primary"):
            if new_nombre.strip():
                crear_cuenta({"nombre": new_nombre.strip(), "broker": new_broker.strip(), "capital": new_capital, "divisa": new_divisa, "riesgo_base": new_riesgo})
                st.success(f"✅ Cuenta «{new_nombre}» creada correctamente.")
                st.toast(f"✅ Cuenta «{new_nombre}» creada", icon="✅")
                st.rerun()
            else:
                st.error("❌ El nombre es obligatorio.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: Perfil y cuenta
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Perfil del Trader")
    st.info("El capital, divisa y riesgo base se configuran por cuenta en la pestaña **Cuentas**.")

    with st.form("form_perfil"):
        nombre_trader = st.text_input("Nombre del trader", value=config.get("nombre_trader", "Trader"))
        guardar_perfil = st.form_submit_button("💾 Guardar", use_container_width=False, type="primary")

    if guardar_perfil:
        nuevos_datos = {
            "nombre_trader": nombre_trader,
            "tamanio_cuenta": config.get("tamanio_cuenta", 10000.0),
            "divisa": config.get("divisa", "USD"),
            "riesgo_base": config.get("riesgo_base", 1.0),
            "umbral_winrate_medio": config.get("umbral_winrate_medio", 60.0),
            "umbral_winrate_alto": config.get("umbral_winrate_alto", 70.0),
            "umbral_dd_conservador": config.get("umbral_dd_conservador", 5.0),
            "umbral_dd_reducido": config.get("umbral_dd_reducido", 8.0),
            "umbral_dd_minimo": config.get("umbral_dd_minimo", 12.0),
        }
        if actualizar_configuracion(nuevos_datos):
            st.success("✅ Nombre guardado correctamente.")
            st.toast("✅ Perfil guardado", icon="✅")
            st.rerun()
        else:
            st.error("❌ Error guardando.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: Motor de riesgo
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Parámetros del Motor de Riesgo")
    st.markdown("Ajusta los umbrales que determinan el comportamiento del motor de riesgo dinámico.")

    with st.form("form_riesgo"):
        st.markdown("#### Umbrales de Drawdown")
        col_dd1, col_dd2, col_dd3 = st.columns(3)

        with col_dd1:
            umbral_dd_conservador = st.slider(
                "DD Conservador (%)",
                min_value=1.0,
                max_value=15.0,
                value=float(config.get("umbral_dd_conservador", 5.0)),
                step=0.5,
                help="Por encima de este DD, riesgo se reduce al 0.75%",
            )

        with col_dd2:
            umbral_dd_reducido = st.slider(
                "DD Reducido (%)",
                min_value=1.0,
                max_value=20.0,
                value=float(config.get("umbral_dd_reducido", 8.0)),
                step=0.5,
                help="Por encima de este DD, riesgo se reduce al 0.5%",
            )

        with col_dd3:
            umbral_dd_minimo = st.slider(
                "DD Mínimo/Crítico (%)",
                min_value=5.0,
                max_value=30.0,
                value=float(config.get("umbral_dd_minimo", 12.0)),
                step=0.5,
                help="Por encima de este DD, riesgo se reduce al 0.25% (zona crítica)",
            )

        st.markdown("#### Umbrales de Winrate (últimas 10 operaciones)")
        col_wr1, col_wr2 = st.columns(2)

        with col_wr1:
            umbral_winrate_medio = st.slider(
                "Winrate para riesgo elevado (%)",
                min_value=40.0,
                max_value=80.0,
                value=float(config.get("umbral_winrate_medio", 60.0)),
                step=1.0,
                help="Por encima de este WR y con DD bajo, riesgo sube al 1.25%",
            )

        with col_wr2:
            umbral_winrate_alto = st.slider(
                "Winrate para riesgo máximo (%)",
                min_value=50.0,
                max_value=90.0,
                value=float(config.get("umbral_winrate_alto", 70.0)),
                step=1.0,
                help="Por encima de este WR y con DD muy bajo, riesgo sube al 1.5%",
            )

        # Validación
        if umbral_dd_conservador >= umbral_dd_reducido:
            st.warning("⚠️ El umbral conservador debe ser menor que el reducido.")
        if umbral_dd_reducido >= umbral_dd_minimo:
            st.warning("⚠️ El umbral reducido debe ser menor que el crítico.")
        if umbral_winrate_medio >= umbral_winrate_alto:
            st.warning("⚠️ El winrate medio debe ser menor que el alto.")

        guardar_riesgo = st.form_submit_button("💾 Guardar Parámetros de Riesgo", use_container_width=True, type="primary")

    if guardar_riesgo:
        nuevos_datos = {
            "nombre_trader": config.get("nombre_trader", "Trader"),
            "tamanio_cuenta": config.get("tamanio_cuenta", 10000.0),
            "divisa": config.get("divisa", "USD"),
            "riesgo_base": config.get("riesgo_base", 1.0),
            "umbral_winrate_medio": umbral_winrate_medio,
            "umbral_winrate_alto": umbral_winrate_alto,
            "umbral_dd_conservador": umbral_dd_conservador,
            "umbral_dd_reducido": umbral_dd_reducido,
            "umbral_dd_minimo": umbral_dd_minimo,
        }
        if actualizar_configuracion(nuevos_datos):
            st.success("✅ Parámetros del motor de riesgo guardados.")
            st.toast("✅ Parámetros guardados", icon="✅")
            st.rerun()
        else:
            st.error("❌ Error guardando los parámetros.")

    # Preview del motor
    st.markdown("---")
    st.markdown("#### Vista previa del motor con los parámetros actuales")
    config_actual = obtener_configuracion()
    st.markdown(f"""
    | Condición | Riesgo aplicado |
    |-----------|----------------|
    | DD > {config_actual.get('umbral_dd_minimo', 12)}% | 🚨 **0.25%** |
    | DD > {config_actual.get('umbral_dd_reducido', 8)}% | ⚠️ **0.50%** |
    | DD > {config_actual.get('umbral_dd_conservador', 5)}% | ⚠️ **0.75%** |
    | Pérdida día > 2% | ⚠️ **0.50%** |
    | Racha perdedora ≥ 3 | ⚠️ **{config_actual.get('riesgo_base', 1.0) * 0.75:.2f}%** |
    | Caso base | ℹ️ **{config_actual.get('riesgo_base', 1.0):.2f}%** |
    | WR-10 > {config_actual.get('umbral_winrate_medio', 60)}% y DD < {config_actual.get('umbral_dd_conservador', 5)}% | ✅ **1.25%** |
    | WR-10 > {config_actual.get('umbral_winrate_alto', 70)}% y DD < 3% | ✅ **1.50%** |
    """)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: Gestión de pares
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Gestión de Pares de Trading")

    pares_actuales = load_pares()

    col_pares1, col_pares2 = st.columns([2, 1])

    with col_pares1:
        st.markdown("#### Pares cargados desde pares.txt")
        for categoria, lista in pares_actuales.items():
            with st.expander(f"**{categoria}** ({len(lista)} pares)"):
                st.markdown(", ".join(f"`{p}`" for p in lista))

    with col_pares2:
        st.markdown("#### Añadir par personalizado")
        st.markdown("Para añadir pares permanentemente, edita el archivo `pares.txt` en la raíz del proyecto.")
        st.markdown("Formato:")
        st.code("""[CATEGORIA]
EURUSD
GBPUSD""", language="text")

        # Añadir par en sesión (no persiste)
        st.markdown("**Añadir par temporalmente (sesión actual):**")
        nueva_categoria = st.text_input("Categoría", placeholder="FOREX")
        nuevo_par = st.text_input("Par", placeholder="EURUSD")

        if st.button("➕ Añadir par", use_container_width=True):
            if nueva_categoria and nuevo_par:
                # Añadir al archivo pares.txt
                try:
                    with open(PARES_PATH, "a", encoding="utf-8") as f:
                        # Comprobar si la categoría ya existe
                        with open(PARES_PATH, "r", encoding="utf-8") as fr:
                            contenido = fr.read()
                        if f"[{nueva_categoria.upper()}]" not in contenido:
                            f.write(f"\n[{nueva_categoria.upper()}]\n{nuevo_par.upper()}\n")
                        else:
                            # La categoría existe, añadir el par después de la última línea de esa categoría
                            f.write(f"{nuevo_par.upper()}\n")
                    st.success(f"✅ Par `{nuevo_par.upper()}` añadido a la categoría `{nueva_categoria.upper()}`.")
                    st.toast(f"✅ Par {nuevo_par.upper()} añadido", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error añadiendo el par: {e}")
            else:
                st.warning("Completa la categoría y el par.")

    # Mostrar ruta del archivo
    st.markdown("---")
    st.info(f"📁 Archivo de pares: `{PARES_PATH}`")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: Estrategias (motor unificado backtest + real)
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Gestión de Estrategias")
    st.caption(
        "Las estrategias se comparten entre el registro real (Nuevo Trade) y el Backtester. "
        "Las condiciones que definas aquí aparecerán como checkboxes en ambas pantallas."
    )

    estrategias_all = obtener_estrategias(solo_activas=False)

    for est in estrategias_all:
        conteo = contar_trades_estrategia(est["id"])
        badge_act = "🟢 activa" if est["activa"] else "⚫ inactiva"
        header = (
            f"**{est['nombre']}** · {est['tipo']} · "
            f"{conteo['total']} trades ({conteo['real']} real / {conteo['backtest']} backtest) · {badge_act}"
        )
        with st.expander(header):
            # Edición de la estrategia
            with st.form(f"edit_strat_{est['id']}"):
                ec1, ec2, ec3, ec4 = st.columns([2, 1, 1, 2])
                with ec1:
                    e_nombre = st.text_input("Nombre", value=est["nombre"], key=f"e_n_{est['id']}")
                with ec2:
                    e_tipo = st.radio(
                        "Tipo",
                        ["DAY", "SCALPING"],
                        index=0 if est["tipo"] == "DAY" else 1,
                        horizontal=True,
                        key=f"e_t_{est['id']}",
                    )
                with ec3:
                    e_color = st.color_picker("Color", value=est.get("color") or "#58a6ff", key=f"e_c_{est['id']}")
                with ec4:
                    e_desc = st.text_input("Descripción", value=est.get("descripcion") or "", key=f"e_d_{est['id']}")
                e_activa = st.checkbox("Activa (visible en dropdowns)", value=bool(est["activa"]), key=f"e_a_{est['id']}")
                cb1, cb2 = st.columns([3, 1])
                with cb1:
                    if st.form_submit_button("💾 Guardar cambios", type="primary"):
                        if not e_nombre.strip():
                            st.error("❌ El nombre es obligatorio.")
                        else:
                            actualizar_estrategia(est["id"], {
                                "nombre": e_nombre.strip(),
                                "tipo": e_tipo,
                                "descripcion": e_desc,
                                "color": e_color,
                                "activa": int(e_activa),
                            })
                            st.success("✅ Estrategia actualizada.")
                            st.toast("✅ Estrategia actualizada", icon="✅")
                            st.rerun()
                with cb2:
                    if st.form_submit_button("🗑️ Eliminar"):
                        if eliminar_estrategia(est["id"]):
                            st.warning("🗑️ Estrategia eliminada.")
                            st.toast("🗑️ Estrategia eliminada", icon="🗑️")
                            st.rerun()
                        else:
                            st.error(
                                f"❌ No se puede eliminar: tiene {conteo['total']} trades asociados. "
                                "Desactívala en su lugar."
                            )

            # Gestión de condiciones
            st.markdown("##### Condiciones")
            condiciones = obtener_condiciones(est["id"], solo_activas=False)
            if not condiciones:
                st.caption("Esta estrategia aún no tiene condiciones.")
            else:
                for cond in condiciones:
                    cc1, cc2, cc3, cc4, cc5 = st.columns([5, 0.6, 0.6, 0.8, 0.8])
                    with cc1:
                        nuevo_nombre = st.text_input(
                            "Nombre",
                            value=cond["nombre"],
                            key=f"cn_{cond['id']}",
                            label_visibility="collapsed",
                        )
                        if nuevo_nombre != cond["nombre"]:
                            actualizar_condicion(cond["id"], nombre=nuevo_nombre)
                    with cc2:
                        if st.button("⬆️", key=f"up_{cond['id']}", help="Subir"):
                            reordenar_condiciones(est["id"], cond["id"], -1)
                            st.toast("✅ Orden actualizado", icon="✅")
                            st.rerun()
                    with cc3:
                        if st.button("⬇️", key=f"dn_{cond['id']}", help="Bajar"):
                            reordenar_condiciones(est["id"], cond["id"], +1)
                            st.toast("✅ Orden actualizado", icon="✅")
                            st.rerun()
                    with cc4:
                        act = st.checkbox("Activa", value=bool(cond["activa"]), key=f"ac_{cond['id']}")
                        if int(act) != int(cond["activa"]):
                            actualizar_condicion(cond["id"], activa=int(act))
                            st.toast("✅ Condición actualizada", icon="✅")
                            st.rerun()
                    with cc5:
                        if st.button("🗑️", key=f"del_{cond['id']}", help="Eliminar"):
                            eliminar_condicion(cond["id"])
                            st.toast("🗑️ Condición eliminada", icon="🗑️")
                            st.rerun()

            # Añadir nueva condición
            with st.form(f"add_cond_{est['id']}", clear_on_submit=True):
                ac1, ac2 = st.columns([4, 1])
                with ac1:
                    nueva_cond = st.text_input(
                        "Nueva condición",
                        placeholder="Ej: HTF en zona S/R importante",
                        key=f"nuevac_{est['id']}",
                        label_visibility="collapsed",
                    )
                with ac2:
                    if st.form_submit_button("➕ Añadir"):
                        if nueva_cond.strip():
                            crear_condicion(est["id"], nueva_cond.strip())
                            st.toast("✅ Condición añadida", icon="✅")
                            st.rerun()

    # ─── Crear nueva estrategia ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Crear nueva estrategia")
    with st.form("nueva_estrategia_cfg"):
        ns1, ns2, ns3, ns4 = st.columns([2, 1, 1, 2])
        with ns1:
            ns_nombre = st.text_input("Nombre *", placeholder="Mi estrategia")
        with ns2:
            ns_tipo = st.radio("Tipo *", ["DAY", "SCALPING"], horizontal=True)
        with ns3:
            ns_color = st.color_picker("Color", value="#58a6ff")
        with ns4:
            ns_desc = st.text_input("Descripción", placeholder="Resumen breve")
        if st.form_submit_button("➕ Crear estrategia", type="primary"):
            if not ns_nombre.strip():
                st.error("❌ El nombre es obligatorio.")
            else:
                try:
                    crear_estrategia(ns_nombre.strip(), ns_tipo, ns_desc, ns_color)
                    st.success(f"✅ Estrategia «{ns_nombre}» creada.")
                    st.toast(f"✅ Estrategia «{ns_nombre}» creada", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}. ¿Quizás el nombre ya existe?")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6: Backup y Reseteo
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.subheader("Backup y Restauración de Datos")

    col_b1, col_b2 = st.columns(2)

    with col_b1:
        st.markdown("#### 📤 Exportar todo a JSON")
        st.markdown("Exporta todos los trades, configuración y snapshots de equity en un único archivo JSON.")

        if st.button("📥 Generar exportación", use_container_width=True, type="primary"):
            try:
                json_data = exportar_todo_json()
                st.download_button(
                    label="⬇️ Descargar JSON",
                    data=json_data.encode("utf-8"),
                    file_name=f"trading_journal_backup_{date.today().isoformat()}.json",
                    mime="application/json",
                    use_container_width=True,
                )
                st.success("✅ Exportación lista para descargar.")
                st.toast("✅ Exportación generada", icon="✅")
            except Exception as e:
                st.error(f"❌ Error generando la exportación: {e}")

    with col_b2:
        st.markdown("#### 📥 Importar desde JSON")
        st.markdown("Importa datos desde un archivo JSON exportado previamente.")

        archivo_importar = st.file_uploader(
            "Selecciona el archivo JSON",
            type=["json"],
        )

        if archivo_importar is not None:
            if st.button("📤 Importar datos", use_container_width=True):
                try:
                    json_str = archivo_importar.read().decode("utf-8")
                    if importar_desde_json(json_str):
                        st.success("✅ Datos importados correctamente.")
                        st.toast("✅ Datos importados", icon="✅")
                        st.rerun()
                    else:
                        st.error("❌ Error importando los datos.")
                except Exception as e:
                    st.error(f"❌ Error procesando el archivo: {e}")

    st.markdown("---")

    # ─── Zona de peligro ─────────────────────────────────────────────────────
    st.subheader("⚠️ Zona de Peligro")
    st.markdown("Las siguientes acciones son **irreversibles**.")

    with st.expander("🗑️ Resetear base de datos", expanded=False):
        st.error("**ADVERTENCIA:** Esta acción eliminará TODOS los trades y snapshots de equity. La configuración se mantendrá.")

        confirm1 = st.checkbox("Entiendo que esta acción es irreversible y eliminará todos mis trades")
        confirm2 = st.text_input("Escribe 'CONFIRMAR RESET' para habilitar el botón:")

        if st.button(
            "💥 RESETEAR BASE DE DATOS",
            use_container_width=True,
            disabled=not (confirm1 and confirm2 == "CONFIRMAR RESET"),
        ):
            if confirm1 and confirm2 == "CONFIRMAR RESET":
                if resetear_base_datos():
                    st.warning("🗑️ Base de datos reseteada. Todos los trades han sido eliminados.")
                    st.toast("🗑️ Base de datos reseteada", icon="🗑️")
                    st.rerun()
                else:
                    st.error("❌ Error reseteando la base de datos.")
