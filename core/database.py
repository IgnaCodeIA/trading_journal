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
                screenshot_path TEXT,
                analisis_asr TEXT
            )
        """)

        # Tabla de cuentas (multi-cuenta)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cuentas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL DEFAULT 'Cuenta Principal',
                broker TEXT DEFAULT '',
                capital REAL DEFAULT 10000.0,
                divisa TEXT DEFAULT 'USD',
                riesgo_base REAL DEFAULT 1.0,
                activa INTEGER DEFAULT 1,
                fecha_creacion TEXT
            )
        """)

        # Migraciones: columnas que pueden no existir en instancias antiguas
        for migration in [
            "ALTER TABLE trades ADD COLUMN analisis_asr TEXT",
            "ALTER TABLE trades ADD COLUMN cuenta_id INTEGER DEFAULT 1",
            "ALTER TABLE trades ADD COLUMN strategy_conditions TEXT",
            "ALTER TABLE trades ADD COLUMN operativa_tipo TEXT",
            "ALTER TABLE trades ADD COLUMN strategy_id INTEGER",
        ]:
            try:
                cursor.execute(migration)
            except Exception:
                pass

        # Crear cuenta por defecto a partir de la configuración existente si no hay ninguna
        cursor.execute("SELECT COUNT(*) FROM cuentas")
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT tamanio_cuenta, divisa, riesgo_base FROM configuracion WHERE id = 1")
            cfg = cursor.fetchone()
            capital_def = float(cfg["tamanio_cuenta"]) if cfg and cfg["tamanio_cuenta"] else 10000.0
            divisa_def  = cfg["divisa"] if cfg and cfg["divisa"] else "USD"
            riesgo_def  = float(cfg["riesgo_base"]) if cfg and cfg["riesgo_base"] else 1.0
            cursor.execute("""
                INSERT INTO cuentas (nombre, broker, capital, divisa, riesgo_base, activa, fecha_creacion)
                VALUES ('Cuenta Principal', '', ?, ?, ?, 1, ?)
            """, (capital_def, divisa_def, riesgo_def, datetime.now().isoformat()))

        # Tabla de imágenes adjuntas por trade (múltiples por operación)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_imagenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER NOT NULL,
                imagen_path TEXT NOT NULL,
                orden INTEGER DEFAULT 0,
                FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE
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

        # ─── Tabla: strategies ────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                tipo TEXT DEFAULT 'DAY',
                descripcion TEXT,
                color TEXT DEFAULT '#58a6ff',
                activa INTEGER DEFAULT 1,
                fecha_creacion TEXT
            )
        """)

        # ─── Tabla: strategy_conditions ───────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_conditions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                orden INTEGER DEFAULT 0,
                activa INTEGER DEFAULT 1,
                FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE
            )
        """)

        # ─── Tabla: backtest_trades ───────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER NOT NULL,
                fecha TEXT,
                instrumento TEXT,
                direccion TEXT,
                resultado TEXT,
                rr REAL,
                condiciones TEXT,
                notas TEXT,
                screenshot_path TEXT,
                FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE
            )
        """)

        # Migración: añadir analisis_asr a backtest_trades si no existe
        try:
            cursor.execute("ALTER TABLE backtest_trades ADD COLUMN analisis_asr TEXT")
        except Exception:
            pass
        # Migración: añadir operativa_tipo a backtest_trades si no existe
        try:
            cursor.execute("ALTER TABLE backtest_trades ADD COLUMN operativa_tipo TEXT")
        except Exception:
            pass

        # ─── Tabla: backtest_imagenes (múltiples capturas por trade backtest) ─
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_imagenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_trade_id INTEGER NOT NULL,
                imagen_path TEXT NOT NULL,
                orden INTEGER DEFAULT 0,
                FOREIGN KEY (backtest_trade_id) REFERENCES backtest_trades(id)
                    ON DELETE CASCADE
            )
        """)

        # ─── Seed inicial de estrategias si la tabla está vacía ───────────
        cursor.execute("SELECT COUNT(*) FROM strategies")
        if cursor.fetchone()[0] == 0:
            ahora = datetime.now().isoformat()
            seed_strategies = [
                ("Black", "DAY", "Estrategia base día (HTF + confluencias)", "#8b949e"),
                ("Blue",  "DAY", "", "#58a6ff"),
                ("Red",   "DAY", "", "#f85149"),
                ("Pink",  "SCALPING", "", "#ff7eb6"),
                ("White", "SCALPING", "", "#c9d1d9"),
                ("Green", "DAY", "", "#3fb950"),
            ]
            for nombre, tipo, desc, color in seed_strategies:
                cursor.execute("""
                    INSERT INTO strategies (nombre, tipo, descripcion, color, activa, fecha_creacion)
                    VALUES (?, ?, ?, ?, 1, ?)
                """, (nombre, tipo, desc, color, ahora))

            # Condiciones por defecto para Black
            cursor.execute("SELECT id FROM strategies WHERE nombre = 'Black'")
            black_row = cursor.fetchone()
            if black_row:
                black_id = black_row["id"]
                black_conds = [
                    "HTF en zona S/R importante (máx/mín HTF)",
                    "Sobrecompra/sobreventa en 4H o 15min",
                    "Acumulación en 4H/15min",
                    "Patrón 1H o 5min por debajo del patrón",
                    "TP en máximos/mínimos de la M15",
                    "Divergencia MACD",
                    "Doble techo / doble suelo en 5min o 1H",
                ]
                for orden, cond in enumerate(black_conds):
                    cursor.execute("""
                        INSERT INTO strategy_conditions (strategy_id, nombre, orden, activa)
                        VALUES (?, ?, ?, 1)
                    """, (black_id, cond, orden))

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
        params = {
            **datos,
            "cuenta_id": datos.get("cuenta_id", 1),
            "strategy_conditions": datos.get("strategy_conditions"),
            "operativa_tipo": datos.get("operativa_tipo"),
            "strategy_id": datos.get("strategy_id"),
        }
        cursor.execute("""
            INSERT INTO trades (
                fecha_entrada, hora_entrada, fecha_salida, hora_salida,
                par, direccion, estrategia, tipo_operacion, timeframe_entrada,
                precio_entrada, stop_loss, tp1, tp2, rr_planificado,
                trailing_stop, trailing_base, sl_breakeven,
                cierre_parcial, porcentaje_cierre_parcial,
                resultado, pips_resultado, porcentaje_cuenta, importe_dinero,
                sesion, condicion_mercado, rr_conseguido, notas, screenshot_path,
                analisis_asr, cuenta_id,
                strategy_conditions, operativa_tipo, strategy_id
            ) VALUES (
                :fecha_entrada, :hora_entrada, :fecha_salida, :hora_salida,
                :par, :direccion, :estrategia, :tipo_operacion, :timeframe_entrada,
                :precio_entrada, :stop_loss, :tp1, :tp2, :rr_planificado,
                :trailing_stop, :trailing_base, :sl_breakeven,
                :cierre_parcial, :porcentaje_cierre_parcial,
                :resultado, :pips_resultado, :porcentaje_cuenta, :importe_dinero,
                :sesion, :condicion_mercado, :rr_conseguido, :notas, :screenshot_path,
                :analisis_asr, :cuenta_id,
                :strategy_conditions, :operativa_tipo, :strategy_id
            )
        """, params)
        nuevo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return nuevo_id
    except Exception as e:
        print(f"Error insertando trade: {e}")
        raise


