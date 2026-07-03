"""Hermes Evolution Agent.

Post-mortem analysis of closed trades.
"""
import json
import os
from .config import PROJECT_ROOT_MARKER

def analyze_and_evolve(journal_path: str, skill_path: str):
    if not os.path.exists(journal_path): return
    
    # Simple post-mortem: Append last trade to skill file
    with open(journal_path, "r") as f:
        lines = f.readlines()
        if not lines: return
        last_trade = json.loads(lines[-1])
        
    with open(skill_path, "a") as f:
        f.write(f"\n## Post-Mortem: {last_trade['symbol']} at {last_trade['exit_time']}\n")
        f.write(f"- Result: {last_trade['reason']}\n")
        f.write(f"- PnL: {last_trade['pnl']:.2f}\n")
        f.write("- Analysis: [Automated analysis would go here]\n")
