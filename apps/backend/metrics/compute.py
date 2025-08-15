import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from config import Config
from ingest.normalize import OrderBook

logger = logging.getLogger(__name__)

class MetricsComputer:
    """Compute market metrics from order books"""
    
    def __init__(self):
        self.window_bps = Config.DEPTH_WINDOW_BPS
    
    def compute_metrics(self, binance_book: OrderBook, coinbase_book: OrderBook) -> dict:
        """Compute all metrics from two venue order books"""
        try:
            # Basic price metrics
            mid_price = self._compute_mid_price(binance_book, coinbase_book)
            spread_bps = self._compute_spread_bps(binance_book, coinbase_book)
            
            # Depth metrics
            depth_050 = self._compute_depth_050(binance_book, coinbase_book)
            
            # Venue-specific metrics
            venue_metrics = self._compute_venue_metrics(binance_book, coinbase_book)
            
            # Market structure metrics
            hhi = self._compute_hhi(venue_metrics)
            logger.debug(f"About to compute imbalance with books: binance={binance_book}, coinbase={coinbase_book}")
            imbalance = self._compute_imbalance(binance_book, coinbase_book)
            logger.debug(f"Imbalance result: {imbalance}")
            
            # Build metrics frame
            metrics = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "symbol": "BTC-USD",
                "window_bps": self.window_bps,
                "mid": round(mid_price, 2) if mid_price else None,
                "spread_bps": round(spread_bps, 1) if spread_bps else None,
                "depth_050": round(depth_050, 6) if depth_050 else None,
                "hhi": round(hhi, 3) if hhi else None,
                "imbalance": round(imbalance, 3) if imbalance else None,
                "venues": venue_metrics
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to compute metrics: {e}")
            return self._get_empty_metrics()
    
    def _compute_mid_price(self, binance_book: OrderBook, coinbase_book: OrderBook) -> Optional[float]:
        """Compute cross-venue mid price"""
        try:
            # Get mid prices from each venue
            binance_mid = binance_book.mid_price if binance_book else None
            coinbase_mid = coinbase_book.mid_price if coinbase_book else None
            
            if binance_mid and coinbase_mid:
                # Simple average of venue mid prices
                return (binance_mid + coinbase_mid) / 2
            elif binance_mid:
                return binance_mid
            elif coinbase_mid:
                return coinbase_mid
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to compute mid price: {e}")
            return None
    
    def _compute_spread_bps(self, binance_book: OrderBook, coinbase_book: OrderBook) -> Optional[float]:
        """Compute cross-venue spread in basis points"""
        try:
            mid_price = self._compute_mid_price(binance_book, coinbase_book)
            if not mid_price:
                return None
            
            # Find best bid and ask across venues
            best_bid = None
            best_ask = None
            
            if binance_book and binance_book.best_bid:
                best_bid = binance_book.best_bid
            if coinbase_book and coinbase_book.best_bid:
                if best_bid is None or coinbase_book.best_bid > best_bid:
                    best_bid = coinbase_book.best_bid
            
            if binance_book and binance_book.best_ask:
                best_ask = binance_book.best_ask
            if coinbase_book and coinbase_book.best_ask:
                if best_ask is None or coinbase_book.best_ask < best_ask:
                    best_ask = coinbase_book.best_ask
            
            if best_bid and best_ask and best_bid < best_ask:
                return 10_000 * (best_ask - best_bid) / mid_price
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to compute spread: {e}")
            return None
    
    def _compute_depth_050(self, binance_book: OrderBook, coinbase_book: OrderBook) -> Optional[float]:
        """Compute total depth within ±0.5% of mid price"""
        try:
            mid_price = self._compute_mid_price(binance_book, coinbase_book)
            if not mid_price:
                return None
            
            total_depth = 0.0
            
            # Add Binance depth
            if binance_book:
                bid_depth, ask_depth = binance_book.get_depth_within_bps(self.window_bps)
                total_depth += bid_depth + ask_depth
            
            # Add Coinbase depth
            if coinbase_book:
                bid_depth, ask_depth = coinbase_book.get_depth_within_bps(self.window_bps)
                total_depth += bid_depth + ask_depth
            
            return total_depth
            
        except Exception as e:
            logger.error(f"Failed to compute depth: {e}")
            return None
    
    def _compute_venue_metrics(self, binance_book: OrderBook, coinbase_book: OrderBook) -> List[dict]:
        """Compute venue-specific metrics"""
        venues = []
        
        # Binance metrics
        if binance_book:
            binance_metrics = self._compute_single_venue_metrics(binance_book, "binance")
            venues.append(binance_metrics)
        
        # Coinbase metrics
        if coinbase_book:
            coinbase_metrics = self._compute_single_venue_metrics(coinbase_book, "coinbase")
            venues.append(coinbase_metrics)
        
        return venues
    
    def _compute_single_venue_metrics(self, order_book: OrderBook, venue: str) -> dict:
        """Compute metrics for a single venue"""
        try:
            # Check if venue is stale
            is_stale = order_book.is_stale() if hasattr(order_book, 'is_stale') and callable(order_book.is_stale) else False
            
            # Basic metrics
            spread_bps = order_book.spread_bps
            mid_price = order_book.mid_price
            
            # Compute depth within window
            bid_depth, ask_depth = order_book.get_depth_within_bps(self.window_bps)
            total_depth = bid_depth + ask_depth
            
            # Compute share (will be normalized later)
            share = total_depth
            
            # Compute latency
            latency_ms = self._compute_latency(order_book)
            
            return {
                "venue": venue,
                "spread_bps": round(spread_bps, 1) if spread_bps else None,
                "share": round(share, 6) if share else 0.0,
                "latency_ms": round(latency_ms, 1) if latency_ms else None,
                "stale": is_stale
            }
            
        except Exception as e:
            logger.error(f"Failed to compute venue metrics for {venue}: {e}")
            return {
                "venue": venue,
                "spread_bps": None,
                "share": 0.0,
                "latency_ms": None,
                "stale": True
            }
    
    def _compute_latency(self, order_book: OrderBook) -> Optional[float]:
        """Compute latency in milliseconds"""
        try:
            now = datetime.now(timezone.utc)
            
            if order_book.server_timestamp:
                # Use server timestamp if available
                latency = (now - order_book.server_timestamp).total_seconds() * 1000
            else:
                # Fall back to local timestamp
                latency = (now - order_book.timestamp).total_seconds() * 1000
            
            return max(0, latency)  # Ensure non-negative
            
        except Exception as e:
            logger.error(f"Failed to compute latency: {e}")
            return None
    
    def _compute_hhi(self, venue_metrics: List[dict]) -> Optional[float]:
        """Compute Herfindahl-Hirschman Index"""
        try:
            if not venue_metrics:
                return None
            
            # Normalize shares to sum to 1
            total_share = sum(venue["share"] for venue in venue_metrics if venue["share"] > 0)
            
            if total_share == 0:
                return 0.0
            
            # Compute HHI
            hhi = 0.0
            for venue in venue_metrics:
                if venue["share"] > 0:
                    normalized_share = venue["share"] / total_share
                    hhi += normalized_share ** 2
            
            return hhi
            
        except Exception as e:
            logger.error(f"Failed to compute HHI: {e}")
            return None
    
    def _compute_imbalance(self, binance_book: OrderBook, coinbase_book: OrderBook) -> Optional[float]:
        """Compute order book imbalance"""
        try:
            mid_price = self._compute_mid_price(binance_book, coinbase_book)
            if not mid_price:
                logger.debug("No mid price available for imbalance calculation")
                return None
            
            total_bid_depth = 0.0
            total_ask_depth = 0.0
            
            # Add Binance depth
            if binance_book:
                bid_depth, ask_depth = binance_book.get_depth_within_bps(self.window_bps)
                total_bid_depth += bid_depth
                total_ask_depth += ask_depth
                logger.debug(f"Binance depth: bid={bid_depth}, ask={ask_depth}")
            
            # Add Coinbase depth
            if coinbase_book:
                bid_depth, ask_depth = coinbase_book.get_depth_within_bps(self.window_bps)
                total_bid_depth += bid_depth
                total_ask_depth += ask_depth
                logger.debug(f"Coinbase depth: bid={bid_depth}, ask={ask_depth}")
            
            # Compute imbalance
            total_depth = total_bid_depth + total_ask_depth
            logger.debug(f"Total depth: bid={total_bid_depth}, ask={total_ask_depth}, total={total_depth}")
            
            if total_depth > 0:
                imbalance = (total_bid_depth - total_ask_depth) / total_depth
                result = max(-1.0, min(1.0, imbalance))  # Clamp to [-1, 1]
                logger.debug(f"Computed imbalance: {imbalance} -> {result}")
                return result
            else:
                logger.debug("Total depth is 0, returning 0.0")
                return 0.0
                
        except Exception as e:
            logger.error(f"Failed to compute imbalance: {e}")
            return None
    
    def _get_empty_metrics(self) -> dict:
        """Return empty metrics when computation fails"""
        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "symbol": "BTC-USD",
            "window_bps": self.window_bps,
            "mid": None,
            "spread_bps": None,
            "depth_050": None,
            "hhi": None,
            "imbalance": None,
            "venues": []
        }
