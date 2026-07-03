import { useEffect, useState, useCallback } from 'react';
import type { NextPage, GetServerSideProps } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import { serverFetch, fetchPipeline } from '../lib/data';
import type { PipelineCycle, PipelineTrade, AgentLog } from '../lib/data';

const C = {
  green: '#22c55e', red: '#ef4444', amber: '#f59e0b', blue: '#3b82f6',
  purple: '#a855f7', cyan: '#06b6d4', orange: '#f97316', pink: '#ec4899',
  gray: '#6b7280',
};

const AGENT_STYLES: Record<string, { label: string; color: string; icon: string }> = {
  mayne:       { label: 'Mayne Gate',     color: C.cyan,    icon: '🔒' },
  researcher:  { label: 'Researcher',      color: C.blue,   icon: '📊' },
  sentiment:   { label: 'Sentiment',       color: C.purple, icon: '📰' },
  bull_r1:     { label: 'Bull R1',         color: C.green,  icon: '🐂' },
  bear_r1:     { label: 'Bear R1',         color: C.red,    icon: '🐻' },
  bull_r2:     { label: 'Bull R2',         color: C.green,  icon: '🐂' },
  bear_r2:     { label: 'Bear R2',         color: C.red,    icon: '🐻' },
  treasury:    { label: 'Treasury',        color: C.amber,  icon: '💰' },
  manager:     { label: 'Manager',         color: C.pink,   icon: '🎯' },
};

const STAGE_ORDER = ['mayne', 'researcher', 'sentiment', 'bull_r1', 'bear_r1', 'bull_r2', 'bear_r2', 'treasury', 'manager'];

const AGENT_KEY_MAP: Record<string, string> = {
  MayneGate: 'mayne',
  ResearcherAgent: 'researcher',
  SentimentAgent: 'sentiment',
  BullRound1: 'bull_r1',
  BearRound1: 'bear_r1',
  BullRound2: 'bull_r2',
  BearRound2: 'bear_r2',
  TreasuryAgent: 'treasury',
  ManagerAgent: 'manager',
};

