import type { NextPage, GetServerSideProps } from 'next';
import Head from 'next/head';
import { getTrades } from '../lib/data';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';

interface Trade {
  symbol: string;
  pnl: number;
  reason: string;
}

interface DashboardProps {
  trades: Trade[];
}

const Dashboard: NextPage<DashboardProps> = ({ trades }) => {
  const equity = 100 + trades.reduce((acc, t) => acc + (t.pnl || 0), 0);
  const winRate = trades.filter(t => t.pnl > 0).length / (trades.length || 1) * 100;

  return (
    <>
      <Head>
        <title>TidoQuant Dashboard</title>
      </Head>

      <div className="min-h-screen bg-gray-50 p-6">
        <h1 className="text-3xl font-bold mb-6">TidoQuant Dashboard</h1>
        
        <div className="grid gap-6 md:grid-cols-3 mb-6">
          <Card>
            <CardHeader><CardTitle>Current Equity</CardTitle></CardHeader>
            <CardContent className="text-2xl font-bold">${equity.toFixed(2)}</CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Total Trades</CardTitle></CardHeader>
            <CardContent className="text-2xl font-bold">{trades.length}</CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Win Rate</CardTitle></CardHeader>
            <CardContent className="text-2xl font-bold">{winRate.toFixed(1)}%</CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader><CardTitle>Trade History</CardTitle></CardHeader>
          <CardContent>
            <table className="w-full">
              <thead>
                <tr>
                  <th className="text-left">Symbol</th>
                  <th className="text-left">PnL</th>
                  <th className="text-left">Reason</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t, i) => (
                  <tr key={i}>
                    <td>{t.symbol}</td>
                    <td className={t.pnl > 0 ? 'text-green-600' : 'text-red-600'}>
                        {t.pnl > 0 ? '+' : ''}{t.pnl.toFixed(2)}
                    </td>
                    <td>{t.reason}</td>
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
  const trades = getTrades();
  return { props: { trades } };
};

export default Dashboard;
