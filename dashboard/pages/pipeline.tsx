import { useEffect, useState, useCallback, useMemo } from 'react';
import type { NextPage, GetServerSideProps } from 'next';
import Head from 'next/head';
import { 
  Card, CardHeader, CardTitle, CardContent, 
  StatCard, DataTable, Badge, Drawer, Tabs 
} from '@/components/ui';
import { HeaderBar } from '@/components/header-bar';
import { fetchPipeline, serverFetch } from '../lib/data';
import type { PipelineCycle, PipelineTrade, AgentLog } from '../lib/data';
import { cn, fmtUSD, fmtNum, relTime } from '@/components/cn';
import {
  Workflow, ChevronRight, ChevronLeft, Clock, Activity,
  TrendingUp, TrendingDown, Minus, CheckCircle2, XCircle,
  AlertCircle, Loader2, FileText, Brain, MessageSquare,
  BarChart3, Shield, Target, Zap, Eye, ExternalLink,
  Search, ArrowRight, FileCode, MessageCircle,
} from 'lucide-react';

const STAGE_ORDER = [
  'mayne', 'researcher', 'sentiment',
  'bull_r1', 'bear_r1', 'bull_r2', 'bear_r2',
  'treasury', 'manager'
];
const AGENT_LABELS: Record<string, string> = {
  mayne: 'Mayne', researcher: 'Research', sentiment: 'Sentiment',
  bull_r1: 'Bull R1', bear_r1: 'Bear R1',
  bull_r2: 'Bull R2', bear_r2: 'Bear R2',
  treasury: 'Treasury', manager: 'Manager'
};
const AGENT_ICONS: Record<string, typeof Brain> = {
  mayne: Activity, researcher: Search, sentiment: MessageCircle,
  bull_r1: TrendingUp, bear_r1: TrendingDown,
  bull_r2: TrendingUp, bear_r2: TrendingDown,
  treasury: Shield, manager: Brain,
};
const AGENT_COLORS: Record<string, string> = {
  mayne: 'primary', researcher: 'info', sentiment: 'purple',
  bull_r1: 'success', bear_r1: 'destructive',
  bull_r2: 'success', bear_r2: 'destructive',
  treasury: 'warning', manager: 'primary',
};
const STATUS_BADGE: Record<string, { tone: 'success' | 'destructive' | 'warning' | 'info'; label: string }> = {
  analyzing: { tone: 'info', label: 'Analyzing' },
  open: { tone: 'success', label: 'Open' },
  closed: { tone: 'warning', label: 'Closed' },
  rejected: { tone: 'destructive', label: 'Rejected' },
  cancelled: { tone: 'destructive', label: 'Cancelled' },
};

function tryParseJSON(text: string | null | undefined): { parsed: boolean; formatted: string } {
  if (!text) return { parsed: false, formatted: '' };
  try {
    const obj = JSON.parse(text);
    return { parsed: true, formatted: JSON.stringify(obj, null, 2) };
  } catch {
    return { parsed: false, formatted: text };
  }
}

function StageIcon({ stage, className }: { stage: string; className?: string }) {
  const Icon = AGENT_ICONS[stage] || Brain;
  return <Icon className={cn("w-4 h-4", className)} />;
}

function DirBadge({ dir }: { dir: string }) {
  return (
    <Badge tone={dir === 'long' ? 'success' : 'destructive'} icon={dir === 'long' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}>
      {dir}
    </Badge>
  );
}

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

