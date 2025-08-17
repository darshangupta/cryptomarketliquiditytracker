"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Wifi, WifiOff, TrendingUp, DollarSign, ChartColumn, Zap, AlertTriangle, CheckCircle, XCircle } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar } from "recharts";

interface MarketData {
  timestamp: string;
  binance: {
    bid: number;
    ask: number;
    spread: number;
  };
  kraken: {
    bid: number;
    ask: number;
    spread: number;
  };
  metrics: {
    mid: number;
    spread_bps: number;
    depth: number;
    hhi: number;
    imbalance: number;
  };
}

const demoMarketData: MarketData = {
  timestamp: new Date().toISOString(),
  binance: { bid: 117669.02, ask: 117669.03, spread: 0.01 },
  kraken: { bid: 117770.60, ask: 117770.70, spread: 0.10 },
  metrics: { mid: 117719.81, spread_bps: 0.85, depth: 1300000, hhi: 0.52, imbalance: 0.12 },
};

// Chart data structure for time series
interface ChartDataPoint {
  timestamp: string;
  binanceBid: number;
  binanceAsk: number;
  krakenBid: number;
  krakenAsk: number;
  spread: number;
  midPrice: number;
}

// Alert structure
interface Alert {
  id: string;
  type: "arbitrage" | "spread" | "price" | "connection";
  severity: "low" | "medium" | "high";
  message: string;
  timestamp: string;
  isActive: boolean;
}

// Exchange fee structure
interface ExchangeFees {
  trading: number;
  withdrawal: number;
  deposit: number;
}

const EXCHANGE_FEES: Record<string, ExchangeFees> = {
  binance: { trading: 0.001, withdrawal: 0.0005, deposit: 0 },
  kraken: { trading: 0.0026, withdrawal: 0.0005, deposit: 0 },
};

