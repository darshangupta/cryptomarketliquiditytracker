"use client";

import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Header,
  MarketOverview,
  RealTimeCharts,
  AlertCenter,
  ArbitrageAnalysis,
  KeyMetrics,
  OrderBooks,
  Analytics,
  ActiveAlerts,
  ErrorDisplay,
  Footer,
  MarketData,
  ChartDataPoint,
  Alert,
  AlertSettings,
  ArbitrageData,
  ExchangeFees
} from "@/components/dashboard";

const EXCHANGE_FEES: Record<string, ExchangeFees> = {
  binance: { trading: 0.001, withdrawal: 0.0005, deposit: 0 },
  kraken: { trading: 0.0026, withdrawal: 0.0005, deposit: 0 },
};

const demoMarketData: MarketData = {
  timestamp: new Date().toISOString(),
  binance: { bid: 117669.02, ask: 117669.03, spread: 0.01 },
  kraken: { bid: 117770.60, ask: 117770.70, spread: 0.10 },
  metrics: { mid: 117719.81, spread_bps: 0.85, depth: 1300000, hhi: 0.52, imbalance: 0.12 },
};

export default function Home() {
  const [marketData, setMarketData] = useState<MarketData>(demoMarketData);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<"disconnected" | "connecting" | "connected">("disconnected");
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
  const [wsError, setWsError] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertSettings, setAlertSettings] = useState<AlertSettings>({
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
  const calculateArbitrage = (): ArbitrageData | null => {
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
        <Header 
          isConnected={isConnected}
          connectionStatus={connectionStatus}
          lastUpdate={lastUpdate}
        />

        {/* Error Display */}
        <ErrorDisplay wsError={wsError} />

        {/* Active Alerts */}
        <ActiveAlerts alerts={alerts} />

        {/* Realistic Arbitrage Analysis */}
        <ArbitrageAnalysis arbitrageData={arbitrageData} />

        {/* Key Metrics */}
        <KeyMetrics marketData={marketData} />

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
            <MarketOverview marketData={marketData} />
          </TabsContent>

          {/* Real-Time Charts Tab */}
          <TabsContent value="charts" className="space-y-6">
            <RealTimeCharts 
              validChartData={validChartData}
              marketData={marketData}
            />
          </TabsContent>

          {/* Alert Center Tab */}
          <TabsContent value="alerts" className="space-y-4">
            <AlertCenter 
              alerts={alerts}
              alertSettings={alertSettings}
              onAlertSettingsChange={setAlertSettings}
            />
          </TabsContent>

          {/* Order Books Tab */}
          <TabsContent value="orderbooks" className="space-y-6">
            <OrderBooks marketData={marketData} />
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics" className="space-y-4">
            <Analytics marketData={marketData} />
          </TabsContent>
        </Tabs>

        {/* Footer */}
        <Footer lastUpdate={lastUpdate} />
      </div>
    </div>
  );
}