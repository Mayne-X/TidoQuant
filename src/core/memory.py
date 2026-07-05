"""Memory module — analyzes past trades to format performance context."""
from __future__ import annotations

import logging
from typing import Dict, Any
from ..database import get_closed_trades

log = logging.getLogger("tidoquant")


def build_performance_briefing() -> str:
    """Analyze up to 100 past closed trades and compile a dynamic memory briefing."""
    trades = get_closed_trades(100)
    if not trades:
        return (
            "### CRITICAL MEMORY & PERFORMANCE BRIEFING\n"
            "No historical trade data is available yet. "
            "Please trade cautiously using standard risk parameters.\n"
        )

    total = len(trades)
    wins = sum(1 for t in trades if (t["pnl"] or 0) > 0)
    losses = sum(1 for t in trades if (t["pnl"] or 0) < 0)
    win_rate = (wins / total * 100) if total > 0 else 0.0

    # Streak analysis (ordered exited_at DESC, so index 0 is latest)
    streak_type = "neutral"
    streak_count = 0
    if total > 0:
        latest_pnl = trades[0]["pnl"] or 0
        if latest_pnl > 0:
            streak_type = "winning"
        elif latest_pnl < 0:
            streak_type = "losing"
        
        for t in trades:
            pnl = t["pnl"] or 0
            if streak_type == "winning" and pnl > 0:
                streak_count += 1
            elif streak_type == "losing" and pnl < 0:
                streak_count += 1
            else:
                break

    # Asset analysis
    asset_stats: Dict[str, Dict[str, Any]] = {}
    for t in trades:
        sym = t["symbol"]
        pnl = t["pnl"] or 0
        if sym not in asset_stats:
            asset_stats[sym] = {"total": 0, "wins": 0, "losses": 0, "pnl": 0.0}
        asset_stats[sym]["total"] += 1
        if pnl > 0:
            asset_stats[sym]["wins"] += 1
        elif pnl < 0:
            asset_stats[sym]["losses"] += 1
        asset_stats[sym]["pnl"] += pnl

    # Direction analysis
    dir_stats = {
        "long": {"total": 0, "wins": 0, "losses": 0, "pnl": 0.0},
        "short": {"total": 0, "wins": 0, "losses": 0, "pnl": 0.0},
    }
    for t in trades:
        d = t["direction"].lower()
        pnl = t["pnl"] or 0
        if d in dir_stats:
            dir_stats[d]["total"] += 1
            if pnl > 0:
                dir_stats[d]["wins"] += 1
            elif pnl < 0:
                dir_stats[d]["losses"] += 1
            dir_stats[d]["pnl"] += pnl

    # Mayne score analysis
    score_stats = {
        "low": {"total": 0, "wins": 0},   # 60-65
        "high": {"total": 0, "wins": 0},  # 66+
    }
    for t in trades:
        score = t["mayne_score"] or 0
        pnl = t["pnl"] or 0
        key = "low" if score <= 65 else "high"
        score_stats[key]["total"] += 1
        if pnl > 0:
            score_stats[key]["wins"] += 1

    # Format into markdown
    lines = []
    lines.append("### CRITICAL MEMORY & PERFORMANCE BRIEFING")
    lines.append(f"- **Overall Performance**: {win_rate:.1f}% Win Rate ({wins}W / {losses}L over {total} trades)")
    
    if streak_count >= 2:
        streak_emoji = "🔥" if streak_type == "winning" else "⚠️"
        lines.append(f"- **Current Streak**: {streak_emoji} On a {streak_count}-trade {streak_type} streak! "
                     f"{'Maximize opportunities' if streak_type == 'winning' else 'Exercise extreme caution and reduce position sizes'}.")

    lines.append("\n**Asset-Specific Performance**:")
    for sym, s in sorted(asset_stats.items()):
        s_wr = (s["wins"] / s["total"] * 100) if s["total"] > 0 else 0.0
        caution = " (⚠️ CAUTION: High failure rate, analyze with caution)" if s_wr < 40.0 and s["total"] >= 2 else ""
        lines.append(f"  * {sym}: {s_wr:.1f}% Win Rate ({s['wins']}W/{s['losses']}L, PnL: ${s['pnl']:.2f}){caution}")

    lines.append("\n**Directional Bias Performance**:")
    for d, s in dir_stats.items():
        if s["total"] > 0:
            s_wr = (s["wins"] / s["total"] * 100)
            lines.append(f"  * {d.upper()} trades: {s_wr:.1f}% Win Rate ({s['wins']}W/{s['losses']}L)")

    lines.append("\n**Confluence Score Performance**:")
    for k, s in score_stats.items():
        if s["total"] > 0:
            s_wr = (s["wins"] / s["total"] * 100)
            range_str = "60-65 (low confluence)" if k == "low" else ">= 66 (high confluence)"
            lines.append(f"  * Mayne Score {range_str}: {s_wr:.1f}% Win Rate ({s['wins']}W/{s['total']} total)")

    return "\n".join(lines)