function TradeDetailCard({ trade }: { trade: PipelineTrade }) {
  const details = [
    { label: 'Entry Price', value: fmtUSD(trade.entry_price) },
    { label: 'Exit Price', value: trade.exit_price ? fmtUSD(trade.exit_price) : '—', muted: !trade.exit_price },
    { label: 'Stop Loss', value: trade.sl ? fmtUSD(trade.sl) : '—', muted: !trade.sl },
    { label: 'Take Profit', value: trade.tp ? fmtUSD(trade.tp) : '—', muted: !trade.tp },
    { label: 'Position Size', value: trade.position_size ? fmtUSD(trade.position_size) : '—', muted: !trade.position_size },
    { label: 'Leverage', value: trade.leverage ? `${trade.leverage}x` : '—', muted: !trade.leverage },
    { label: 'Duration', value: fmtDuration(trade.entered_at, trade.exited_at) },
    { label: 'Limit Price', value: trade.limit_price ? fmtUSD(trade.limit_price) : '—', muted: !trade.limit_price },
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
      {details.map(d => (
        <div key={d.label} className={cn("p-3 rounded-lg bg-white/5 border border-[color:var(--border)]", d.muted && "opacity-50")}>
          <p className="text-[10px] uppercase tracking-wider text-[color:var(--muted-foreground)] mb-1">{d.label}</p>
          <p className="font-mono font-semibold tabular">{d.value}</p>
        </div>
      ))}
    </div>
  );
}

