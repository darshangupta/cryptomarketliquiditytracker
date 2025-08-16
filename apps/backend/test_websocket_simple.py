#!/usr/bin/env python3
"""
Simple WebSocket test to debug exchange data flow
"""

import asyncio
import websockets
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_binance_websocket():
    """Test Binance WebSocket directly"""
    uri = "wss://stream.binance.com:9443/ws/btcusdt@depth20@100ms"
    
    logger.info(f"🔌 Testing Binance WebSocket: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Connected to Binance WebSocket")
            
            # Wait for messages
            message_count = 0
            for _ in range(10):  # Wait for up to 10 messages
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    message_count += 1
                    logger.info(f"📨 Binance message #{message_count}: {message[:200]}...")
                    
                    # Try to parse as JSON
                    try:
                        data = json.loads(message)
                        logger.info(f"   Parsed: {type(data)} - keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                    except:
                        logger.info("   Not valid JSON")
                        
                except asyncio.TimeoutError:
                    logger.warning("⏰ Timeout waiting for message")
                    break
                    
            logger.info(f"📊 Total messages received: {message_count}")
            
    except Exception as e:
        logger.error(f"❌ Binance WebSocket test failed: {e}")

async def test_kraken_websocket():
    """Test Kraken WebSocket directly"""
    uri = "wss://ws.kraken.com"
    
    logger.info(f"🔌 Testing Kraken WebSocket: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Connected to Kraken WebSocket")
            
            # Subscribe to order book
            subscribe_msg = {
                "event": "subscribe",
                "pair": ["XBT/USD"],
                "subscription": {
                    "name": "book",
                    "depth": 25
                }
            }
            
            await websocket.send(json.dumps(subscribe_msg))
            logger.info("📤 Sent subscription request")
            
            # Wait for subscription response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            logger.info(f"📨 Kraken response: {response}")
            
            # Wait for order book updates
            message_count = 0
            for _ in range(10):  # Wait for up to 10 messages
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    message_count += 1
                    logger.info(f"📨 Kraken message #{message_count}: {message[:200]}...")
                    
                    # Try to parse as JSON
                    try:
                        data = json.loads(message)
                        logger.info(f"   Parsed: {type(data)} - keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                    except:
                        logger.info("   Not valid JSON")
                        
                except asyncio.TimeoutError:
                    logger.warning("⏰ Timeout waiting for message")
                    break
                    
            logger.info(f"📊 Total messages received: {message_count}")
            
    except Exception as e:
        logger.error(f"❌ Kraken WebSocket test failed: {e}")

async def main():
    """Run both tests"""
    logger.info("🚀 Starting WebSocket tests...")
    
    logger.info("\n" + "="*50)
    logger.info("TESTING BINANCE")
    logger.info("="*50)
    await test_binance_websocket()
    
    logger.info("\n" + "="*50)
    logger.info("TESTING KRAKEN")
    logger.info("="*50)
    await test_kraken_websocket()
    
    logger.info("\n" + "="*50)
    logger.info("TESTS COMPLETE")
    logger.info("="*50)

if __name__ == "__main__":
    asyncio.run(main())
