"""
Módulo de base de datos: toda la lógica SQLite y operaciones CRUD
para Trading Journal Pro.
"""

import sqlite3
import os
import json
from datetime import datetime, date
from typing import Optional

# Ruta absoluta a la base de datos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "trades.db")
PARES_PATH = os.path.join(BASE_DIR, "pares.txt")


def get_connection() -> sqlite3.Connection:
    """Devuelve una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_db():
    """Crea las tablas si no existen e inserta configuración por defecto."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Tabla principal de trades
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_entrada TEXT,
                hora_entrada TEXT,
                fecha_salida TEXT,
                hora_salida TEXT,
                par TEXT,
                direccion TEXT,
                estrategia TEXT,
                tipo_operacion TEXT,
                timeframe_entrada TEXT,
                precio_entrada REAL,
                stop_loss REAL,
                tp1 REAL,
                tp2 REAL,
                rr_planificado REAL,
                trailing_stop INTEGER DEFAULT 0,
                trailing_base TEXT,
                sl_breakeven INTEGER DEFAULT 0,
                cierre_parcial INTEGER DEFAULT 0,
                porcentaje_cierre_parcial REAL,
                resultado TEXT,
                pips_resultado REAL,
                porcentaje_cuenta REAL,
                importe_dinero REAL,
                sesion TEXT,
                condicion_mercado TEXT,
                rr_conseguido REAL,
                notas TEXT,
                screenshot_path TEXT
            )
        """)

        # Tabla de configuración (una sola fila)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracion (
                id INTEGER PRIMARY KEY,
                nombre_trader TEXT DEFAULT 'Trader',
                tamanio_cuenta REAL DEFAULT 10000.0,
                divisa TEXT DEFAULT 'USD',
                riesgo_base REAL DEFAULT 1.0,
                umbral_winrate_medio REAL DEFAULT 60.0,
                umbral_winrate_alto REAL DEFAULT 70.0,
                umbral_dd_conservador REAL DEFAULT 5.0,
                umbral_dd_reducido REAL DEFAULT 8.0,
                umbral_dd_minimo REAL DEFAULT 12.0
            )
        """)

        # Tabla de snapshots de equity
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshots_equity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                equity REAL
            )
        """)

        # Insertar configuración por defecto si no existe
        cursor.execute("SELECT COUNT(*) FROM configuracion")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO configuracion (id, nombre_trader, tamanio_cuenta, divisa,
                    riesgo_base, umbral_winrate_medio, umbral_winrate_alto,
                    umbral_dd_conservador, umbral_dd_reducido, umbral_dd_minimo)
                VALUES (1, 'Trader', 10000.0, 'USD', 1.0, 60.0, 70.0, 5.0, 8.0, 12.0)
            """)

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error inicializando base de datos: {e}")
        raise


# ─── TRADES ───────────────────────────────────────────────────────────────────

def insertar_trade(datos: dict) -> int:
    """Inserta un nuevo trade y devuelve el ID generado."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO trades (
                fecha_entrada, hora_entrada, fecha_salida, hora_salida,
                par, direccion, estrategia, tipo_operacion, timeframe_entrada,
                precio_entrada, stop_loss, tp1, tp2, rr_planificado,
                trailing_stop, trailing_base, sl_breakeven,
                cierre_parcial, porcentaje_cierre_parcial,
                resultado, pips_resultado, porcentaje_cuenta, importe_dinero,
                sesion, condicion_mercado, rr_conseguido, notas, screenshot_path
            ) VALUES (
                :fecha_entrada, :hora_entrada, :fecha_salida, :hora_salida,
                :par, :direccion, :estrategia, :tipo_operacion, :timeframe_entrada,
                :precio_entrada, :stop_loss, :tp1, :tp2, :rr_planificado,
                :trailing_stop, :trailing_base, :sl_breakeven,
                :cierre_parcial, :porcentaje_cierre_parcial,
                :resultado, :pips_resultado, :porcentaje_cuenta, :importe_dinero,
                :sesion, :condicion_mercado, :rr_conseguido, :notas, :screenshot_path
            )
        """, datos)
        nuevo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return nuevo_id
    except Exception as e:
        print(f"Error insertando trade: {e}")
        raise


