/** Server-side fetch (uses internal Docker hostname). */
export const API_BASE = process.env.API_URL || 'http://localhost:4900';

/** Client-side fetch (proxied through Next.js rewrites). */
const CLIENT_BASE = '';

export interface Summary {
  equity: number;
  total_trades: number;
  wins: number;
  losses: number;
  total_pnl: number;
}

export interface Detail {
  equity: number;
  total_trades: number;
  total_pnl: number;
  wins: number;
  losses: number;
  avg_win: number;
  avg_loss: number;
  best_trade: number;
  worst_trade: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown_pct: number;
}

export interface Trade {
  id: number;
  symbol: string;
  direction: string;
  entry_price: number;
  exit_price?: number;
  sl?: number;
  tp?: number;
  position_size?: number;
  leverage?: number;
  pnl?: number;
  reason?: string;
  status: string;
  mayne_score?: number;
  manager_decision?: string;
  manager_confidence?: number;
  debate_transcript?: string;
  entered_at: string;
  exited_at?: string;
}

export interface EquityPoint {
  id: number;
  equity: number;
  timestamp: string;
}

export interface SymbolStats {
  symbol: string;
  count: number;
  wins: number;
  losses: number;
  total_pnl: number;
}

export interface DailyPnl {
  day: string;
  trades: number;
  pnl: number;
}

export interface CycleLog {
  id: number;
  equity: number;
  timestamp: string;
  trades_since: number;
}

export interface AgentLog {
  agent_name: string;
  prompt: string;
  response: string;
  latency_ms: number | null;
  error: string | null;
  created_at?: string;
}

export interface PipelineTrade {
  id: number;
  symbol: string;
  direction: string;
  entry_price: number;
  exit_price: number | null;
  sl: number | null;
  tp: number | null;
  position_size: number | null;
  leverage: number | null;
  pnl: number | null;
  reason: string | null;
  status: string;
  mayne_score: number | null;
  manager_decision: string | null;
  manager_confidence: number | null;
  debate_transcript: string | null;
  entered_at: string;
  exited_at: string | null;
  agents: AgentLog[];
}

export interface PipelineCycle {
  id: number;
  equity: number;
  timestamp: string;
  trades: PipelineTrade[];
}

async function fetchJSON(base: string, path: string) {
  const res = await fetch(`${base}${path}`);
  if (!res.ok) throw new Error(`API ${res.status} on ${path}`);
  return res.json();
}

/** For getServerSideProps (next.js server-side). */
export function serverFetch(path: string) { return fetchJSON(API_BASE, path); }

/** For client-side (proxied through Next.js rewrites). */
export async function clientFetch(path: string) { return fetchJSON(CLIENT_BASE, path); }

export async function fetchSummary() { return clientFetch('/api/summary'); }
export async function fetchDetail() { return clientFetch('/api/detail'); }
export async function fetchClosedTrades(limit = 100) { return clientFetch(`/api/trades/closed`); }
export async function fetchOpenTrades() { return clientFetch('/api/trades/open'); }
export async function fetchEquityHistory() { return clientFetch('/api/equity'); }
export async function fetchSymbolStats() { return clientFetch('/api/trades/by_symbol'); }
export async function fetchDailyPnl() { return clientFetch('/api/pnl/daily'); }
export async function fetchCycles() { return clientFetch('/api/cycles'); }
export async function fetchPipeline() { return clientFetch('/api/pipeline'); }
