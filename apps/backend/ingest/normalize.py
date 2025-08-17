from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple
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
    def is_stale(order_book: OrderBook, threshold_seconds: float = 3.0) -> bool:
        """Check if order book is stale"""
        now = datetime.now(timezone.utc)
        age = (now - order_book.timestamp).total_seconds()
        return age > threshold_seconds
    
    def is_stale(self, threshold_seconds: float = 3.0) -> bool:
        """Check if this order book is stale"""
        return OrderBookNormalizer.is_stale(self, threshold_seconds)