def obtener_todos_los_trades() -> list:
    """Devuelve todos los trades como lista de diccionarios."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trades ORDER BY fecha_entrada DESC, hora_entrada DESC")
        filas = [dict(fila) for fila in cursor.fetchall()]
        conn.close()
        return filas
    except Exception as e:
        print(f"Error obteniendo trades: {e}")
        return []


def obtener_trade_por_id(trade_id: int) -> Optional[dict]:
    """Devuelve un trade por su ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
        fila = cursor.fetchone()
        conn.close()
        return dict(fila) if fila else None
    except Exception as e:
        print(f"Error obteniendo trade {trade_id}: {e}")
        return None


def actualizar_trade(trade_id: int, datos: dict) -> bool:
    """Actualiza un trade existente. Devuelve True si tuvo éxito."""
    try:
        datos["id"] = trade_id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE trades SET
                fecha_entrada = :fecha_entrada,
                hora_entrada = :hora_entrada,
                fecha_salida = :fecha_salida,
                hora_salida = :hora_salida,
                par = :par,
                direccion = :direccion,
                estrategia = :estrategia,
                tipo_operacion = :tipo_operacion,
                timeframe_entrada = :timeframe_entrada,
                precio_entrada = :precio_entrada,
                stop_loss = :stop_loss,
                tp1 = :tp1,
                tp2 = :tp2,
                rr_planificado = :rr_planificado,
                trailing_stop = :trailing_stop,
                trailing_base = :trailing_base,
                sl_breakeven = :sl_breakeven,
                cierre_parcial = :cierre_parcial,
                porcentaje_cierre_parcial = :porcentaje_cierre_parcial,
                resultado = :resultado,
                pips_resultado = :pips_resultado,
                porcentaje_cuenta = :porcentaje_cuenta,
                importe_dinero = :importe_dinero,
                sesion = :sesion,
                condicion_mercado = :condicion_mercado,
                rr_conseguido = :rr_conseguido,
                notas = :notas,
                screenshot_path = :screenshot_path
            WHERE id = :id
        """, datos)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando trade {trade_id}: {e}")
        return False


def eliminar_trade(trade_id: int) -> bool:
    """Elimina un trade por ID. Devuelve True si tuvo éxito."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando trade {trade_id}: {e}")
        return False


def obtener_trades_por_fecha(fecha_inicio: str, fecha_fin: str) -> list:
    """Devuelve trades filtrados por rango de fechas."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM trades
            WHERE fecha_entrada BETWEEN ? AND ?
            ORDER BY fecha_entrada DESC, hora_entrada DESC
        """, (fecha_inicio, fecha_fin))
        filas = [dict(fila) for fila in cursor.fetchall()]
        conn.close()
        return filas
    except Exception as e:
        print(f"Error obteniendo trades por fecha: {e}")
        return []


def obtener_ultimos_trades(n: int = 10) -> list:
    """Devuelve los últimos N trades."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM trades
            ORDER BY fecha_entrada DESC, hora_entrada DESC
            LIMIT ?
        """, (n,))
        filas = [dict(fila) for fila in cursor.fetchall()]
        conn.close()
        return filas
    except Exception as e:
        print(f"Error obteniendo últimos trades: {e}")
        return []


# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────

def obtener_configuracion() -> dict:
    """Devuelve la configuración actual."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM configuracion WHERE id = 1")
        fila = cursor.fetchone()
        conn.close()
        if fila:
            return dict(fila)
        return {}
    except Exception as e:
        print(f"Error obteniendo configuración: {e}")
        return {}


def actualizar_configuracion(datos: dict) -> bool:
    """Actualiza la configuración. Devuelve True si tuvo éxito."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE configuracion SET
                nombre_trader = :nombre_trader,
                tamanio_cuenta = :tamanio_cuenta,
                divisa = :divisa,
                riesgo_base = :riesgo_base,
                umbral_winrate_medio = :umbral_winrate_medio,
                umbral_winrate_alto = :umbral_winrate_alto,
                umbral_dd_conservador = :umbral_dd_conservador,
                umbral_dd_reducido = :umbral_dd_reducido,
                umbral_dd_minimo = :umbral_dd_minimo
            WHERE id = 1
        """, datos)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando configuración: {e}")
        return False


# ─── SNAPSHOTS DE EQUITY ──────────────────────────────────────────────────────

def insertar_snapshot_equity(fecha: str, equity: float) -> bool:
    """Inserta un snapshot de equity."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO snapshots_equity (fecha, equity) VALUES (?, ?)",
            (fecha, equity)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error insertando snapshot de equity: {e}")
        return False