export default function Home() {
  const [marketData, setMarketData] = useState<MarketData>(demoMarketData);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<"disconnected" | "connecting" | "connected">("disconnected");
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
  const [wsError, setWsError] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertSettings, setAlertSettings] = useState({
    spreadThreshold: 10, // $10 spread difference
    priceChangeThreshold: 1, // 1% price change
    arbitrageMinProfit: 50, // $50 minimum profit after fees
  });

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: NodeJS.Timeout;

    const connectWebSocket = () => {
      try {
        if (ws && ws.readyState === WebSocket.OPEN) {
          return; // Already connected
        }

        setConnectionStatus("connecting");
        setWsError(null);
        
        ws = new WebSocket("ws://localhost:8000/ws/stream");

        ws.onopen = () => {
          console.log("✅ WebSocket connected");
          setIsConnected(true);
          setConnectionStatus("connected");
          setWsError(null);
          addAlert("connection", "low", "WebSocket connected successfully");
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === "market_metrics" && message.data) {
              setMarketData(message.data);
              setLastUpdate(new Date().toLocaleTimeString());
              
              // Add to chart data with safety checks
              const newDataPoint: ChartDataPoint = {
                timestamp: new Date().toLocaleTimeString(),
                binanceBid: Number(message.data.binance?.bid) || 0,
                binanceAsk: Number(message.data.binance?.ask) || 0,
                krakenBid: Number(message.data.kraken?.bid) || 0,
                krakenAsk: Number(message.data.kraken?.ask) || 0,
                spread: Number(message.data.binance?.spread) || 0,
                midPrice: Number(message.data.metrics?.mid) || 0,
              };
              
              setChartData(prev => {
                const updated = [...prev, newDataPoint];
                // Keep only last 50 data points for performance
                return updated.slice(-50);
              });

              // Check for alerts
              checkForAlerts(message.data);
            }
          } catch (error) {
            console.error("❌ Failed to parse WebSocket message:", error);
            setWsError("Failed to parse market data");
            addAlert("connection", "high", "Failed to parse market data");
          }
        };

        ws.onerror = (error) => {
          console.error("❌ WebSocket error:", error);
          setIsConnected(false);
          setConnectionStatus("disconnected");
          setWsError("WebSocket connection error");
          addAlert("connection", "high", "WebSocket connection error");
        };

        ws.onclose = (event) => {
          console.log(`🔌 WebSocket disconnected: ${event.code} ${event.reason}`);
          setIsConnected(false);
          setConnectionStatus("disconnected");
          addAlert("connection", "medium", "WebSocket disconnected");
          
          // Auto-reconnect after 3 seconds
          reconnectTimer = setTimeout(connectWebSocket, 3000);
        };

      } catch (error) {
        console.error("❌ Failed to create WebSocket:", error);
        setConnectionStatus("disconnected");
        setWsError("Failed to create WebSocket connection");
        addAlert("connection", "high", "Failed to create WebSocket connection");
      }
    };

    connectWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
    };
  }, []);

  // Alert management
  const addAlert = (type: Alert["type"], severity: Alert["severity"], message: string) => {
    const newAlert: Alert = {
      id: Date.now().toString(),
      type,
      severity,
      message,
      timestamp: new Date().toLocaleTimeString(),
      isActive: true,
    };

    setAlerts(prev => {
      const updated = [newAlert, ...prev.slice(0, 9)]; // Keep last 10 alerts
      return updated;
    });

    // Auto-deactivate alerts after 30 seconds
    setTimeout(() => {
      setAlerts(prev => 
        prev.map(alert => 
          alert.id === newAlert.id ? { ...alert, isActive: false } : alert
        )
      );
    }, 30000);
  };

  const checkForAlerts = (data: MarketData) => {
    // Spread widening alert
    const spreadDiff = Math.abs((data.binance?.spread || 0) - (data.kraken?.spread || 0));
    if (spreadDiff > alertSettings.spreadThreshold) {
      addAlert("spread", "medium", `Large spread difference: $${spreadDiff.toFixed(2)}`);
    }

    // Price change alert (if we have previous data)
    if (chartData.length > 1) {
      const lastPrice = chartData[chartData.length - 1].midPrice;
      const currentPrice = data.metrics?.mid || 0;
      const priceChange = Math.abs((currentPrice - lastPrice) / lastPrice) * 100;
      
      if (priceChange > alertSettings.priceChangeThreshold) {
        addAlert("price", "high", `Large price movement: ${priceChange.toFixed(2)}%`);
      }
    }
  };

  // Realistic arbitrage calculation with fees
  const calculateArbitrage = () => {
    const binanceAsk = marketData.binance?.ask || 0;
    const krakenBid = marketData.kraken?.bid || 0;
    
    if (binanceAsk === 0 || krakenBid === 0) return null;

    const grossProfit = krakenBid - binanceAsk;
    
    // Calculate total fees
    const binanceFees = binanceAsk * EXCHANGE_FEES.binance.trading;
    const krakenFees = krakenBid * EXCHANGE_FEES.kraken.trading;
    const totalFees = binanceFees + krakenFees;
    
    const netProfit = grossProfit - totalFees;
    const profitMargin = (netProfit / binanceAsk) * 100;
    
    return {
      grossProfit,
      totalFees,
      netProfit,
      profitMargin,
      isProfitable: netProfit > alertSettings.arbitrageMinProfit,
      execution: {
        buyExchange: "Binance",
        buyPrice: binanceAsk,
        sellExchange: "Kraken",
        sellPrice: krakenBid,
      }
    };
  };

  const arbitrageData = calculateArbitrage();

  // Ensure chart data is valid before rendering
  const validChartData = chartData.filter(point => 
    point.binanceBid > 0 && 
    point.binanceAsk > 0 && 
    point.krakenBid > 0 && 
    point.krakenAsk > 0
  );

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Crypto Liquidity Tracker</h1>
            <p className="text-gray-600">Real-time multi-venue market analytics</p>
          </div>
          <div className="flex items-center space-x-4">
            <Badge variant={isConnected ? "default" : "destructive"} className="flex items-center space-x-2">
              {isConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
              <span>{connectionStatus === "connected" ? "Connected" : "Disconnected"}</span>
            </Badge>
            {lastUpdate && (
              <span className="text-sm text-gray-500">Last update: {lastUpdate}</span>
            )}
          </div>
        </div>

        {/* Error Display */}
        {wsError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-red-800">Connection Error:</span>
              <span className="text-red-700">{wsError}</span>
            </div>
          </div>
        )}

        {/* Active Alerts */}
        {alerts.filter(alert => alert.isActive).length > 0 && (
          <div className="space-y-2">
            {alerts.filter(alert => alert.isActive).map(alert => (
              <div 
                key={alert.id}
                className={`border rounded-lg p-4 ${
                  alert.severity === "high" 
                    ? "bg-red-50 border-red-200" 
                    : alert.severity === "medium"
                    ? "bg-yellow-50 border-yellow-200"
                    : "bg-blue-50 border-blue-200"
                }`}
              >
                <div className="flex items-center space-x-2">
                  {alert.severity === "high" ? (
                    <AlertTriangle className="w-5 h-5 text-red-600" />
                  ) : alert.severity === "medium" ? (
                    <AlertTriangle className="w-5 h-5 text-yellow-600" />
                  ) : (
                    <CheckCircle className="w-5 h-5 text-blue-600" />
                  )}
                  <span className={`font-semibold ${
                    alert.severity === "high" ? "text-red-800" :
                    alert.severity === "medium" ? "text-yellow-800" : "text-blue-800"
                  }`}>
                    {alert.type.charAt(0).toUpperCase() + alert.type.slice(1)} Alert
                  </span>
                  <span className="text-sm text-gray-500">({alert.timestamp})</span>
                </div>
                <p className={`mt-1 ${
                  alert.severity === "high" ? "text-red-700" :
                  alert.severity === "medium" ? "text-yellow-700" : "text-blue-700"
                }`}>
                  {alert.message}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Realistic Arbitrage Analysis */}
        {arbitrageData && (
          <div className={`border rounded-lg p-4 ${
            arbitrageData.isProfitable 
              ? "bg-green-50 border-green-200" 
              : "bg-gray-50 border-gray-200"
          }`}>
            <div className="flex items-center space-x-2 mb-3">
              {arbitrageData.isProfitable ? (
                <TrendingUp className="w-5 h-5 text-green-600" />
              ) : (
                <XCircle className="w-5 h-5 text-gray-600" />
              )}
              <span className={`font-semibold ${
                arbitrageData.isProfitable ? "text-green-800" : "text-gray-800"
              }`}>
                {arbitrageData.isProfitable ? "Profitable Arbitrage Opportunity!" : "Arbitrage Analysis"}
              </span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="text-center p-3 bg-white rounded-lg">
                <div className="text-sm text-gray-600">Gross Profit</div>
                <div className="text-lg font-bold text-green-600">${arbitrageData.grossProfit.toFixed(2)}</div>
              </div>
              <div className="text-center p-3 bg-white rounded-lg">
                <div className="text-sm text-gray-600">Total Fees</div>
                <div className="text-lg font-bold text-red-600">${arbitrageData.totalFees.toFixed(2)}</div>
              </div>
              <div className="text-center p-3 bg-white rounded-lg">
                <div className="text-sm text-gray-600">Net Profit</div>
                <div className={`text-lg font-bold ${
                  arbitrageData.netProfit > 0 ? "text-green-600" : "text-red-600"
                }`}>
                  ${arbitrageData.netProfit.toFixed(2)}
                </div>
              </div>
              <div className="text-center p-3 bg-white rounded-lg">
                <div className="text-sm text-gray-600">Profit Margin</div>
                <div className={`text-lg font-bold ${
                  arbitrageData.profitMargin > 0 ? "text-green-600" : "text-red-600"
                }`}>
                  {arbitrageData.profitMargin.toFixed(3)}%
                </div>
              </div>
            </div>

            <div className="mt-4 p-3 bg-white rounded-lg">
              <div className="text-sm font-medium mb-2">Execution Strategy:</div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Buy on {arbitrageData.execution.buyExchange}:</span>
                  <span className="ml-2 font-semibold text-red-600">${arbitrageData.execution.buyPrice.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-gray-600">Sell on {arbitrageData.execution.sellExchange}:</span>
                  <span className="ml-2 font-semibold text-green-600">${arbitrageData.execution.sellPrice.toLocaleString()}</span>
                </div>
              </div>
            </div>

            {arbitrageData.isProfitable && (
              <div className="mt-3 p-3 bg-green-100 rounded-lg">
                <div className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-sm font-medium text-green-800">
                    This opportunity exceeds minimum profit threshold (${alertSettings.arbitrageMinProfit})
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Mid Price</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${(marketData.metrics?.mid || 0).toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">Cross-venue average</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Spread (BPS)</CardTitle>
              <ChartColumn className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{marketData.metrics?.spread_bps || 0}</div>
              <p className="text-xs text-muted-foreground">Basis points</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Market Depth</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${((marketData.metrics?.depth || 0) / 1000000).toFixed(1)}M</div>
              <p className="text-xs text-muted-foreground">±0.5% window</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">HHI</CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{marketData.metrics?.hhi || 0}</div>
              <p className="text-xs text-muted-foreground">Concentration index</p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Market Overview</TabsTrigger>
            <TabsTrigger value="charts">Real-Time Charts</TabsTrigger>
            <TabsTrigger value="alerts">Alert Center</TabsTrigger>
            <TabsTrigger value="orderbooks">Order Books</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>

          {/* Market Overview Tab */}
          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader className="grid auto-rows-min grid-rows-[auto_auto] items-start gap-1.5 pb-2">
                  <CardTitle className="leading-none font-semibold flex items-center space-x-2">
                    <span>Binance</span>
                    <Badge variant="secondary">BTC/USDT</Badge>
                  </CardTitle>
                  <CardDescription>Real-time order book data</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">${(marketData.binance?.bid || 0).toLocaleString()}</div>
                      <div className="text-sm text-gray-500">Best Bid</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-red-600">${(marketData.binance?.ask || 0).toLocaleString()}</div>
                      <div className="text-sm text-gray-500">Best Ask</div>
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-semibold">Spread: ${(marketData.binance?.spread || 0).toFixed(2)}</div>
                    <div className="text-sm text-gray-500">
                      ({((marketData.binance?.spread || 0) / (marketData.binance?.bid || 1) * 10000).toFixed(2)} bps)
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="grid auto-rows-min grid-rows-[auto_auto] items-start gap-1.5 pb-2">
                  <CardTitle className="leading-none font-semibold flex items-center space-x-2">
                    <span>Kraken</span>
                    <Badge variant="secondary">XBT/USD</Badge>
                  </CardTitle>
                  <CardDescription>Real-time order book data</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">${(marketData.kraken?.bid || 0).toLocaleString()}</div>
                      <div className="text-sm text-gray-500">Best Bid</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-red-600">${(marketData.kraken?.ask || 0).toLocaleString()}</div>
                      <div className="text-sm text-gray-500">Best Ask</div>
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-semibold">Spread: ${(marketData.kraken?.spread || 0).toFixed(2)}</div>
                    <div className="text-sm text-gray-500">
                      ({((marketData.kraken?.spread || 0) / (marketData.kraken?.bid || 1) * 10000).toFixed(2)} bps)
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Real-Time Charts Tab */}
          <TabsContent value="charts" className="space-y-6">
            {/* Price Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Live Price Chart</CardTitle>
                <CardDescription>Real-time BTC-USD prices from both exchanges</CardDescription>
              </CardHeader>
              <CardContent>
                {validChartData.length > 0 ? (
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={validChartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="timestamp" />
                        <YAxis domain={['dataMin - 10', 'dataMax + 10']} />
                        <Tooltip 
                          formatter={(value: number) => [`$${value.toLocaleString()}`, '']}
                          labelFormatter={(label) => `Time: ${label}`}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="binanceBid" 
                          stroke="#10b981" 
                          strokeWidth={2}
                          name="Binance Bid"
                          dot={false}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="binanceAsk" 
                          stroke="#ef4444" 
                          strokeWidth={2}
                          name="Binance Ask"
                          dot={false}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="krakenBid" 
                          stroke="#3b82f6" 
                          strokeWidth={2}
                          name="Kraken Bid"
                          dot={false}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="krakenAsk" 
                          stroke="#8b5cf6" 
                          strokeWidth={2}
                          name="Kraken Ask"
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-80 flex items-center justify-center text-gray-500">
                    <p>Waiting for live data...</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Spread Analysis */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Spread Comparison</CardTitle>
                  <CardDescription>Bid-ask spreads across venues</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={[
                        { venue: 'Binance', spread: marketData.binance?.spread || 0 },
                        { venue: 'Kraken', spread: marketData.kraken?.spread || 0 }
                      ]}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="venue" />
                        <YAxis />
                        <Tooltip formatter={(value: number) => [`$${value.toFixed(2)}`, 'Spread']} />
                        <Bar dataKey="spread" fill="#3b82f6" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Mid Price Trend</CardTitle>
                  <CardDescription>Cross-venue average price movement</CardDescription>
                </CardHeader>
                <CardContent>
                  {validChartData.length > 0 ? (
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={validChartData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="timestamp" />
                          <YAxis domain={['dataMin - 5', 'dataMax + 5']} />
                          <Tooltip 
                            formatter={(value: number) => [`$${value.toLocaleString()}`, 'Mid Price']}
                            labelFormatter={(label) => `Time: ${label}`}
                          />
                          <Area 
                            type="monotone" 
                            dataKey="midPrice" 
                            stroke="#10b981" 
                            fill="#10b981" 
                            fillOpacity={0.3}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="h-64 flex items-center justify-center text-gray-500">
                      <p>Waiting for live data...</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Alert Center Tab */}
          <TabsContent value="alerts" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Alert Settings</CardTitle>
                <CardDescription>Configure alert thresholds</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="text-sm font-medium">Spread Threshold ($)</label>
                    <input
                      type="number"
                      value={alertSettings.spreadThreshold}
                      onChange={(e) => setAlertSettings(prev => ({ ...prev, spreadThreshold: Number(e.target.value) }))}
                      className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Price Change Threshold (%)</label>
                    <input
                      type="number"
                      value={alertSettings.priceChangeThreshold}
                      onChange={(e) => setAlertSettings(prev => ({ ...prev, priceChangeThreshold: Number(e.target.value) }))}
                      className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Min Arbitrage Profit ($)</label>
                    <input
                      type="number"
                      value={alertSettings.arbitrageMinProfit}
                      onChange={(e) => setAlertSettings(prev => ({ ...prev, arbitrageMinProfit: Number(e.target.value) }))}
                      className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Alert History</CardTitle>
                <CardDescription>Recent alerts and notifications</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {alerts.length > 0 ? (
                    alerts.map(alert => (
                      <div 
                        key={alert.id}
                        className={`p-3 rounded-lg border ${
                          alert.severity === "high" 
                            ? "bg-red-50 border-red-200" 
                            : alert.severity === "medium"
                            ? "bg-yellow-50 border-yellow-200"
                            : "bg-blue-50 border-blue-200"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            {alert.severity === "high" ? (
                              <AlertTriangle className="w-4 h-4 text-red-600" />
                            ) : alert.severity === "medium" ? (
                              <AlertTriangle className="w-4 h-4 text-yellow-600" />
                            ) : (
                              <CheckCircle className="w-4 h-4 text-blue-600" />
                            )}
                            <span className="text-sm font-medium capitalize">{alert.type}</span>
                            <Badge variant={alert.severity === "high" ? "destructive" : "secondary"}>
                              {alert.severity}
                            </Badge>
                          </div>
                          <span className="text-xs text-gray-500">{alert.timestamp}</span>
                        </div>
                        <p className="mt-1 text-sm">{alert.message}</p>
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-gray-500 py-8">
                      <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
                      <p>No alerts yet</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Order Books Tab */}
          <TabsContent value="orderbooks" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Binance Order Book</CardTitle>
                  <CardDescription>Top 10 levels</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Price</TableHead>
                        <TableHead>Size</TableHead>
                        <TableHead>Total</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <TableRow>
                        <TableCell className="text-green-600 font-medium">${(marketData.binance?.bid || 0).toLocaleString()}</TableCell>
                        <TableCell>2.02</TableCell>
                        <TableCell>2.02</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="text-green-600">${((marketData.binance?.bid || 0) - 0.01).toLocaleString()}</TableCell>
                        <TableCell>0.02</TableCell>
                        <TableCell>2.04</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Kraken Order Book</CardTitle>
                  <CardDescription>Top 10 levels</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Price</TableHead>
                        <TableHead>Size</TableHead>
                        <TableHead>Total</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <TableRow>
                        <TableCell className="text-green-600 font-medium">${(marketData.kraken?.bid || 0).toLocaleString()}</TableCell>
                        <TableCell>1.70</TableCell>
                        <TableCell>1.70</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="text-green-600">${((marketData.kraken?.bid || 0) - 0.10).toLocaleString()}</TableCell>
                        <TableCell>0.03</TableCell>
                        <TableCell>1.73</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Market Metrics</CardTitle>
                  <CardDescription>Real-time market analysis</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">{marketData.metrics?.hhi || 0}</div>
                      <div className="text-sm text-blue-600">HHI Index</div>
                    </div>
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">{marketData.metrics?.imbalance || 0}</div>
                      <div className="text-sm text-green-600">Imbalance</div>
                    </div>
                  </div>
                  <div className="text-center p-4 bg-purple-50 rounded-lg">
                    <div className="text-2xl font-bold text-purple-600">${((marketData.metrics?.depth || 0) / 1000000).toFixed(2)}M</div>
                    <div className="text-sm text-purple-600">Total Depth</div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Exchange Fee Analysis</CardTitle>
                  <CardDescription>Fee structure comparison</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">Binance Trading Fee:</span>
                      <span className="text-lg font-bold text-blue-600">{(EXCHANGE_FEES.binance.trading * 100).toFixed(2)}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">Kraken Trading Fee:</span>
                      <span className="text-lg font-bold text-purple-600">{(EXCHANGE_FEES.kraken.trading * 100).toFixed(2)}%</span>
                    </div>
                    <div className="border-t pt-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm font-medium">Fee Difference:</span>
                        <span className="text-lg font-bold text-red-600">
                          {((EXCHANGE_FEES.kraken.trading - EXCHANGE_FEES.binance.trading) * 100).toFixed(2)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* Footer */}
        <div className="text-center text-sm text-gray-500">
          <p>Built with Next.js, Tailwind CSS, and shadcn/ui</p>
          <p>Real-time data from Binance and Kraken</p>
          {lastUpdate && (
            <p className="mt-2 text-xs">Data timestamp: {lastUpdate}</p>
          )}
        </div>
      </div>
    </div>
  );
}
