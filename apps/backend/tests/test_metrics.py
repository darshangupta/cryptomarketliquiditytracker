import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from metrics.compute import MetricsComputer
from ingest.normalize import OrderBook, OrderBookLevel

class TestMetricsComputer:
    """Test metrics computation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.computer = MetricsComputer()
        
        # Create mock order books (using regular Mock, not spec)
        self.binance_book = Mock()
        self.coinbase_book = Mock()
        
        # Set up mock properties
        self.binance_book.best_bid = 50000.0
        self.binance_book.best_ask = 50010.0
        self.binance_book.mid_price = 50005.0
        self.binance_book.spread_bps = 2.0
        self.binance_book.timestamp = datetime.now(timezone.utc)
        self.binance_book.server_timestamp = datetime.now(timezone.utc)
        
        self.coinbase_book.best_bid = 50001.0
        self.coinbase_book.best_ask = 50009.0
        self.coinbase_book.mid_price = 50005.0
        self.coinbase_book.spread_bps = 1.6
        self.coinbase_book.timestamp = datetime.now(timezone.utc)
        self.coinbase_book.server_timestamp = None
        
        # Mock depth calculation methods
        self.binance_book.get_depth_within_bps = Mock(return_value=(100.0, 100.0))
        self.coinbase_book.get_depth_within_bps = Mock(return_value=(80.0, 80.0))
        
        # Mock is_stale method
        self.binance_book.is_stale = Mock(return_value=False)
        self.coinbase_book.is_stale = Mock(return_value=False)
    
    def test_compute_mid_price(self):
        """Test mid price computation"""
        mid_price = self.computer._compute_mid_price(self.binance_book, self.coinbase_book)
        assert mid_price == 50005.0
    
    def test_compute_mid_price_single_venue(self):
        """Test mid price with only one venue"""
        mid_price = self.computer._compute_mid_price(self.binance_book, None)
        assert mid_price == 50005.0
        
        mid_price = self.computer._compute_mid_price(None, self.coinbase_book)
        assert mid_price == 50005.0
    
    def test_compute_spread_bps(self):
        """Test spread computation in basis points"""
        spread_bps = self.computer._compute_spread_bps(self.binance_book, self.coinbase_book)
        # Best bid: 50001.0, Best ask: 50009.0, Mid: 50005.0
        # Spread: (50009.0 - 50001.0) / 50005.0 * 10000 = 1.6 bps
        assert abs(spread_bps - 1.6) < 0.1
    
    def test_compute_depth_050(self):
        """Test depth computation within ±0.5%"""
        depth = self.computer._compute_depth_050(self.binance_book, self.coinbase_book)
        # Binance: 100 + 100 = 200, Coinbase: 80 + 80 = 160, Total: 360
        assert depth == 360.0
    
    def test_compute_hhi(self):
        """Test Herfindahl-Hirschman Index computation"""
        venue_metrics = [
            {"venue": "binance", "share": 200.0},
            {"venue": "coinbase", "share": 160.0}
        ]
        
        hhi = self.computer._compute_hhi(venue_metrics)
        # Normalized shares: binance = 200/360 = 0.556, coinbase = 160/360 = 0.444
        # HHI = 0.556² + 0.444² = 0.309 + 0.197 = 0.506
        expected_hhi = (200/360)**2 + (160/360)**2
        assert abs(hhi - expected_hhi) < 0.001
    
    def test_compute_imbalance(self):
        """Test order book imbalance computation"""
        imbalance = self.computer._compute_imbalance(self.binance_book, self.coinbase_book)
        # Total bid depth: 100 + 80 = 180, Total ask depth: 100 + 80 = 180
        # Imbalance: (180 - 180) / 360 = 0
        assert imbalance == 0.0
    
    def test_compute_venue_metrics(self):
        """Test venue-specific metrics computation"""
        venue_metrics = self.computer._compute_venue_metrics(self.binance_book, self.coinbase_book)
        
        assert len(venue_metrics) == 2
        
        # Check Binance metrics
        binance_metrics = next(v for v in venue_metrics if v["venue"] == "binance")
        assert binance_metrics["venue"] == "binance"
        assert binance_metrics["spread_bps"] == 2.0
        assert binance_metrics["share"] == 200.0
        assert binance_metrics["stale"] == False
        
        # Check Coinbase metrics
        coinbase_metrics = next(v for v in venue_metrics if v["venue"] == "coinbase")
        assert coinbase_metrics["venue"] == "coinbase"
        assert coinbase_metrics["spread_bps"] == 1.6
        assert coinbase_metrics["share"] == 160.0
        assert coinbase_metrics["stale"] == False
    
    def test_compute_metrics_full(self):
        """Test full metrics computation"""
        metrics = self.computer.compute_metrics(self.binance_book, self.coinbase_book)
        
        assert "ts" in metrics
        assert metrics["symbol"] == "BTC-USD"
        assert metrics["window_bps"] == 50
        assert metrics["mid"] == 50005.0
        assert abs(metrics["spread_bps"] - 1.6) < 0.1
        assert metrics["depth_050"] == 360.0
        assert metrics["hhi"] is not None
        assert metrics["imbalance"] == 0.0
        assert len(metrics["venues"]) == 2
    
    def test_empty_metrics_on_error(self):
        """Test that empty metrics are returned on error"""
        # Create invalid order books that will cause errors
        invalid_book = Mock()
        invalid_book.mid_price = None
        invalid_book.best_bid = None
        invalid_book.best_ask = None
        invalid_book.get_depth_within_bps = Mock(side_effect=Exception("Test error"))
        invalid_book.is_stale = Mock(return_value=True)
        
        metrics = self.computer.compute_metrics(invalid_book, invalid_book)
        
        assert metrics["mid"] is None
        assert metrics["spread_bps"] is None
        assert metrics["depth_050"] is None
        # Venues will still be created but with error states
        assert len(metrics["venues"]) == 2
        for venue in metrics["venues"]:
            assert venue["stale"] == True

if __name__ == "__main__":
    pytest.main([__file__])
