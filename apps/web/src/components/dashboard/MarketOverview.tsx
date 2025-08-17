"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MarketData } from "./types";

interface MarketOverviewProps {
  marketData: MarketData;
}

export function MarketOverview({ marketData }: MarketOverviewProps) {
  return (
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
  );
}
