"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { MarketData } from "./types";

interface AnalyticsProps {
  marketData: MarketData;
}

const EXCHANGE_FEES = {
  binance: { trading: 0.001, withdrawal: 0.0005, deposit: 0 },
  kraken: { trading: 0.0026, withdrawal: 0.0005, deposit: 0 },
};

export function Analytics({ marketData }: AnalyticsProps) {
  return (
    <div className="space-y-4">
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
    </div>
  );
}
