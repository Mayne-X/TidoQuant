import { render, screen, fireEvent, act } from '@testing-library/react';
import PipelinePage from '../pages/pipeline';
import type { PipelineCycle } from '../lib/data';

jest.mock('../lib/data', () => ({
  serverFetch: jest.fn().mockResolvedValue([]),
  fetchPipeline: jest.fn().mockResolvedValue([]),
}));

const mockAgent = (name: string, lat: number, resp = 'ok') => ({
  agent_name: name,
  prompt: `Prompt for ${name}`,
  response: resp,
  latency_ms: lat,
  error: null,
});

const fullAgents = [
  mockAgent('MayneGate', 150),
  mockAgent('ResearcherAgent', 3200),
  mockAgent('SentimentAgent', 2100),
  mockAgent('BullRound1', 4100),
  mockAgent('BearRound1', 3800),
  mockAgent('BullRound2', 2900),
  mockAgent('BearRound2', 3500),
  mockAgent('TreasuryAgent', 1800),
  mockAgent('ManagerAgent', 900),
];

function mockTrade(overrides: Partial<any> = {}) {
  return {
    id: 1, symbol: 'BTCUSDT', direction: 'long', pnl: 0,
    reason: null, status: 'open', mayne_score: 72,
    manager_decision: 'GO', manager_confidence: 80,
    debate_transcript: null,
    entry_price: 50000, exit_price: null,
    sl: 49000, tp: 52000,
    position_size: 10, leverage: 2,
    entered_at: '2026-07-03 10:00:00', exited_at: null,
    agents: [],
    ...overrides,
  };
}

function makeCycle(id: number, equity: number, trades: any[]): PipelineCycle {
  const ts = new Date(2026, 6, 3, 10, id).toISOString().replace('Z', '');
  return { id, equity, timestamp: ts, trades };
}

