"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MarketData } from "./types";

interface OrderBooksProps {
  marketData: MarketData;
}

export function OrderBooks({ marketData }: OrderBooksProps) {
  return (
    <div className="space-y-6">
      {/* Market Impact Calculator */}
      <Card>
        <CardHeader>
          <CardTitle>Market Impact Calculator</CardTitle>
          <CardDescription>Calculate price impact of your trades</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Binance Impact */}
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                <h4 className="font-semibold">Binance Market Impact</h4>
              </div>
              <div className="space-y-3">
                {[0.1, 0.5, 1.0, 2.0, 5.0, 10.0].map(size => {
                  const impact = marketData.binance?.market_impact?.[size.toString()];
                  if (!impact) return null;
                  
                  return (
                    <div key={size} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                      <span className="text-sm font-medium">{size} BTC</span>
                      <div className="text-right">
                        <div className="text-xs text-gray-600">Buy: ${impact.buy?.price?.toFixed(2) || 'N/A'}</div>
                        <div className="text-xs text-gray-600">Sell: ${impact.sell?.price?.toFixed(2) || 'N/A'}</div>
                        <div className="text-xs text-red-600">
                          Impact: {Math.max(impact.buy?.impact_bps || 0, impact.sell?.impact_bps || 0).toFixed(1)} bps
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              {marketData.binance?.optimal_trade_size && (
                <div className="p-3 bg-green-50 border border-green-200 rounded">
                  <div className="text-sm font-medium text-green-800">Optimal Trade Size</div>
                  <div className="text-lg font-bold text-green-600">
                    {marketData.binance.optimal_trade_size.toFixed(1)} BTC
                  </div>
                  <div className="text-xs text-green-600">
                    Max impact: {marketData.binance.optimal_impact_bps?.toFixed(1) || 0} bps
                  </div>
                </div>
              )}
            </div>

            {/* Kraken Impact */}
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                <h4 className="font-semibold">Kraken Market Impact</h4>
              </div>
              <div className="space-y-3">
                {[0.1, 0.5, 1.0, 2.0, 5.0, 10.0].map(size => {
                  const impact = marketData.kraken?.market_impact?.[size.toString()];
                  if (!impact) return null;
                  
                  return (
                    <div key={size} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                      <span className="text-sm font-medium">{size} BTC</span>
                      <div className="text-right">
                        <div className="text-xs text-gray-600">Buy: ${impact.buy?.price?.toFixed(2) || 'N/A'}</div>
                        <div className="text-xs text-gray-600">Sell: ${impact.sell?.price?.toFixed(2) || 'N/A'}</div>
                        <div className="text-xs text-red-600">
                          Impact: {Math.max(impact.buy?.impact_bps || 0, impact.sell?.impact_bps || 0).toFixed(1)} bps
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              {marketData.kraken?.optimal_trade_size && (
                <div className="p-3 bg-green-50 border border-green-200 rounded">
                  <div className="text-sm font-medium text-green-800">Optimal Trade Size</div>
                  <div className="text-lg font-bold text-green-600">
                    {marketData.kraken.optimal_trade_size.toFixed(1)} BTC
                  </div>
                  <div className="text-xs text-green-600">
                    Max impact: {marketData.kraken.optimal_impact_bps?.toFixed(1) || 0} bps
                  </div>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Real Order Books */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Binance Order Book */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span>Binance Order Book</span>
              <Badge variant="secondary">BTC/USDT</Badge>
            </CardTitle>
            <CardDescription>
              Top 20 levels • Total Depth: {((marketData.binance?.depth || 0) / 1000).toFixed(1)}k BTC
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {/* Asks (Sell Orders) */}
              <div className="text-sm font-medium text-red-600 mb-2">Asks (Sell Orders)</div>
              {marketData.binance?.top_asks?.slice(0, 10).map((level, index) => (
                <div key={index} className="flex justify-between items-center text-sm">
                  <span className="text-red-600">${level.price.toLocaleString()}</span>
                  <span className="text-gray-600">{level.size.toFixed(4)}</span>
                  <span className="text-gray-500">${(level.price * level.size).toLocaleString()}</span>
                </div>
              ))}
              
              {/* Spread */}
              <div className="border-t border-gray-200 my-3 pt-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Spread:</span>
                  <span className="text-sm font-bold text-red-600">
                    ${(marketData.binance?.spread || 0).toFixed(2)} 
                    ({marketData.binance?.spread_bps?.toFixed(2) || 0} bps)
                  </span>
                </div>
              </div>
              
              {/* Bids (Buy Orders) */}
              <div className="text-sm font-medium text-green-600 mb-2">Bids (Buy Orders)</div>
              {marketData.binance?.top_bids?.slice(0, 10).map((level, index) => (
                <div key={index} className="flex justify-between items-center text-sm">
                  <span className="text-green-600">${level.price.toLocaleString()}</span>
                  <span className="text-gray-600">{level.size.toFixed(4)}</span>
                  <span className="text-gray-500">${(level.price * level.size).toLocaleString()}</span>
                </div>
              ))}
            </div>
            
            {/* Liquidity Score */}
            {marketData.binance?.liquidity_score && (
              <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
                <div className="text-sm font-medium text-blue-800">Liquidity Score</div>
                <div className="text-lg font-bold text-blue-600">
                  ${(marketData.binance.liquidity_score / 1000000).toFixed(1)}M
                </div>
                <div className="text-xs text-blue-600">±50 bps window</div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Kraken Order Book */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
              <span>Kraken Order Book</span>
              <Badge variant="secondary">XBT/USD</Badge>
            </CardTitle>
            <CardDescription>
              Top 20 levels • Total Depth: {((marketData.kraken?.depth || 0) / 1000).toFixed(1)}k BTC
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {/* Asks (Sell Orders) */}
              <div className="text-sm font-medium text-red-600 mb-2">Asks (Sell Orders)</div>
              {marketData.kraken?.top_asks?.slice(0, 10).map((level, index) => (
                <div key={index} className="flex justify-between items-center text-sm">
                  <span className="text-red-600">${level.price.toLocaleString()}</span>
                  <span className="text-gray-600">{level.size.toFixed(4)}</span>
                  <span className="text-gray-500">${(level.price * level.size).toLocaleString()}</span>
                </div>
              ))}
              
              {/* Spread */}
              <div className="border-t border-gray-200 my-3 pt-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Spread:</span>
                  <span className="text-sm font-bold text-red-600">
                    ${(marketData.kraken?.spread || 0).toFixed(2)} 
                    ({marketData.kraken?.spread_bps?.toFixed(2) || 0} bps)
                  </span>
                </div>
              </div>
              
              {/* Bids (Buy Orders) */}
              <div className="text-sm font-medium text-green-600 mb-2">Bids (Buy Orders)</div>
              {marketData.kraken?.top_bids?.slice(0, 10).map((level, index) => (
                <div key={index} className="flex justify-between items-center text-sm">
                  <span className="text-green-600">${level.price.toLocaleString()}</span>
                  <span className="text-gray-600">{level.size.toFixed(4)}</span>
                  <span className="text-gray-500">${(level.price * level.size).toLocaleString()}</span>
                </div>
              ))}
            </div>
            
            {/* Liquidity Score */}
            {marketData.kraken?.liquidity_score && (
              <div className="mt-4 p-3 bg-purple-50 border border-purple-200 rounded">
                <div className="text-sm font-medium text-purple-800">Liquidity Score</div>
                <div className="text-lg font-bold text-purple-600">
                  ${(marketData.kraken.liquidity_score / 1000000).toFixed(1)}M
                </div>
                <div className="text-xs text-purple-600">±50 bps window</div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Depth Analysis */}
      <Card>
        <CardHeader>
          <CardTitle>Market Depth Analysis</CardTitle>
          <CardDescription>Liquidity distribution and execution insights</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">
                ${((marketData.binance?.depth || 0) / 1000).toFixed(1)}k
              </div>
              <div className="text-sm text-blue-600">Binance Depth</div>
              <div className="text-xs text-gray-500">Total available liquidity</div>
            </div>
            
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">
                ${((marketData.kraken?.depth || 0) / 1000).toFixed(1)}k
              </div>
              <div className="text-sm text-purple-600">Kraken Depth</div>
              <div className="text-xs text-gray-500">Total available liquidity</div>
            </div>
            
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">
                ${((marketData.metrics?.depth || 0) / 1000).toFixed(1)}k
              </div>
              <div className="text-sm text-green-600">Combined Depth</div>
              <div className="text-xs text-gray-500">Cross-venue liquidity</div>
            </div>
          </div>
          
          {/* Execution Recommendations */}
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <h4 className="font-semibold mb-3">Execution Recommendations</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-sm font-medium text-blue-600">Binance</div>
                <div className="text-sm text-gray-600">
                  Optimal size: {marketData.binance?.optimal_trade_size?.toFixed(1) || 'N/A'} BTC
                </div>
                <div className="text-sm text-gray-600">
                  Max impact: {marketData.binance?.optimal_impact_bps?.toFixed(1) || 'N/A'} bps
                </div>
              </div>
              <div>
                <div className="text-sm font-medium text-purple-600">Kraken</div>
                <div className="text-sm text-gray-600">
                  Optimal size: {marketData.kraken?.optimal_trade_size?.toFixed(1) || 'N/A'} BTC
                </div>
                <div className="text-sm text-gray-600">
                  Max impact: {marketData.kraken?.optimal_impact_bps?.toFixed(1) || 'N/A'} bps
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