def obtener_todos_los_trades(cuenta_id: int = None) -> list:
    """Devuelve todos los trades. Si cuenta_id se especifica, filtra por esa cuenta."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if cuenta_id is not None:
            cursor.execute(
                "SELECT * FROM trades WHERE cuenta_id = ? ORDER BY fecha_entrada DESC, hora_entrada DESC",
                (cuenta_id,)
            )
        else:
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
                screenshot_path = :screenshot_path,
                analisis_asr = :analisis_asr
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


def obtener_ultimos_trades(n: int = 10, cuenta_id: int = None) -> list:
    """Devuelve los últimos N trades, opcionalmente filtrados por cuenta."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if cuenta_id is not None:
            cursor.execute(
                "SELECT * FROM trades WHERE cuenta_id = ? ORDER BY fecha_entrada DESC, hora_entrada DESC LIMIT ?",
                (cuenta_id, n)
            )
        else:
            cursor.execute(
                "SELECT * FROM trades ORDER BY fecha_entrada DESC, hora_entrada DESC LIMIT ?",
                (n,)
            )
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


# ─── CUENTAS ──────────────────────────────────────────────────────────────────

def obtener_cuentas() -> list:
    """Devuelve todas las cuentas."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cuentas ORDER BY id ASC")
        filas = [dict(f) for f in cursor.fetchall()]
        conn.close()
        return filas
    except Exception as e:
        print(f"Error obteniendo cuentas: {e}")
        return []


def obtener_cuenta(cuenta_id: int) -> Optional[dict]:
    """Devuelve una cuenta por su ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cuentas WHERE id = ?", (cuenta_id,))
        fila = cursor.fetchone()
        conn.close()
        return dict(fila) if fila else None
    except Exception as e:
        print(f"Error obteniendo cuenta {cuenta_id}: {e}")
        return None


