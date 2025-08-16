import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from ingest.normalize import OrderBook

logger = logging.getLogger(__name__)

class SmartOrderRouter:
    """Smart Order Router for fee-aware execution"""
    
    def __init__(self):
        pass
    
    def execute_order(
        self,
        side: str,
        notional_usd: float,
        fee_bps: Dict[str, float],
        binance_book: OrderBook,
        coinbase_book: OrderBook
    ) -> dict:
        """Execute order using SOR vs naive baseline"""
        try:
            # Get current mid price for slippage calculation
            mid_t0 = self._get_cross_venue_mid(binance_book, coinbase_book)
            if not mid_t0:
                raise ValueError("Unable to determine mid price")
            
            # Execute naive (single venue) strategy
            naive_result = self._execute_naive(
                side, notional_usd, fee_bps, binance_book, coinbase_book
            )
            
            # Execute SOR (multi-venue) strategy
            sor_result = self._execute_sor(
                side, notional_usd, fee_bps, binance_book, coinbase_book
            )
            
            # Calculate slippage savings
            slippage_saved_bps = naive_result["slippage_bps"] - sor_result["slippage_bps"]
            
            return {
                "ts": datetime.now(timezone.utc).isoformat(),
                "symbol": "BTC-USD",
                "side": side,
                "notional": notional_usd,
                "mid_t0": mid_t0,
                "naive": naive_result,
                "sor": sor_result,
                "slippage_saved_bps": slippage_saved_bps
            }
            
        except Exception as e:
            logger.error(f"SOR execution failed: {e}")
            raise
    
    def _get_cross_venue_mid(self, binance_book: OrderBook, coinbase_book: OrderBook) -> Optional[float]:
        """Get cross-venue mid price"""
        binance_mid = binance_book.mid_price if binance_book else None
        coinbase_mid = coinbase_book.mid_price if coinbase_book else None
        
        if binance_mid and coinbase_mid:
            return (binance_mid + coinbase_mid) / 2
        elif binance_mid:
            return binance_mid
        elif coinbase_mid:
            return coinbase_mid
        else:
            return None
    
    def _execute_naive(
        self,
        side: str,
        notional_usd: float,
        fee_bps: Dict[str, float],
        binance_book: OrderBook,
        coinbase_book: OrderBook
    ) -> dict:
        """Execute order using single venue (naive approach)"""
        # Choose best venue based on fees
        venue = "binance" if fee_bps.get("binance", 0) <= fee_bps.get("coinbase", 0) else "coinbase"
        order_book = binance_book if venue == "binance" else coinbase_book
        
        # Execute sweep on single venue
        fills = self._sweep_order_book(side, notional_usd, order_book, fee_bps.get(venue, 0))
        
        # Calculate VWAP and slippage
        vwap = self._calculate_vwap(fills)
        slippage_bps = self._calculate_slippage_bps(vwap, self._get_cross_venue_mid(binance_book, coinbase_book))
        
        return {
            "venue": venue,
            "vwap": vwap,
            "slippage_bps": slippage_bps,
            "fills": fills
        }
    
    def _execute_sor(
        self,
        side: str,
        notional_usd: float,
        fee_bps: Dict[str, float],
        binance_book: OrderBook,
        coinbase_book: OrderBook
    ) -> dict:
        """Execute order using Smart Order Router (multi-venue)"""
        # Merge order books and sort by effective price
        merged_levels = self._merge_order_books(
            side, binance_book, coinbase_book, fee_bps
        )
        
        # Execute sweep on merged order book
        fills = self._sweep_merged_levels(side, notional_usd, merged_levels)
        
        # Calculate VWAP and slippage
        vwap = self._calculate_vwap(fills)
        slippage_bps = self._calculate_slippage_bps(vwap, self._get_cross_venue_mid(binance_book, coinbase_book))
        
        return {
            "vwap": vwap,
            "slippage_bps": slippage_bps,
            "fills": fills
        }
    
    def _merge_order_books(
        self,
        side: str,
        binance_book: OrderBook,
        coinbase_book: OrderBook,
        fee_bps: Dict[str, float]
    ) -> List[dict]:
        """Merge order books and sort by effective price"""
        merged = []
        
        # Add Binance levels
        if binance_book:
            for level in binance_book.bids if side == "sell" else binance_book.asks:
                effective_price = self._apply_fee(level.price, side, fee_bps.get("binance", 0))
                merged.append({
                    "venue": "binance",
                    "price": level.price,
                    "size": level.size,
                    "effective_price": effective_price
                })
        
        # Add Coinbase levels
        if coinbase_book:
            for level in coinbase_book.bids if side == "sell" else coinbase_book.asks:
                effective_price = self._apply_fee(level.price, side, fee_bps.get("coinbase", 0))
                merged.append({
                    "venue": "coinbase",
                    "price": level.price,
                    "size": level.size,
                    "effective_price": effective_price
                })
        
        # Sort by effective price (best first)
        if side == "buy":
            merged.sort(key=lambda x: x["effective_price"])
        else:
            merged.sort(key=lambda x: x["effective_price"], reverse=True)
        
        return merged
    
    def _apply_fee(self, price: float, side: str, fee_bps: float) -> float:
        """Apply fee to price to get effective price"""
        fee_multiplier = 1 + (fee_bps / 10000)
        if side == "buy":
            return price * fee_multiplier  # Buy: pay more
        else:
            return price / fee_multiplier  # Sell: receive less
    
    def _sweep_order_book(
        self,
        side: str,
        notional_usd: float,
        order_book: OrderBook,
        fee_bps: float
    ) -> List[dict]:
        """Sweep order book to fill notional"""
        fills = []
        remaining_notional = notional_usd
        
        levels = order_book.bids if side == "sell" else order_book.asks
        
        for level in levels:
            if remaining_notional <= 0:
                break
            
            # Calculate how much we can fill at this level
            level_notional = level.price * level.size
            fill_notional = min(remaining_notional, level_notional)
            fill_size = fill_notional / level.price
            
            fills.append({
                "venue": order_book.venue,
                "px": level.price,
                "qty": fill_size
            })
            
            remaining_notional -= fill_notional
        
        return fills
    
    def _sweep_merged_levels(
        self,
        side: str,
        notional_usd: float,
        merged_levels: List[dict]
    ) -> List[dict]:
        """Sweep merged order book levels to fill notional"""
        fills = []
        remaining_notional = notional_usd
        
        for level in merged_levels:
            if remaining_notional <= 0:
                break
            
            # Calculate how much we can fill at this level
            level_notional = level["price"] * level["size"]
            fill_notional = min(remaining_notional, level_notional)
            fill_size = fill_notional / level["price"]
            
            fills.append({
                "venue": level["venue"],
                "px": level["price"],
                "qty": fill_size
            })
            
            remaining_notional -= fill_notional
        
        return fills
    
    def _calculate_vwap(self, fills: List[dict]) -> float:
        """Calculate Volume Weighted Average Price"""
        if not fills:
            return 0.0
        
        total_value = sum(fill["px"] * fill["qty"] for fill in fills)
        total_quantity = sum(fill["qty"] for fill in fills)
        
        return total_value / total_quantity if total_quantity > 0 else 0.0
    
    def _calculate_slippage_bps(self, execution_price: float, mid_price: float) -> float:
        """Calculate slippage in basis points"""
        if not mid_price or mid_price == 0:
            return 0.0
        
        slippage = abs(execution_price - mid_price) / mid_price
        return slippage * 10000  # Convert to basis points
