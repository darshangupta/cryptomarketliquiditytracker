"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TrendingUp, TrendingDown, Activity, DollarSign, BarChart3, Zap, Wifi, WifiOff } from "lucide-react";

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

export default function Dashboard() {
  const [isConnected, setIsConnected] = useState(false);
  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string>("");
  const [connectionStatus, setConnectionStatus] = useState<"connecting" | "connected" | "disconnected">("disconnected");

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: NodeJS.Timeout;

    const connectWebSocket = () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        return; // Already connected
      }

      setConnectionStatus("connecting");
      
      try {
        ws = new WebSocket("ws://localhost:8000/ws/stream");
        
        ws.onopen = () => {
          console.log("✅ WebSocket connected to backend");
          setIsConnected(true);
          setConnectionStatus("connected");
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log("📊 Received market data:", data);
            
            if (data.type === "market_metrics") {
              setMarketData(data.data);
              setLastUpdate(new Date().toLocaleTimeString());
            }
          } catch (error) {
            console.error("❌ Failed to parse WebSocket message:", error);
          }
        };

        ws.onclose = (event) => {
          console.log(`🔌 WebSocket disconnected: ${event.code} ${event.reason}`);
          setIsConnected(false);
          setConnectionStatus("disconnected");
          
          // Auto-reconnect after 3 seconds
          reconnectTimer = setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = (error) => {
          console.error("❌ WebSocket error:", error);
          setConnectionStatus("disconnected");
        };

      } catch (error) {
        console.error("❌ Failed to create WebSocket:", error);
        setConnectionStatus("disconnected");
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

  // Demo data fallback when not connected
  const demoData: MarketData = {
    timestamp: new Date().toISOString(),
    binance: { bid: 117669.02, ask: 117669.03, spread: 0.01 },
    kraken: { bid: 117770.6, ask: 117770.7, spread: 0.10 },
    metrics: { mid: 117719.81, spread_bps: 0.85, depth: 1300000, hhi: 0.52, imbalance: 0.12 }
  };

  const data = marketData || demoData;

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
              <span>{isConnected ? "Live" : "Disconnected"}</span>
            </Badge>
            {lastUpdate && (
              <Badge variant="outline" className="text-xs">
                Last: {lastUpdate}
              </Badge>
            )}
          </div>
        </div>

        {/* Market Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Mid Price</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${data.metrics.mid.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">Cross-venue average</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Spread (BPS)</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{data.metrics.spread_bps}</div>
              <p className="text-xs text-muted-foreground">Basis points</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Market Depth</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${(data.metrics.depth / 1000000).toFixed(1)}M</div>
              <p className="text-xs text-muted-foreground">±0.5% window</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">HHI</CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{data.metrics.hhi}</div>
              <p className="text-xs text-muted-foreground">Concentration index</p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Market Overview</TabsTrigger>
            <TabsTrigger value="orderbooks">Order Books</TabsTrigger>
            <TabsTrigger value="metrics">Analytics</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Binance Card */}
              <Card>
                <CardHeader className="grid auto-rows-min grid-rows-[auto_auto] items-start gap-1.5 px-6 pb-2">
                  <CardTitle className="leading-none font-semibold flex items-center space-x-2">
                    <span>Binance</span>
                    <Badge variant="secondary">BTC/USDT</Badge>
                  </CardTitle>
                  <CardDescription className="text-sm">Real-time order book data</CardDescription>
                </CardHeader>
                <CardContent className="px-6 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">${data.binance.bid.toLocaleString()}</div>
                      <div className="text-sm text-gray-500">Best Bid</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-red-600">${data.binance.ask.toLocaleString()}</div>
                      <div className="text-sm text-gray-500">Best Ask</div>
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-semibold">Spread: ${data.binance.spread}</div>
                    <div className="text-sm text-gray-500">({((data.binance.spread / data.binance.bid) * 10000).toFixed(2)} bps)</div>
                  </div>
                </CardContent>
              </Card>

              {/* Kraken Card */}
              <Card>
                <CardHeader className="grid auto-rows-min grid-rows-[auto_auto] items-start gap-1.5 px-6 pb-2">
                  <CardTitle className="leading-none font-semibold flex items-center space-x-2">
                    <span>Kraken</span>
                    <Badge variant="secondary">XBT/USD</Badge>
                  </CardTitle>
                  <CardDescription className="text-sm">Real-time order book data</CardDescription>
                </CardHeader>
                <CardContent className="px-6 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">${data.kraken.bid.toLocaleString()}</div>
                      <div className="text-sm text-gray-500">Best Bid</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-red-600">${data.kraken.ask.toLocaleString()}</div>
                      <div className="text-sm text-gray-500">Best Ask</div>
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-semibold">Spread: ${data.kraken.spread}</div>
                    <div className="text-sm text-gray-500">({((data.kraken.spread / data.kraken.bid) * 10000).toFixed(2)} bps)</div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="orderbooks" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Order Book Comparison</CardTitle>
                <CardDescription>Real-time order book data from both venues</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Order book details will be displayed here</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="metrics" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Market Analytics</CardTitle>
                <CardDescription>Advanced market metrics and analysis</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Analytics will be displayed here</p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Footer */}
        <div className="text-center text-sm text-gray-500">
          <p>Built with Next.js, Tailwind CSS, and shadcn/ui</p>
          <p>Real-time data from Binance and Kraken</p>
          {data.timestamp && (
            <p className="mt-2 text-xs">Data timestamp: {new Date(data.timestamp).toLocaleString()}</p>
          )}
        </div>
      </div>
    </div>
  );
}