def crear_cuenta(datos: dict) -> int:
    """Crea una nueva cuenta. Devuelve el ID generado."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cuentas (nombre, broker, capital, divisa, riesgo_base, activa, fecha_creacion)
            VALUES (:nombre, :broker, :capital, :divisa, :riesgo_base, 1, :fecha_creacion)
        """, {**datos, "fecha_creacion": datetime.now().isoformat()})
        nuevo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return nuevo_id
    except Exception as e:
        print(f"Error creando cuenta: {e}")
        raise


def actualizar_cuenta(cuenta_id: int, datos: dict) -> bool:
    """Actualiza una cuenta existente."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE cuentas SET nombre = :nombre, broker = :broker, capital = :capital,
                divisa = :divisa, riesgo_base = :riesgo_base
            WHERE id = :id
        """, {**datos, "id": cuenta_id})
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando cuenta {cuenta_id}: {e}")
        return False


def eliminar_cuenta(cuenta_id: int) -> bool:
    """Elimina una cuenta (solo si no es la última)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cuentas")
        if cursor.fetchone()[0] <= 1:
            conn.close()
            return False  # No se puede eliminar la última cuenta
        cursor.execute("DELETE FROM cuentas WHERE id = ?", (cuenta_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando cuenta {cuenta_id}: {e}")
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


# ─── IMÁGENES POR TRADE ───────────────────────────────────────────────────────

def insertar_imagen_trade(trade_id: int, imagen_path: str, orden: int = 0) -> int:
    """Asocia una imagen a un trade. Devuelve el ID de la fila creada."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO trade_imagenes (trade_id, imagen_path, orden) VALUES (?, ?, ?)",
            (trade_id, imagen_path, orden),
        )
        nuevo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return nuevo_id
    except Exception as e:
        print(f"Error insertando imagen para trade {trade_id}: {e}")
        raise