function AgentFlow({ agents, onAgentClick }: { agents: AgentLog[]; onAgentClick: (a: AgentLog) => void }) {
  return (
    <div className="relative flex flex-wrap gap-0">
      {STAGE_ORDER.map((key, i) => {
        const agent = agents.find(a => a.agent_name.replace(/_/g, '').toLowerCase() === key.replace(/_/g, ''));
        const Icon = AGENT_ICONS[key] || Brain;
        const hasData = !!(agent?.response || agent?.error || agent?.prompt);
        const hasError = !!agent?.error;
        const latMs = agent?.latency_ms;
        const color = AGENT_COLORS[key] as string;

        return (
          <div key={key} className="flex items-center">
            <button
              onClick={() => agent && onAgentClick(agent)}
              disabled={!hasData}
              className={cn(
                "group relative flex flex-col items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-medium transition-all min-w-[72px]",
                hasData
                  ? cn(
                      "bg-[color:var(--surface)] border cursor-pointer hover:scale-105",
                      hasError
                        ? "border-[color:var(--destructive)]/40 shadow-[0_0_0_1px_rgba(239,68,68,0.2)_inset]"
                        : "border-[color:var(--border-strong)] hover:border-[color:var(--primary)] hover:shadow-[0_0_0_1px_rgba(99,102,241,0.3)_inset]"
                    )
                  : "bg-white/5 border border-[color:var(--border)] opacity-30 cursor-default"
              )}
              title={agent?.agent_name}
            >
              <div className={cn(
                "w-8 h-8 rounded-lg grid place-items-center transition-colors",
                hasData
                  ? hasError
                    ? "bg-[color:var(--destructive-soft)]"
                    : `bg-[color:var(--${color}-soft)]`
                  : "bg-white/5"
              )}>
                <Icon className={cn(
                  "w-4 h-4",
                  hasData
                    ? hasError ? "text-[color:var(--destructive-foreground)]" : `text-[color:var(--${color})]`
                    : "text-[color:var(--muted-foreground)]"
                )} />
              </div>
              <span className="text-[10px] font-semibold text-center leading-tight">{AGENT_LABELS[key]}</span>
              {latMs != null && (
                <span className="text-[9px] tabular text-[color:var(--muted-foreground)]">{latMs > 1000 ? `${(latMs / 1000).toFixed(1)}s` : `${latMs}ms`}</span>
              )}
              {hasError && <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-[color:var(--destructive)] grid place-items-center"><XCircle className="w-2.5 h-2.5 text-white" /></span>}
              {!hasData && !hasError && <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-white/10 grid place-items-center"><Minus className="w-2 h-2 text-[color:var(--muted-foreground)]" /></span>}
            </button>
            {i < STAGE_ORDER.length - 1 && (
              <ChevronRight className="w-4 h-4 mx-0.5 text-[color:var(--muted-foreground)]/30 shrink-0" />
            )}
          </div>
        );
      })}
    </div>
  );
}

function TranscriptSection({ transcript }: { transcript: string | null }) {
  if (!transcript) return null;
  const lines = transcript.split('\n');
  const sections: { agent: string; content: string[] }[] = [];
  let current: { agent: string; content: string[] } | null = null;
  for (const line of lines) {
    const match = line.match(/^\[(\w+(?: \w+)?)\]\s*/);
    if (match) {
      if (current) sections.push(current);
      current = { agent: match[1], content: [line.replace(/^\[\w+(?: \w+)?\]\s*/, '')] };
    } else if (current) {
      current.content.push(line);
    } else {
      if (!current) current = { agent: 'Info', content: [] };
      current.content.push(line);
    }
  }
  if (current) sections.push(current);

  return (
    <div className="space-y-2">
      {sections.map((s, i) => (
        <details key={i} className="group bg-white/5 rounded-lg border border-[color:var(--border)] overflow-hidden" open={sections.length <= 6}>
          <summary className="flex items-center gap-2 px-3 py-2 cursor-pointer text-xs font-semibold hover:bg-white/5 transition-colors">
            <ChevronRight className="w-3 h-3 text-[color:var(--muted-foreground)] transition-transform group-open:rotate-90" />
            {s.agent}
          </summary>
          <div className="px-3 pb-2 text-xs text-[color:var(--muted-foreground)] font-mono leading-relaxed whitespace-pre-wrap">
            {s.content.join('\n').trim() || '—'}
          </div>
        </details>
      ))}
    </div>
  );
}

function TradeView({
  trade, expandedAgent, onAgentClick, onCloseAgent,
}: {
  trade: PipelineTrade;
  expandedAgent: AgentLog | null;
  onAgentClick: (a: AgentLog) => void;
  onCloseAgent: () => void;
}) {
  const statusBadge = STATUS_BADGE[trade.status] || STATUS_BADGE.analyzing;
  const pnl = trade.pnl;
  const pnlTone = pnl != null ? (pnl >= 0 ? 'success' : 'destructive') : 'neutral';
  const decisionTone = trade.manager_decision === 'GO' ? 'success' : trade.manager_decision === 'NO-GO' ? 'destructive' : 'neutral';

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-lg font-bold tabular">{trade.symbol}</span>
        <DirBadge dir={trade.direction} />
        <Badge tone={trade.strategy === 'scalper' ? 'purple' : 'info'}>
          {trade.strategy === 'scalper' ? 'SCALPER' : 'SWING'}
        </Badge>
        <Badge tone={statusBadge.tone}>{statusBadge.label}</Badge>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Mayne Score" value={trade.mayne_score ?? '—'} tone="info" hint={trade.mayne_score != null && trade.mayne_score >= 60 ? 'Gate Passed' : 'Gate Missed'} />
        <StatCard label="Decision" value={trade.manager_decision || '—'} tone={decisionTone} />
        <StatCard label="Confidence" value={trade.manager_confidence != null ? `${trade.manager_confidence}%` : '—'} tone="warning" />
        <StatCard label="PnL" value={pnl != null ? fmtUSD(pnl) : '—'} tone={pnlTone} icon={pnl != null ? pnl >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" /> : undefined} />
        {trade.strategy === 'scalper' && trade.filter_score != null && (
          <StatCard label="Filter Score" value={`${trade.filter_score}%`} tone={trade.filter_score >= 60 ? 'success' : 'destructive'} hint={trade.filter_score >= 60 ? 'Passed' : 'Blocked'} />
        )}
        {trade.strategy === 'scalper' && trade.scalper_score != null && (
          <StatCard label="Scalper Score" value={trade.scalper_score} tone="purple" />
        )}
        {trade.limit_price != null && (
          <StatCard label="Limit Price" value={fmtUSD(trade.limit_price)} tone="info" />
        )}
      </div>

      <Card>
        <CardHeader><CardTitle>Trade Details</CardTitle></CardHeader>
        <CardContent><TradeDetailCard trade={trade} /></CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle hint={trade.agents ? `${trade.agents.filter(a => a.response).length}/${STAGE_ORDER.length} stages completed` : ''}>Agent Pipeline Flow</CardTitle></CardHeader>
        <CardContent>
          {trade.agents && trade.agents.length > 0 ? (
            <AgentFlow agents={trade.agents} onAgentClick={onAgentClick} />
          ) : (
            <p className="text-xs text-[color:var(--muted-foreground)]">No agent data recorded for this trade.</p>
          )}
        </CardContent>
      </Card>

      {trade.reason && (
        <Card>
          <CardHeader><CardTitle>Reasoning</CardTitle></CardHeader>
          <CardContent>
            <p className="text-xs text-[color:var(--muted-foreground)] leading-relaxed whitespace-pre-wrap">{trade.reason}</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle hint={`${trade.agents?.length || 0} agent outputs`}>Debate Transcript</CardTitle></CardHeader>
        <CardContent>
          {trade.debate_transcript ? (
            <TranscriptSection transcript={trade.debate_transcript} />
          ) : trade.agents && trade.agents.length > 0 ? (
            <div className="space-y-4">
              {trade.agents.map((agent, i) => {
                const resp = tryParseJSON(agent.response);
                return (
                  <details key={i} className="group bg-white/5 rounded-lg border border-[color:var(--border)] overflow-hidden">
                    <summary className="flex items-center gap-2 px-3 py-2.5 cursor-pointer text-xs font-semibold hover:bg-white/5 transition-colors">
                      <ChevronRight className="w-3 h-3 text-[color:var(--muted-foreground)] transition-transform group-open:rotate-90" />
                      <span className={cn(
                        "w-1.5 h-1.5 rounded-full shrink-0",
                        agent.error ? "bg-[color:var(--destructive)]" : agent.response ? "bg-[color:var(--success)]" : "bg-white/20"
                      )} />
                      {agent.agent_name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                      {agent.latency_ms != null && <span className="text-[10px] text-[color:var(--muted-foreground)] ml-auto tabular">{agent.latency_ms}ms</span>}
                      {agent.error && <Badge tone="destructive" className="ml-auto">Error</Badge>}
                    </summary>
                    <div className="px-3 pb-3 space-y-3">
                      <div>
                        <p className="text-[10px] text-[color:var(--muted-foreground)] uppercase mb-1 font-semibold tracking-wider">Prompt</p>
                        <pre className="text-[11px] p-3 bg-black/30 rounded-lg overflow-x-auto leading-relaxed max-h-48 overflow-y-auto">{agent.prompt}</pre>
                      </div>
                      <div>
                        <p className="text-[10px] text-[color:var(--muted-foreground)] uppercase mb-1 font-semibold tracking-wider">Response</p>
                        <pre className={cn(
                          "text-[11px] p-3 rounded-lg overflow-x-auto leading-relaxed max-h-64 overflow-y-auto",
                          resp.parsed ? "bg-black/40 text-[color:var(--success-foreground)]" : "bg-black/30"
                        )}>{resp.formatted || agent.error || '—'}</pre>
                      </div>
                    </div>
                  </details>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-[color:var(--muted-foreground)]">No transcript data available.</p>
          )}
        </CardContent>
      </Card>

      <Drawer open={!!expandedAgent} onClose={onCloseAgent}
        title={expandedAgent?.agent_name?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
        subtitle={expandedAgent?.latency_ms ? `Latency: ${fmtNum(expandedAgent.latency_ms / 1000, 1)}s` : ''}
        width="w-[700px] max-w-[94vw]"
      >
        {expandedAgent && (
          <div className="space-y-4">
            <div>
              <p className="text-[10px] text-[color:var(--muted-foreground)] uppercase tracking-wider font-semibold mb-1.5 flex items-center gap-1.5"><FileCode className="w-3 h-3" />Prompt</p>
              <pre className="text-[11px] p-3 bg-black/30 rounded-lg overflow-x-auto leading-relaxed max-h-[45vh] overflow-y-auto">{expandedAgent.prompt}</pre>
            </div>
            <div>
              <p className="text-[10px] text-[color:var(--muted-foreground)] uppercase tracking-wider font-semibold mb-1.5 flex items-center gap-1.5"><MessageSquare className="w-3 h-3" />Response</p>
              <pre className={cn(
                "text-[11px] p-3 rounded-lg overflow-x-auto leading-relaxed max-h-[45vh] overflow-y-auto",
                tryParseJSON(expandedAgent.response).parsed ? "bg-black/40 text-[color:var(--success-foreground)]" : "bg-black/30"
              )}>{tryParseJSON(expandedAgent.response).formatted || expandedAgent.error || '—'}</pre>
            </div>
            {expandedAgent.error && (
              <div>
                <p className="text-[10px] text-[color:var(--destructive-foreground)] uppercase tracking-wider font-semibold mb-1.5 flex items-center gap-1.5"><AlertCircle className="w-3 h-3" />Error</p>
                <pre className="text-[11px] p-3 bg-[color:var(--destructive-soft)] rounded-lg border border-[color:var(--destructive)]/30 overflow-x-auto">{expandedAgent.error}</pre>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
}

const PipelinePage: NextPage<Props> = ({ initial }) => {
  const [cycles, setCycles] = useState<PipelineCycle[]>(initial);
  const [selectedCycleId, setSelectedCycleId] = useState<number | null>(initial?.[0]?.id ?? null);
  const [selectedTradeIdx, setSelectedTradeIdx] = useState(0);
  const [expandedAgent, setExpandedAgent] = useState<AgentLog | null>(null);
  const [polling, setPolling] = useState(true);
  const [showEmpty, setShowEmpty] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchPipeline();
      if (data && data.length > 0) {
        setCycles(data);
        if (selectedCycleId == null || !data.some((c: PipelineCycle) => c.id === selectedCycleId)) {
          setSelectedCycleId(data[0].id);
          setSelectedTradeIdx(0);
        }
      }
    } catch { /* ignore */ }
  }, [selectedCycleId]);

  useEffect(() => {
    if (!polling) return;
    const id = setInterval(refresh, 10_000);
    return () => clearInterval(id);
  }, [polling, refresh]);

  const selectedCycle = cycles.find(c => c.id === selectedCycleId);
  const currentTrade = selectedCycle?.trades?.[selectedTradeIdx] ?? null;
  const totalTradesInCycle = selectedCycle?.trades?.length ?? 0;
  const cycleTradesWithDecisions = useMemo(() => {
    return cycles.map(c => ({
      id: c.id,
      timestamp: c.timestamp,
      tradeCount: c.trades.length,
      decisions: c.trades.map(t => t.manager_decision).filter(Boolean),
      hasError: c.trades.some(t => t.agents?.some(a => a.error)),
      swingCount: c.trades.filter(t => t.strategy !== 'scalper').length,
      scalperCount: c.trades.filter(t => t.strategy === 'scalper').length,
    }));
  }, [cycles]);

  return (
    <>
      <Head><title>Pipeline | TidoQuant</title></Head>
      <div className="flex h-screen overflow-hidden">
        <aside className="hidden md:flex flex-col w-[280px] shrink-0 border-r border-[color:var(--border)] bg-[color:var(--surface)]/40">
          <div className="p-4 border-b border-[color:var(--border)]">
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-sm font-semibold">Cycles</h2>
              <Badge tone="info">{cycles.length}</Badge>
            </div>
            <p className="text-[10px] text-[color:var(--muted-foreground)]">Click a cycle to view details</p>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {cycleTradesWithDecisions.length === 0 ? (
              <p className="text-xs text-[color:var(--muted-foreground)] p-3">No cycles recorded yet.</p>
            ) : (
              cycleTradesWithDecisions.map(c => {
                const active = c.id === selectedCycleId;
                const bestDecision = c.decisions[0] || null;
                const worstDecision = c.decisions.some(d => d === 'NO-GO') ? 'NO-GO' : bestDecision;
                return (
                  <button
                    key={c.id}
                    onClick={() => { setSelectedCycleId(c.id); setSelectedTradeIdx(0); }}
                    className={cn(
                      "w-full text-left px-3 py-2.5 rounded-xl text-xs transition-all",
                      active
                        ? "bg-[color:var(--primary-soft)] border border-[color:var(--primary)]/30 shadow-[0_0_0_1px_rgba(99,102,241,0.2)_inset]"
                        : "hover:bg-white/5 border border-transparent"
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className={cn("font-semibold", active ? "text-[color:var(--primary)]" : "text-foreground")}>Cycle #{c.id}</span>
                      <span className="text-[10px] text-[color:var(--muted-foreground)] tabular">{relTime(c.timestamp)}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      {c.tradeCount > 0 ? (
                        <>
                          <span className="text-[color:var(--muted-foreground)]">{c.tradeCount} trade{c.tradeCount !== 1 ? 's' : ''}</span>
                          {c.decisions.filter(d => d === 'GO').length > 0 && <Badge tone="success">{c.decisions.filter(d => d === 'GO').length} GO</Badge>}
                          {c.decisions.filter(d => d === 'NO-GO').length > 0 && <Badge tone="destructive">{c.decisions.filter(d => d === 'NO-GO').length} NO-GO</Badge>}
                          {c.hasError && <Badge tone="destructive">Error</Badge>}
                          {c.swingCount > 0 && <Badge tone="info">{c.swingCount} SW</Badge>}
                          {c.scalperCount > 0 && <Badge tone="purple">{c.scalperCount} SC</Badge>}
                        </>
                      ) : (
                        <span className="text-[color:var(--muted-foreground)]/60 italic">No signals</span>
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </aside>

        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <div className="p-4 pb-0">
            <HeaderBar
              title="Pipeline"
              subtitle={selectedCycle
                ? `Cycle #${selectedCycle.id} · ${relTime(selectedCycle.timestamp)} · ${selectedCycle.trades.length} trade${selectedCycle.trades.length !== 1 ? 's' : ''}`
                : 'Select a cycle'
              }
              live={selectedCycle != null}
              polling={polling}
              onTogglePolling={() => setPolling(p => !p)}
            >
              <button
                onClick={() => setShowEmpty(p => !p)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-[color:var(--border)] hover:bg-white/5 transition-colors md:hidden"
              >
                <Workflow className="w-3.5 h-3.5" />
                Cycles
              </button>
            </HeaderBar>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {currentTrade ? (
              <div className="max-w-[1100px] mx-auto space-y-0">
                {totalTradesInCycle > 1 && (
                  <div className="flex items-center justify-between mb-4">
                    <Tabs
                      value={String(selectedTradeIdx)}
                      onValueChange={v => setSelectedTradeIdx(Number(v))}
                      items={selectedCycle!.trades.map((t, i) => ({
                        value: String(i),
                        label: `${t.symbol} ${t.direction}`,
                        right: (
                          <div className="flex items-center gap-1">
                            <Badge tone={t.strategy === 'scalper' ? 'purple' : 'info'}>{t.strategy === 'scalper' ? 'SC' : 'SW'}</Badge>
                            {t.manager_decision && <Badge tone={t.manager_decision === 'GO' ? 'success' : 'destructive'}>{t.manager_decision}</Badge>}
                          </div>
                        ),
                      }))}
                    />
                    <span className="text-[10px] text-[color:var(--muted-foreground)] tabular">{selectedTradeIdx + 1} / {totalTradesInCycle}</span>
                  </div>
                )}
                <TradeView
                  trade={currentTrade}
                  expandedAgent={expandedAgent}
                  onAgentClick={setExpandedAgent}
                  onCloseAgent={() => setExpandedAgent(null)}
                />
              </div>
            ) : selectedCycle ? (
              <div className="max-w-[480px] mx-auto text-center py-20">
                <div className="w-16 h-16 rounded-2xl bg-white/5 border border-[color:var(--border)] grid place-items-center mx-auto mb-4">
                  <Minus className="w-7 h-7 text-[color:var(--muted-foreground)]/40" />
                </div>
                <h3 className="text-sm font-semibold mb-1">No Trades in This Cycle</h3>
                <p className="text-xs text-[color:var(--muted-foreground)]">All symbols failed the Mayne gate check (need score &ge;60). Select another cycle.</p>
              </div>
            ) : (
              <div className="max-w-[480px] mx-auto text-center py-20">
                <div className="w-16 h-16 rounded-2xl bg-white/5 border border-[color:var(--border)] grid place-items-center mx-auto mb-4">
                  <Loader2 className="w-7 h-7 text-[color:var(--muted-foreground)]/40 animate-spin" />
                </div>
                <h3 className="text-sm font-semibold mb-1">Waiting for Pipeline Data</h3>
                <p className="text-xs text-[color:var(--muted-foreground)]">The system will auto-refresh when new cycle data is available.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {showEmpty && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowEmpty(false)} />
          <div className="absolute left-0 top-0 bottom-0 w-[280px] bg-[color:var(--surface)] border-r border-[color:var(--border)] p-4 overflow-y-auto z-50">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold">Cycles</h2>
              <button onClick={() => setShowEmpty(false)} className="text-xs text-[color:var(--muted-foreground)]">Close</button>
            </div>
            {cycleTradesWithDecisions.map(c => {
              const active = c.id === selectedCycleId;
              return (
                <button
                  key={c.id}
                  onClick={() => { setSelectedCycleId(c.id); setSelectedTradeIdx(0); setShowEmpty(false); }}
                  className={cn("w-full text-left px-3 py-2.5 rounded-xl text-xs transition-all block mb-1", active ? "bg-[color:var(--primary-soft)] border border-[color:var(--primary)]/30" : "hover:bg-white/5 border border-transparent")}
                >
                  <div className="flex items-center justify-between">
                    <span className={cn("font-semibold", active ? "text-[color:var(--primary)]" : "text-foreground")}>Cycle #{c.id}</span>
                    <span className="text-[10px] text-[color:var(--muted-foreground)] tabular">{relTime(c.timestamp)}</span>
                  </div>
                  {c.tradeCount > 0 ? (
                    <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                      <span className="text-[color:var(--muted-foreground)]">{c.tradeCount} trade{c.tradeCount !== 1 ? 's' : ''}</span>
                      {c.decisions.filter(d => d === 'GO').length > 0 && <Badge tone="success">{c.decisions.filter(d => d === 'GO').length} GO</Badge>}
                      {c.decisions.filter(d => d === 'NO-GO').length > 0 && <Badge tone="destructive">{c.decisions.filter(d => d === 'NO-GO').length} NO-GO</Badge>}
                      {c.swingCount > 0 && <Badge tone="info">{c.swingCount} SW</Badge>}
                      {c.scalperCount > 0 && <Badge tone="purple">{c.scalperCount} SC</Badge>}
                    </div>
                  ) : (
                    <span className="text-[10px] text-[color:var(--muted-foreground)]/60 mt-1 block">No signals</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
};

interface Props { initial: PipelineCycle[]; }
export const getServerSideProps: GetServerSideProps = async () => {
  try {
    const data = await serverFetch('/api/pipeline');
    return { props: { initial: data || [] } };
  } catch {
    return { props: { initial: [] } };
  }
};

export default PipelinePage;