# TidoQuant: Autonomous Paper Trader

A self-evolving crypto trading bot implementation based on the "Trader Mayne" OTE/Sweep playbook.

## Setup
1. Ensure Python 3.12+ is installed.
2. Install dependencies:
   ```bash
   pip install requests feedparser
   ```
3. Run the bot:
   ```bash
   python main.py
   ```

## Structure
- `src/`: Core logic (Mayne scorer, catalyst engine, indicator math).
- `journal/`: JSONL records of all closed trades.
- `reports/`: Daily UTC roll-up reports.
- `skills/trader_evolution.md`: Self-evolving post-mortem journal.

## Warnings
- This is a paper trading bot only. It uses public APIs.
- It does not interact with your wallet.
- The circuit breaker stops trading at -30% equity.