def obtener_imagenes_trade(trade_id: int) -> list:
    """Devuelve la lista de imágenes de un trade ordenadas por 'orden'."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM trade_imagenes WHERE trade_id = ? ORDER BY orden ASC",
            (trade_id,),
        )
        filas = [dict(f) for f in cursor.fetchall()]
        conn.close()
        return filas
    except Exception as e:
        print(f"Error obteniendo imágenes del trade {trade_id}: {e}")
        return []


def eliminar_imagen_trade(imagen_id: int) -> bool:
    """Elimina una imagen por su ID de fila. Devuelve True si tuvo éxito."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Recuperar ruta para borrar el archivo físico opcionalmente
        cursor.execute("SELECT imagen_path FROM trade_imagenes WHERE id = ?", (imagen_id,))
        fila = cursor.fetchone()
        if fila:
            path = fila["imagen_path"]
            if os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        cursor.execute("DELETE FROM trade_imagenes WHERE id = ?", (imagen_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando imagen {imagen_id}: {e}")
        return False


def eliminar_todas_imagenes_trade(trade_id: int) -> bool:
    """Elimina todas las imágenes asociadas a un trade (archivos + registros)."""
    try:
        imagenes = obtener_imagenes_trade(trade_id)
        for img in imagenes:
            path = img.get("imagen_path", "")
            if path and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trade_imagenes WHERE trade_id = ?", (trade_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando imágenes del trade {trade_id}: {e}")
        return False


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


# ═════════════════════════════════════════════════════════════════════════════
# STRATEGIES (motor unificado backtest + real)
# ═════════════════════════════════════════════════════════════════════════════

def obtener_estrategias(solo_activas: bool = True, tipo: str = None) -> list:
    """Devuelve estrategias, opcionalmente filtradas por tipo (SCALPING|DAY)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        q = "SELECT * FROM strategies"
        condiciones = []
        params = []
        if solo_activas:
            condiciones.append("activa = 1")
        if tipo:
            condiciones.append("tipo = ?")
            params.append(tipo)
        if condiciones:
            q += " WHERE " + " AND ".join(condiciones)
        q += " ORDER BY id ASC"
        cursor.execute(q, params)
        filas = [dict(f) for f in cursor.fetchall()]
        conn.close()
        return filas
    except Exception as e:
        print(f"Error obteniendo estrategias: {e}")
        return []


def obtener_estrategia(strategy_id: int) -> Optional[dict]:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
        fila = cursor.fetchone()
        conn.close()
        return dict(fila) if fila else None
    except Exception as e:
        print(f"Error obteniendo estrategia {strategy_id}: {e}")
        return None


def obtener_estrategia_por_nombre(nombre: str) -> Optional[dict]:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM strategies WHERE nombre = ?", (nombre,))
        fila = cursor.fetchone()
        conn.close()
        return dict(fila) if fila else None
    except Exception as e:
        print(f"Error obteniendo estrategia por nombre: {e}")
        return None


def crear_estrategia(nombre: str, tipo: str = "DAY", descripcion: str = "",
                     color: str = "#58a6ff") -> int:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO strategies (nombre, tipo, descripcion, color, activa, fecha_creacion)
            VALUES (?, ?, ?, ?, 1, ?)
        """, (nombre.strip(), tipo, descripcion, color, datetime.now().isoformat()))
        nuevo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return nuevo_id
    except Exception as e:
        print(f"Error creando estrategia: {e}")
        raise


def actualizar_estrategia(strategy_id: int, datos: dict) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE strategies SET
                nombre = :nombre,
                tipo = :tipo,
                descripcion = :descripcion,
                color = :color,
                activa = :activa
            WHERE id = :id
        """, {**datos, "id": strategy_id})
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando estrategia {strategy_id}: {e}")
        return False


def contar_trades_estrategia(strategy_id: int) -> dict:
    """Cuenta trades reales y backtest asociados a una estrategia."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM backtest_trades WHERE strategy_id = ?", (strategy_id,))
        n_bt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM trades WHERE strategy_id = ?", (strategy_id,))
        n_real = cursor.fetchone()[0]
        conn.close()
        return {"backtest": n_bt, "real": n_real, "total": n_bt + n_real}
    except Exception as e:
        print(f"Error contando trades estrategia: {e}")
        return {"backtest": 0, "real": 0, "total": 0}


