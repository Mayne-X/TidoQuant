"""Daily Report Generator.

Aggregates JSONL trades into a human-readable daily markdown report.
"""
from datetime import datetime
import json
import os

def generate_daily_report(journal_path: str, report_dir: str):
    if not os.path.exists(journal_path): return
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    report_file = os.path.join(report_dir, f"{today}.md")
    
    # Simple aggregate
    trades = []
    with open(journal_path, "r") as f:
        for line in f:
            trade = json.loads(line)
            # Filter by today
            if trade["exit_time"].startswith(today):
                trades.append(trade)
                
    if not trades: return
    
    with open(report_file, "w") as f:
        f.write(f"# Daily Report {today}\n\n")
        for t in trades:
            f.write(f"- {t['symbol']} {t['direction']}: {t['pnl']:.2f} ({t['reason']})\n")
