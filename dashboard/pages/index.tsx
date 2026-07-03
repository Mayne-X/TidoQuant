import type { NextPage, GetServerSideProps } from 'next';
import Head from 'next/head';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';

interface Trade {
  id: number;
  symbol: string;
  direction: string;
  pnl: number;
  reason: string;
  mayne_score: number;
  manager_decision: string;
  entered_at: string;
  exited_at: string;
}

interface DashboardProps {
  summary: {
    equity: number;
    total_trades: number;
    wins: number;
    losses: number;
    total_pnl: number;
  };
  closedTrades: Trade[];
}

const Dashboard: NextPage<DashboardProps> = ({ summary, closedTrades }) => {
  const winRate = summary.total_trades > 0
    ? ((summary.wins / summary.total_trades) * 100).toFixed(1)
    : '0.0';

  return (
    <>
      <Head>
        <title>TidoQuant Dashboard</title>
      </Head>

      <div className="min-h-screen bg-gray-50 p-6">
        <h1 className="text-3xl font-bold mb-6">TidoQuant · Multi-Agent Trading System</h1>

        <div className="grid gap-6 md:grid-cols-4 mb-6">
          <Card>
            <CardHeader><CardTitle>Current Equity</CardTitle></CardHeader>
            <CardContent className="text-2xl font-bold">
              ${summary.equity.toFixed(2)}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Total Trades</CardTitle></CardHeader>
            <CardContent className="text-2xl font-bold">
              {summary.total_trades}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Win Rate</CardTitle></CardHeader>
            <CardContent className="text-2xl font-bold">
              {winRate}%
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Total PnL</CardTitle></CardHeader>
            <CardContent className={`text-2xl font-bold ${summary.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {summary.total_pnl >= 0 ? '+' : ''}${summary.total_pnl.toFixed(2)}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader><CardTitle>Closed Trade History</CardTitle></CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">Symbol</th>
                  <th className="text-left py-2">Direction</th>
                  <th className="text-left py-2">PnL</th>
                  <th className="text-left py-2">Reason</th>
                  <th className="text-left py-2">Mayne Score</th>
                  <th className="text-left py-2">Manager</th>
                  <th className="text-left py-2">Exited</th>
                </tr>
              </thead>
              <tbody>
                {closedTrades.length === 0 && (
                  <tr><td colSpan={7} className="py-4 text-gray-400 text-center">No trades yet</td></tr>
                )}
                {closedTrades.map((t) => (
                  <tr key={t.id} className="border-b hover:bg-gray-100">
                    <td className="py-2">{t.symbol}</td>
                    <td className={`py-2 ${t.direction === 'long' ? 'text-green-600' : 'text-red-600'}`}>
                      {t.direction}
                    </td>
                    <td className={`py-2 font-mono ${t.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {t.pnl >= 0 ? '+' : ''}${t.pnl?.toFixed(2)}
                    </td>
                    <td className="py-2">{t.reason}</td>
                    <td className="py-2">{t.mayne_score}</td>
                    <td className="py-2">{t.manager_decision}</td>
                    <td className="py-2 text-gray-500 text-xs">
                      {t.exited_at ? new Date(t.exited_at + 'Z').toLocaleDateString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
    </>
  );
};

export const getServerSideProps: GetServerSideProps = async () => {
  const API = process.env.API_URL || 'http://localhost:4900';

  try {
    const [summaryRes, tradesRes] = await Promise.all([
      fetch(`${API}/api/summary`),
      fetch(`${API}/api/trades/closed`),
    ]);
    const summary = await summaryRes.json();
    const closedTrades = await tradesRes.json();
    return { props: { summary, closedTrades } };
  } catch {
    return {
      props: {
        summary: { equity: 100, total_trades: 0, wins: 0, losses: 0, total_pnl: 0 },
        closedTrades: [],
      },
    };
  }
};

export default Dashboard;