describe('PipelinePage', () => {
  const emptyInitial: PipelineCycle[] = [];

  it('renders the title and navigation', () => {
    render(<PipelinePage initial={emptyInitial} />);
    expect(screen.getByText('Pipeline')).toBeInTheDocument();
    expect(screen.getByText('← Dashboard')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /dashboard/i })).toHaveAttribute('href', '/');
  });

  it('shows idle state when no cycles', () => {
    render(<PipelinePage initial={emptyInitial} />);
    expect(screen.getByText(/idle/i)).toBeInTheDocument();
  });

  it('shows waiting message when no cycles selected', () => {
    render(<PipelinePage initial={emptyInitial} />);
    expect(screen.getByText(/no pipeline cycles yet/i)).toBeInTheDocument();
  });

  it('renders cycles count in status when data present', () => {
    const cycles = [makeCycle(1, 102.5, [])];
    render(<PipelinePage initial={cycles} />);
    expect(screen.getByText(/1 cycles/)).toBeInTheDocument();
  });

  it('displays cycle scrubber with cycle ID and date', () => {
    const cycles = [makeCycle(5, 105.0, [])];
    render(<PipelinePage initial={cycles} />);
    expect(screen.getAllByText(/#5/).length).toBeGreaterThanOrEqual(1);
  });

  it('shows cycle header with equity', () => {
    const cycles = [makeCycle(1, 110.5, [])];
    render(<PipelinePage initial={cycles} />);
    expect(screen.getByText(/110.50/)).toBeInTheDocument();
  });

  it('shows no trade message when cycle has no trades', () => {
    const cycles = [makeCycle(1, 100.0, [])];
    render(<PipelinePage initial={cycles} />);
    expect(screen.getByText(/mayne gate not triggered/i)).toBeInTheDocument();
  });

  it('renders trade card with symbol and PnL', () => {
    const trade = mockTrade({
      id: 42, symbol: 'ETHUSDT', pnl: 50.0,
      reason: 'TP_HIT', status: 'closed',
      debate_transcript: 'Bull vs Bear debate',
      agents: fullAgents,
    });
    const cycles = [makeCycle(1, 102.0, [trade])];
    render(<PipelinePage initial={cycles} />);
    expect(screen.getByText('ETHUSDT')).toBeInTheDocument();
    expect(screen.getByText(/\$50\.00/)).toBeInTheDocument();
  });

  it('shows direction badge on trade card', () => {
    const trade = mockTrade({
      direction: 'short', mayne_score: 68,
      manager_decision: 'NO-GO', manager_confidence: 0,
      agents: [],
    });
    const cycles = [makeCycle(1, 100.0, [trade])];
    render(<PipelinePage initial={cycles} />);
    expect(screen.getByText('SHORT')).toBeInTheDocument();
  });

  it('expands trade card on click to show details', () => {
    const trade = mockTrade({
      pnl: 100.0, reason: 'TP_HIT', status: 'closed', mayne_score: 75,
      manager_decision: 'GO', manager_confidence: 85,
      debate_transcript: 'Bull: strong momentum\nBear: overbought',
      entered_at: '2026-07-03 10:00:00', exited_at: '2026-07-03 12:00:00',
      agents: fullAgents,
    });
    const cycles = [makeCycle(1, 102.0, [trade])];
    render(<PipelinePage initial={cycles} />);

    const toggle = screen.getByText(/BTCUSDT/).closest('button')!;
    act(() => fireEvent.click(toggle));

    expect(screen.getByText('Mayne Score')).toBeInTheDocument();
    expect(screen.getByText('75')).toBeInTheDocument();
    expect(screen.getByText('Debate Transcript')).toBeInTheDocument();
    expect(screen.getByText(/Bull: strong momentum/)).toBeInTheDocument();
  });

  it('expands agent detail card on click', () => {
    const trade = mockTrade({ agents: fullAgents });
    const cycles = [makeCycle(1, 100.0, [trade])];
    render(<PipelinePage initial={cycles} />);

    const toggle = screen.getByText(/BTCUSDT/).closest('button')!;
    act(() => fireEvent.click(toggle));

    const mayneGate = screen.getAllByText('Mayne Gate')[0];
    act(() => fireEvent.click(mayneGate));

    expect(screen.getByText('Prompt')).toBeInTheDocument();
    expect(screen.getByText('Response')).toBeInTheDocument();
    expect(screen.getByText(/Prompt for MayneGate/)).toBeInTheDocument();
  });

  it('shows latency on agent blocks', () => {
    const trade = mockTrade({ agents: fullAgents });
    const cycles = [makeCycle(1, 100.0, [trade])];
    render(<PipelinePage initial={cycles} />);
    expect(screen.getByText('0.1s')).toBeInTheDocument();
    expect(screen.getByText('3.2s')).toBeInTheDocument();
  });

  it('renders pipeline flow with all 9 agent stages', () => {
    const trade = mockTrade({ agents: [] });
    const cycles = [makeCycle(1, 100.0, [trade])];
    render(<PipelinePage initial={cycles} />);
    expect(screen.getByText('Mayne Gate')).toBeInTheDocument();
    expect(screen.getByText('Researcher')).toBeInTheDocument();
    expect(screen.getByText('Sentiment')).toBeInTheDocument();
    expect(screen.getByText('Bull R1')).toBeInTheDocument();
    expect(screen.getByText('Bear R1')).toBeInTheDocument();
    expect(screen.getByText('Bull R2')).toBeInTheDocument();
    expect(screen.getByText('Bear R2')).toBeInTheDocument();
    expect(screen.getByText('Treasury')).toBeInTheDocument();
    expect(screen.getByText('Manager')).toBeInTheDocument();
  });

  it('has pause/live toggle button', () => {
    const cycles = [makeCycle(1, 100.0, [])];
    render(<PipelinePage initial={cycles} />);
    expect(screen.getByText(/Live 10s/)).toBeInTheDocument();
  });

  it('toggles polling on button click', () => {
    const cycles = [makeCycle(1, 100.0, [])];
    render(<PipelinePage initial={cycles} />);
    const btn = screen.getByText(/Live 10s/);
    act(() => fireEvent.click(btn));
    expect(screen.getByText(/Paused/)).toBeInTheDocument();
  });

  it('shows error state on agent blocks via CSS class', () => {
    const errAgent = { ...fullAgents[0], error: 'LLM timeout' };
    const trade = mockTrade({
      manager_decision: 'NO-GO', manager_confidence: 0,
      agents: [errAgent, ...fullAgents.slice(1)],
    });
    const cycles = [makeCycle(1, 100.0, [trade])];
    render(<PipelinePage initial={cycles} />);
    const tradeBtn = screen.getByText(/BTCUSDT/).closest('button')!;
    act(() => fireEvent.click(tradeBtn));
    const mayneGate = screen.getAllByText('Mayne Gate')[0];
    act(() => fireEvent.click(mayneGate));
    expect(screen.getByText('Error: LLM timeout')).toBeInTheDocument();
  });

  it('handles missing agents gracefully', () => {
    const trade = mockTrade({
      pnl: null, mayne_score: null,
      manager_decision: null, manager_confidence: null,
      agents: [],
    });
    const cycles = [makeCycle(1, 100.0, [trade])];
    render(<PipelinePage initial={cycles} />);
    expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
  });

  it('cycles scrubber allows switching between cycles', () => {
    const c1 = makeCycle(1, 100.0, []);
    const c2 = makeCycle(2, 105.0, []);
    render(<PipelinePage initial={[c1, c2]} />);
    expect(screen.getAllByText(/#1/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/#2/).length).toBeGreaterThanOrEqual(1);
    act(() => fireEvent.click(screen.getAllByText(/#2/)[0]));
    expect(screen.getByText(/Cycle #2/)).toBeInTheDocument();
  });

  it('shows auto-refresh footer text', () => {
    render(<PipelinePage initial={[]} />);
    expect(screen.getByText(/auto-refreshes every 10s/i)).toBeInTheDocument();
    expect(screen.getByText(/multi-timeframe/i)).toBeInTheDocument();
  });

  it('renders agent pipeline log table when trade has agents', () => {
    const trade = mockTrade({
      pnl: 50.0, reason: 'TP_HIT', status: 'closed',
      agents: fullAgents,
    });
    const cycles = [makeCycle(1, 102.0, [trade])];
    render(<PipelinePage initial={cycles} />);
    const toggle = screen.getByText(/BTCUSDT/).closest('button')!;
    act(() => fireEvent.click(toggle));
    expect(screen.getByText('Agent Pipeline Log')).toBeInTheDocument();
    expect(screen.getByText('Latency')).toBeInTheDocument();
    expect(screen.getByText('Response Preview')).toBeInTheDocument();
  });
});
