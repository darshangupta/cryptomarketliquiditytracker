"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { TrendingUp, BarChart3, Shield, Target, Activity } from "lucide-react";

interface PerformanceMetrics {
  total_return: number;
  annualized_return: number;
  volatility: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  calmar_ratio: number;
  win_rate: number;
  profit_factor: number;
  avg_win: number;
  avg_loss: number;
  largest_win: number;
  largest_loss: number;
}

interface RiskMetrics {
  var_95: number;
  var_99: number;
  expected_shortfall: number;
  beta: number;
  correlation: number;
  treynor_ratio: number;
  information_ratio: number;
  ulcer_index: number;
  gain_to_pain_ratio: number;
}

interface AllocationMetrics {
  allocations: Record<string, {
    allocation_pct: number;
    market_value_usd: number;
    unrealized_pnl_usd: number;
    pnl_pct: number;
  }>;
  concentration: {
    herfindahl_index: number;
    largest_position_pct: number;
    top_3_concentration: number;
    diversification_score: number;
  };
  total_positions: number;
}

interface ArbitrageMetrics {
  total_arbitrage_trades: number;
  success_rate: number;
  avg_profit_bps: number;
  total_profit_usd: number;
  profitable_trades: number;
  unprofitable_trades: number;
}

interface DiversificationMetrics {
  effective_positions: number;
  diversification_benefit: number;
  position_count: number;
}

interface AnalyticsData {
  timestamp: string;
  performance: PerformanceMetrics;
  risk: RiskMetrics;
  allocation: AllocationMetrics;
  arbitrage: ArbitrageMetrics;
  diversification: DiversificationMetrics;
}

