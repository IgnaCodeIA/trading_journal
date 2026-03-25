"""
Módulo de estadísticas y métricas para Trading Journal Pro.
Todos los cálculos estadísticos derivados del historial de trades.
"""

from datetime import date, datetime, timedelta
from collections import defaultdict
from typing import Optional
from core.database import obtener_todos_los_trades, obtener_configuracion


def calcular_pnl_periodo(trades: list, fecha_inicio: str, fecha_fin: str) -> float:
    """Calcula el P&L (en % de cuenta) para un rango de fechas dado."""
    total = 0.0
    for trade in trades:
        fecha = trade.get("fecha_salida") or trade.get("fecha_entrada", "")
        if fecha_inicio <= fecha <= fecha_fin:
            total += trade.get("porcentaje_cuenta", 0) or 0
    return round(total, 2)


def calcular_pnl_dia(trades: list) -> float:
    """P&L del día actual."""
    hoy = date.today().isoformat()
    return calcular_pnl_periodo(trades, hoy, hoy)


def calcular_pnl_semana(trades: list) -> float:
    """P&L de la semana actual (lunes a hoy)."""
    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    return calcular_pnl_periodo(trades, inicio_semana.isoformat(), hoy.isoformat())


def calcular_pnl_mes(trades: list) -> float:
    """P&L del mes actual."""
    hoy = date.today()
    inicio_mes = hoy.replace(day=1).isoformat()
    return calcular_pnl_periodo(trades, inicio_mes, hoy.isoformat())


def calcular_winrate(trades: list) -> float:
    """Winrate global sobre trades con resultado definido."""
    validos = [t for t in trades if t.get("resultado") in ("Win", "Loss", "Breakeven", "Parcial")]
    if not validos:
        return 0.0
    wins = sum(1 for t in validos if t.get("resultado") == "Win")
    return round((wins / len(validos)) * 100, 1)


def calcular_profit_factor(trades: list) -> float:
    """
    Profit Factor = suma de ganancias / suma de pérdidas (en valor absoluto).
    Usa importe_dinero si disponible, sino porcentaje_cuenta.
    """
    ganancias = 0.0
    perdidas = 0.0
    for trade in trades:
        if trade.get("resultado") not in ("Win", "Loss", "Breakeven", "Parcial"):
            continue
        valor = trade.get("importe_dinero") or trade.get("porcentaje_cuenta", 0) or 0
        if valor > 0:
            ganancias += valor
        elif valor < 0:
            perdidas += abs(valor)
    if perdidas == 0:
        return float("inf") if ganancias > 0 else 0.0
    return round(ganancias / perdidas, 2)


def calcular_expectativa(winrate_pct: float, rr_medio: float) -> float:
    """
    Expectativa matemática = (Winrate × RR_medio) - (1 - Winrate)
    Winrate debe ser entre 0 y 1 para este cálculo.
    """
    wr = winrate_pct / 100
    return round((wr * rr_medio) - (1 - wr), 3)


def calcular_rr_medio(trades: list) -> dict:
    """Calcula el R:R medio planificado y conseguido."""
    rr_planificados = [t.get("rr_planificado", 0) or 0 for t in trades if t.get("rr_planificado")]
    rr_conseguidos = [t.get("rr_conseguido", 0) or 0 for t in trades if t.get("rr_conseguido")]
    return {
        "planificado": round(sum(rr_planificados) / len(rr_planificados), 2) if rr_planificados else 0.0,
        "conseguido": round(sum(rr_conseguidos) / len(rr_conseguidos), 2) if rr_conseguidos else 0.0,
    }


