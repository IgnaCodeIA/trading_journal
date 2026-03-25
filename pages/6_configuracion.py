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
    PARES_PATH,
    BASE_DIR,
)

st.set_page_config(page_title="Configuración — Trading Journal Pro", layout="wide")

# CSS
css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("⚙️ Configuración")
st.markdown("---")

config = obtener_configuracion()

# ─── Tabs de configuración ─────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "👤 Perfil y Cuenta",
    "📊 Motor de Riesgo",
    "📁 Pares",
    "💾 Backup y Reseteo",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: Perfil y cuenta
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Datos del Trader")

    with st.form("form_perfil"):
        col1, col2 = st.columns(2)

        with col1:
            nombre_trader = st.text_input(
                "Nombre del trader",
                value=config.get("nombre_trader", "Trader"),
            )
            tamanio_cuenta = st.number_input(
                "Tamaño de cuenta",
                min_value=0.0,
                value=float(config.get("tamanio_cuenta", 10000.0)),
                step=100.0,
                format="%.2f",
                help="Capital total de la cuenta de trading",
            )

        with col2:
            divisa = st.selectbox(
                "Divisa de la cuenta",
                options=["USD", "EUR", "GBP"],
                index=["USD", "EUR", "GBP"].index(config.get("divisa", "USD")),
            )
            riesgo_base = st.number_input(
                "Riesgo base por operación (%)",
                min_value=0.1,
                max_value=5.0,
                value=float(config.get("riesgo_base", 1.0)),
                step=0.1,
                format="%.1f",
                help="Porcentaje de la cuenta a arriesgar en condiciones normales",
            )

        guardar_perfil = st.form_submit_button("💾 Guardar Configuración", use_container_width=True, type="primary")

    if guardar_perfil:
        nuevos_datos = {
            "nombre_trader": nombre_trader,
            "tamanio_cuenta": tamanio_cuenta,
            "divisa": divisa,
            "riesgo_base": riesgo_base,
            "umbral_winrate_medio": config.get("umbral_winrate_medio", 60.0),
            "umbral_winrate_alto": config.get("umbral_winrate_alto", 70.0),
            "umbral_dd_conservador": config.get("umbral_dd_conservador", 5.0),
            "umbral_dd_reducido": config.get("umbral_dd_reducido", 8.0),
            "umbral_dd_minimo": config.get("umbral_dd_minimo", 12.0),
        }
        if actualizar_configuracion(nuevos_datos):
            st.success("✅ Configuración de perfil guardada correctamente.")
            st.rerun()
        else:
            st.error("❌ Error guardando la configuración.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: Motor de riesgo
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
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
# TAB 3: Gestión de pares
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
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
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error añadiendo el par: {e}")
            else:
                st.warning("Completa la categoría y el par.")

    # Mostrar ruta del archivo
    st.markdown("---")
    st.info(f"📁 Archivo de pares: `{PARES_PATH}`")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: Backup y Reseteo
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
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
                    st.success("✅ Base de datos reseteada. Todos los trades han sido eliminados.")
                    st.rerun()
                else:
                    st.error("❌ Error reseteando la base de datos.")
