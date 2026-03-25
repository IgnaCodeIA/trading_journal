"""
Motor de riesgo dinámico para Trading Journal Pro.
Aplica reglas en orden de prioridad para calcular el % de riesgo recomendado
y el tamaño de posición.
"""

from datetime import date, datetime
from typing import Optional
from core.database import obtener_todos_los_trades, obtener_configuracion


def calcular_metricas_riesgo(trades: Optional[list] = None) -> dict:
    """
    Calcula las métricas necesarias para el motor de riesgo.
    Devuelve un diccionario con winrate_10, winrate_20, drawdown_actual,
    racha_actual, tipo_racha, pnl_dia.
    """
    if trades is None:
        trades = obtener_todos_los_trades()

    if not trades:
        return {
            "winrate_10": 0.0,
            "winrate_20": 0.0,
            "drawdown_actual": 0.0,
            "racha_actual": 0,
            "tipo_racha": "ninguna",
            "pnl_dia": 0.0,
        }

    # Filtrar trades con resultado definido
    trades_con_resultado = [
        t for t in trades
        if t.get("resultado") in ("Win", "Loss", "Breakeven", "Parcial")
    ]

    # Winrate últimas 10 y 20 operaciones
    def calcular_winrate(ultimos_n):
        subset = trades_con_resultado[:ultimos_n]
        if not subset:
            return 0.0
        wins = sum(1 for t in subset if t.get("resultado") == "Win")
        return (wins / len(subset)) * 100

    winrate_10 = calcular_winrate(10)
    winrate_20 = calcular_winrate(20)

    # Racha actual (ganadora o perdedora)
    racha_actual = 0
    tipo_racha = "ninguna"
    if trades_con_resultado:
        primer_resultado = trades_con_resultado[0].get("resultado")
        if primer_resultado == "Win":
            tipo_racha = "ganadora"
            for t in trades_con_resultado:
                if t.get("resultado") == "Win":
                    racha_actual += 1
                else:
                    break
        elif primer_resultado == "Loss":
            tipo_racha = "perdedora"
            for t in trades_con_resultado:
                if t.get("resultado") == "Loss":
                    racha_actual += 1
                else:
                    break

    # Drawdown actual desde el último máximo de equity
    drawdown_actual = calcular_drawdown_actual(trades_con_resultado)

    # P&L del día actual
    hoy = date.today().isoformat()
    trades_hoy = [t for t in trades_con_resultado if t.get("fecha_salida") == hoy or t.get("fecha_entrada") == hoy]
    pnl_dia = sum(t.get("porcentaje_cuenta", 0) or 0 for t in trades_hoy)

    return {
        "winrate_10": winrate_10,
        "winrate_20": winrate_20,
        "drawdown_actual": drawdown_actual,
        "racha_actual": racha_actual,
        "tipo_racha": tipo_racha,
        "pnl_dia": pnl_dia,
    }


def calcular_drawdown_actual(trades_con_resultado: list) -> float:
    """
    Calcula el drawdown actual como % desde el último máximo de equity acumulada.
    Usa porcentaje_cuenta de cada trade.
    """
    if not trades_con_resultado:
        return 0.0

    # Ordenar por fecha de más antiguo a más reciente
    trades_ordenados = sorted(
        trades_con_resultado,
        key=lambda t: (t.get("fecha_entrada", "") or "", t.get("hora_entrada", "") or "")
    )

    equity = 100.0  # Base 100%
    max_equity = 100.0
    for trade in trades_ordenados:
        pct = trade.get("porcentaje_cuenta", 0) or 0
        equity += pct
        if equity > max_equity:
            max_equity = equity

    drawdown = ((max_equity - equity) / max_equity) * 100 if max_equity > 0 else 0.0
    return max(0.0, drawdown)