def eliminar_estrategia(strategy_id: int) -> bool:
    """Elimina una estrategia. Devuelve False si tiene trades asociados."""
    try:
        conteo = contar_trades_estrategia(strategy_id)
        if conteo["total"] > 0:
            return False
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM strategy_conditions WHERE strategy_id = ?", (strategy_id,))
        cursor.execute("DELETE FROM strategies WHERE id = ?", (strategy_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando estrategia {strategy_id}: {e}")
        return False


# ═════════════════════════════════════════════════════════════════════════════
# STRATEGY CONDITIONS
# ═════════════════════════════════════════════════════════════════════════════

def obtener_condiciones(strategy_id: int, solo_activas: bool = True) -> list:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if solo_activas:
            cursor.execute("""
                SELECT * FROM strategy_conditions
                WHERE strategy_id = ? AND activa = 1
                ORDER BY orden ASC, id ASC
            """, (strategy_id,))
        else:
            cursor.execute("""
                SELECT * FROM strategy_conditions
                WHERE strategy_id = ?
                ORDER BY orden ASC, id ASC
            """, (strategy_id,))
        filas = [dict(f) for f in cursor.fetchall()]
        conn.close()
        return filas
    except Exception as e:
        print(f"Error obteniendo condiciones de la estrategia {strategy_id}: {e}")
        return []


def crear_condicion(strategy_id: int, nombre: str, orden: int = None) -> int:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if orden is None:
            cursor.execute("SELECT COALESCE(MAX(orden), -1) + 1 FROM strategy_conditions WHERE strategy_id = ?", (strategy_id,))
            orden = cursor.fetchone()[0]
        cursor.execute("""
            INSERT INTO strategy_conditions (strategy_id, nombre, orden, activa)
            VALUES (?, ?, ?, 1)
        """, (strategy_id, nombre.strip(), orden))
        nuevo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return nuevo_id
    except Exception as e:
        print(f"Error creando condición: {e}")
        raise


def actualizar_condicion(condicion_id: int, nombre: str = None, orden: int = None,
                         activa: int = None) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        sets = []
        params = []
        if nombre is not None:
            sets.append("nombre = ?")
            params.append(nombre.strip())
        if orden is not None:
            sets.append("orden = ?")
            params.append(orden)
        if activa is not None:
            sets.append("activa = ?")
            params.append(int(activa))
        if not sets:
            conn.close()
            return True
        params.append(condicion_id)
        cursor.execute(f"UPDATE strategy_conditions SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando condición {condicion_id}: {e}")
        return False


def eliminar_condicion(condicion_id: int) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM strategy_conditions WHERE id = ?", (condicion_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando condición {condicion_id}: {e}")
        return False


def reordenar_condiciones(strategy_id: int, condicion_id: int, direccion: int) -> bool:
    """Mueve una condición arriba (-1) o abajo (+1) intercambiando 'orden' con la vecina."""
    try:
        conds = obtener_condiciones(strategy_id, solo_activas=False)
        idx = next((i for i, c in enumerate(conds) if c["id"] == condicion_id), None)
        if idx is None:
            return False
        nuevo_idx = idx + direccion
        if nuevo_idx < 0 or nuevo_idx >= len(conds):
            return False
        a = conds[idx]
        b = conds[nuevo_idx]
        actualizar_condicion(a["id"], orden=b["orden"])
        actualizar_condicion(b["id"], orden=a["orden"])
        return True
    except Exception as e:
        print(f"Error reordenando condición: {e}")
        return False


# ═════════════════════════════════════════════════════════════════════════════
# BACKTEST TRADES
# ═════════════════════════════════════════════════════════════════════════════

def insertar_backtest_trade(datos: dict) -> int:
    """Inserta un trade de backtest. Espera dict con strategy_id, fecha, instrumento,
    direccion, resultado, rr, condiciones (JSON), notas, screenshot_path,
    y opcionalmente analisis_asr, operativa_tipo."""
    try:
        params = {
            "strategy_id":     datos.get("strategy_id"),
            "fecha":           datos.get("fecha"),
            "instrumento":     datos.get("instrumento"),
            "direccion":       datos.get("direccion"),
            "resultado":       datos.get("resultado"),
            "rr":              datos.get("rr"),
            "condiciones":     datos.get("condiciones"),
            "notas":           datos.get("notas"),
            "screenshot_path": datos.get("screenshot_path"),
            "analisis_asr":    datos.get("analisis_asr"),
            "operativa_tipo":  datos.get("operativa_tipo"),
        }
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO backtest_trades (
                strategy_id, fecha, instrumento, direccion, resultado, rr,
                condiciones, notas, screenshot_path, analisis_asr, operativa_tipo
            ) VALUES (
                :strategy_id, :fecha, :instrumento, :direccion, :resultado, :rr,
                :condiciones, :notas, :screenshot_path, :analisis_asr, :operativa_tipo
            )
        """, params)
        nuevo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return nuevo_id
    except Exception as e:
        print(f"Error insertando backtest trade: {e}")
        raise


def obtener_backtest_trades(strategy_id: int = None) -> list:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if strategy_id is not None:
            cursor.execute("""
                SELECT * FROM backtest_trades
                WHERE strategy_id = ?
                ORDER BY fecha DESC, id DESC
            """, (strategy_id,))
        else:
            cursor.execute("SELECT * FROM backtest_trades ORDER BY fecha DESC, id DESC")
        filas = [dict(f) for f in cursor.fetchall()]
        conn.close()
        return filas
    except Exception as e:
        print(f"Error obteniendo backtest trades: {e}")
        return []


def eliminar_backtest_trade(bt_id: int) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT screenshot_path FROM backtest_trades WHERE id = ?", (bt_id,))
        fila = cursor.fetchone()
        if fila and fila["screenshot_path"]:
            try:
                if os.path.isfile(fila["screenshot_path"]):
                    os.remove(fila["screenshot_path"])
            except OSError:
                pass
        cursor.execute("DELETE FROM backtest_trades WHERE id = ?", (bt_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando backtest trade {bt_id}: {e}")
        return False


def obtener_backtest_trade_por_id(trade_id: int) -> Optional[dict]:
    """Devuelve un trade de backtest por su ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM backtest_trades WHERE id = ?", (trade_id,))
        fila = cursor.fetchone()
        conn.close()
        return dict(fila) if fila else None
    except Exception as e:
        print(f"Error obteniendo backtest trade {trade_id}: {e}")
        return None


def actualizar_backtest_trade(trade_id: int, datos: dict) -> bool:
    """Actualiza un trade de backtest existente. Devuelve True si tuvo éxito."""
    try:
        params = {
            "id": trade_id,
            "strategy_id": datos.get("strategy_id"),
            "fecha": datos.get("fecha"),
            "instrumento": datos.get("instrumento"),
            "direccion": datos.get("direccion"),
            "resultado": datos.get("resultado"),
            "rr": datos.get("rr"),
            "condiciones": datos.get("condiciones"),
            "notas": datos.get("notas"),
            "screenshot_path": datos.get("screenshot_path"),
            "analisis_asr": datos.get("analisis_asr"),
            "operativa_tipo": datos.get("operativa_tipo"),
        }
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE backtest_trades SET
                strategy_id = :strategy_id,
                fecha = :fecha,
                instrumento = :instrumento,
                direccion = :direccion,
                resultado = :resultado,
                rr = :rr,
                condiciones = :condiciones,
                notas = :notas,
                screenshot_path = :screenshot_path,
                analisis_asr = :analisis_asr,
                operativa_tipo = :operativa_tipo
            WHERE id = :id
        """, params)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando backtest trade {trade_id}: {e}")
        return False


# ─── IMÁGENES POR TRADE BACKTEST ─────────────────────────────────────────────

def insertar_imagen_backtest(backtest_trade_id: int, imagen_path: str, orden: int = 0) -> int:
    """Asocia una imagen a un trade de backtest. Devuelve el ID de la fila creada."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO backtest_imagenes (backtest_trade_id, imagen_path, orden) VALUES (?, ?, ?)",
            (backtest_trade_id, imagen_path, orden),
        )
        nuevo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return nuevo_id
    except Exception as e:
        print(f"Error insertando imagen para backtest trade {backtest_trade_id}: {e}")
        raise


