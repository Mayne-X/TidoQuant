import { useEffect, useState, useCallback } from 'react';
import type { NextPage, GetServerSideProps } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { serverFetch, fetchDetail, fetchClosedTrades, fetchOpenTrades, fetchEquityHistory, fetchSymbolStats, fetchDailyPnl } from '../lib/data';
import type { Detail, Trade, EquityPoint, SymbolStats, DailyPnl } from '../lib/data';

const C = { green: '#22c55e', red: '#ef4444', blue: '#3b82f6', amber: '#f59e0b' };
const PIE_COLORS = [C.green, C.red];

function fmt(n: number) { return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

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
    } catch { /* swallow polling errors */ }
  }, []);

  useEffect(() => {
    if (!polling) return;
    const id = setInterval(refresh, 15_000);
    return () => clearInterval(id);
  }, [polling, refresh]);

  const equityData = [...equity].reverse();
  const closedRev = [...closed].reverse();
  const pnlBars = closedRev.map((t, i) => ({ idx: i + 1, pnl: t.pnl || 0 }));
  const winLoss = [
    { name: 'Wins', value: d.wins },
    { name: 'Losses', value: d.losses },
  ];

  return (
    <>
      <Head>
        <title>TidoQuant Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <div className="min-h-screen bg-gray-950 text-gray-100 p-4 md:p-6">
        <div className="max-w-7xl mx-auto space-y-6">

          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight">TidoQuant</h1>
              <p className="text-sm text-gray-400 mt-1">Multi-Agent AI Trading System · Paper Trading</p>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <Link href="/pipeline" className="text-gray-500 hover:text-gray-300 transition-colors">
                Pipeline →
              </Link>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                {d.total_trades > 0 ? 'Live' : 'Waiting'}
              </span>
              <button onClick={() => { setPolling(p => !p); refresh(); }}
                className="px-3 py-1 rounded text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 transition-colors">
                {polling ? 'Auto-refresh ON' : 'Paused'}
              </button>
            </div>
          </div>

          {/* Stat Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <Stat title="Equity" value={`$${fmt(d.equity)}`} color={d.equity >= 100 ? C.green : C.red} sub="Started $100" />
            <Stat title="Total PnL" value={`${d.total_pnl >= 0 ? '+' : ''}$${fmt(d.total_pnl)}`}
              color={d.total_pnl >= 0 ? C.green : C.red} sub={`${d.total_trades} trades`} />
            <Stat title="Win Rate" value={`${d.win_rate}%`} color={d.win_rate >= 40 ? C.green : C.amber} sub={`${d.wins}W / ${d.losses}L`} />
            <Stat title="Profit Factor" value={fmt(d.profit_factor)} color={d.profit_factor >= 1 ? C.green : C.red} sub="Gross win / loss" />
            <Stat title="Avg W / L" value={`$${fmt(d.avg_win)} / -$${fmt(Math.abs(d.avg_loss))}`}
              color={C.blue} sub={`Best $${fmt(d.best_trade)}`} />
            <Stat title="Max Drawdown" value={`${d.max_drawdown_pct}%`}
              color={d.max_drawdown_pct > 10 ? C.red : C.green} sub="Peak to trough" />
          </div>

          {/* Row 1 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2 bg-gray-900/60 border-gray-800">
              <CardHeader><CardTitle>Equity Curve</CardTitle></CardHeader>
              <CardContent>
                <div className="h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={equityData}>
                      <defs>
                        <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={C.green} stopOpacity={0.25} />
                          <stop offset="95%" stopColor={C.green} stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis dataKey="id" stroke="#6b7280" tick={false} />
                      <YAxis domain={['dataMin - 5', 'dataMax + 5']} stroke="#6b7280" tickFormatter={v => `$${v}`} />
                        <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                          formatter={(v: any) => [`$${fmt(Number(v))}`, 'Equity']} />
                      <Area type="monotone" dataKey="equity" stroke={C.green} strokeWidth={2} fill="url(#eqGrad)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-900/60 border-gray-800">
              <CardHeader><CardTitle>Win / Loss</CardTitle></CardHeader>
              <CardContent>
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={winLoss} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={4} dataKey="value">
                        {winLoss.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
                      </Pie>
                      <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex justify-center gap-6 text-sm mt-2">
                  <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full" style={{ background: C.green }} /> Wins {d.wins}</span>
                  <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full" style={{ background: C.red }} /> Losses {d.losses}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Row 2 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="bg-gray-900/60 border-gray-800">
              <CardHeader><CardTitle>PnL per Trade</CardTitle></CardHeader>
              <CardContent>
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={pnlBars.slice(-30)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis dataKey="idx" stroke="#6b7280" tick={false} />
                      <YAxis stroke="#6b7280" tickFormatter={v => `$${v}`} />
                      <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                        formatter={(v: any) => [`$${fmt(Number(v))}`, 'PnL']} />
                      <Bar dataKey="pnl" maxBarSize={16}>
                        {pnlBars.slice(-30).map((e, i) => (<Cell key={i} fill={e.pnl >= 0 ? C.green : C.red} />))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-900/60 border-gray-800">
              <CardHeader><CardTitle>By Symbol</CardTitle></CardHeader>
              <CardContent>
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={sym} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis type="number" stroke="#6b7280" tickFormatter={v => `$${v}`} />
                      <YAxis type="category" dataKey="symbol" stroke="#6b7280" width={60} />
                      <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                        formatter={(v: any) => [`$${fmt(Number(v))}`, 'PnL']} />
                      <Bar dataKey="total_pnl" maxBarSize={20}>
                        {sym.map((s, i) => (<Cell key={i} fill={s.total_pnl >= 0 ? C.green : C.red} />))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-900/60 border-gray-800">
              <CardHeader><CardTitle>Daily PnL</CardTitle></CardHeader>
              <CardContent>
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={daily}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis dataKey="day" stroke="#6b7280" tick={false} />
                      <YAxis stroke="#6b7280" tickFormatter={v => `$${v}`} />
                      <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                        formatter={(v: any) => [`$${fmt(Number(v))}`, 'Daily PnL']} />
                      <Bar dataKey="pnl" maxBarSize={20}>
                        {daily.map((d, i) => (<Cell key={i} fill={d.pnl >= 0 ? C.green : C.red} />))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Open Positions */}
          {open.length > 0 && (
            <Card className="bg-gray-900/60 border-gray-800">
              <CardHeader><CardTitle>Open Positions</CardTitle></CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead><tr className="border-b border-gray-800 text-gray-400">
                      <th className="text-left py-2">Symbol</th><th className="text-left py-2">Dir</th>
                      <th className="text-left py-2">Entry</th><th className="text-left py-2">SL</th><th className="text-left py-2">TP</th>
                      <th className="text-left py-2">Size</th><th className="text-left py-2">Lev</th><th className="text-left py-2">Mayne</th>
                      <th className="text-left py-2">Entered</th>
                    </tr></thead>
                    <tbody>{open.map(t => (
                      <tr key={t.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                        <td className="py-2 font-mono">{t.symbol}</td>
                        <td className={`py-2 ${t.direction === 'long' ? 'text-green-400' : 'text-red-400'}`}>{t.direction}</td>
                        <td className="py-2 font-mono">${fmt(t.entry_price)}</td>
                        <td className="py-2 font-mono text-red-400">${fmt(t.sl || 0)}</td>
                        <td className="py-2 font-mono text-green-400">${fmt(t.tp || 0)}</td>
                        <td className="py-2">${fmt(t.position_size || 0)}</td>
                        <td className="py-2">{t.leverage}x</td>
                        <td className="py-2">{t.mayne_score}</td>
                        <td className="py-2 text-gray-500 text-xs">{new Date(t.entered_at + 'Z').toLocaleString()}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Trade History */}
          <Card className="bg-gray-900/60 border-gray-800">
            <CardHeader><CardTitle>Trade History <span className="text-gray-500 text-xs font-normal">({closed.length} trades)</span></CardTitle></CardHeader>
            <CardContent>
              <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-gray-900"><tr className="border-b border-gray-800 text-gray-400">
                    <th className="text-left py-2">#</th><th className="text-left py-2">Symbol</th><th className="text-left py-2">Dir</th>
                    <th className="text-left py-2">PnL</th><th className="text-left py-2">Return</th><th className="text-left py-2">Reason</th>
                    <th className="text-left py-2">Mayne</th><th className="text-left py-2">Mgr</th><th className="text-left py-2">Exited</th>
                  </tr></thead>
                  <tbody>
                    {closed.length === 0 && (
                      <tr><td colSpan={9} className="py-8 text-center text-gray-600">No trades yet — waiting for Mayne gate signal</td></tr>
                    )}
                    {closedRev.map(t => {
                      const ret = t.position_size && t.position_size > 0
                        ? ((t.pnl || 0) / (t.position_size / (t.leverage || 1))) * 100 : 0;
                      return (
                        <tr key={t.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                          <td className="py-2 text-gray-500">{t.id}</td>
                          <td className="py-2 font-mono">{t.symbol}</td>
                          <td className={`py-2 ${t.direction === 'long' ? 'text-green-400' : 'text-red-400'}`}>{t.direction}</td>
                          <td className={`py-2 font-mono ${(t.pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {(t.pnl || 0) >= 0 ? '+' : ''}${fmt(t.pnl || 0)}
                          </td>
                          <td className={`py-2 font-mono text-xs ${ret >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {ret >= 0 ? '+' : ''}{ret.toFixed(1)}%
                          </td>
                          <td className="py-2">
                            <span className={`px-2 py-0.5 rounded text-xs ${t.reason === 'TP_HIT' ? 'bg-green-900/50 text-green-300' : t.reason === 'SL_HIT' ? 'bg-red-900/50 text-red-300' : 'bg-gray-800 text-gray-300'}`}>
                              {t.reason}
                            </span>
                          </td>
                          <td className="py-2">{t.mayne_score}</td>
                          <td className="py-2">{t.manager_decision}</td>
                          <td className="py-2 text-gray-500 text-xs">{t.exited_at ? new Date(t.exited_at + 'Z').toLocaleDateString() : '-'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          <div className="text-center text-xs text-gray-700 pb-8">
            TidoQuant v2 · Mayne → Researcher → Sentiment → Bull v Bear → Treasury → Manager · Polls API every 15s
          </div>
        </div>
      </div>
    </>
  );
};

function Stat({ title, value, color, sub }: { title: string; value: string; color: string; sub: string }) {
  return (
    <Card className="bg-gray-900/60 border-gray-800">
      <CardContent className="p-4">
        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">{title}</p>
        <p className="text-lg md:text-xl font-bold" style={{ color }}>{value}</p>
        <p className="text-xs text-gray-600 mt-0.5">{sub}</p>
      </CardContent>
    </Card>
  );
}

export const getServerSideProps: GetServerSideProps = async () => {
  const f = serverFetch;
  const [detail, closedTrades, openTrades, equity, symbolStats, dailyPnl] = await Promise.all([
    f('/api/detail'), f('/api/trades/closed'), f('/api/trades/open'),
    f('/api/equity'), f('/api/trades/by_symbol'), f('/api/pnl/daily'),
  ]);

  return {
    props: {
      initial: {
        detail: detail || { equity: 100, total_trades: 0, total_pnl: 0, wins: 0, losses: 0, avg_win: 0, avg_loss: 0, best_trade: 0, worst_trade: 0, win_rate: 0, profit_factor: 0, max_drawdown_pct: 0 },
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
