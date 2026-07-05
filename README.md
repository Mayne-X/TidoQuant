# TidoQuant

Autonomous multi-agent crypto paper-trading bot. Runs Trader Mayne's OTE/Sweep/FVG playbook as an algorithmic gatekeeper, then passes winning signals through a 8-agent AI debate pipeline (Researcher → Sentiment → Bull R1 → Bear R1 → Bull R2 → Bear R2 → Treasury → Manager) powered by **Qwen2.5:7b** via Ollama. 

Features:
- **Full Agent Visibility**: Every agent call is logged with prompt/response/latency.
- **Dynamic Memory**: Heuristic-based performance tracking that injects lessons learned (win streaks, asset performance, score accuracy) into agent prompts.
- **Fine-Tuning Ready**: Autonomous dataset exporter (`scripts/export_dataset.py`) captures full pipeline conversations for future model training.

## Architecture

```
Binance REST API  ──→  Mayne Gate (Python scorer)
                             │
                       Gate passes? (score ≥ 60)
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
              AI Pipeline      Mayne-only fallback
         (8 agents via Ollama)  (fixed SL/TP sizing)
                    │
              Manager GO/NO-GO
                    │
              Paper Engine (SQLite)
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
     Dashboard  Pipeline   REST API
     (:5000)    (:5000)    (:4900)
```

## Quick Start

```bash
# 1. Ensure Ollama is running with Qwen2.5:7b
ollama serve
ollama pull qwen2.5:7b

# 2. Start with Docker
docker compose up -d --build

# 3. Open the dashboard
open http://localhost:5000
```

## Components

| Component | Language | Port | Description |
|-----------|----------|------|-------------|
| **Backend** | Python 3.12 | 4900 | Main loop, agents, paper engine, REST API |
| **Frontend** | Next.js 16 | 5000 | Dashboard + Pipeline visualizer |
| **Database** | SQLite (WAL) | — | Trades, agent logs, equity snapshots |
| **AI** | Qwen2.5:7b (Ollama) | 11434 | All 8 agents + debate rounds |

## Trading Logic

1. **Scan** — Every 15 minutes, fetch 5 perps (BTC/ETH/SOL/BNB/XRP) across 3 timeframes (1h/4h/12h)
2. **Mayne Gate** — Configurable algorithmic score (0-90) based on OTE zone + Sweep detection + FVG detection; multi-timeframe weighted (configurable via `config.py`) + Dynamic Confluence Bonus.
3. **AI Pipeline** — 8-agent debate with full transcript logging:
   - Researcher: on-chain + macro analysis
   - Sentiment: social/news polarity
   - Bull R1 → Bear R1: round 1 debate
   - Bull R2 → Bear R2: round 2 counter-rebuttals
   - Treasury: position sizing (risk brackets 1%/2x, 2%/3x, 3%/5x)
   - Manager: final GO/NO-GO with confidence score
4. **Execution** — Paper engine tracks positions, SL/TP (checked intra-interval via candle High/Low), equity; circuit breaker at -30% drawdown
5. **Memory & Learning** — Dynamic performance briefings injected into agent prompts; data export for fine-tuning.
6. **Mayne Refinements** — Configurable TFs/Weights, Dynamic Confluence Bonus for high-conviction setups, and robust intra-interval SL/TP checking using candle High/Low.

## Risk Parameters

| Mayne Score | Risk % | Leverage | Max Position ($1k equity) |
|-------------|--------|----------|--------------------------|
| 60-70       | 1%     | 2x       | $20                      |
| 71-85       | 2%     | 3x       | $60                      |
| 86-100      | 3%     | 5x       | $150                     |

- Minimum confidence: 60/100
- Minimum R:R ratio: 2:1
- Starting equity: $1,000 (configurable)

## API

All endpoints available at `http://localhost:4900`:

| Endpoint | Description |
|----------|-------------|
| `/api/health` | Service status |
| `/api/summary` | Equity, total trades, wins/losses |
| `/api/detail` | Detailed stats (win rate, profit factor, max DD) |
| `/api/pipeline` | Last 20 cycles with full agent logs |
| `/api/equity` | Equity history (last 200 points) |
| `/api/trades/open` | Open positions |
| `/api/trades/closed` | Closed trades |
| `/api/trades/by_symbol` | Per-symbol P&L |
| `/api/pnl/daily` | Daily P&L |
| `/api/cycles` | Cycle summary |

## Testing

```bash
# Backend (85 tests)
python -m pytest tests/ -v

# Frontend (25 tests)
cd dashboard && npx jest

# All 110 tests pass
```

## Production Notes

- All agent calls are logged to SQLite with full prompt, response, latency, and error
- Pipeline creates placeholder trades before execution — even NO-GO/rejected trades are visible with their agent logs
- Paper engine recovers open positions on restart
- WAL mode for concurrent read access
- Circuit breaker stops trading at -30% drawdown
- No real funds — paper trading only
