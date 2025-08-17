"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DollarSign, ChartColumn, TrendingUp, Zap } from "lucide-react";
import { MarketData } from "./types";

interface KeyMetricsProps {
  marketData: MarketData;
}

export function KeyMetrics({ marketData }: KeyMetricsProps) {
  return (
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
  );
}