def calcular_riesgo_recomendado(metricas: Optional[dict] = None) -> dict:
    """
    Aplica las reglas del motor de riesgo en orden de prioridad.
    Devuelve el % de riesgo recomendado y la justificación textual.
    """
    config = obtener_configuracion()
    riesgo_base = config.get("riesgo_base", 1.0)
    umbral_dd_minimo = config.get("umbral_dd_minimo", 12.0)
    umbral_dd_reducido = config.get("umbral_dd_reducido", 8.0)
    umbral_dd_conservador = config.get("umbral_dd_conservador", 5.0)
    umbral_winrate_alto = config.get("umbral_winrate_alto", 70.0)
    umbral_winrate_medio = config.get("umbral_winrate_medio", 60.0)

    if metricas is None:
        metricas = calcular_metricas_riesgo()

    dd = metricas["drawdown_actual"]
    winrate_10 = metricas["winrate_10"]
    racha_actual = metricas["racha_actual"]
    tipo_racha = metricas["tipo_racha"]
    pnl_dia = metricas["pnl_dia"]

    # ─── REGLAS DE PRIORIDAD ALTA (1-5) ─────────────────────────────────────
    # Regla 1: Drawdown crítico > 12%
    if dd > umbral_dd_minimo:
        return {
            "riesgo": 0.25,
            "nivel": "CRITICO",
            "color": "red",
            "justificacion": (
                f"🚨 ALERTA CRÍTICA: Drawdown actual {dd:.1f}% supera el umbral mínimo "
                f"({umbral_dd_minimo}%). Riesgo reducido al mínimo absoluto. "
                "Considera pausar el trading."
            ),
            "sugerencia_parar": True,
        }

    # Regla 2: Drawdown > 8%
    if dd > umbral_dd_reducido:
        return {
            "riesgo": 0.5,
            "nivel": "ALTO",
            "color": "red",
            "justificacion": (
                f"⚠️ Drawdown actual {dd:.1f}% supera el umbral reducido "
                f"({umbral_dd_reducido}%). Riesgo reducido al 0.5%."
            ),
            "sugerencia_parar": False,
        }

    # Regla 3: Drawdown > 5%
    if dd > umbral_dd_conservador:
        return {
            "riesgo": 0.75,
            "nivel": "ELEVADO",
            "color": "orange",
            "justificacion": (
                f"⚠️ Drawdown actual {dd:.1f}% supera el umbral conservador "
                f"({umbral_dd_conservador}%). Riesgo reducido al 0.75%."
            ),
            "sugerencia_parar": False,
        }

    # Regla 4: Pérdida acumulada en el día > 2%
    if pnl_dia < -2.0:
        return {
            "riesgo": 0.5,
            "nivel": "PRECAUCION_DIA",
            "color": "orange",
            "justificacion": (
                f"⚠️ Pérdida acumulada hoy: {pnl_dia:.2f}%. Supera el límite diario del 2%. "
                "Riesgo reducido al 0.5%. Se recomienda parar por hoy."
            ),
            "sugerencia_parar": True,
        }

    # Regla 5: Racha perdedora >= 3
    if tipo_racha == "perdedora" and racha_actual >= 3:
        riesgo = round(riesgo_base * 0.75, 2)
        return {
            "riesgo": riesgo,
            "nivel": "RACHA_NEGATIVA",
            "color": "orange",
            "justificacion": (
                f"⚠️ Racha perdedora de {racha_actual} operaciones consecutivas. "
                f"Riesgo reducido al 75% del base ({riesgo}%)."
            ),
            "sugerencia_parar": False,
        }

    # ─── REGLAS DE EXPANSIÓN (6-9) ───────────────────────────────────────────
    # Regla 6: Winrate > 70% y drawdown < 3%
    if winrate_10 > umbral_winrate_alto and dd < 3.0:
        return {
            "riesgo": 1.5,
            "nivel": "OPTIMO",
            "color": "green",
            "justificacion": (
                f"✅ Winrate últimas 10 ops: {winrate_10:.1f}% (>{umbral_winrate_alto}%) "
                f"y drawdown {dd:.1f}% (<3%). Condiciones excelentes. Riesgo aumentado al 1.5%."
            ),
            "sugerencia_parar": False,
        }

    # Regla 7: Winrate > 60% y drawdown < 5%
    if winrate_10 > umbral_winrate_medio and dd < umbral_dd_conservador:
        return {
            "riesgo": 1.25,
            "nivel": "BUENO",
            "color": "green",
            "justificacion": (
                f"✅ Winrate últimas 10 ops: {winrate_10:.1f}% (>{umbral_winrate_medio}%) "
                f"y drawdown {dd:.1f}% (<{umbral_dd_conservador}%). "
                "Buenas condiciones. Riesgo aumentado al 1.25%."
            ),
            "sugerencia_parar": False,
        }

    # Regla 8: Racha ganadora >= 5 y drawdown < 3%
    if tipo_racha == "ganadora" and racha_actual >= 5 and dd < 3.0:
        return {
            "riesgo": 1.5,
            "nivel": "RACHA_POSITIVA",
            "color": "green",
            "justificacion": (
                f"✅ Racha ganadora de {racha_actual} operaciones consecutivas "
                f"y drawdown {dd:.1f}% (<3%). Riesgo aumentado al 1.5%."
            ),
            "sugerencia_parar": False,
        }

    # Regla 9: Caso base
    return {
        "riesgo": riesgo_base,
        "nivel": "NORMAL",
        "color": "blue",
        "justificacion": (
            f"ℹ️ Condiciones normales. Riesgo base aplicado: {riesgo_base}%."
        ),
        "sugerencia_parar": False,
    }


