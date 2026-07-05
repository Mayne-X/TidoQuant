import json
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.database import _db

def export(output_file: str, mode: str):
    with _db() as db:
        # Get all closed trades
        trades = db.execute("SELECT * FROM trades WHERE status='closed'").fetchall()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for trade in trades:
                trade_id = trade['id']
                
                # Fetch agent logs
                logs = db.execute("SELECT * FROM agent_logs WHERE trade_id=? ORDER BY id", (trade_id,)).fetchall()
                
                # Prepare conversation
                messages = []
                # System prompt is agent-specific but we can infer/store it if needed.
                # Actually, the agent_logs.prompt contains both ## System and ## User.
                
                for log in logs:
                    prompt = log['prompt']
                    # Split prompt into System and User
                    # The prompt format is "## System\n{system}\n\n## User\n{user}"
                    
                    parts = prompt.split("## User\n")
                    system_part = parts[0].replace("## System\n", "").strip()
                    user_part = parts[1].strip() if len(parts) > 1 else ""
                    
                    messages.append({"role": "system", "content": system_part})
                    messages.append({"role": "user", "content": user_part})
                    messages.append({"role": "assistant", "content": log['response']})

                # Filter based on mode (simplified for now: just export everything)
                if mode == "sft" and (trade['pnl'] or 0) <= 0:
                    continue
                    
                entry = {
                    "messages": messages,
                    "metadata": {
                        "trade_id": trade_id,
                        "symbol": trade['symbol'],
                        "pnl": trade['pnl'],
                        "outcome": "win" if (trade['pnl'] or 0) > 0 else "loss"
                    }
                }
                f.write(json.dumps(entry) + '\n')
    print(f"Exported to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="dataset.jsonl")
    parser.add_argument("--mode", choices=["sft", "all"], default="all")
    args = parser.parse_args()
    export(args.output, args.mode)