def obtener_imagenes_backtest(backtest_trade_id: int) -> list:
    """Devuelve la lista de imágenes de un trade de backtest, ordenadas por 'orden'."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM backtest_imagenes WHERE backtest_trade_id = ? ORDER BY orden ASC",
            (backtest_trade_id,),
        )
        filas = [dict(f) for f in cursor.fetchall()]
        conn.close()
        return filas
    except Exception as e:
        print(f"Error obteniendo imágenes del backtest trade {backtest_trade_id}: {e}")
        return []


def eliminar_imagen_backtest(imagen_id: int) -> bool:
    """Elimina una imagen de backtest por su ID. Devuelve True si tuvo éxito."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT imagen_path FROM backtest_imagenes WHERE id = ?", (imagen_id,))
        fila = cursor.fetchone()
        if fila:
            path = fila["imagen_path"]
            if os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        cursor.execute("DELETE FROM backtest_imagenes WHERE id = ?", (imagen_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando imagen backtest {imagen_id}: {e}")
        return False


def eliminar_todas_imagenes_backtest(backtest_trade_id: int) -> bool:
    """Elimina todas las imágenes asociadas a un trade de backtest (archivos + registros)."""
    try:
        imagenes = obtener_imagenes_backtest(backtest_trade_id)
        for img in imagenes:
            path = img.get("imagen_path", "")
            if path and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM backtest_imagenes WHERE backtest_trade_id = ?",
            (backtest_trade_id,),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando imágenes del backtest trade {backtest_trade_id}: {e}")
        return False