export default function AdvancedAnalytics() {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAnalyticsData();
    const interval = setInterval(fetchAnalyticsData, 300000); // Refresh every 5 minutes
    return () => clearInterval(interval);
  }, []);

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/analytics/performance');
      if (response.ok) {
        const data = await response.json();
        setAnalyticsData(data);
        setError(null);
      } else {
        setError('Failed to fetch analytics data');
      }
    } catch (err) {
      setError('Failed to fetch analytics data');
      console.error('Error fetching analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !analyticsData) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center">Loading analytics data...</div>
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

  if (!analyticsData) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-muted-foreground">No analytics data available</div>
        </CardContent>
      </Card>
    );
  }

  const { performance, risk, allocation, arbitrage, diversification } = analyticsData;

  return (
    <div className="space-y-6">
      {/* Analytics Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <BarChart3 className="w-5 h-5" />
            <span>Advanced Portfolio Analytics</span>
          </CardTitle>
          <CardDescription>
            Comprehensive performance metrics, risk analysis, and portfolio insights
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className={`text-2xl font-bold ${
                performance.total_return >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {performance.total_return >= 0 ? '+' : ''}{(performance.total_return * 100).toFixed(2)}%
              </div>
              <div className="text-sm text-muted-foreground">Total Return</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {performance.sharpe_ratio.toFixed(2)}
              </div>
              <div className="text-sm text-muted-foreground">Sharpe Ratio</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {(performance.max_drawdown * 100).toFixed(2)}%
              </div>
              <div className="text-sm text-muted-foreground">Max Drawdown</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {performance.win_rate.toFixed(1)}%
              </div>
              <div className="text-sm text-muted-foreground">Win Rate</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Analytics Tabs */}
      <Tabs defaultValue="performance" className="space-y-4">
        <TabsList>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="risk">Risk Analysis</TabsTrigger>
          <TabsTrigger value="allocation">Asset Allocation</TabsTrigger>
          <TabsTrigger value="arbitrage">Arbitrage Metrics</TabsTrigger>
        </TabsList>

        {/* Performance Tab */}
        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Return Metrics */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <TrendingUp className="w-5 h-5" />
                  <span>Return Metrics</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span>Total Return:</span>
                  <span className={performance.total_return >= 0 ? 'text-green-600' : 'text-red-600'}>
                    {performance.total_return >= 0 ? '+' : ''}{(performance.total_return * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Annualized Return:</span>
                  <span className={performance.annualized_return >= 0 ? 'text-green-600' : 'text-red-600'}>
                    {performance.annualized_return >= 0 ? '+' : ''}{(performance.annualized_return * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Volatility:</span>
                  <span>{(performance.volatility * 100).toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Calmar Ratio:</span>
                  <span>{performance.calmar_ratio.toFixed(2)}</span>
                </div>
              </CardContent>
            </Card>

            {/* Trade Statistics */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Activity className="w-5 h-5" />
                  <span>Trade Statistics</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span>Win Rate:</span>
                  <span className="text-green-600">{performance.win_rate.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Profit Factor:</span>
                  <span>{performance.profit_factor.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Avg Win:</span>
                  <span className="text-green-600">${performance.avg_win.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Avg Loss:</span>
                  <span className="text-red-600">${performance.avg_loss.toFixed(2)}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Risk Analysis Tab */}
        <TabsContent value="risk" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Value at Risk */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Shield className="w-5 h-5" />
                  <span>Value at Risk</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span>VaR (95%):</span>
                  <span className="text-red-600">{(risk.var_95 * 100).toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>VaR (99%):</span>
                  <span className="text-red-600">{(risk.var_99 * 100).toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Expected Shortfall:</span>
                  <span className="text-red-600">{(risk.expected_shortfall * 100).toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Ulcer Index:</span>
                  <span>{risk.ulcer_index.toFixed(3)}</span>
                </div>
              </CardContent>
            </Card>

            {/* Risk Ratios */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Target className="w-5 h-5" />
                  <span>Risk Ratios</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span>Beta:</span>
                  <span>{risk.beta.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Correlation:</span>
                  <span>{risk.correlation.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Treynor Ratio:</span>
                  <span>{risk.treynor_ratio.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Information Ratio:</span>
                  <span>{risk.information_ratio.toFixed(2)}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Asset Allocation Tab */}
        <TabsContent value="allocation" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Allocation Overview */}
            <Card>
              <CardHeader>
                <CardTitle>Asset Allocation</CardTitle>
                <CardDescription>Current portfolio distribution</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(allocation.allocations).map(([symbol, data]) => (
                    <div key={symbol} className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="font-medium">{symbol}</span>
                        <span>{data.allocation_pct.toFixed(1)}%</span>
                      </div>
                      <Progress value={data.allocation_pct} className="h-2" />
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>${data.market_value_usd.toLocaleString()}</span>
                        <span className={data.pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {data.pnl_pct >= 0 ? '+' : ''}{data.pnl_pct.toFixed(2)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Concentration Metrics */}
            <Card>
              <CardHeader>
                <CardTitle>Concentration Analysis</CardTitle>
                <CardDescription>Portfolio diversification metrics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span>Diversification Score:</span>
                    <Badge variant={allocation.concentration.diversification_score > 70 ? "default" : "secondary"}>
                      {allocation.concentration.diversification_score.toFixed(0)}/100
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span>Largest Position:</span>
                    <span>{allocation.concentration.largest_position_pct.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Top 3 Concentration:</span>
                    <span>{allocation.concentration.top_3_concentration.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Total Positions:</span>
                    <span>{allocation.total_positions}</span>
                  </div>
                </div>
                
                <div className="pt-4">
                  <div className="text-sm font-medium mb-2">Diversification Benefit</div>
                  <div className="flex justify-between text-sm">
                    <span>Effective Positions:</span>
                    <span>{diversification.effective_positions.toFixed(1)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Risk Reduction:</span>
                    <span className="text-green-600">{diversification.diversification_benefit.toFixed(1)}%</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Arbitrage Metrics Tab */}
        <TabsContent value="arbitrage" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Arbitrage Performance */}
            <Card>
              <CardHeader>
                <CardTitle>Arbitrage Performance</CardTitle>
                <CardDescription>Cross-exchange arbitrage metrics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span>Total Trades:</span>
                  <span className="font-medium">{arbitrage.total_arbitrage_trades}</span>
                </div>
                <div className="flex justify-between">
                  <span>Success Rate:</span>
                  <Badge variant={arbitrage.success_rate > 70 ? "default" : "secondary"}>
                    {arbitrage.success_rate.toFixed(1)}%
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>Avg Profit:</span>
                  <span className="text-green-600">{arbitrage.avg_profit_bps.toFixed(1)} bps</span>
                </div>
                <div className="flex justify-between">
                  <span>Total Profit:</span>
                  <span className="text-green-600">${arbitrage.total_profit_usd.toFixed(2)}</span>
                </div>
              </CardContent>
            </Card>

            {/* Trade Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>Trade Breakdown</CardTitle>
                <CardDescription>Profitable vs unprofitable trades</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span>Profitable Trades:</span>
                  <span className="text-green-600">{arbitrage.profitable_trades}</span>
                </div>
                <div className="flex justify-between">
                  <span>Unprofitable Trades:</span>
                  <span className="text-red-600">{arbitrage.unprofitable_trades}</span>
                </div>
                <div className="pt-4">
                  <div className="text-sm font-medium mb-2">Profit Distribution</div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Profitable:</span>
                      <span className="text-green-600">
                        {arbitrage.total_arbitrage_trades > 0 ? 
                          (arbitrage.profitable_trades / arbitrage.total_arbitrage_trades * 100).toFixed(1) : 0}%
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Unprofitable:</span>
                      <span className="text-red-600">
                        {arbitrage.total_arbitrage_trades > 0 ? 
                          (arbitrage.unprofitable_trades / arbitrage.total_arbitrage_trades * 100).toFixed(1) : 0}%
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
