import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import asyncio

from config import Config
from ingest.normalize import OrderBook
from state.portfolio import ArbitrageOpportunity

logger = logging.getLogger(__name__)

class ArbitrageDetector:
    """Advanced arbitrage detection across multiple assets and exchanges"""
    
    def __init__(self):
        self.opportunities: Dict[str, List[ArbitrageOpportunity]] = {}
        self.last_detection = {}
        self.detection_stats = {
            "total_opportunities": 0,
            "profitable_opportunities": 0,
            "total_profit_potential_usd": Decimal('0'),
            "avg_spread_bps": Decimal('0')
        }
        
        # Initialize opportunity tracking for each asset
        for symbol in Config.SYMBOLS:
            self.opportunities[symbol] = []
            self.last_detection[symbol] = None
    
    def detect_opportunities(
        self,
        binance_books: Dict[str, OrderBook],
        kraken_books: Dict[str, OrderBook]
    ) -> List[ArbitrageOpportunity]:
        """Detect arbitrage opportunities across all assets"""
        all_opportunities = []
        
        for symbol in Config.SYMBOLS:
            try:
                binance_book = binance_books.get(symbol)
                kraken_book = kraken_books.get(symbol)
                
                if not binance_book or not kraken_book:
                    continue
                
                # Check if order books are fresh
                if self._is_stale(binance_book) or self._is_stale(kraken_book):
                    continue
                
                # Detect opportunities for this symbol
                symbol_opportunities = self._detect_symbol_opportunities(
                    symbol, binance_book, kraken_book
                )
                
                if symbol_opportunities:
                    all_opportunities.extend(symbol_opportunities)
                    self.opportunities[symbol].extend(symbol_opportunities)
                    self.last_detection[symbol] = datetime.now(timezone.utc)
                    
                    # Update statistics
                    self._update_stats(symbol_opportunities)
                    
            except Exception as e:
                logger.error(f"Error detecting opportunities for {symbol}: {e}")
                continue
        
        # Clean up expired opportunities
        self._cleanup_expired_opportunities()
        
        return all_opportunities
    
    def _detect_symbol_opportunities(
        self,
        symbol: str,
        binance_book: OrderBook,
        kraken_book: OrderBook
    ) -> List[ArbitrageOpportunity]:
        """Detect arbitrage opportunities for a specific symbol"""
        opportunities = []
        
        try:
            # Get asset-specific thresholds
            thresholds = Config.ASSET_LIQUIDITY_THRESHOLDS.get(symbol, {})
            min_spread_bps = Decimal(str(thresholds.get("min_spread_bps", 10)))
            max_impact_bps = Decimal(str(thresholds.get("max_impact_bps", 25)))
            min_depth_usd = Decimal(str(thresholds.get("min_depth_usd", 50000)))
            
            # Calculate cross-exchange spread
            binance_mid = binance_book.mid_price
            kraken_mid = kraken_book.mid_price
            
            if not binance_mid or not kraken_mid:
                return opportunities
            
            # Calculate spread in basis points
            spread = abs(binance_mid - kraken_mid)
            spread_bps = (spread / min(binance_mid, kraken_mid)) * 10000
            
            # Check if spread meets minimum threshold
            if spread_bps < min_spread_bps:
                return opportunities
            
            # Determine buy/sell venues
            if binance_mid < kraken_mid:
                buy_venue = "binance"
                sell_venue = "kraken"
                buy_price = binance_mid
                sell_price = kraken_mid
            else:
                buy_venue = "kraken"
                sell_venue = "binance"
                buy_price = kraken_mid
                sell_price = binance_mid
            
            # Calculate optimal trade size
            optimal_size = self._calculate_optimal_trade_size(
                symbol, buy_venue, sell_venue, buy_price, sell_price,
                binance_book, kraken_book, max_impact_bps, min_depth_usd
            )
            
            if optimal_size <= 0:
                return opportunities
            
            # Calculate estimated profit
            estimated_profit_usd = (sell_price - buy_price) * optimal_size
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                symbol, spread_bps, optimal_size, binance_book, kraken_book
            )
            
            # Create opportunity
            opportunity = ArbitrageOpportunity(
                symbol=symbol,
                buy_venue=buy_venue,
                sell_venue=sell_venue,
                buy_price=Decimal(str(buy_price)),
                sell_price=Decimal(str(sell_price)),
                spread_bps=Decimal(str(spread_bps)),
                estimated_profit_usd=Decimal(str(estimated_profit_usd)),
                max_trade_size=Decimal(str(optimal_size)),
                confidence_score=confidence_score,
                timestamp=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)  # 5 min expiry
            )
            
            opportunities.append(opportunity)
            logger.info(f"Arbitrage opportunity detected: {symbol} {spread_bps:.1f} bps spread, "
                       f"${estimated_profit_usd:.2f} profit potential")
            
        except Exception as e:
            logger.error(f"Error in symbol opportunity detection for {symbol}: {e}")
        
        return opportunities
    
    def _calculate_optimal_trade_size(
        self,
        symbol: str,
        buy_venue: str,
        sell_venue: str,
        buy_price: float,
        sell_price: float,
        binance_book: OrderBook,
        kraken_book: OrderBook,
        max_impact_bps: Decimal,
        min_depth_usd: Decimal
    ) -> float:
        """Calculate optimal trade size that maximizes profit while minimizing market impact"""
        try:
            # Get order book for buy venue
            buy_book = binance_book if buy_venue == "binance" else kraken_book
            
            # Calculate how much we can buy without exceeding max impact
            buy_depth = buy_book.analyze_depth()
            optimal_buy_size, buy_impact = buy_depth.get_optimal_trade_size(float(max_impact_bps))
            
            # Get order book for sell venue
            sell_book = binance_book if sell_venue == "binance" else kraken_book
            
            # Calculate how much we can sell without exceeding max impact
            sell_depth = sell_book.analyze_depth()
            optimal_sell_size, sell_impact = sell_depth.get_optimal_trade_size(float(max_impact_bps))
            
            # Use the smaller of the two to ensure we can execute both sides
            optimal_size = min(optimal_buy_size, optimal_sell_size)
            
            # Check minimum depth requirement
            if optimal_size * buy_price < float(min_depth_usd):
                return 0.0
            
            # Check if opportunity is still profitable after fees
            fees_bps = 20  # 0.2% total fees (0.1% per side)
            net_spread_bps = float(max_impact_bps) - fees_bps
            
            if net_spread_bps <= 0:
                return 0.0
            
            return optimal_size
            
        except Exception as e:
            logger.error(f"Error calculating optimal trade size: {e}")
            return 0.0
    
    def _calculate_confidence_score(
        self,
        symbol: str,
        spread_bps: Decimal,
        trade_size: float,
        binance_book: OrderBook,
        kraken_book: OrderBook
    ) -> float:
        """Calculate confidence score for arbitrage opportunity (0-1)"""
        try:
            score = 0.0
            
            # Base score from spread size (higher spread = higher confidence)
            max_spread = 100  # 100 bps = 1% spread
            spread_score = min(float(spread_bps) / max_spread, 1.0)
            score += spread_score * 0.4  # 40% weight
            
            # Liquidity score (more liquid = higher confidence)
            binance_liquidity = binance_book.calculate_liquidity_score()
            kraken_liquidity = kraken_book.calculate_liquidity_score()
            total_liquidity = binance_liquidity + kraken_liquidity
            
            # Normalize liquidity (assume $1M is "high" liquidity)
            liquidity_score = min(total_liquidity / 1000000, 1.0)
            score += liquidity_score * 0.3  # 30% weight
            
            # Market depth score (deeper order book = higher confidence)
            binance_depth = binance_book.analyze_depth()
            kraken_depth = kraken_book.analyze_depth()
            
            total_depth = binance_depth.total_bid_depth + binance_depth.total_ask_depth + \
                         kraken_depth.total_bid_depth + kraken_depth.total_ask_depth
            
            # Normalize depth (assume 100 BTC is "deep" order book)
            depth_score = min(total_depth / 100, 1.0)
            score += depth_score * 0.2  # 20% weight
            
            # Recency score (fresher data = higher confidence)
            now = datetime.now(timezone.utc)
            binance_age = (now - binance_book.timestamp).total_seconds()
            kraken_age = (now - kraken_book.timestamp).total_seconds()
            
            max_age = 5.0  # 5 seconds
            recency_score = max(0, 1 - (max(binance_age, kraken_age) / max_age))
            score += recency_score * 0.1  # 10% weight
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating confidence score: {e}")
            return 0.5  # Default to medium confidence
    
    def _is_stale(self, order_book: OrderBook) -> bool:
        """Check if order book is stale"""
        if not order_book:
            return True
        
        now = datetime.now(timezone.utc)
        age = (now - order_book.timestamp).total_seconds()
        return age > Config.VENUE_STALE_THRESHOLD
    
    def _cleanup_expired_opportunities(self):
        """Remove expired opportunities from all symbols"""
        for symbol in self.opportunities:
            self.opportunities[symbol] = [
                opp for opp in self.opportunities[symbol] 
                if not opp.is_expired()
            ]
    
    def _update_stats(self, opportunities: List[ArbitrageOpportunity]):
        """Update detection statistics"""
        if not opportunities:
            return
        
        self.detection_stats["total_opportunities"] += len(opportunities)
        
        for opp in opportunities:
            if opp.is_profitable(Config.MIN_PROFIT_THRESHOLD_BPS):
                self.detection_stats["profitable_opportunities"] += 1
                self.detection_stats["total_profit_potential_usd"] += opp.estimated_profit_usd
        
        # Update average spread
        total_spread = sum(opp.spread_bps for opp in opportunities)
        self.detection_stats["avg_spread_bps"] = total_spread / len(opportunities)
    
    def get_opportunities_summary(self) -> dict:
        """Get summary of all current opportunities"""
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_opportunities": 0,
            "profitable_opportunities": 0,
            "total_profit_potential_usd": 0.0,
            "avg_spread_bps": 0.0,
            "by_symbol": {},
            "detection_stats": self.detection_stats.copy()
        }
        
        for symbol in self.opportunities:
            symbol_opps = [opp for opp in self.opportunities[symbol] if not opp.is_expired()]
            
            if symbol_opps:
                symbol_summary = {
                    "count": len(symbol_opps),
                    "best_spread_bps": float(max(opp.spread_bps for opp in symbol_opps)),
                    "total_profit_potential_usd": float(sum(opp.estimated_profit_usd for opp in symbol_opps)),
                    "avg_confidence": sum(opp.confidence_score for opp in symbol_opps) / len(symbol_opps)
                }
                
                summary["by_symbol"][symbol] = symbol_summary
                summary["total_opportunities"] += len(symbol_opps)
                
                profitable_opps = [opp for opp in symbol_opps if opp.is_profitable(Config.MIN_PROFIT_THRESHOLD_BPS)]
                summary["profitable_opportunities"] += len(profitable_opps)
                summary["total_profit_potential_usd"] += sum(opp.estimated_profit_usd for opp in profitable_opps)
        
        if summary["total_opportunities"] > 0:
            summary["avg_spread_bps"] = summary["total_profit_potential_usd"] / summary["total_opportunities"]
        
        return summary
    
    def get_best_opportunities(self, limit: int = 10) -> List[ArbitrageOpportunity]:
        """Get best arbitrage opportunities across all symbols"""
        all_opportunities = []
        
        for symbol_opps in self.opportunities.values():
            all_opportunities.extend(symbol_opps)
        
        # Filter out expired opportunities and sort by profit potential
        valid_opportunities = [
            opp for opp in all_opportunities 
            if not opp.is_expired() and opp.is_profitable(Config.MIN_PROFIT_THRESHOLD_BPS)
        ]
        
        return sorted(
            valid_opportunities,
            key=lambda x: (x.estimated_profit_usd, x.confidence_score),
            reverse=True
        )[:limit]
