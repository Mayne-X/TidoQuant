import { useEffect, useState, useCallback } from 'react';
import type { NextPage, GetServerSideProps } from 'next';
import Head from 'next/head';
import { 
  Card, CardHeader, CardTitle, CardContent, 
  StatCard, DataTable, Badge, Drawer, ProgressBar 
} from '@/components/ui';
import { HeaderBar } from '@/components/header-bar';
import { fetchPipeline } from '../lib/data';
import type { PipelineCycle, PipelineTrade, AgentLog } from '../lib/data';
import { cn, fmtUSD, fmtNum, relTime } from '@/components/cn';

const STAGE_ORDER = ['mayne', 'researcher', 'sentiment', 'bull_r1', 'bear_r1', 'bull_r2', 'bear_r2', 'treasury', 'manager'];
const AGENT_LABELS: Record<string, string> = {
  mayne: 'Mayne Gate', researcher: 'Researcher', sentiment: 'Sentiment', 
  bull_r1: 'Bull R1', bear_r1: 'Bear R1', bull_r2: 'Bull R2', bear_r2: 'Bear R2',
  treasury: 'Treasury', manager: 'Manager'
};

const PipelinePage: NextPage<Props> = ({ initial }) => {
  const [cycles, setCycles] = useState<PipelineCycle[]>(initial);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [expandedAgent, setExpandedAgent] = useState<AgentLog | null>(null);
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

  const cycle = cycles[selectedIdx];
  const trade = cycle?.trades?.[0];

  return (
    <>
      <Head><title>Pipeline | TidoQuant</title></Head>
      <div className="p-6 space-y-6">
        <HeaderBar title="Pipeline" subtitle={cycle ? `Cycle #${cycle.id}` : 'Waiting for signals'} live={true} polling={polling} onTogglePolling={() => setPolling(p => !p)} />

        {cycle && (
          <div className="grid grid-cols-1 gap-6">
            <Card>
              <CardHeader><CardTitle hint={`Analyzed ${cycle.trades.length} symbols`}>Pipeline Flow</CardTitle></CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {STAGE_ORDER.map(key => {
                  const agent = trade?.agents?.find(a => a.agent_name.toLowerCase().includes(key.replace('_', '')));
                  return (
                    <button
                      key={key}
                      onClick={() => agent && setExpandedAgent(agent)}
                      className={cn(
                        "px-3 py-2 rounded-lg text-xs font-medium border flex items-center gap-2 transition-all",
                        agent ? "bg-[color:var(--surface-raised)] border-[color:var(--border-strong)] hover:border-[color:var(--primary)]" : "opacity-30 border-[color:var(--border)]"
                      )}
                    >
                      {AGENT_LABELS[key]}
                      {agent?.error && <Badge tone="destructive">Error</Badge>}
                    </button>
                  );
                })}
              </CardContent>
            </Card>

            {trade && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatCard label="Mayne Score" value={trade.mayne_score || '—'} tone="info" />
                <StatCard label="Decision" value={trade.manager_decision || '—'} tone={trade.manager_decision === 'GO' ? 'success' : 'destructive'} />
                <StatCard label="Confidence" value={`${trade.manager_confidence || 0}%`} tone="warning" />
                <StatCard label="PnL" value={fmtUSD(trade.pnl || 0)} tone={trade.pnl != null && trade.pnl >= 0 ? "success" : "destructive"} />
              </div>
            )}
          </div>
        )}

        <Drawer 
          open={!!expandedAgent} onClose={() => setExpandedAgent(null)} 
          title={expandedAgent?.agent_name}
          subtitle={expandedAgent?.latency_ms ? `Latency: ${fmtNum(expandedAgent.latency_ms / 1000, 1)}s` : ''}
        >
          <div className="space-y-4">
            <div>
              <p className="text-[10px] text-[color:var(--muted-foreground)] uppercase">Prompt</p>
              <pre className="text-xs p-3 bg-white/5 rounded-lg overflow-x-auto mt-1">{expandedAgent?.prompt}</pre>
            </div>
            <div>
              <p className="text-[10px] text-[color:var(--muted-foreground)] uppercase">Response</p>
              <pre className="text-xs p-3 bg-white/5 rounded-lg overflow-x-auto mt-1">{expandedAgent?.response || expandedAgent?.error}</pre>
            </div>
          </div>
        </Drawer>
      </div>
    </>
  );
};

interface Props { initial: PipelineCycle[] }
export const getServerSideProps: GetServerSideProps = async () => {
  const data = await fetchPipeline();
  return { props: { initial: data || [] } };
};

export default PipelinePage;
