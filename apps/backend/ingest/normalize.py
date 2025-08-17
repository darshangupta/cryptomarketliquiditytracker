from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict
import logging

logger = logging.getLogger(__name__)

@dataclass
class OrderBookLevel:
    """Single level in an order book"""
    price: float
    size: float
    
    def __post_init__(self):
        # Ensure positive values
        if self.price <= 0:
            raise ValueError(f"Price must be positive: {self.price}")
        if self.size <= 0:
            raise ValueError(f"Size must be positive: {self.size}")

@dataclass
class DepthAnalysis:
    """Analysis of order book depth and liquidity"""
    cumulative_bid_depth: Dict[float, float]  # price -> cumulative size
    cumulative_ask_depth: Dict[float, float]  # price -> cumulative size
    total_bid_depth: float
    total_ask_depth: float
    bid_levels: int
    ask_levels: int
    
    def get_market_impact(self, trade_size: float, side: str) -> Tuple[float, float]:
        """Calculate market impact of a trade
        
        Args:
            trade_size: Size of trade in BTC
            side: 'buy' or 'sell'
            
        Returns:
            (execution_price, price_impact)
        """
        if side.lower() == "buy":
            return self._calculate_buy_impact(trade_size)
        elif side.lower() == "sell":
            return self._calculate_sell_impact(trade_size)
        else:
            raise ValueError("Side must be 'buy' or 'sell'")
    
    def _calculate_buy_impact(self, trade_size: float) -> Tuple[float, float]:
        """Calculate impact of buying trade_size BTC"""
        remaining_size = trade_size
        total_cost = 0.0
        weighted_price = 0.0
        
        # Sort asks by price (ascending)
        sorted_prices = sorted(self.cumulative_ask_depth.keys())
        
        for price in sorted_prices:
            available_size = self.cumulative_ask_depth[price]
            if remaining_size <= 0:
                break
                
            # How much we can buy at this price
            buy_size = min(remaining_size, available_size)
            total_cost += buy_size * price
            weighted_price += buy_size * price
            remaining_size -= buy_size
        
        if trade_size - remaining_size > 0:
            avg_price = weighted_price / (trade_size - remaining_size)
            price_impact = (avg_price - sorted_prices[0]) / sorted_prices[0] * 100
            return avg_price, price_impact
        
        return 0.0, 0.0
    
    def _calculate_sell_impact(self, trade_size: float) -> Tuple[float, float]:
        """Calculate impact of selling trade_size BTC"""
        remaining_size = trade_size
        total_revenue = 0.0
        weighted_price = 0.0
        
        # Sort bids by price (descending)
        sorted_prices = sorted(self.cumulative_bid_depth.keys(), reverse=True)
        
        for price in sorted_prices:
            available_size = self.cumulative_bid_depth[price]
            if remaining_size <= 0:
                break
                
            # How much we can sell at this price
            sell_size = min(remaining_size, available_size)
            total_revenue += sell_size * price
            weighted_price += sell_size * price
            remaining_size -= sell_size
        
        if trade_size - remaining_size > 0:
            avg_price = weighted_price / (trade_size - remaining_size)
            price_impact = (sorted_prices[0] - avg_price) / sorted_prices[0] * 100
            return avg_price, price_impact
        
        return 0.0, 0.0
    
    def get_optimal_trade_size(self, max_impact_bps: float = 10.0) -> Tuple[float, float]:
        """Find optimal trade size that keeps price impact below threshold
        
        Args:
            max_impact_bps: Maximum price impact in basis points
            
        Returns:
            (optimal_size, expected_impact_bps)
        """
        # Test different trade sizes
        test_sizes = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
        
        for size in test_sizes:
            buy_price, buy_impact = self._calculate_buy_impact(size)
            sell_price, sell_impact = self._calculate_sell_impact(size)
            
            # Use the worse of the two impacts
            max_impact = max(buy_impact, sell_impact)
            
            if max_impact <= max_impact_bps / 100:  # Convert bps to percentage
                return size, max_impact * 100  # Return in bps
        
        return 0.0, 0.0

