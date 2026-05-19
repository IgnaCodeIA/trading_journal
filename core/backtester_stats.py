"""
Motor de estadísticas para el backtester de estrategias.
Toda la lógica analítica que consume `backtest_trades` + `strategy_conditions`.
"""

import json
from typing import Optional

from core.database import (
    obtener_backtest_trades,
    obtener_condiciones,
    obtener_estrategia,
)

# Resultados considerados como "ganadores" para winrate
WIN_RESULTS = {"WIN", "PARTIAL_TP"}
LOSS_RESULTS = {"LOSS", "PARTIAL_SL"}
ALL_RESULT_TYPES = ["WIN", "PARTIAL_TP", "BE", "LOSS", "PARTIAL_SL"]

RESULT_COLORS = {
    "WIN":         "#00e676",
    "LOSS":        "#ff3c00",
    "BE":          "#ffc107",
    "PARTIAL_TP":  "#00bcd4",
    "PARTIAL_SL":  "#ff9800",
}


def _parse_conditions(raw) -> dict:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return {}


def _is_win(resultado: str) -> bool:
    return resultado in WIN_RESULTS


def _winrate(trades: list) -> float:
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if _is_win(t.get("resultado", "")))
    return wins / len(trades) * 100.0


def _sum_r(trades: list) -> float:
    return sum(float(t.get("rr") or 0) for t in trades)


def _best_streak(trades: list) -> int:
    """Racha máxima de wins consecutivos (orden cronológico ascendente)."""
    if not trades:
        return 0
    ordenados = sorted(trades, key=lambda t: (t.get("fecha") or "", t.get("id") or 0))
    actual = 0
    best = 0
    for t in ordenados:
        if _is_win(t.get("resultado", "")):
            actual += 1
            best = max(best, actual)
        else:
            actual = 0
    return best


# ─── KPIs globales ────────────────────────────────────────────────────────────

def kpis_globales(strategy_id: int, trades: Optional[list] = None) -> dict:
    if trades is None:
        trades = obtener_backtest_trades(strategy_id)
    total = len(trades)
    wr = _winrate(trades)
    net_r = _sum_r(trades)
    avg_r = net_r / total if total else 0.0
    return {
        "total": total,
        "winrate": wr,
        "net_r": net_r,
        "avg_r": avg_r,
        "best_streak": _best_streak(trades),
    }


# ─── Impacto por condición ────────────────────────────────────────────────────

def impacto_condiciones(strategy_id: int, trades: Optional[list] = None) -> list:
    """Para cada condición de la estrategia, calcula WR cuando cumple vs no cumple."""
    condiciones = obtener_condiciones(strategy_id, solo_activas=False)
    if trades is None:
        trades = obtener_backtest_trades(strategy_id)

    parsed = [(t, _parse_conditions(t.get("condiciones"))) for t in trades]
    resultados = []

    for cond in condiciones:
        cid = str(cond["id"])
        cumple_trades = [t for (t, conds) in parsed if conds.get(cid) == 1]
        no_cumple_trades = [t for (t, conds) in parsed if conds.get(cid) != 1]

        wr_si = _winrate(cumple_trades) if cumple_trades else 0.0
        wr_no = _winrate(no_cumple_trades) if no_cumple_trades else 0.0
        delta = wr_si - wr_no if (cumple_trades and no_cumple_trades) else 0.0

        if delta > 10:
            impacto, badge = "ALTA POSITIVA", "🟢"
        elif delta > 5:
            impacto, badge = "MEDIA POSITIVA", "🟡"
        elif delta >= -5:
            impacto, badge = "NEUTRAL", "⚪"
        else:
            impacto, badge = "NEGATIVA", "🔴"

        resultados.append({
            "condicion_id": cond["id"],
            "condicion": cond["nombre"],
            "n_cumple": len(cumple_trades),
            "wr_cumple": wr_si,
            "n_no_cumple": len(no_cumple_trades),
            "wr_no_cumple": wr_no,
            "delta_wr": delta,
            "impacto": impacto,
            "badge": badge,
        })

    resultados.sort(key=lambda r: r["delta_wr"], reverse=True)
    return resultados


def top_condiciones(strategy_id: int, n: int = 3, trades: Optional[list] = None) -> list:
    """Devuelve top N condiciones por Δ WR (positivo)."""
    todas = impacto_condiciones(strategy_id, trades)
    return [c for c in todas if c["n_cumple"] > 0 and c["n_no_cumple"] > 0][:n]