def calcular_tamano_posicion(
    cuenta: float,
    riesgo_pct: float,
    precio_entrada: float,
    stop_loss: float,
    par: str,
    tipo_cuenta: str = "Forex estándar"
) -> dict:
    """
    Calcula el tamaño de posición y métricas relacionadas.

    Args:
        cuenta: Tamaño de la cuenta en divisa base
        riesgo_pct: % de riesgo a aplicar
        precio_entrada: Precio de entrada
        stop_loss: Precio de stop loss
        par: Par operado (ej: EURUSD)
        tipo_cuenta: 'Forex estándar' / 'Índices' / 'Metales'

    Returns:
        Diccionario con importe_riesgo, lotes, valor_pip, margen_estimado
    """
    if precio_entrada <= 0 or stop_loss <= 0 or cuenta <= 0:
        return {"error": "Datos inválidos para el cálculo"}

    # Importe a arriesgar
    importe_riesgo = cuenta * (riesgo_pct / 100)

    # Distancia en pips
    distancia_precio = abs(precio_entrada - stop_loss)

    if distancia_precio == 0:
        return {"error": "La distancia entre entrada y SL es 0"}

    resultado = {
        "importe_riesgo": round(importe_riesgo, 2),
        "lotes": 0.0,
        "valor_pip": 0.0,
        "margen_estimado": 0.0,
    }

    if tipo_cuenta == "Forex estándar":
        # Forex: 1 lote estándar = 100,000 unidades
        # Valor del pip para pares XXX/USD ≈ 10 USD por pip por lote estándar
        # Para JPY: pip = 0.01, para el resto pip = 0.0001
        par_upper = par.upper()
        if "JPY" in par_upper:
            valor_pip_por_lote = 1000 / precio_entrada  # aprox en USD
            pips = distancia_precio * 100
        else:
            valor_pip_por_lote = 10.0  # USD por pip por lote estándar
            pips = distancia_precio * 10000

        if pips > 0 and valor_pip_por_lote > 0:
            lotes = importe_riesgo / (pips * valor_pip_por_lote)
        else:
            lotes = 0.0

        resultado["lotes"] = round(lotes, 2)
        resultado["valor_pip"] = round(valor_pip_por_lote * lotes, 2)
        resultado["margen_estimado"] = round(lotes * 100000 / 30, 2)  # leverage ~30

    elif tipo_cuenta == "Índices":
        # Índices: tamaño por punto
        puntos = distancia_precio
        if puntos > 0:
            contratos = importe_riesgo / puntos
        else:
            contratos = 0.0
        resultado["lotes"] = round(contratos, 4)
        resultado["valor_pip"] = round(importe_riesgo / puntos if puntos > 0 else 0, 2)
        resultado["margen_estimado"] = round(contratos * precio_entrada * 0.01, 2)

    elif tipo_cuenta == "Metales":
        # Oro: 1 lote = 100 oz, valor pip ~1 USD por 0.01 de movimiento por lote
        if "XAU" in par.upper():
            valor_pip_por_lote = 1.0  # USD por 0.01 de precio
            pips = distancia_precio * 100
            if pips > 0:
                lotes = importe_riesgo / (pips * valor_pip_por_lote)
            else:
                lotes = 0.0
            resultado["lotes"] = round(lotes, 2)
            resultado["valor_pip"] = round(lotes, 2)
            resultado["margen_estimado"] = round(lotes * precio_entrada * 100 / 100, 2)
        else:
            # Plata u otros metales
            pips = distancia_precio * 100
            if pips > 0:
                lotes = importe_riesgo / pips
            else:
                lotes = 0.0
            resultado["lotes"] = round(lotes, 2)
            resultado["valor_pip"] = round(lotes, 2)
            resultado["margen_estimado"] = round(lotes * precio_entrada * 5000 / 100, 2)

    return resultado


def calcular_rr(precio_entrada: float, stop_loss: float, tp: float) -> float:
    """Calcula el R:R dado entrada, SL y TP."""
    if precio_entrada <= 0 or stop_loss <= 0 or tp <= 0:
        return 0.0
    riesgo = abs(precio_entrada - stop_loss)
    beneficio = abs(tp - precio_entrada)
    if riesgo == 0:
        return 0.0
    return round(beneficio / riesgo, 2)


def calcular_semaforo(metricas: dict, config: dict) -> dict:
    """
    Calcula el estado del semáforo de trading.
    Returns dict con 'color', 'texto', 'descripcion'.
    """
    dd = metricas.get("drawdown_actual", 0)
    winrate_10 = metricas.get("winrate_10", 0)
    umbral_dd_conservador = config.get("umbral_dd_conservador", 5.0)
    umbral_dd_reducido = config.get("umbral_dd_reducido", 8.0)

    if dd > umbral_dd_reducido or winrate_10 < 40:
        return {
            "color": "red",
            "texto": "🔴 STOP",
            "descripcion": (
                f"Condiciones desfavorables: DD {dd:.1f}% > {umbral_dd_reducido}% "
                f"o Winrate {winrate_10:.0f}% < 40%"
            ),
        }
    elif (umbral_dd_conservador <= dd <= umbral_dd_reducido) or (40 <= winrate_10 <= 50):
        return {
            "color": "orange",
            "texto": "🟡 PRECAUCIÓN",
            "descripcion": (
                f"Condiciones mixtas: DD {dd:.1f}% o Winrate {winrate_10:.0f}% "
                "requieren cautela."
            ),
        }
    else:
        return {
            "color": "green",
            "texto": "🟢 OPERAR",
            "descripcion": (
                f"Condiciones favorables: DD {dd:.1f}% < {umbral_dd_conservador}% "
                f"y Winrate {winrate_10:.0f}% > 50%"
            ),
        }
