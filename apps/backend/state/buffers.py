import logging
from collections import deque
from datetime import datetime, timezone
from typing import Deque, List, Optional, TypeVar, Generic

from ingest.normalize import OrderBook

logger = logging.getLogger(__name__)

T = TypeVar('T')

class RingBuffer(Generic[T]):
    """Generic ring buffer implementation"""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.buffer: Deque[T] = deque(maxlen=max_size)
    
    def add(self, item: T) -> None:
        """Add item to buffer"""
        self.buffer.append(item)
    
    def get_latest(self) -> Optional[T]:
        """Get most recent item"""
        return self.buffer[-1] if self.buffer else None
    
    def get_all(self) -> List[T]:
        """Get all items in buffer"""
        return list(self.buffer)
    
    def get_recent(self, count: int) -> List[T]:
        """Get most recent n items"""
        return list(self.buffer)[-count:]
    
    def size(self) -> int:
        """Get current buffer size"""
        return len(self.buffer)
    
    def is_full(self) -> bool:
        """Check if buffer is full"""
        return len(self.buffer) >= self.max_size
    
    def clear(self) -> None:
        """Clear all items from buffer"""
        self.buffer.clear()

class OrderBookBuffer:
    """Ring buffer for order book data"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.binance_buffer = RingBuffer[OrderBook](max_size)
        self.kraken_buffer = RingBuffer[OrderBook](max_size)
        self.metrics_buffer = RingBuffer[dict](max_size)
    
    def add_order_book(self, order_book: OrderBook) -> None:
        """Add order book to appropriate buffer based on venue"""
        try:
            if order_book.venue == "binance":
                self.binance_buffer.add(order_book)
                logger.debug(f"Added Binance order book to buffer. Buffer size: {self.binance_buffer.size()}")
            elif order_book.venue == "kraken":
                self.kraken_buffer.add(order_book)
                logger.debug(f"Added Kraken order book to buffer. Buffer size: {self.kraken_buffer.size()}")
            else:
                logger.warning(f"Unknown venue: {order_book.venue}")
        except Exception as e:
            logger.error(f"Failed to add order book to buffer: {e}")
    
    def add_binance_book(self, order_book: OrderBook) -> None:
        """Add Binance order book to buffer"""
        try:
            self.binance_buffer.add(order_book)
            logger.debug(f"Added Binance order book to buffer. Buffer size: {self.binance_buffer.size()}")
        except Exception as e:
            logger.error(f"Failed to add Binance order book to buffer: {e}")
    
    def add_kraken_book(self, order_book: OrderBook) -> None:
        """Add Kraken order book to buffer"""
        try:
            self.kraken_buffer.add(order_book)
            logger.debug(f"Added Kraken order book to buffer. Buffer size: {self.kraken_buffer.size()}")
        except Exception as e:
            logger.error(f"Failed to add Kraken order book to buffer: {e}")
    
    def add_metrics(self, metrics: dict) -> None:
        """Add computed metrics to buffer"""
        try:
            self.metrics_buffer.add(metrics)
            logger.debug(f"Added metrics to buffer. Buffer size: {self.metrics_buffer.size()}")
        except Exception as e:
            logger.error(f"Failed to add metrics to buffer: {e}")
    
    def get_latest_binance_book(self) -> Optional[OrderBook]:
        """Get most recent Binance order book"""
        return self.binance_buffer.get_latest()
    
    def get_latest_kraken_book(self) -> Optional[OrderBook]:
        """Get most recent Kraken order book"""
        return self.kraken_buffer.get_latest()
    
    def get_latest_metrics(self) -> Optional[dict]:
        """Get most recent metrics"""
        return self.metrics_buffer.get_latest()
    
    def get_recent_metrics(self, count: int) -> List[dict]:
        """Get most recent n metrics"""
        return self.metrics_buffer.get_recent(count)
    
    def get_metrics_since(self, timestamp: datetime) -> List[dict]:
        """Get all metrics since given timestamp"""
        try:
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            
            metrics = []
            for metric in reversed(self.metrics_buffer.get_all()):
                metric_ts = datetime.fromisoformat(metric["ts"].replace('Z', '+00:00'))
                if metric_ts >= timestamp:
                    metrics.append(metric)
                else:
                    break
            
            return list(reversed(metrics))  # Return in chronological order
            
        except Exception as e:
            logger.error(f"Failed to get metrics since timestamp: {e}")
            return []
    
    def get_venue_status(self) -> dict:
        """Get current status of both venues"""
        binance_book = self.get_latest_binance_book()
        kraken_book = self.get_latest_kraken_book()
        
        return {
            "binance": {
                "has_data": binance_book is not None,
                "is_stale": binance_book.is_stale() if binance_book else True,
                "last_update": binance_book.timestamp.isoformat() if binance_book else None
            },
            "kraken": {
                "has_data": kraken_book is not None,
                "is_stale": kraken_book.is_stale() if kraken_book else True,
                "last_update": kraken_book.timestamp.isoformat() if kraken_book else None
            }
        }
    
    def get_buffer_stats(self) -> dict:
        """Get statistics about buffer usage"""
        return {
            "binance_buffer_size": self.binance_buffer.size(),
            "kraken_buffer_size": self.kraken_buffer.size(),
            "metrics_buffer_size": self.metrics_buffer.size(),
            "max_size": self.max_size,
            "binance_buffer_full": self.binance_buffer.is_full(),
            "kraken_buffer_full": self.kraken_buffer.is_full(),
            "metrics_buffer_full": self.metrics_buffer.is_full()
        }
    
    def clear_all(self) -> None:
        """Clear all buffers"""
        self.binance_buffer.clear()
        self.kraken_buffer.clear()
        self.metrics_buffer.clear()
        logger.info("All buffers cleared")
