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

class BinanceAdapter:
    """Binance WebSocket adapter for order book data"""
    
    def __init__(self, on_book_update: Optional[Callable[[OrderBook], None]] = None):
        self.ws_url = Config.BINANCE_WS_URL
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.latest_book: Optional[OrderBook] = None
        self.on_book_update = on_book_update
        
        # Connection state
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def run(self):
        """Main run loop for the adapter"""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        
        try:
            await self._task
        except asyncio.CancelledError:
            logger.info("Binance adapter cancelled")
        except Exception as e:
            logger.error(f"Binance adapter failed: {e}")
        finally:
            self._running = False
    
    async def _run_loop(self):
        """Main connection loop with reconnection logic"""
        while self._running:
            try:
                if not self.is_connected:
                    await self._connect()
                
                if self.is_connected:
                    await self._listen()
                    
            except Exception as e:
                logger.error(f"Binance adapter error: {e}")
                self.is_connected = False
                
                if self._running:
                    await self._handle_reconnect()
                    
            await asyncio.sleep(1)  # Brief pause before reconnection
    
    async def _connect(self):
        """Establish WebSocket connection to Binance"""
        try:
            logger.info(f"Connecting to Binance WebSocket: {self.ws_url}")
            
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("Successfully connected to Binance WebSocket")
            
        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            self.is_connected = False
            raise
    
    async def _listen(self):
        """Listen for messages from Binance WebSocket"""
        try:
            logger.info("🎧 Binance: Starting to listen for messages...")
            message_count = 0
            
            async for message in self.websocket:
                message_count += 1
                logger.info(f"📨 Binance: Received message #{message_count}: {message[:200]}...")
                
                await self._handle_message(message)
                
        except ConnectionClosed:
            logger.warning("⚠️ Binance WebSocket connection closed")
            self.is_connected = False
        except WebSocketException as e:
            logger.error(f"❌ Binance WebSocket error: {e}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"❌ Unexpected error in Binance listener: {e}")
            self.is_connected = False
        finally:
            logger.info("Binance adapter cancelled")
    
    async def _handle_message(self, message: str):
        """Process incoming message from Binance"""
        try:
            data = json.loads(message)
            logger.debug(f"Received Binance message: {data}")
            
            # Handle different message types
            if "e" in data:  # Event type
                event_type = data["e"]
                logger.info(f"🔍 Binance event type: {event_type}")
                
                if event_type == "depthUpdate":
                    await self._handle_depth_update(data)
                elif event_type == "depthSnapshot":
                    await self._handle_depth_snapshot(data)
                else:
                    logger.debug(f"Unhandled Binance event: {event_type}")
            else:
                # This might be a depth snapshot (no event type)
                logger.info(f"📊 Binance message without event type - treating as depth snapshot: {list(data.keys())}")
                await self._handle_depth_snapshot(data)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Binance message: {e}")
        except Exception as e:
            logger.error(f"Error handling Binance message: {e}")
    
    async def _handle_depth_update(self, data: dict):
        """Handle order book depth update"""
        try:
            logger.info(f"🔄 Processing Binance depth update: {list(data.keys())}")
            
            # Create order book from update
            order_book = OrderBookNormalizer.normalize_binance(data, "binance")
            
            # Update latest book
            self.latest_book = order_book
            
            # Notify callback if set
            if self.on_book_update:
                self.on_book_update(order_book)
                
            logger.info(f"✅ Binance depth update processed: {order_book.symbol} bid={order_book.best_bid} ask={order_book.best_ask}")
            
        except Exception as e:
            logger.error(f"❌ Failed to handle Binance depth update: {e}")
            logger.error(f"   Data: {data}")
    
    async def _handle_depth_snapshot(self, data: dict):
        """Handle order book depth snapshot"""
        try:
            logger.info(f"🔄 Processing Binance depth snapshot: {list(data.keys())}")
            
            # Create order book from snapshot
            order_book = OrderBookNormalizer.normalize_binance(data, "binance")
            
            # Update latest book
            self.latest_book = order_book
            
            # Notify callback if set
            if self.on_book_update:
                self.on_book_update(order_book)
                
            logger.info(f"✅ Binance depth snapshot processed: {order_book.symbol} bid={order_book.best_bid} ask={order_book.best_ask}")
            
        except Exception as e:
            logger.error(f"❌ Failed to handle Binance depth snapshot: {e}")
            logger.error(f"   Data: {data}")
    
    async def _handle_reconnect(self):
        """Handle reconnection with exponential backoff"""
        if self.reconnect_attempts >= Config.WS_MAX_RECONNECT_ATTEMPTS:
            logger.error("Max reconnection attempts reached for Binance")
            return
        
        self.reconnect_attempts += 1
        delay = Config.WS_RECONNECT_DELAY * (2 ** (self.reconnect_attempts - 1))
        delay = min(delay, 60)  # Cap at 60 seconds
        
        logger.info(f"Reconnecting to Binance in {delay} seconds (attempt {self.reconnect_attempts})")
        await asyncio.sleep(delay)
    
    def get_latest_book(self) -> Optional[OrderBook]:
        """Get the latest order book"""
        return self.latest_book
    
    def is_stale(self) -> bool:
        """Check if the latest order book is stale"""
        if not self.latest_book:
            return True
        
        return OrderBookNormalizer.is_stale(
            self.latest_book, 
            Config.VENUE_STALE_THRESHOLD
        )
    
    async def stop(self):
        """Stop the adapter"""
        self._running = False
        
        if self._task:
            self._task.cancel()
        
        if self.websocket:
            await self.websocket.close()
        
        self.is_connected = False
        logger.info("Binance adapter stopped")

    async def connect(self):
        """Connect to Binance WebSocket"""
        try:
            logger.info(f"Connecting to Binance WebSocket: {self.ws_url}")
            
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("✅ Binance WebSocket connected")
            
            # Start listening
            await self._listen()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Binance: {e}")
            self.is_connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from Binance WebSocket"""
        self._running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("🔌 Binance WebSocket disconnected")
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
