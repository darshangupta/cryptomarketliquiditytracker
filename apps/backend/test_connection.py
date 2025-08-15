#!/usr/bin/env python3
"""
Simple test script to verify exchange adapters can connect and receive data.
Run this to test the backend before starting the full FastAPI server.
"""

import asyncio
import logging
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingest.binance import BinanceAdapter
from ingest.coinbase import CoinbaseAdapter
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_binance_connection():
    """Test Binance WebSocket connection"""
    logger.info("Testing Binance connection...")
    
    adapter = BinanceAdapter()
    
    try:
        # Start the adapter
        task = asyncio.create_task(adapter.run())
        
        # Wait for some data
        await asyncio.sleep(10)
        
        # Check if we received data
        latest_book = adapter.get_latest_book()
        if latest_book:
            logger.info(f"✅ Binance connection successful!")
            logger.info(f"   Symbol: {latest_book.symbol}")
            logger.info(f"   Best bid: {latest_book.best_bid}")
            logger.info(f"   Best ask: {latest_book.best_ask}")
            logger.info(f"   Mid price: {latest_book.mid_price}")
            logger.info(f"   Spread: {latest_book.spread_bps} bps")
        else:
            logger.warning("⚠️  Binance connected but no data received")
        
        # Stop the adapter
        await adapter.stop()
        task.cancel()
        
    except Exception as e:
        logger.error(f"❌ Binance connection failed: {e}")
        return False
    
    return True

async def test_coinbase_connection():
    """Test Coinbase WebSocket connection"""
    logger.info("Testing Coinbase connection...")
    
    adapter = CoinbaseAdapter()
    
    try:
        # Start the adapter
        task = asyncio.create_task(adapter.run())
        
        # Wait for some data
        await asyncio.sleep(10)
        
        # Check if we received data
        latest_book = adapter.get_latest_book()
        if latest_book:
            logger.info(f"✅ Coinbase connection successful!")
            logger.info(f"   Symbol: {latest_book.symbol}")
            logger.info(f"   Best bid: {latest_book.best_bid}")
            logger.info(f"   Best ask: {latest_book.best_ask}")
            logger.info(f"   Mid price: {latest_book.mid_price}")
            logger.info(f"   Spread: {latest_book.spread_bps} bps")
        else:
            logger.warning("⚠️  Coinbase connected but no data received")
        
        # Stop the adapter
        await adapter.stop()
        task.cancel()
        
    except Exception as e:
        logger.error(f"❌ Coinbase connection failed: {e}")
        return False
    
    return True

async def main():
    """Main test function"""
    logger.info("🚀 Starting exchange connection tests...")
    logger.info(f"   TICK_HZ: {Config.TICK_HZ}")
    logger.info(f"   DEPTH_WINDOW_BPS: {Config.DEPTH_WINDOW_BPS}")
    logger.info(f"   BINANCE_WS_URL: {Config.BINANCE_WS_URL}")
    logger.info(f"   COINBASE_WS_URL: {Config.COINBASE_WS_URL}")
    logger.info("")
    
    # Test Binance
    binance_success = await test_binance_connection()
    
    logger.info("")
    
    # Test Coinbase
    coinbase_success = await test_coinbase_connection()
    
    logger.info("")
    
    # Summary
    if binance_success and coinbase_success:
        logger.info("🎉 All exchange connections successful! Backend is ready to run.")
        return True
    else:
        logger.error("💥 Some exchange connections failed. Check the logs above.")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Test failed with unexpected error: {e}")
        sys.exit(1)