function fmt(n: number) { return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
function fmtTs(ts: string) { return new Date(ts + 'Z').toLocaleString(); }

interface Props { initial: PipelineCycle[] }

const PipelinePage: NextPage<Props> = ({ initial }) => {
  const [cycles, setCycles] = useState<PipelineCycle[]>(initial);
  const [selectedCycle, setSelectedCycle] = useState(0);
  const [expandedTrade, setExpandedTrade] = useState<number | null>(null);
  const [expandedAgent, setExpandedAgent] = useState<number | null>(null);
  const [polling, setPolling] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchPipeline();
      if (data && data.length > 0) setCycles(data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (!polling) return;
    const id = setInterval(refresh, 10_000);
    return () => clearInterval(id);
  }, [polling, refresh]);

  const cycle = cycles[selectedCycle];
  const trade = cycle?.trades?.[0];

  return (
    <>
      <Head><title>TidoQuant — Pipeline</title></Head>
      <div className="min-h-screen bg-gray-950 text-gray-100 p-4 md:p-6">
        <div className="max-w-7xl mx-auto space-y-6">

          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/" className="text-gray-500 hover:text-gray-300 transition-colors text-sm">
                ← Dashboard
              </Link>
              <h1 className="text-xl md:text-2xl font-bold tracking-tight">Pipeline</h1>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                {cycles.length > 0 ? `${cycles.length} cycles` : 'Idle'}
              </span>
              <button onClick={() => { setPolling(p => !p); refresh(); }}
                className="px-3 py-1 rounded text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 transition-colors">
                {polling ? 'Live 10s' : 'Paused'}
              </button>
            </div>
          </div>

          {/* Cycle Scrubber */}
          {cycles.length > 0 && (
            <div className="flex items-center gap-2 overflow-x-auto pb-1">
              {cycles.map((c, i) => (
                <button key={c.id} onClick={() => { setSelectedCycle(i); setExpandedTrade(null); setExpandedAgent(null); }}
                  className={`shrink-0 px-3 py-1.5 rounded-lg text-xs font-mono transition-all
                    ${i === selectedCycle
                      ? 'bg-blue-600/30 border border-blue-500/50 text-blue-200'
                      : 'bg-gray-800/50 border border-gray-700/50 text-gray-400 hover:bg-gray-700/50'}`}>
                  #{c.id} {fmtTs(c.timestamp).split(',')[0]}
                </button>
              ))}
            </div>
          )}

          {!cycle ? (
            <div className="text-center py-20 text-gray-600">
              <p className="text-4xl mb-4">⏳</p>
              <p>No pipeline cycles yet. Waiting for Mayne gate to trigger...</p>
            </div>
          ) : (
            <>
              {/* Cycle Header */}
              <div className="flex items-center gap-3 text-sm text-gray-400">
                <span className="font-semibold text-gray-200">Cycle #{cycle.id}</span>
                <span className="w-1 h-1 rounded-full bg-gray-700" />
                <span>{fmtTs(cycle.timestamp)}</span>
                <span className="w-1 h-1 rounded-full bg-gray-700" />
                <span>Equity: <span className={cycle.equity >= 100 ? 'text-green-400' : 'text-red-400'}>${fmt(cycle.equity)}</span></span>
                <span className="w-1 h-1 rounded-full bg-gray-700" />
                <span>Trades: {cycle.trades.length}</span>
              </div>

              {/* Pipeline Flow */}
              <div className="relative">
                <div className="flex items-center gap-1 md:gap-2 overflow-x-auto pb-2">
                  {STAGE_ORDER.map((key, i) => {
                    const style = AGENT_STYLES[key];
                    const agent = trade?.agents?.find(a => AGENT_KEY_MAP[a.agent_name] === key);
                    const hasData = !!agent;
                    const hasError = agent?.error;
                    return (
                      <div key={key} className="shrink-0 flex items-center gap-1 md:gap-2">
                        <div
                          className={`relative px-2 md:px-3 py-2 rounded-lg text-xs border transition-all
                            ${!hasData ? 'opacity-30 border-gray-800 bg-gray-900/30' :
                              hasError ? 'border-red-500/50 bg-red-900/20' :
                              i >= 6 ? 'border-amber-500/30 bg-amber-900/10' :
                              'border-gray-700/50 bg-gray-800/50 hover:bg-gray-700/50 cursor-pointer'}`}
                          onClick={() => { if (hasData && agent) setExpandedAgent(expandedAgent === i ? null : i); }}>
                          <div className="flex items-center gap-1.5">
                            <span>{style.icon}</span>
                            <span className="font-medium text-gray-200">{style.label}</span>
                            {hasData && <span className="w-1.5 h-1.5 rounded-full bg-green-400" />}
                            {hasError && <span className="w-1.5 h-1.5 rounded-full bg-red-400" />}
                          </div>
                          {agent?.latency_ms != null && (
                            <div className="text-[10px] text-gray-500 mt-0.5">{(agent.latency_ms / 1000).toFixed(1)}s</div>
                          )}
                        </div>
                        {i < STAGE_ORDER.length - 1 && (
                          <div className={`w-2 h-0.5 ${hasData ? 'bg-gray-600' : 'bg-gray-800'}`} />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Expanded Agent Detail */}
              {expandedAgent != null && trade?.agents?.[expandedAgent] && (
                <AgentDetailCard agent={trade.agents[expandedAgent]} stage={STAGE_ORDER[expandedAgent]} />
              )}

              {/* Trades */}
              <div className="space-y-3">
                {cycle.trades.length === 0 && (
                  <div className="text-center py-8 text-gray-600 text-sm">No trade in this cycle — Mayne gate not triggered</div>
                )}
                {cycle.trades.map(t => (
                  <TradeCard key={t.id} trade={t} expanded={expandedTrade === t.id}
                    onToggle={() => setExpandedTrade(expandedTrade === t.id ? null : t.id)} />
                ))}
              </div>
            </>
          )}

          <div className="text-center text-xs text-gray-700 pb-8">
            Pipeline auto-refreshes every 10s · Multi-timeframe analysis: 1h / 4h / 12h
          </div>
        </div>
      </div>
    </>
  );
};

function AgentDetailCard({ agent, stage }: { agent: AgentLog; stage: string }) {
  const style = AGENT_STYLES[stage] || { label: agent.agent_name, color: '#6b7280', icon: '🤖' };
  return (
    <div className="border border-gray-700/50 rounded-lg bg-gray-900/40 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span>{style.icon}</span>
        <span className="font-semibold text-sm" style={{ color: style.color }}>{style.label}</span>
        {agent.latency_ms != null && (
          <span className="text-xs text-gray-500">{(agent.latency_ms / 1000).toFixed(1)}s</span>
        )}
        {agent.error && <span className="text-xs text-red-400 ml-auto">Error: {agent.error}</span>}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="space-y-1">
          <p className="text-[10px] text-gray-500 uppercase tracking-wider">Prompt</p>
          <pre className="text-xs text-gray-300 bg-gray-950/60 rounded p-2 max-h-40 overflow-y-auto whitespace-pre-wrap">{agent.prompt}</pre>
        </div>
        <div className="space-y-1">
          <p className="text-[10px] text-gray-500 uppercase tracking-wider">Response</p>
          <pre className="text-xs text-gray-300 bg-gray-950/60 rounded p-2 max-h-40 overflow-y-auto whitespace-pre-wrap">{agent.response || agent.error || '—'}</pre>
        </div>
      </div>
    </div>
  );
}

function TradeCard({ trade, expanded, onToggle }: { trade: PipelineTrade; expanded: boolean; onToggle: () => void }) {
  const pnl = trade.pnl;
  const mgr = trade.manager_decision;
  const isGo = mgr === 'GO';
  const closed = trade.status === 'closed';

  const duration = trade.entered_at && trade.exited_at
    ? ((new Date(trade.exited_at + 'Z').getTime() - new Date(trade.entered_at + 'Z').getTime()) / 1000).toFixed(0)
    : null;
  const ret = trade.position_size && trade.position_size > 0 && trade.leverage && trade.leverage > 0
    ? ((pnl || 0) / (trade.position_size / trade.leverage)) * 100
    : null;

  return (
    <div className={`border rounded-lg transition-all ${closed && pnl != null && pnl >= 0 ? 'border-green-800/40' : closed && pnl != null && pnl < 0 ? 'border-red-800/40' : 'border-gray-700/50'} bg-gray-900/40`}>
      <button onClick={onToggle} className="w-full text-left p-4 flex items-center justify-between gap-4 hover:bg-gray-800/20 transition-colors">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="font-mono font-bold text-sm">{trade.symbol}</span>
          <span className={`text-xs px-2 py-0.5 rounded font-medium ${trade.direction === 'long' ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'}`}>
            {trade.direction.toUpperCase()}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded font-medium ${isGo ? 'bg-green-900/40 text-green-300' : 'bg-red-900/40 text-red-300'}`}>
            {mgr || '—'}
          </span>
          {trade.manager_confidence != null && (
            <span className="text-xs text-gray-400">{trade.manager_confidence}%</span>
          )}
        </div>
        <div className="flex items-center gap-4">
          {pnl != null && (
            <span className={`font-mono text-sm font-bold ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {pnl >= 0 ? '+' : ''}${fmt(pnl)}
            </span>
          )}
          <span className="text-gray-600 text-xs">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-800/50 pt-3">
          {/* Mayne + Manager Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <Stat label="Mayne Score" value={trade.mayne_score?.toString() || '—'} color={C.cyan} />
            <Stat label="Manager Decision" value={mgr || '—'} color={isGo ? C.green : C.red} />
            <Stat label="Confidence" value={trade.manager_confidence != null ? `${trade.manager_confidence}%` : '—'} color={C.amber} />
            {pnl != null && <Stat label="PnL" value={`${pnl >= 0 ? '+' : ''}$${fmt(pnl)}`} color={pnl >= 0 ? C.green : C.red} />}
          </div>

          {/* Entry / Exit / SL / TP / Size / Leverage */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <Stat label="Entry" value={`$${fmt(trade.entry_price)}`} color={C.blue} />
            <Stat label="SL" value={trade.sl ? `$${fmt(trade.sl)}` : '—'} color={C.red} />
            <Stat label="TP" value={trade.tp ? `$${fmt(trade.tp)}` : '—'} color={C.green} />
            <Stat label="Exit" value={trade.exit_price ? `$${fmt(trade.exit_price)}` : '—'} color={C.cyan} />
            <Stat label="Size" value={trade.position_size ? `$${fmt(trade.position_size)}` : '—'} color={C.purple} />
            <Stat label="Leverage" value={trade.leverage ? `${trade.leverage}x` : '—'} color={C.purple} />
            <Stat label="Return" value={ret != null ? `${ret >= 0 ? '+' : ''}${ret.toFixed(1)}%` : '—'} color={ret != null && ret >= 0 ? C.green : C.red} />
            <Stat label="Duration" value={duration ? `${+duration >= 3600 ? `${(+duration / 3600).toFixed(1)}h` : `${(+duration / 60).toFixed(0)}m`}` : '—'} color={C.orange} />
          </div>

          {/* Debate Transcript */}
          {trade.debate_transcript && (
            <div className="space-y-1">
              <p className="text-[10px] text-gray-500 uppercase tracking-wider">Debate Transcript</p>
              <pre className="text-xs text-gray-400 bg-gray-950/60 rounded p-3 max-h-48 overflow-y-auto whitespace-pre-wrap font-mono">
                {trade.debate_transcript}
              </pre>
            </div>
          )}

          {/* Agent Logs Table */}
          {trade.agents && trade.agents.length > 0 && (
            <div className="space-y-1">
              <p className="text-[10px] text-gray-500 uppercase tracking-wider">Agent Pipeline Log</p>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead><tr className="border-b border-gray-800 text-gray-500">
                    <th className="text-left py-1 pr-2">Agent</th>
                    <th className="text-left py-1 px-2">Latency</th>
                    <th className="text-left py-1 px-2">Error</th>
                    <th className="text-left py-1 pl-2">Response Preview</th>
                  </tr></thead>
                  <tbody>
                    {trade.agents.map((a, i) => (
                      <tr key={i} className="border-b border-gray-800/30 hover:bg-gray-800/20">
                        <td className="py-1.5 pr-2 font-medium" style={{ color: AGENT_STYLES[AGENT_KEY_MAP[a.agent_name]]?.color || '#9ca3af' }}>
                          {AGENT_STYLES[AGENT_KEY_MAP[a.agent_name]]?.label || a.agent_name}
                        </td>
                        <td className="py-1.5 px-2 text-gray-500">{a.latency_ms != null ? `${(a.latency_ms / 1000).toFixed(1)}s` : '—'}</td>
                        <td className="py-1.5 px-2">{a.error ? <span className="text-red-400">{a.error}</span> : <span className="text-gray-600">—</span>}</td>
                        <td className="py-1.5 pl-2 text-gray-500 truncate max-w-[200px]">
                          {a.response ? a.response.slice(0, 120).replace(/\n/g, ' ') + (a.response.length > 120 ? '...' : '') : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Timing */}
          <div className="flex gap-4 text-[10px] text-gray-600">
            <span>Entered: {fmtTs(trade.entered_at)}</span>
            {trade.exited_at && <span>Exited: {fmtTs(trade.exited_at)}</span>}
            {trade.reason && <span>Reason: {trade.reason}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-gray-800/30 rounded p-2.5">
      <p className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</p>
      <p className="text-sm font-bold font-mono mt-0.5" style={{ color }}>{value}</p>
    </div>
  );
}

export const getServerSideProps: GetServerSideProps = async () => {
  try {
    const data = await serverFetch('/api/pipeline');
    return { props: { initial: data || [] } };
  } catch {
    return { props: { initial: [] } };
  }
};

export default PipelinePage;
