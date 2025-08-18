"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { TrendingUp, AlertTriangle, Target, Zap, Shield, Clock, DollarSign, BarChart3 } from "lucide-react";
import { MarketData, RiskMetrics } from "./types";

interface RiskAdjustedArbitrageProps {
  marketData: MarketData;
  riskMetrics: RiskMetrics;
}

interface ArbitrageScore {
  grossProfit: number;
  netProfit: number;
  executionProbability: number;
  riskScore: number;
  overallScore: number;
  factors: {
    profitMargin: number;
    liquidityDepth: number;
    volatilityRisk: number;
    executionSpeed: number;
    regulatoryRisk: number;
    technicalRisk: number;
  };
  recommendations: string[];
}

interface RiskFactors {
  liquidityDepth: number;
  volatilityRisk: number;
  executionSpeed: number;
  technicalRisk: number;
}

export function RiskAdjustedArbitrage({ marketData, riskMetrics }: RiskAdjustedArbitrageProps) {
  const [arbitrageScore, setArbitrageScore] = useState<ArbitrageScore | null>(null);

  // Calculate arbitrage opportunity when market data changes
  useEffect(() => {
    if (marketData.binance?.ask && marketData.kraken?.bid) {
      const binanceAsk = marketData.binance.ask;
      const krakenBid = marketData.kraken.bid;
      
      if (krakenBid > binanceAsk) {
        const grossProfit = krakenBid - binanceAsk;
        
        // Calculate fees (simplified)
        const binanceFees = binanceAsk * 0.001; // 0.1%
        const krakenFees = krakenBid * 0.0026; // 0.26%
        const totalFees = binanceFees + krakenFees;
        
        const netProfit = grossProfit - totalFees;
        const profitMargin = (netProfit / binanceAsk) * 100;

        // Factor scoring (0-100, higher = better)
        const factors = {
          profitMargin: Math.min(100, Math.max(0, profitMargin * 10)), // 0-10% = 0-100
          liquidityDepth: calculateLiquidityScore(),
          volatilityRisk: calculateVolatilityRisk(),
          executionSpeed: calculateExecutionSpeed(),
          regulatoryRisk: 85, // Placeholder - would be dynamic
          technicalRisk: calculateTechnicalRisk(),
        };

        // Weighted scoring
        const weights = {
          profitMargin: 0.3,
          liquidityDepth: 0.2,
          volatilityRisk: 0.15,
          executionSpeed: 0.15,
          regulatoryRisk: 0.1,
          technicalRisk: 0.1,
        };

        const overallScore = Object.entries(factors).reduce((score, [key, value]) => {
          return score + (value * weights[key as keyof typeof weights]);
        }, 0);

        // Risk score (0-100, higher = riskier)
        const riskScore = 100 - overallScore;

        // Execution probability based on overall score
        const executionProbability = Math.max(0, Math.min(100, overallScore));

        // Generate recommendations
        const recommendations = generateRecommendations(factors, netProfit, overallScore);

        setArbitrageScore({
          grossProfit,
          netProfit,
          executionProbability,
          riskScore,
          overallScore,
          factors,
          recommendations,
        });
      } else {
        setArbitrageScore(null);
      }
    }
  }, [marketData, riskMetrics]);

  const calculateLiquidityScore = (): number => {
    const binanceDepth = marketData.binance?.depth || 0;
    const krakenDepth = marketData.kraken?.depth || 0;
    const totalDepth = binanceDepth + krakenDepth;
    
    // Score based on available liquidity (0-100)
    if (totalDepth > 1000000) return 100; // >$1M
    if (totalDepth > 500000) return 80;   // >$500K
    if (totalDepth > 100000) return 60;   // >$100K
    if (totalDepth > 50000) return 40;    // >$50K
    return 20; // <$50K
  };

  const calculateVolatilityRisk = (): number => {
    // Higher volatility = higher risk = lower score
    const volatility = riskMetrics.volatility;
    if (volatility < 20) return 100;      // Low volatility
    if (volatility < 40) return 80;       // Medium volatility
    if (volatility < 60) return 60;       // High volatility
    if (volatility < 80) return 40;       // Very high volatility
    return 20; // Extreme volatility
  };

  const calculateExecutionSpeed = (): number => {
    // Based on spread and market depth
    const spread = marketData.binance?.spread || 0;
    const midPrice = marketData.metrics?.mid || 1;
    const spreadPercent = (spread / midPrice) * 100;
    
    if (spreadPercent < 0.01) return 100;     // Very tight spread
    if (spreadPercent < 0.05) return 80;      // Tight spread
    if (spreadPercent < 0.1) return 60;       // Normal spread
    if (spreadPercent < 0.2) return 40;       // Wide spread
    return 20; // Very wide spread
  };

  const calculateTechnicalRisk = (): number => {
    // Based on market metrics
    const hhi = marketData.metrics?.hhi || 0;
    const imbalance = marketData.metrics?.imbalance || 0;
    
    let score = 100;
    
    // HHI penalty (higher concentration = higher risk)
    if (hhi > 0.8) score -= 30;
    else if (hhi > 0.6) score -= 20;
    else if (hhi > 0.4) score -= 10;
    
    // Imbalance penalty
    if (imbalance > 0.3) score -= 20;
    else if (imbalance > 0.2) score -= 10;
    
    return Math.max(0, score);
  };

  const generateRecommendations = (factors: RiskFactors, netProfit: number, overallScore: number): string[] => {
    const recommendations: string[] = [];
    
    if (netProfit < 50) {
      recommendations.push("Low profit margin - consider waiting for better opportunity");
    }
    
    if (factors.liquidityDepth < 50) {
      recommendations.push("Limited liquidity - reduce trade size or wait");
    }
    
    if (factors.volatilityRisk < 50) {
      recommendations.push("High volatility - consider hedging or smaller position");
    }
    
    if (factors.executionSpeed < 50) {
      recommendations.push("Wide spreads - execution may be challenging");
    }
    
    if (overallScore > 80) {
      recommendations.push("Excellent opportunity - execute with confidence");
    } else if (overallScore > 60) {
      recommendations.push("Good opportunity - execute with caution");
    } else if (overallScore > 40) {
      recommendations.push("Moderate opportunity - consider waiting");
    } else {
      recommendations.push("High risk - not recommended at this time");
    }
    
    return recommendations;
  };

  if (!arbitrageScore) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Target className="w-5 h-5" />
            <span>Risk-Adjusted Arbitrage Scoring</span>
          </CardTitle>
          <CardDescription>No profitable arbitrage opportunities currently available</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center text-gray-500 py-8">
            <Target className="w-8 h-8 mx-auto mb-2" />
            <p>Monitor market conditions for arbitrage opportunities</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overall Score */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Target className="w-5 h-5" />
            <span>Arbitrage Opportunity Score</span>
            <Badge variant={arbitrageScore.overallScore > 70 ? "default" : arbitrageScore.overallScore > 50 ? "secondary" : "destructive"}>
              {arbitrageScore.overallScore > 70 ? "Excellent" : arbitrageScore.overallScore > 50 ? "Good" : "High Risk"}
            </Badge>
          </CardTitle>
          <CardDescription>Multi-factor risk assessment and execution probability</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Overall Score */}
            <div className="text-center">
              <div className="text-4xl font-bold text-blue-600 mb-2">{arbitrageScore.overallScore.toFixed(0)}</div>
              <div className="text-sm text-gray-600">Overall Score</div>
              <div className="text-xs text-gray-500">0-100 scale</div>
            </div>
            
            {/* Execution Probability */}
            <div className="text-center">
              <div className="text-4xl font-bold text-green-600 mb-2">{arbitrageScore.executionProbability.toFixed(0)}%</div>
              <div className="text-sm text-gray-600">Execution Probability</div>
              <div className="text-xs text-gray-500">Success likelihood</div>
            </div>
            
            {/* Risk Score */}
            <div className="text-center">
              <div className="text-4xl font-bold text-red-600 mb-2">{arbitrageScore.riskScore.toFixed(0)}</div>
              <div className="text-sm text-gray-600">Risk Score</div>
              <div className="text-xs text-gray-500">Lower is better</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Profit Analysis */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <DollarSign className="w-5 h-5" />
            <span>Profit Analysis</span>
          </CardTitle>
          <CardDescription>Gross vs net profit after fees and risk adjustment</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">${arbitrageScore.grossProfit.toFixed(2)}</div>
                <div className="text-sm text-green-600">Gross Profit</div>
                <div className="text-xs text-gray-500">Before fees</div>
              </div>
              
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">${arbitrageScore.netProfit.toFixed(2)}</div>
                <div className="text-sm text-blue-600">Net Profit</div>
                <div className="text-xs text-gray-500">After fees</div>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">
                  {((arbitrageScore.netProfit / (marketData.binance?.ask || 1)) * 100).toFixed(3)}%
                </div>
                <div className="text-sm text-purple-600">Profit Margin</div>
                <div className="text-xs text-gray-500">Net profit %</div>
              </div>
              
              <div className="text-center p-4 bg-orange-50 rounded-lg">
                <div className="text-2xl font-bold text-orange-600">
                  {((arbitrageScore.grossProfit - arbitrageScore.netProfit) / arbitrageScore.grossProfit * 100).toFixed(1)}%
                </div>
                <div className="text-sm text-orange-600">Fee Impact</div>
                <div className="text-xs text-gray-500">Fee % of gross</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Factor Analysis */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <BarChart3 className="w-5 h-5" />
            <span>Factor Analysis</span>
          </CardTitle>
          <CardDescription>Individual factor scores and weights</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Object.entries(arbitrageScore.factors).map(([factor, score]) => (
              <div key={factor} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {factor === 'profitMargin' && <DollarSign className="w-4 h-4 text-green-600" />}
                    {factor === 'liquidityDepth' && <Zap className="w-4 h-4 text-blue-600" />}
                    {factor === 'volatilityRisk' && <AlertTriangle className="w-4 h-4 text-yellow-600" />}
                    {factor === 'executionSpeed' && <Clock className="w-4 h-4 text-purple-600" />}
                    {factor === 'regulatoryRisk' && <Shield className="w-4 h-4 text-indigo-600" />}
                    {factor === 'technicalRisk' && <TrendingUp className="w-4 h-4 text-pink-600" />}
                    <span className="font-medium capitalize">{factor.replace(/([A-Z])/g, ' $1').trim()}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Progress value={score} className="w-20" />
                    <span className="text-sm font-medium w-12 text-right">{score.toFixed(0)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5" />
            <span>Execution Recommendations</span>
          </CardTitle>
          <CardDescription>Actionable insights based on risk assessment</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {arbitrageScore.recommendations.map((recommendation, index) => (
              <div key={index} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0"></div>
                <span className="text-sm text-gray-700">{recommendation}</span>
              </div>
            ))}
          </div>
          
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <Target className="w-5 h-5 text-blue-600" />
              <span className="font-semibold text-blue-800">Final Verdict</span>
            </div>
            <p className="text-sm text-blue-700">
              {arbitrageScore.overallScore > 80 
                ? "This is an excellent arbitrage opportunity with high execution probability and manageable risk."
                : arbitrageScore.overallScore > 60
                ? "This is a good opportunity with moderate risk. Execute with appropriate position sizing."
                : arbitrageScore.overallScore > 40
                ? "This opportunity has elevated risk. Consider waiting for better conditions or reduce position size."
                : "This opportunity has high risk and is not recommended for execution at this time."
              }
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