@dataclass
class OrderBook:
    """Normalized order book from any exchange"""
    venue: str
    symbol: str
    timestamp: datetime
    server_timestamp: Optional[datetime]
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    
    def __post_init__(self):
        # Ensure UTC timestamps
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)
        if self.server_timestamp and self.server_timestamp.tzinfo is None:
            self.server_timestamp = self.server_timestamp.replace(tzinfo=timezone.utc)
        
        # Sort bids (descending) and asks (ascending)
        self.bids.sort(key=lambda x: x.price, reverse=True)
        self.asks.sort(key=lambda x: x.price)
        
        # Validate order book integrity
        if self.bids and self.asks:
            best_bid = self.bids[0].price
            best_ask = self.asks[0].price
            if best_bid >= best_ask:
                logger.warning(f"Crossed order book: best_bid={best_bid}, best_ask={best_ask}")
    
    @property
    def best_bid(self) -> Optional[float]:
        """Best bid price"""
        return self.bids[0].price if self.bids else None
    
    @property
    def best_ask(self) -> Optional[float]:
        """Best ask price"""
        return self.asks[0].price if self.asks else None
    
    @property
    def mid_price(self) -> Optional[float]:
        """Mid price"""
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2
        return None
    
    @property
    def spread_bps(self) -> Optional[float]:
        """Spread in basis points"""
        if self.best_bid and self.best_ask:
            mid = self.mid_price
            return 10_000 * (self.best_ask - self.best_bid) / mid
        return None
    
    def get_depth_at_price(self, target_price: float, side: str) -> float:
        """Get total size at or better than target price"""
        if side.lower() == "bid":
            levels = [level for level in self.bids if level.price >= target_price]
        elif side.lower() == "ask":
            levels = [level for level in self.asks if level.price <= target_price]
        else:
            raise ValueError("Side must be 'bid' or 'ask'")
        
        return sum(level.size for level in levels)
    
    def get_depth_within_bps(self, bps: float) -> Tuple[float, float]:
        """Get bid and ask depth within ±bps of mid price"""
        mid = self.mid_price
        if not mid:
            return 0.0, 0.0
        
        # Calculate price bounds
        bid_bound = mid * (1 - bps / 10_000)
        ask_bound = mid * (1 + bps / 10_000)
        
        bid_depth = self.get_depth_at_price(bid_bound, "bid")
        ask_depth = self.get_depth_at_price(ask_bound, "ask")
        
        return bid_depth, ask_depth
    
    def analyze_depth(self) -> DepthAnalysis:
        """Analyze order book depth and liquidity"""
        # Calculate cumulative bid depth
        cumulative_bid_depth = {}
        running_total = 0.0
        for level in self.bids:
            running_total += level.size
            cumulative_bid_depth[level.price] = running_total
        
        # Calculate cumulative ask depth
        cumulative_ask_depth = {}
        running_total = 0.0
        for level in self.asks:
            running_total += level.size
            cumulative_ask_depth[level.price] = running_total
        
        return DepthAnalysis(
            cumulative_bid_depth=cumulative_bid_depth,
            cumulative_ask_depth=cumulative_ask_depth,
            total_bid_depth=sum(level.size for level in self.bids),
            total_ask_depth=sum(level.size for level in self.asks),
            bid_levels=len(self.bids),
            ask_levels=len(self.asks)
        )
    
    def get_top_levels(self, count: int = 20) -> Tuple[List[OrderBookLevel], List[OrderBookLevel]]:
        """Get top N bid and ask levels"""
        top_bids = self.bids[:count] if self.bids else []
        top_asks = self.asks[:count] if self.asks else []
        return top_bids, top_asks
    
    def calculate_liquidity_score(self, window_bps: float = 50.0) -> float:
        """Calculate liquidity score based on depth within price window
        
        Higher score = more liquid market
        """
        mid = self.mid_price
        if not mid:
            return 0.0
        
        # Get depth within ±window_bps
        bid_depth, ask_depth = self.get_depth_within_bps(window_bps)
        total_depth = bid_depth + ask_depth
        
        # Normalize by mid price (depth in USD terms)
        if mid > 0:
            return total_depth * mid
        return 0.0