def peor_condicion(strategy_id: int, trades: Optional[list] = None) -> Optional[dict]:
    todas = impacto_condiciones(strategy_id, trades)
    candidatas = [c for c in todas if c["n_cumple"] > 0 and c["delta_wr"] < -5]
    if not candidatas:
        return None
    return min(candidatas, key=lambda c: c["delta_wr"])


# ─── Tabla de confluencia ─────────────────────────────────────────────────────

def tabla_confluencia(strategy_id: int, trades: Optional[list] = None) -> list:
    if trades is None:
        trades = obtener_backtest_trades(strategy_id)
    condiciones = obtener_condiciones(strategy_id, solo_activas=False)
    cond_ids = {str(c["id"]) for c in condiciones}

    buckets = {}
    for t in trades:
        conds = _parse_conditions(t.get("condiciones"))
        n_cumple = sum(1 for cid in cond_ids if conds.get(cid) == 1)
        buckets.setdefault(n_cumple, []).append(t)

    salida = []
    for n_cumple in sorted(buckets.keys()):
        grupo = buckets[n_cumple]
        wr = _winrate(grupo)
        net_r = _sum_r(grupo)
        if wr > 60:
            rec = "Operar"
        elif wr >= 40:
            rec = "Precaución"
        else:
            rec = "Evitar"
        salida.append({
            "n_condiciones": n_cumple,
            "n_ops": len(grupo),
            "winrate": wr,
            "net_r": net_r,
            "recomendacion": rec,
        })
    return salida


def confluencia_optima(strategy_id: int, trades: Optional[list] = None,
                       min_ops: int = 3) -> Optional[dict]:
    """Devuelve el bucket de confluencia con mejor WR (con muestra mínima)."""
    tabla = tabla_confluencia(strategy_id, trades)
    candidatos = [t for t in tabla if t["n_ops"] >= min_ops]
    if not candidatos:
        return None
    return max(candidatos, key=lambda r: r["winrate"])


# ─── Desglose por tipo de resultado ───────────────────────────────────────────

def desglose_resultados(strategy_id: int, trades: Optional[list] = None) -> list:
    if trades is None:
        trades = obtener_backtest_trades(strategy_id)
    total = len(trades)
    salida = []
    for tipo in ALL_RESULT_TYPES:
        grupo = [t for t in trades if t.get("resultado") == tipo]
        n = len(grupo)
        pct = (n / total * 100.0) if total else 0.0
        r_medio = (_sum_r(grupo) / n) if n else 0.0
        r_neto = _sum_r(grupo)
        salida.append({
            "tipo": tipo,
            "n": n,
            "pct": pct,
            "r_medio": r_medio,
            "r_neto": r_neto,
            "color": RESULT_COLORS[tipo],
        })
    return salida


# ─── Breakdown por instrumento ────────────────────────────────────────────────

def breakdown_instrumento(strategy_id: int, trades: Optional[list] = None) -> list:
    if trades is None:
        trades = obtener_backtest_trades(strategy_id)
    buckets = {}
    for t in trades:
        ins = t.get("instrumento") or "—"
        buckets.setdefault(ins, []).append(t)
    salida = []
    for ins, grupo in buckets.items():
        salida.append({
            "instrumento": ins,
            "n": len(grupo),
            "winrate": _winrate(grupo),
            "net_r": _sum_r(grupo),
            "avg_r": _sum_r(grupo) / len(grupo) if grupo else 0.0,
        })
    salida.sort(key=lambda r: r["net_r"], reverse=True)
    return salida


# ─── Equity curve ─────────────────────────────────────────────────────────────

def equity_curve(strategy_id: int, trades: Optional[list] = None) -> list:
    if trades is None:
        trades = obtener_backtest_trades(strategy_id)
    ordenados = sorted(trades, key=lambda t: (t.get("fecha") or "", t.get("id") or 0))
    equity = 0.0
    salida = []
    for t in ordenados:
        equity += float(t.get("rr") or 0)
        salida.append({
            "fecha": t.get("fecha"),
            "equity_r": equity,
            "id": t.get("id"),
        })
    return salida


# ─── Resumen completo para Strategy Intelligence ─────────────────────────────

def resumen_estrategia(strategy_id: int) -> dict:
    estrategia = obtener_estrategia(strategy_id)
    trades = obtener_backtest_trades(strategy_id)
    return {
        "estrategia": estrategia,
        "kpis": kpis_globales(strategy_id, trades),
        "top_condiciones": top_condiciones(strategy_id, n=3, trades=trades),
        "peor_condicion": peor_condicion(strategy_id, trades),
        "confluencia_optima": confluencia_optima(strategy_id, trades),
        "n_trades": len(trades),
    }
