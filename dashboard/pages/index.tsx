import { useEffect, useState, useCallback } from 'react';
import type { NextPage, GetServerSideProps } from 'next';
import Head from 'next/head';
import { 
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { 
  Card, CardHeader, CardTitle, CardContent, StatCard, DataTable,
} from '../components/ui';
import { HeaderBar } from '../components/header-bar';
import { serverFetch, fetchDetail, fetchClosedTrades, fetchOpenTrades, fetchEquityHistory, fetchSymbolStats, fetchDailyPnl } from '../lib/data';
import type { Detail, Trade, EquityPoint, SymbolStats, DailyPnl } from '../lib/data';
import { fmtUSD, fmtPct, fmtNum, relTime } from '../components/cn';

function fmtDuration(start: string, end?: string | null) {
  const s = new Date(start + (start.endsWith("Z") ? "" : "Z"));
  const e = end ? new Date(end + (end.endsWith("Z") ? "" : "Z")) : new Date();
  const ms = e.getTime() - s.getTime();
  if (ms < 0) return '—';
  const hrs = Math.floor(ms / 3600000);
  const mins = Math.floor((ms % 3600000) / 60000);
  if (hrs > 0) return `${hrs}h ${mins}m`;
  return `${mins}m`;
}

const C = { green: '#10b981', red: '#ef4444', blue: '#6366f1', amber: '#f59e0b', purple: '#a855f7' };

interface Props {
  initial: { detail: Detail; closedTrades: Trade[]; openTrades: Trade[]; equity: EquityPoint[]; symbolStats: SymbolStats[]; dailyPnl: DailyPnl[] };
}

const Dashboard: NextPage<Props> = ({ initial }) => {
  const [d, setD] = useState<Detail>(initial.detail);
  const [closed, setClosed] = useState<Trade[]>(initial.closedTrades);
  const [open, setOpen] = useState<Trade[]>(initial.openTrades);
  const [equity, setEquity] = useState<EquityPoint[]>(initial.equity);
  const [sym, setSym] = useState<SymbolStats[]>(initial.symbolStats);
  const [daily, setDaily] = useState<DailyPnl[]>(initial.dailyPnl);
  const [polling, setPolling] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [rd, rc, ro, re, rs, rpnl] = await Promise.all([
        fetchDetail(), fetchClosedTrades(), fetchOpenTrades(),
        fetchEquityHistory(), fetchSymbolStats(), fetchDailyPnl(),
      ]);
      if (rd) setD(rd);
      if (rc) setClosed(rc);
      if (ro) setOpen(ro);
      if (re) setEquity(re);
      if (rs) setSym(rs);
      if (rpnl) setDaily(rpnl);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (!polling) return;
    const id = setInterval(refresh, 15_000);
    return () => clearInterval(id);
  }, [polling, refresh]);

  const equitySpark = equity.map(e => e.equity);
  const closedRev = [...closed].reverse();

  return (
    <>
      <Head><title>Dashboard | TidoQuant</title></Head>
      <div className="p-6 space-y-6">
        <HeaderBar title="Dashboard" live={d.total_trades > 0} polling={polling} onTogglePolling={() => setPolling(p => !p)} />

        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Equity" value={fmtUSD(d.equity)} tone="primary" sparkline={equitySpark} delta={(d.equity - 1000)/1000 * 100} />
          <StatCard label="Total PnL" value={fmtUSD(d.total_pnl)} tone={d.total_pnl >= 0 ? "success" : "destructive"} />
          <StatCard label="Win Rate" value={`${d.win_rate}%`} tone="info" subtitle={`${d.wins}W / ${d.losses}L`} />
          <StatCard label="Max Drawdown" value={fmtPct(d.max_drawdown_pct, 1)} tone="warning" />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle>Equity Curve</CardTitle></CardHeader>
            <CardContent className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={equity}>
                  <defs>
                    <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={C.blue} stopOpacity={0.2} />
                      <stop offset="95%" stopColor={C.blue} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="timestamp" hide />
                  <YAxis domain={['auto', 'auto']} stroke="#6b7280" fontSize={12} tickFormatter={v => fmtUSD(v, 0)} />
                  <Tooltip contentStyle={{ background: '#11141b', borderColor: 'var(--border)' }} formatter={(v: any) => fmtUSD(v)} />
                  <Area type="monotone" dataKey="equity" stroke={C.blue} strokeWidth={2} fill="url(#eqGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Performance Metrics</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between text-sm"><span>Avg Win</span><span className="font-mono text-success">{fmtUSD(d.avg_win)}</span></div>
                <div className="flex justify-between text-sm"><span>Avg Loss</span><span className="font-mono text-destructive">{fmtUSD(Math.abs(d.avg_loss))}</span></div>
                <div className="flex justify-between text-sm"><span>Profit Factor</span><span className="font-mono">{fmtNum(d.profit_factor)}</span></div>
                <div className="flex justify-between text-sm"><span>Best Trade</span><span className="font-mono text-success">{fmtUSD(d.best_trade)}</span></div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tables */}
        {open.length > 0 && (
          <Card>
            <CardHeader><CardTitle>Open Positions</CardTitle></CardHeader>
            <CardContent>
              <DataTable
                columns={[
                  { key: 'symbol', header: 'Symbol', render: r => <span className="font-mono font-medium">{r.symbol}</span> },
                  { key: 'direction', header: 'Dir', render: r => <span className={r.direction === 'long' ? 'text-success' : 'text-destructive'}>{r.direction}</span> },
                  { key: 'entry', header: 'Entry', render: r => fmtUSD(r.entry_price) },
                  { key: 'sl', header: 'SL', render: r => <span className="text-destructive">{fmtUSD(r.sl || 0)}</span> },
                  { key: 'tp', header: 'TP', render: r => <span className="text-success">{fmtUSD(r.tp || 0)}</span> },
                  { key: 'size', header: 'Size', render: r => r.position_size ? fmtUSD(r.position_size) : '—' },
                  { key: 'lev', header: 'Lev', render: r => r.leverage ? `${r.leverage}x` : '—' },
                  { key: 'score', header: 'Score', render: r => <span className="tabular">{r.mayne_score ?? '—'}</span> },
                  { key: 'decision', header: 'Decision', render: r => r.manager_decision ? <span className={r.manager_decision === 'GO' ? 'text-success' : 'text-destructive'}>{r.manager_decision}</span> : '—' },
                  { key: 'age', header: 'Age', render: r => relTime(r.entered_at) },
                ]}
                rows={open} getKey={r => r.id}
              />
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader><CardTitle>Trade History</CardTitle></CardHeader>
          <CardContent>
            <DataTable
              columns={[
                { key: 'symbol', header: 'Symbol', render: r => <span className="font-mono font-medium">{r.symbol}</span> },
                { key: 'direction', header: 'Dir', render: r => <span className={r.direction === 'long' ? 'text-success' : 'text-destructive'}>{r.direction}</span> },
                { key: 'entry', header: 'Entry', render: r => <span className="tabular">{fmtUSD(r.entry_price)}</span> },
                { key: 'exit', header: 'Exit', render: r => <span className="tabular">{r.exit_price ? fmtUSD(r.exit_price) : '—'}</span> },
                { key: 'size', header: 'Size', render: r => r.position_size ? fmtUSD(r.position_size) : '—' },
                { key: 'lev', header: 'Lev', render: r => r.leverage ? `${r.leverage}x` : '—' },
                { key: 'sl', header: 'SL', render: r => r.sl ? <span className="tabular text-destructive">{fmtUSD(r.sl)}</span> : '—' },
                { key: 'tp', header: 'TP', render: r => r.tp ? <span className="tabular text-success">{fmtUSD(r.tp)}</span> : '—' },
                { key: 'pnl', header: 'PnL', render: r => <span className={(r.pnl || 0) >= 0 ? 'text-success tabular' : 'text-destructive tabular'}>{fmtUSD(r.pnl || 0)}</span> },
                { key: 'duration', header: 'Dur', render: r => fmtDuration(r.entered_at, r.exited_at) },
                { key: 'reason', header: 'Why', render: r => <span className="text-[10px] uppercase font-bold opacity-60">{r.reason || '—'}</span> },
              ]}
              rows={closedRev} getKey={r => r.id}
            />
          </CardContent>
        </Card>
      </div>
    </>
  );
};

export const getServerSideProps: GetServerSideProps = async () => {
  const f = serverFetch;
  const [detail, closedTrades, openTrades, equity, symbolStats, dailyPnl] = await Promise.all([
    f('/api/detail'), f('/api/trades/closed'), f('/api/trades/open'),
    f('/api/equity'), f('/api/trades/by_symbol'), f('/api/pnl/daily'),
  ]);

  return {
    props: {
      initial: {
        detail: detail || { equity: 1000, total_trades: 0, total_pnl: 0, wins: 0, losses: 0, avg_win: 0, avg_loss: 0, best_trade: 0, worst_trade: 0, win_rate: 0, profit_factor: 0, max_drawdown_pct: 0 },
        closedTrades: closedTrades || [],
        openTrades: openTrades || [],
        equity: equity || [],
        symbolStats: symbolStats || [],
        dailyPnl: dailyPnl || [],
      },
    },
  };
};

export default Dashboard;