class OrderBookNormalizer:
    """Normalize order books from different exchanges"""
    
    @staticmethod
    def normalize_binance(data: dict, venue: str = "binance") -> OrderBook:
        """Normalize Binance order book data"""
        try:
            # Extract order book data
            symbol = data.get("s", "BTCUSDT")  # Symbol
            timestamp = datetime.fromtimestamp(data.get("E", 0) / 1000, tz=timezone.utc)
            
            # Parse bids and asks
            bids = []
            asks = []
            
            # Handle both snapshot and update formats
            if "bids" in data:
                for price_str, size_str in data["bids"]:
                    price = float(price_str)
                    size = float(size_str)
                    if price > 0 and size > 0:
                        bids.append(OrderBookLevel(price, size))
            
            if "asks" in data:
                for price_str, size_str in data["asks"]:
                    price = float(price_str)
                    size = float(size_str)
                    if price > 0 and size > 0:
                        asks.append(OrderBookLevel(price, size))
            
            return OrderBook(
                venue=venue,
                symbol=symbol,
                timestamp=timestamp,
                server_timestamp=timestamp,  # Binance provides server timestamp
                bids=bids,
                asks=asks
            )
            
        except Exception as e:
            logger.error(f"Failed to normalize Binance data: {e}")
            raise
    
    @staticmethod
    def normalize_coinbase(data: dict, venue: str = "coinbase") -> OrderBook:
        """Normalize Coinbase order book data"""
        try:
            # Extract order book data
            symbol = data.get("product_id", "BTC-USD")
            
            # Coinbase doesn't provide server timestamp in order book updates
            timestamp = datetime.now(timezone.utc)
            
            # Parse bids and asks
            bids = []
            asks = []
            
            if "bids" in data:
                for bid_data in data["bids"]:
                    if isinstance(bid_data, list) and len(bid_data) >= 2:
                        price = float(bid_data[0])
                        size = float(bid_data[1])
                        if price > 0 and size > 0:
                            bids.append(OrderBookLevel(price, size))
            
            if "asks" in data:
                for ask_data in data["asks"]:
                    if isinstance(ask_data, list) and len(ask_data) >= 2:
                        price = float(ask_data[0])
                        size = float(ask_data[1])
                        if price > 0 and size > 0:
                            asks.append(OrderBookLevel(price, size))
            
            return OrderBook(
                venue=venue,
                symbol=symbol,
                timestamp=timestamp,
                server_timestamp=None,  # Coinbase doesn't provide this
                bids=bids,
                asks=asks
            )
            
        except Exception as e:
            logger.error(f"Failed to normalize Coinbase data: {e}")
            raise
    
    @staticmethod
    def normalize_kraken(data: dict, venue: str = "kraken") -> OrderBook:
        """Normalize Kraken order book data"""
        try:
            # Extract order book data
            symbol = "XBT/USD"  # Kraken uses XBT for Bitcoin
            
            # Kraken doesn't provide server timestamp in order book updates
            timestamp = datetime.now(timezone.utc)
            
            # Parse bids and asks
            bids = []
            asks = []
            
            if "b" in data:  # Bids
                for bid_data in data["b"]:
                    if isinstance(bid_data, list) and len(bid_data) >= 2:
                        price = float(bid_data[0])
                        size = float(bid_data[1])
                        if price > 0 and size > 0:
                            bids.append(OrderBookLevel(price, size))
            
            if "a" in data:  # Asks
                for ask_data in data["a"]:
                    if isinstance(ask_data, list) and len(ask_data) >= 2:
                        price = float(ask_data[0])
                        size = float(ask_data[1])
                        if price > 0 and size > 0:
                            asks.append(OrderBookLevel(price, size))
            
            return OrderBook(
                venue=venue,
                symbol=symbol,
                timestamp=timestamp,
                server_timestamp=None,  # Kraken doesn't provide this
                bids=bids,
                asks=asks
            )
            
        except Exception as e:
            logger.error(f"Failed to normalize Kraken data: {e}")
            raise
    
    @staticmethod
    def is_stale(order_book: OrderBook, threshold_seconds: float = 3.0) -> bool:
        """Check if order book is stale"""
        now = datetime.now(timezone.utc)
        age = (now - order_book.timestamp).total_seconds()
        return age > threshold_seconds
    
    def is_stale(self, threshold_seconds: float = 3.0) -> bool:
        """Check if this order book is stale"""
        return OrderBookNormalizer.is_stale(self, threshold_seconds)
