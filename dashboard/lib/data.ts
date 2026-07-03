const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4900';

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
  entered_at: string;
  exited_at?: string;
}

export interface Summary {
  equity: number;
  total_trades: number;
  wins: number;
  losses: number;
  total_pnl: number;
}

export interface EquityPoint {
  id: number;
  equity: number;
  timestamp: string;
}

export async function fetchSummary(): Promise<Summary> {
  const res = await fetch(`${API_BASE}/api/summary`);
  return res.json();
}

export async function fetchClosedTrades(): Promise<Trade[]> {
  const res = await fetch(`${API_BASE}/api/trades/closed`);
  return res.json();
}

export async function fetchOpenTrades(): Promise<Trade[]> {
  const res = await fetch(`${API_BASE}/api/trades/open`);
  return res.json();
}

export async function fetchEquityHistory(): Promise<EquityPoint[]> {
  const res = await fetch(`${API_BASE}/api/equity`);
  return res.json();
}
