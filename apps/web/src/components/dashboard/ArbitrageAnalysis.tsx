"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, XCircle, CheckCircle } from "lucide-react";
import { ArbitrageData } from "./types";

interface ArbitrageAnalysisProps {
  arbitrageData: ArbitrageData | null;
}

export function ArbitrageAnalysis({ arbitrageData }: ArbitrageAnalysisProps) {
  if (!arbitrageData) return null;

  return (
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
              This opportunity exceeds minimum profit threshold
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