def calcular_rachas(trades: list) -> dict:
    """
    Calcula la mejor racha ganadora y peor racha perdedora consecutivas.
    Returns dict con max_ganadora y max_perdedora.
    """
    trades_ordenados = sorted(
        [t for t in trades if t.get("resultado") in ("Win", "Loss", "Breakeven", "Parcial")],
        key=lambda t: (t.get("fecha_entrada", ""), t.get("hora_entrada", ""))
    )

    max_ganadora = 0
    max_perdedora = 0
    racha_ganadora = 0
    racha_perdedora = 0

    for trade in trades_ordenados:
        resultado = trade.get("resultado")
        if resultado == "Win":
            racha_ganadora += 1
            racha_perdedora = 0
        elif resultado == "Loss":
            racha_perdedora += 1
            racha_ganadora = 0
        else:
            racha_ganadora = 0
            racha_perdedora = 0

        max_ganadora = max(max_ganadora, racha_ganadora)
        max_perdedora = max(max_perdedora, racha_perdedora)

    return {"max_ganadora": max_ganadora, "max_perdedora": max_perdedora}


def calcular_trades_por_periodo(trades: list) -> dict:
    """Calcula la media de trades por semana y por mes."""
    if not trades:
        return {"por_semana": 0.0, "por_mes": 0.0}

    fechas = sorted([t.get("fecha_entrada", "") for t in trades if t.get("fecha_entrada")])
    if len(fechas) < 2:
        return {"por_semana": len(trades), "por_mes": len(trades)}

    try:
        fecha_inicio = datetime.fromisoformat(fechas[0]).date()
        fecha_fin = datetime.fromisoformat(fechas[-1]).date()
        dias_totales = (fecha_fin - fecha_inicio).days + 1

        semanas = max(dias_totales / 7, 1)
        meses = max(dias_totales / 30.44, 1)

        return {
            "por_semana": round(len(trades) / semanas, 1),
            "por_mes": round(len(trades) / meses, 1),
        }
    except Exception:
        return {"por_semana": 0.0, "por_mes": 0.0}


def calcular_equity_curve(trades: list, capital_inicial: float = None) -> list:
    """
    Construye la curva de equity a partir de los trades.
    Devuelve lista de dicts con fecha y equity acumulada.
    Si capital_inicial es None, usa el de configuración.
    """
    if capital_inicial is None:
        config = obtener_configuracion()
        capital_inicial = config.get("tamanio_cuenta", 10000.0)

    trades_ordenados = sorted(
        [t for t in trades if t.get("resultado") in ("Win", "Loss", "Breakeven", "Parcial")],
        key=lambda t: (t.get("fecha_entrada", ""), t.get("hora_entrada", ""))
    )

    equity_actual = capital_inicial
    curva = [{"fecha": "", "equity": equity_actual, "trade_id": None}]

    for trade in trades_ordenados:
        pct = trade.get("porcentaje_cuenta", 0) or 0
        equity_actual = equity_actual * (1 + pct / 100)
        curva.append({
            "fecha": trade.get("fecha_salida") or trade.get("fecha_entrada", ""),
            "equity": round(equity_actual, 2),
            "trade_id": trade.get("id"),
        })

    return curva


def calcular_drawdown_historico(curva_equity: list) -> dict:
    """
    Calcula el drawdown máximo histórico y el drawdown actual.
    Returns dict con max_drawdown_pct, drawdown_actual_pct.
    """
    if len(curva_equity) < 2:
        return {"max_drawdown_pct": 0.0, "drawdown_actual_pct": 0.0, "serie": []}

    max_equity = curva_equity[0]["equity"]
    max_drawdown = 0.0
    drawdown_serie = []

    for punto in curva_equity:
        eq = punto["equity"]
        if eq > max_equity:
            max_equity = eq
        dd_pct = ((max_equity - eq) / max_equity) * 100 if max_equity > 0 else 0
        drawdown_serie.append({"fecha": punto["fecha"], "drawdown": dd_pct})
        max_drawdown = max(max_drawdown, dd_pct)

    drawdown_actual = drawdown_serie[-1]["drawdown"] if drawdown_serie else 0.0

    return {
        "max_drawdown_pct": round(max_drawdown, 2),
        "drawdown_actual_pct": round(drawdown_actual, 2),
        "serie": drawdown_serie,
    }


