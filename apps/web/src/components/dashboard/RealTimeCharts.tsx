"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar } from "recharts";
import { ChartDataPoint, MarketData } from "./types";

interface RealTimeChartsProps {
  validChartData: ChartDataPoint[];
  marketData: MarketData;
}

export function RealTimeCharts({ validChartData, marketData }: RealTimeChartsProps) {
  return (
    <div className="space-y-6">
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
    </div>
  );
}
