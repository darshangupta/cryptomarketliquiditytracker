import os
from typing import List

class Config:
    """Application configuration"""
    
    # Exchange settings
    EXCHANGES = os.getenv("EXCHANGES", "binance,kraken").split(",")
    SYMBOLS = os.getenv("SYMBOLS", "BTC-USD").split(",")
    
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
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if cls.TICK_HZ not in [2, 4]:
            raise ValueError("TICK_HZ must be 2 or 4")
        
        if cls.DEPTH_WINDOW_BPS != 50:
            raise ValueError("DEPTH_WINDOW_BPS must be 50 for initial implementation")
        
        return True
