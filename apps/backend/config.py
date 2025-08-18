import os
from typing import List, Dict

class Config:
    """Application configuration"""
    
    # Exchange settings
    EXCHANGES = os.getenv("EXCHANGES", "binance,kraken").split(",")
    
    # Multi-asset configuration - optimized for arbitrage opportunities
    SYMBOLS = os.getenv("SYMBOLS", "BTC-USD,ETH-USD,UNI-USD,AAVE-USD,MATIC-USD,ARB-USD,OP-USD,AXS-USD,SAND-USD,MANA-USD").split(",")
    
    # Asset-specific liquidity thresholds (in basis points)
    ASSET_LIQUIDITY_THRESHOLDS = {
        "BTC-USD": {"min_spread_bps": 5, "max_impact_bps": 10, "min_depth_usd": 1000000},
        "ETH-USD": {"min_spread_bps": 8, "max_impact_bps": 15, "min_depth_usd": 500000},
        "UNI-USD": {"min_spread_bps": 15, "max_impact_bps": 25, "min_depth_usd": 100000},
        "AAVE-USD": {"min_spread_bps": 20, "max_impact_bps": 35, "min_depth_usd": 75000},
        "MATIC-USD": {"min_spread_bps": 18, "max_impact_bps": 30, "min_depth_usd": 100000},
        "ARB-USD": {"min_spread_bps": 25, "max_impact_bps": 40, "min_depth_usd": 50000},
        "OP-USD": {"min_spread_bps": 22, "max_impact_bps": 38, "min_depth_usd": 60000},
        "AXS-USD": {"min_spread_bps": 30, "max_impact_bps": 50, "min_depth_usd": 25000},
        "SAND-USD": {"min_spread_bps": 35, "max_impact_bps": 60, "min_depth_usd": 20000},
        "MANA-USD": {"min_spread_bps": 28, "max_impact_bps": 45, "min_depth_usd": 30000}
    }
    
    # Multi-asset WebSocket configuration
    MULTI_ASSET_WS_CONFIG = {
        "binance": {
            "base_url": "wss://stream.binance.com:9443/ws",
            "symbols": ["btcusdt", "ethusdt", "uniusdt", "aaveusdt", "maticusdt", "arbusdt", "opusdt", "axsusdt", "sandusdt", "manausdt"],
            "streams": ["@depth20@100ms", "@ticker", "@kline_1m"]
        },
        "kraken": {
            "base_url": "wss://ws.kraken.com",
            "symbols": ["XBT/USD", "ETH/USD", "UNI/USD", "AAVE/USD", "MATIC/USD", "ARB/USD", "OP/USD", "AXS/USD", "SAND/USD", "MANA/USD"],
            "streams": ["book", "ticker", "ohlc-1"]
        }
    }
    
    # Performance settings
    TICK_HZ = int(os.getenv("TICK_HZ", "2"))  # 2 Hz default
    TOP_LEVELS = int(os.getenv("TOP_LEVELS", "50"))  # Number of order book levels to track
    
    # WebSocket settings
    WS_HEARTBEAT_INTERVAL = 5  # seconds
    WS_RECONNECT_DELAY = 1  # seconds
    WS_MAX_RECONNECT_ATTEMPTS = 10
    
    # Venue settings
    VENUE_STALE_THRESHOLD = 3.0  # seconds
    
    # Depth window settings (from rules)
    DEPTH_WINDOW_BPS = 50  # ±0.5% = 50 basis points
    
    # Exchange WebSocket URLs (public feeds, no auth required)
    BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@depth20@100ms"
    KRAKEN_WS_URL = "wss://ws.kraken.com"
    
    # API settings
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # CORS settings
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # V1.5 settings (optional)
    DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/market_data.duckdb")
    PARQUET_DIR = os.getenv("PARQUET_DIR", "data/parquet")
    
    # Portfolio simulation settings
    INITIAL_PORTFOLIO_USD = float(os.getenv("INITIAL_PORTFOLIO_USD", "10000"))
    MAX_POSITION_SIZE_PCT = float(os.getenv("MAX_POSITION_SIZE_PCT", "20"))  # Max 20% in any single asset
    MIN_PROFIT_THRESHOLD_BPS = float(os.getenv("MIN_PROFIT_THRESHOLD_BPS", "25"))  # Min 25 bps profit to execute
    
    # Analytics settings
    ANALYTICS_WINDOW_DAYS = int(os.getenv("ANALYTICS_WINDOW_DAYS", "30"))  # Days of data to analyze
    PERFORMANCE_METRICS_INTERVAL = int(os.getenv("PERFORMANCE_METRICS_INTERVAL", "300"))  # 5 minutes
    RISK_METRICS_UPDATE_FREQ = int(os.getenv("RISK_METRICS_UPDATE_FREQ", "60"))  # 1 minute
    
    # Risk management settings
    MAX_DRAWDOWN_THRESHOLD = float(os.getenv("MAX_DRAWDOWN_THRESHOLD", "0.15"))  # 15% max drawdown
    TARGET_SHARPE_RATIO = float(os.getenv("TARGET_SHARPE_RATIO", "1.5"))  # Target Sharpe ratio
    VOLATILITY_TARGET = float(os.getenv("VOLATILITY_TARGET", "0.20"))  # 20% annualized volatility
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if cls.TICK_HZ not in [2, 4]:
            raise ValueError("TICK_HZ must be 2 or 4")
        
        if cls.DEPTH_WINDOW_BPS != 50:
            raise ValueError("DEPTH_WINDOW_BPS must be 50 for initial implementation")
        
        return True
