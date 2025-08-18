"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface Position {
  quantity: number;
  avg_price_usd: number;
  market_value_usd: number;
  unrealized_pnl_usd: number;
  pnl_pct: number;
}

interface PortfolioSummary {
  timestamp: string;
  initial_balance_usd: number;
  cash_usd: number;
  total_market_value_usd: number;
  total_cost_basis_usd: number;
  total_pnl_usd: number;
  total_pnl_pct: number;
  total_fees_usd: number;
  trades_executed: number;
  arbitrage_trades: number;
  positions: Record<string, Position>;
}

interface Trade {
  id: string;
  symbol: string;
  side: string;
  quantity: number;
  price_usd: number;
  total_usd: number;
  venue: string;
  timestamp: string;
  fees_usd: number;
  arbitrage_profit_bps?: number;
}

interface ArbitrageOpportunity {
  symbol: string;
  buy_venue: string;
  sell_venue: string;
  buy_price: number;
  sell_price: number;
  spread_bps: number;
  estimated_profit_usd: number;
  max_trade_size: number;
  confidence_score: number;
  timestamp: string;
  expires_at: string;
}

export default function PortfolioAnalysis() {
  // Portfolio state
  const [portfolioSummary, setPortfolioSummary] = useState<PortfolioSummary | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [arbitrageOpportunities, setArbitrageOpportunities] = useState<ArbitrageOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch portfolio data
  useEffect(() => {
    fetchPortfolioData();
    const interval = setInterval(fetchPortfolioData, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      
      // Fetch portfolio summary
      const summaryResponse = await fetch('/api/portfolio/summary');
      if (summaryResponse.ok) {
        const summary = await summaryResponse.json();
        setPortfolioSummary(summary);
      }
      
      // Fetch recent trades
      const tradesResponse = await fetch('/api/portfolio/trades?limit=20');
      if (tradesResponse.ok) {
        const tradesData = await tradesResponse.json();
        setTrades(tradesData.trades);
      }
      
      // Fetch arbitrage opportunities
      const opportunitiesResponse = await fetch('/api/arbitrage/opportunities?limit=10');
      if (opportunitiesResponse.ok) {
        const opportunitiesData = await opportunitiesResponse.json();
        setArbitrageOpportunities(opportunitiesData.opportunities);
      }
      
      setError(null);
    } catch (err) {
      setError('Failed to fetch portfolio data');
      console.error('Error fetching portfolio data:', err);
    } finally {
      setLoading(false);
    }
  };

  const resetPortfolio = async () => {
    try {
      const response = await fetch('/api/portfolio/reset', { method: 'POST' });
      if (response.ok) {
        await fetchPortfolioData(); // Refresh data
      }
    } catch (err) {
      console.error('Error resetting portfolio:', err);
    }
  };

  const executeArbitrage = async (opportunity: ArbitrageOpportunity) => {
    try {
      const tradeSize = Math.min(1000, opportunity.max_trade_size); // Use $1000 or max trade size
      const response = await fetch('/api/arbitrage/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: opportunity.symbol,
          trade_size_usd: tradeSize
        })
      });
      
      if (response.ok) {
        await fetchPortfolioData(); // Refresh data
      }
    } catch (err) {
      console.error('Error executing arbitrage:', err);
    }
  };

  if (loading && !portfolioSummary) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center">Loading portfolio data...</div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-red-500">Error: {error}</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Portfolio Overview */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Portfolio Overview</CardTitle>
              <CardDescription>
                Real-time portfolio performance and arbitrage execution
              </CardDescription>
            </div>
            <Button onClick={resetPortfolio} variant="outline">
              Reset Portfolio
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {portfolioSummary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold">
                  ${portfolioSummary.total_market_value_usd.toLocaleString()}
                </div>
                <div className="text-sm text-muted-foreground">Total Value</div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${
                  portfolioSummary.total_pnl_usd >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  ${portfolioSummary.total_pnl_usd.toLocaleString()}
                </div>
                <div className="text-sm text-muted-foreground">
                  P&L ({portfolioSummary.total_pnl_pct.toFixed(2)}%)
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">
                  ${portfolioSummary.cash_usd.toLocaleString()}
                </div>
                <div className="text-sm text-muted-foreground">Available Cash</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {portfolioSummary.arbitrage_trades}
                </div>
                <div className="text-sm text-muted-foreground">Arbitrage Trades</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Tabs defaultValue="positions" className="space-y-4">
        <TabsList>
          <TabsTrigger value="positions">Positions</TabsTrigger>
          <TabsTrigger value="arbitrage">Arbitrage Opportunities</TabsTrigger>
          <TabsTrigger value="trades">Trade History</TabsTrigger>
        </TabsList>

        {/* Positions Tab */}
        <TabsContent value="positions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Current Positions</CardTitle>
              <CardDescription>
                Asset positions and unrealized P&L
              </CardDescription>
            </CardHeader>
            <CardContent>
              {portfolioSummary && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Asset</TableHead>
                      <TableHead>Quantity</TableHead>
                      <TableHead>Avg Price</TableHead>
                      <TableHead>Market Value</TableHead>
                      <TableHead>Unrealized P&L</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Object.entries(portfolioSummary.positions).map(([symbol, position]) => (
                      <TableRow key={symbol}>
                        <TableCell className="font-medium">{symbol}</TableCell>
                        <TableCell>{position.quantity.toFixed(6)}</TableCell>
                        <TableCell>${position.avg_price_usd.toFixed(2)}</TableCell>
                        <TableCell>${position.market_value_usd.toFixed(2)}</TableCell>
                        <TableCell>
                          <span className={position.unrealized_pnl_usd >= 0 ? 'text-green-600' : 'text-red-600'}>
                            ${position.unrealized_pnl_usd.toFixed(2)} ({position.pnl_pct.toFixed(2)}%)
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Arbitrage Opportunities Tab */}
        <TabsContent value="arbitrage" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Arbitrage Opportunities</CardTitle>
              <CardDescription>
                Cross-exchange price differences and profit potential
              </CardDescription>
            </CardHeader>
            <CardContent>
              {arbitrageOpportunities.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Asset</TableHead>
                      <TableHead>Buy Venue</TableHead>
                      <TableHead>Sell Venue</TableHead>
                      <TableHead>Spread (bps)</TableHead>
                      <TableHead>Profit Potential</TableHead>
                      <TableHead>Confidence</TableHead>
                      <TableHead>Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {arbitrageOpportunities.map((opportunity) => (
                      <TableRow key={`${opportunity.symbol}-${opportunity.timestamp}`}>
                        <TableCell className="font-medium">{opportunity.symbol}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{opportunity.buy_venue}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{opportunity.sell_venue}</Badge>
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-green-600">
                            {opportunity.spread_bps.toFixed(1)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-green-600">
                            ${opportunity.estimated_profit_usd.toFixed(2)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            <div className="w-16 bg-gray-200 rounded-full h-2">
                              <div 
                                className="bg-blue-600 h-2 rounded-full" 
                                style={{ width: `${opportunity.confidence_score * 100}%` }}
                              />
                            </div>
                            <span className="text-sm">{(opportunity.confidence_score * 100).toFixed(0)}%</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Button 
                            size="sm" 
                            onClick={() => executeArbitrage(opportunity)}
                            disabled={opportunity.estimated_profit_usd < 10}
                          >
                            Execute
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  No arbitrage opportunities detected at the moment.
                  <br />
                  <span className="text-sm">
                    The system continuously monitors for cross-exchange price differences.
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trade History Tab */}
        <TabsContent value="trades" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Trade History</CardTitle>
              <CardDescription>
                Recent portfolio trades and arbitrage executions
              </CardDescription>
            </CardHeader>
            <CardContent>
              {trades.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Time</TableHead>
                      <TableHead>Asset</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead>Quantity</TableHead>
                      <TableHead>Price</TableHead>
                      <TableHead>Total</TableHead>
                      <TableHead>Venue</TableHead>
                      <TableHead>Arbitrage Profit</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {trades.map((trade) => (
                      <TableRow key={trade.id}>
                        <TableCell className="text-sm">
                          {new Date(trade.timestamp).toLocaleTimeString()}
                        </TableCell>
                        <TableCell className="font-medium">{trade.symbol}</TableCell>
                        <TableCell>
                          <Badge variant={trade.side === 'buy' ? 'default' : 'secondary'}>
                            {trade.side.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell>{trade.quantity.toFixed(6)}</TableCell>
                        <TableCell>${trade.price_usd.toFixed(2)}</TableCell>
                        <TableCell>${trade.total_usd.toFixed(2)}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{trade.venue}</Badge>
                        </TableCell>
                        <TableCell>
                          {trade.arbitrage_profit_bps ? (
                            <span className="text-green-600 font-mono">
                              {trade.arbitrage_profit_bps.toFixed(1)} bps
                            </span>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  No trades executed yet.
                  <br />
                  <span className="text-sm">
                    Trades will appear here as arbitrage opportunities are executed.
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