def obtener_snapshots_equity(dias: int = 30) -> list:
    """Devuelve los snapshots de equity de los últimos N días."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM snapshots_equity
            ORDER BY fecha DESC
            LIMIT ?
        """, (dias,))
        filas = [dict(fila) for fila in cursor.fetchall()]
        conn.close()
        return list(reversed(filas))
    except Exception as e:
        print(f"Error obteniendo snapshots: {e}")
        return []


def obtener_todos_snapshots_equity() -> list:
    """Devuelve todos los snapshots de equity ordenados por fecha."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM snapshots_equity ORDER BY fecha ASC")
        filas = [dict(fila) for fila in cursor.fetchall()]
        conn.close()
        return filas
    except Exception as e:
        print(f"Error obteniendo todos los snapshots: {e}")
        return []


# ─── PARES ────────────────────────────────────────────────────────────────────

def load_pares() -> dict:
    """
    Lee pares.txt y devuelve un diccionario {categoria: [lista_de_pares]}.
    Formato esperado del archivo:
        [FOREX]
        EURUSD
        [METALES]
        XAUUSD
    """
    pares = {}
    categoria_actual = "OTROS"

    if not os.path.exists(PARES_PATH):
        # Pares por defecto si no existe el archivo
        return {
            "FOREX": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"],
            "METALES": ["XAUUSD", "XAGUSD"],
            "INDICES": ["NAS100", "US500", "GER40"],
        }

    try:
        with open(PARES_PATH, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#"):
                    continue
                if linea.startswith("[") and linea.endswith("]"):
                    categoria_actual = linea[1:-1].strip().upper()
                    if categoria_actual not in pares:
                        pares[categoria_actual] = []
                elif linea:
                    if categoria_actual not in pares:
                        pares[categoria_actual] = []
                    pares[categoria_actual].append(linea)
    except Exception as e:
        print(f"Error leyendo pares.txt: {e}")
        return {"FOREX": ["EURUSD", "GBPUSD", "XAUUSD"]}

    return pares


def get_lista_pares_plana() -> list:
    """Devuelve todos los pares como una lista plana."""
    pares_dict = load_pares()
    lista = []
    for categoria, pares in pares_dict.items():
        for par in pares:
            lista.append(par)
    return lista


# ─── BACKUP / RESTORE ─────────────────────────────────────────────────────────

def exportar_todo_json() -> str:
    """Exporta toda la base de datos a un JSON."""
    try:
        trades = obtener_todos_los_trades()
        config = obtener_configuracion()
        snapshots = obtener_todos_snapshots_equity()
        datos = {
            "exportado_en": datetime.now().isoformat(),
            "trades": trades,
            "configuracion": config,
            "snapshots_equity": snapshots,
        }
        return json.dumps(datos, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        print(f"Error exportando a JSON: {e}")
        return "{}"


def importar_desde_json(json_str: str) -> bool:
    """Importa datos desde un JSON exportado previamente."""
    try:
        datos = json.loads(json_str)
        conn = get_connection()
        cursor = conn.cursor()

        # Importar trades
        if "trades" in datos:
            for trade in datos["trades"]:
                trade.pop("id", None)
                columnas = ", ".join(trade.keys())
                placeholders = ", ".join(["?" for _ in trade])
                cursor.execute(
                    f"INSERT OR IGNORE INTO trades ({columnas}) VALUES ({placeholders})",
                    list(trade.values())
                )

        # Importar configuración
        if "configuracion" in datos and datos["configuracion"]:
            cfg = datos["configuracion"]
            cursor.execute("""
                UPDATE configuracion SET
                    nombre_trader = ?, tamanio_cuenta = ?, divisa = ?,
                    riesgo_base = ?, umbral_winrate_medio = ?, umbral_winrate_alto = ?,
                    umbral_dd_conservador = ?, umbral_dd_reducido = ?, umbral_dd_minimo = ?
                WHERE id = 1
            """, (
                cfg.get("nombre_trader", "Trader"),
                cfg.get("tamanio_cuenta", 10000.0),
                cfg.get("divisa", "USD"),
                cfg.get("riesgo_base", 1.0),
                cfg.get("umbral_winrate_medio", 60.0),
                cfg.get("umbral_winrate_alto", 70.0),
                cfg.get("umbral_dd_conservador", 5.0),
                cfg.get("umbral_dd_reducido", 8.0),
                cfg.get("umbral_dd_minimo", 12.0),
            ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error importando desde JSON: {e}")
        return False


def resetear_base_datos() -> bool:
    """Elimina todos los datos de trades y snapshots (mantiene configuración)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trades")
        cursor.execute("DELETE FROM snapshots_equity")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error reseteando base de datos: {e}")
        return False