def calcular_pnl_mensual(trades: list) -> list:
    """
    Calcula el P&L mensual para los últimos 12 meses.
    Devuelve lista de dicts con mes (YYYY-MM) y pnl.
    """
    meses = {}
    for trade in trades:
        if trade.get("resultado") not in ("Win", "Loss", "Breakeven", "Parcial"):
            continue
        fecha = trade.get("fecha_salida") or trade.get("fecha_entrada", "")
        if len(fecha) >= 7:
            mes = fecha[:7]  # YYYY-MM
            meses[mes] = meses.get(mes, 0) + (trade.get("porcentaje_cuenta", 0) or 0)

    # Últimos 12 meses
    hoy = date.today()
    resultado = []
    for i in range(11, -1, -1):
        mes_fecha = date(hoy.year, hoy.month, 1) - timedelta(days=i * 30)
        mes_str = mes_fecha.strftime("%Y-%m")
        resultado.append({
            "mes": mes_str,
            "pnl": round(meses.get(mes_str, 0), 2),
        })

    return resultado


def calcular_pnl_trimestral(trades: list) -> list:
    """Calcula el P&L por trimestre."""
    trimestres = {}
    for trade in trades:
        if trade.get("resultado") not in ("Win", "Loss", "Breakeven", "Parcial"):
            continue
        fecha = trade.get("fecha_salida") or trade.get("fecha_entrada", "")
        if len(fecha) >= 7:
            try:
                dt = datetime.fromisoformat(fecha)
                trimestre = f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"
                trimestres[trimestre] = trimestres.get(trimestre, 0) + (
                    trade.get("porcentaje_cuenta", 0) or 0
                )
            except Exception:
                pass

    return [{"trimestre": k, "pnl": round(v, 2)} for k, v in sorted(trimestres.items())]


def calcular_stats_por_estrategia(trades: list) -> list:
    """
    Estadísticas agrupadas por estrategia: Blue, Red, Pink, White.
    Devuelve lista de dicts con estrategia, winrate, pnl, rr_medio, n_trades, profit_factor.
    """
    grupos = defaultdict(list)
    for trade in trades:
        estrategia = trade.get("estrategia", "Sin estrategia") or "Sin estrategia"
        grupos[estrategia].append(trade)

    resultado = []
    for estrategia, grupo in sorted(grupos.items()):
        winrate = calcular_winrate(grupo)
        pnl = sum(t.get("porcentaje_cuenta", 0) or 0 for t in grupo)
        rr = calcular_rr_medio(grupo)
        pf = calcular_profit_factor(grupo)
        resultado.append({
            "estrategia": estrategia,
            "winrate": winrate,
            "pnl": round(pnl, 2),
            "rr_medio_conseguido": rr["conseguido"],
            "n_trades": len(grupo),
            "profit_factor": pf,
        })

    return resultado


def calcular_stats_por_sesion(trades: list) -> list:
    """Estadísticas agrupadas por sesión de trading."""
    grupos = defaultdict(list)
    for trade in trades:
        sesion = trade.get("sesion", "Sin sesión") or "Sin sesión"
        grupos[sesion].append(trade)

    resultado = []
    for sesion, grupo in sorted(grupos.items()):
        pnl = sum(t.get("porcentaje_cuenta", 0) or 0 for t in grupo)
        resultado.append({
            "sesion": sesion,
            "n_trades": len(grupo),
            "winrate": calcular_winrate(grupo),
            "pnl": round(pnl, 2),
        })
    return resultado


def calcular_stats_por_tipo_operacion(trades: list) -> list:
    """Estadísticas agrupadas por tipo de operación."""
    grupos = defaultdict(list)
    for trade in trades:
        tipo = trade.get("tipo_operacion", "Sin tipo") or "Sin tipo"
        grupos[tipo].append(trade)

    resultado = []
    for tipo, grupo in sorted(grupos.items()):
        pnl = sum(t.get("porcentaje_cuenta", 0) or 0 for t in grupo)
        resultado.append({
            "tipo": tipo,
            "n_trades": len(grupo),
            "winrate": calcular_winrate(grupo),
            "pnl": round(pnl, 2),
        })
    return resultado


