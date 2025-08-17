import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Callable
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from config import Config
from .normalize import OrderBook, OrderBookNormalizer

logger = logging.getLogger(__name__)

class KrakenAdapter:
    """Kraken WebSocket adapter for order book data"""
    
    def __init__(self, on_book_update: Optional[Callable[[OrderBook], None]] = None):
        self.ws: Optional[websockets.WebSocketServerProtocol] = None
        self.latest_book: Optional[OrderBook] = None
        self.on_book_update = on_book_update
        self.running = False
        
        # Accumulate incremental updates
        self.current_bids = {}  # price -> size
        self.current_asks = {}  # price -> size
        self.last_sequence = None
        
    async def connect(self):
        """Connect to Kraken WebSocket"""
        try:
            self.ws = await websockets.connect("wss://ws.kraken.com")
            logger.info("✅ Kraken WebSocket connected")
            await self._subscribe()
            self.running = True
            await self._listen()
        except Exception as e:
            logger.error(f"❌ Failed to connect to Kraken: {e}")
            raise
    
    async def _subscribe(self):
        """Subscribe to order book feed"""
        try:
            # Subscribe to XBT/USD order book
            subscribe_message = {
                "event": "subscribe",
                "pair": ["XBT/USD"],
                "subscription": {
                    "name": "book",
                    "depth": 25
                }
            }
            
            await self.ws.send(json.dumps(subscribe_message))
            logger.info("📡 Kraken: Sent subscription request")
            
            # Wait for subscription confirmation
            response = await self.ws.recv()
            data = json.loads(response)
            
            if data.get("event") == "systemStatus":
                logger.info("📡 Kraken: Received system status, waiting for subscription confirmation...")
                # Wait for the actual subscription confirmation
                response = await self.ws.recv()
                data = json.loads(response)
            
            if data.get("event") == "subscriptionStatus" and data.get("status") == "subscribed":
                logger.info(f"✅ Kraken: Successfully subscribed to {data.get('pair')}")
            else:
                logger.warning(f"⚠️ Kraken: Unexpected subscription response: {data}")
                
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to Kraken: {e}")
            raise
    
    async def _listen(self):
        """Listen for messages from Kraken"""
        try:
            message_count = 0
            while self.running and self.ws:
                try:
                    message = await self.ws.recv()
                    message_count += 1
                    logger.info(f"📨 Kraken: Received message #{message_count}: {message[:100]}...")
                    
                    data = json.loads(message)
                    await self._handle_message(data)
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("⚠️ Kraken WebSocket connection closed")
                    break
                except Exception as e:
                    logger.error(f"❌ Error handling Kraken message: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Kraken listen error: {e}")
        finally:
            logger.info("Kraken adapter cancelled")
    
    async def _handle_message(self, data):
        """Handle incoming message from Kraken"""
        try:
            # Handle different message types
            if isinstance(data, list) and len(data) >= 4:
                # Order book update: [channelID, data, channel_name, pair]
                channel_name = data[2]
                if "book" in str(channel_name):
                    await self._handle_order_book_update(data)
                else:
                    logger.debug(f"Unhandled Kraken channel: {channel_name}")
            elif isinstance(data, dict):
                if data.get("event") == "heartbeat":
                    logger.debug("💓 Kraken heartbeat")
                elif data.get("event") == "systemStatus":
                    logger.debug("📊 Kraken system status")
                elif data.get("event") == "subscriptionStatus":
                    logger.debug("📡 Kraken subscription status")
                else:
                    logger.debug(f"Unhandled Kraken event: {data.get('event')}")
            else:
                logger.debug(f"Unhandled Kraken message format: {type(data)}")
                
        except Exception as e:
            logger.error(f"❌ Failed to handle Kraken message: {e}")
            logger.error(f"   Data: {data}")
    
    async def _handle_order_book_update(self, data: list):
        """Handle order book update from Kraken"""
        try:
            logger.info(f"🔄 Processing Kraken order book update: {len(data)} elements")
            
            # Kraken format: [channelID, data, channel_name, pair]
            if len(data) >= 4 and "book" in str(data[2]):
                book_data = data[1]
                logger.info(f"📊 Kraken book data keys: {list(book_data.keys()) if isinstance(book_data, dict) else 'not dict'}")
                
                # Accumulate incremental updates
                await self._accumulate_order_book_update(book_data)
                
                # Create complete order book from accumulated data
                if self.current_bids and self.current_asks:
                    order_book = self._create_complete_order_book()
                    self.latest_book = order_book
                    
                    # Notify callback if set
                    if self.on_book_update:
                        self.on_book_update(order_book)
                        
                    logger.info(f"✅ Kraken complete order book created: bid={order_book.best_bid} ask={order_book.best_ask}")
                else:
                    logger.debug("⏳ Kraken: Waiting for both bids and asks to accumulate...")
            else:
                logger.warning(f"⚠️ Kraken message doesn't match expected format: {data}")
                
        except Exception as e:
            logger.error(f"❌ Failed to handle Kraken order book update: {e}")
            logger.error(f"   Data: {data}")
    
    async def _accumulate_order_book_update(self, book_data: dict):
        """Accumulate incremental order book updates"""
        try:
            # Handle bids
            if "b" in book_data:
                for bid_update in book_data["b"]:
                    if isinstance(bid_update, list) and len(bid_update) >= 2:
                        price = float(bid_update[0])
                        size = float(bid_update[1])
                        
                        if size > 0:
                            self.current_bids[price] = size
                        else:
                            # Remove price level if size is 0
                            self.current_bids.pop(price, None)
            
            # Handle asks
            if "a" in book_data:
                for ask_update in book_data["a"]:
                    if isinstance(ask_update, list) and len(ask_update) >= 2:
                        price = float(ask_update[0])
                        size = float(ask_update[1])
                        
                        if size > 0:
                            self.current_asks[price] = size
                        else:
                            # Remove price level if size is 0
                            self.current_asks.pop(price, None)
            
            logger.debug(f"📊 Kraken: Accumulated - {len(self.current_bids)} bids, {len(self.current_asks)} asks")
            
        except Exception as e:
            logger.error(f"❌ Failed to accumulate Kraken order book update: {e}")
    
    def _create_complete_order_book(self) -> OrderBook:
        """Create a complete OrderBook from accumulated data"""
        try:
            # Convert accumulated data to OrderBookLevel format
            bids = []
            for price, size in sorted(self.current_bids.items(), reverse=True):  # Highest bid first
                if price > 0 and size > 0:
                    from .normalize import OrderBookLevel
                    bids.append(OrderBookLevel(price, size))
            
            asks = []
            for price, size in sorted(self.current_asks.items()):  # Lowest ask first
                if price > 0 and size > 0:
                    from .normalize import OrderBookLevel
                    asks.append(OrderBookLevel(price, size))
            
            # Create order book
            return OrderBook(
                venue="kraken",
                symbol="XBT-USD",
                timestamp=datetime.now(timezone.utc),
                server_timestamp=None,  # Kraken doesn't provide this
                bids=bids,
                asks=asks
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to create complete Kraken order book: {e}")
            raise
    
    async def _handle_reconnect(self):
        """Handle reconnection logic"""
        logger.info("🔄 Kraken: Attempting to reconnect...")
        try:
            await self.connect()
        except Exception as e:
            logger.error(f"❌ Kraken reconnection failed: {e}")
    
    def get_latest_book(self) -> Optional[OrderBook]:
        """Get the latest order book"""
        return self.latest_book
    
    async def disconnect(self):
        """Disconnect from Kraken WebSocket"""
        self.running = False
        if self.ws:
            await self.ws.close()
            logger.info("🔌 Kraken WebSocket disconnected")
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
