// Shared types for dashboard components

export interface MarketData {
  timestamp: string;
  binance: {
    bid: number;
    ask: number;
    spread: number;
    spread_bps?: number;
    market_impact?: {
      [key: string]: {
        buy?: { price: number; impact_bps: number };
        sell?: { price: number; impact_bps: number };
      };
    };
    optimal_trade_size?: number;
    optimal_impact_bps?: number;
    top_asks?: { price: number; size: number }[];
    top_bids?: { price: number; size: number }[];
    depth?: number;
    liquidity_score?: number;
  };
  kraken: {
    bid: number;
    ask: number;
    spread: number;
    spread_bps?: number;
    market_impact?: {
      [key: string]: {
        buy?: { price: number; impact_bps: number };
        sell?: { price: number; impact_bps: number };
      };
    };
    optimal_trade_size?: number;
    optimal_impact_bps?: number;
    top_asks?: { price: number; size: number }[];
    top_bids?: { price: number; size: number }[];
    depth?: number;
    liquidity_score?: number;
  };
  metrics: {
    mid: number;
    spread_bps: number;
    depth: number;
    hhi: number;
    imbalance: number;
  };
}

export interface ChartDataPoint {
  timestamp: string;
  binanceBid: number;
  binanceAsk: number;
  krakenBid: number;
  krakenAsk: number;
  spread: number;
  midPrice: number;
}

export interface Alert {
  id: string;
  type: "arbitrage" | "spread" | "price" | "connection";
  severity: "low" | "medium" | "high";
  message: string;
  timestamp: string;
  isActive: boolean;
}

export interface ExchangeFees {
  trading: number;
  withdrawal: number;
  deposit: number;
}

export interface ArbitrageData {
  grossProfit: number;
  totalFees: number;
  netProfit: number;
  profitMargin: number;
  isProfitable: boolean;
  execution: {
    buyExchange: string;
    buyPrice: number;
    sellExchange: string;
    sellPrice: number;
  };
}

export interface AlertSettings {
  spreadThreshold: number;
  priceChangeThreshold: number;
  arbitrageMinProfit: number;
}