def calcular_impacto_trailing_stop(trades: list) -> dict:
    """
    Compara el rendimiento con y sin trailing stop.
    Returns dict con con_trailing y sin_trailing.
    """
    con_trailing = [t for t in trades if t.get("trailing_stop") == 1]
    sin_trailing = [t for t in trades if t.get("trailing_stop") != 1]

    def metricas(grupo):
        pnl_medio = (
            sum(t.get("porcentaje_cuenta", 0) or 0 for t in grupo) / len(grupo)
            if grupo else 0
        )
        return {
            "n_trades": len(grupo),
            "winrate": calcular_winrate(grupo),
            "pnl_medio": round(pnl_medio, 3),
        }

    return {
        "con_trailing": metricas(con_trailing),
        "sin_trailing": metricas(sin_trailing),
    }


def calcular_top_pares(trades: list, n: int = 10) -> list:
    """Top N pares por P&L total."""
    grupos = defaultdict(list)
    for trade in trades:
        par = trade.get("par", "Desconocido") or "Desconocido"
        grupos[par].append(trade)

    pares_pnl = []
    for par, grupo in grupos.items():
        pnl = sum(t.get("porcentaje_cuenta", 0) or 0 for t in grupo)
        pares_pnl.append({
            "par": par,
            "n_trades": len(grupo),
            "pnl": round(pnl, 2),
            "winrate": calcular_winrate(grupo),
        })

    return sorted(pares_pnl, key=lambda x: x["pnl"], reverse=True)[:n]


def calcular_rentabilidad_anual(trades: list) -> dict:
    """Calcula la rentabilidad anual acumulada."""
    anios = defaultdict(float)
    for trade in trades:
        if trade.get("resultado") not in ("Win", "Loss", "Breakeven", "Parcial"):
            continue
        fecha = trade.get("fecha_salida") or trade.get("fecha_entrada", "")
        if len(fecha) >= 4:
            anio = fecha[:4]
            anios[anio] += trade.get("porcentaje_cuenta", 0) or 0

    return {anio: round(pnl, 2) for anio, pnl in sorted(anios.items())}


def get_resumen_completo(trades: Optional[list] = None) -> dict:
    """
    Devuelve un resumen completo de todas las estadísticas.
    Usado para evitar múltiples llamadas a la DB.
    """
    if trades is None:
        trades = obtener_todos_los_trades()

    trades_validos = [
        t for t in trades
        if t.get("resultado") in ("Win", "Loss", "Breakeven", "Parcial")
    ]

    winrate = calcular_winrate(trades_validos)
    rr_medio = calcular_rr_medio(trades_validos)
    profit_factor = calcular_profit_factor(trades_validos)
    expectativa = calcular_expectativa(winrate, rr_medio["conseguido"])
    rachas = calcular_rachas(trades_validos)
    trades_periodo = calcular_trades_por_periodo(trades_validos)
    curva = calcular_equity_curve(trades_validos)
    drawdown_info = calcular_drawdown_historico(curva)

    return {
        "n_trades": len(trades_validos),
        "winrate": winrate,
        "rr_medio": rr_medio,
        "profit_factor": profit_factor,
        "expectativa": expectativa,
        "rachas": rachas,
        "trades_por_semana": trades_periodo["por_semana"],
        "trades_por_mes": trades_periodo["por_mes"],
        "drawdown_max": drawdown_info["max_drawdown_pct"],
        "drawdown_actual": drawdown_info["drawdown_actual_pct"],
        "curva_equity": curva,
        "drawdown_serie": drawdown_info["serie"],
        "pnl_dia": calcular_pnl_dia(trades_validos),
        "pnl_semana": calcular_pnl_semana(trades_validos),
        "pnl_mes": calcular_pnl_mes(trades_validos),
    }
