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
    
    def __init__(self):
        self.ws_url = Config.KRAKEN_WS_URL
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.latest_book: Optional[OrderBook] = None
        self.on_book_update: Optional[Callable[[OrderBook], None]] = None
        
        # Connection state
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Kraken specific
        self.subscribed = False
        self.heartbeat_task: Optional[asyncio.Task] = None
    
    async def run(self):
        """Main run loop for the adapter"""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        
        try:
            await self._task
        except asyncio.CancelledError:
            logger.info("Kraken adapter cancelled")
        except Exception as e:
            logger.error(f"Kraken adapter failed: {e}")
        finally:
            self._running = False
    
    async def _run_loop(self):
        """Main connection loop with reconnection logic"""
        while self._running:
            try:
                if not self.is_connected:
                    await self._connect()
                
                if self.is_connected and not self.subscribed:
                    await self._subscribe()
                
                if self.is_connected and self.subscribed:
                    await self._listen()
                    
            except Exception as e:
                logger.error(f"Kraken adapter error: {e}")
                self.is_connected = False
                self.subscribed = False
                
                if self._running:
                    await self._handle_reconnect()
                    
            await asyncio.sleep(1)  # Brief pause before reconnection
    
    async def _connect(self):
        """Establish WebSocket connection to Kraken"""
        try:
            logger.info(f"Connecting to Kraken WebSocket: {self.ws_url}")
            
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("Successfully connected to Kraken WebSocket")
            
        except Exception as e:
            logger.error(f"Failed to connect to Kraken: {e}")
            self.is_connected = False
            raise
    
    async def _subscribe(self):
        """Subscribe to order book updates for XBT/USD"""
        try:
            subscribe_message = {
                "event": "subscribe",
                "pair": ["XBT/USD"],
                "subscription": {
                    "name": "book",
                    "depth": 25
                }
            }
            
            await self.websocket.send(json.dumps(subscribe_message))
            logger.info("Sent subscription request to Kraken")
            
            # Wait for subscription confirmation
            response = await self.websocket.recv()
            data = json.loads(response)
            
            # Handle system status message first
            if data.get("event") == "systemStatus":
                logger.info(f"Kraken system status: {data}")
                # Wait for actual subscription response
                response = await self.websocket.recv()
                data = json.loads(response)
            
            if data.get("event") == "subscriptionStatus" and data.get("status") == "subscribed":
                self.subscribed = True
                logger.info("Successfully subscribed to Kraken order book")
                logger.info("🚀 Kraken: Subscription confirmed, starting to listen for order book updates...")
                
                # Start heartbeat
                self.heartbeat_task = asyncio.create_task(self._run_heartbeat())
            else:
                logger.warning(f"Unexpected response to subscription: {data}")
                
        except Exception as e:
            logger.error(f"Failed to subscribe to Kraken: {e}")
            self.subscribed = False
            raise
    
    async def _run_heartbeat(self):
        """Send heartbeat to keep connection alive"""
        while self._running and self.is_connected:
            try:
                await asyncio.sleep(30)  # Kraken expects heartbeat every 30s
                if self.websocket:
                    await self.websocket.send(json.dumps({"event": "ping"}))
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
                break
    
    async def _listen(self):
        """Listen for messages from Kraken WebSocket"""
        try:
            logger.info("🎧 Kraken: Starting to listen for messages...")
            message_count = 0
            
            async for message in self.websocket:
                if not self._running:
                    break
                
                message_count += 1
                logger.info(f"📨 Kraken: Received message #{message_count}: {message[:200]}...")
                
                await self._handle_message(message)
                
        except ConnectionClosed:
            logger.warning("Kraken WebSocket connection closed")
            self.is_connected = False
            self.subscribed = False
        except WebSocketException as e:
            logger.error(f"Kraken WebSocket error: {e}")
            self.is_connected = False
            self.subscribed = False
        except Exception as e:
            logger.error(f"Unexpected error in Kraken listener: {e}")
            self.is_connected = False
            self.subscribed = False
    
    async def _handle_message(self, message: str):
        """Process incoming message from Kraken"""
        try:
            data = json.loads(message)
            logger.debug(f"Received Kraken message: {data}")
            
            # Handle different message types
            if isinstance(data, list) and len(data) > 2:
                # Order book update
                await self._handle_order_book_update(data)
            elif isinstance(data, dict):
                if data.get("event") == "pong":
                    logger.debug("Kraken pong received")
                elif data.get("event") == "heartbeat":
                    logger.debug("Kraken heartbeat received")
                elif data.get("event") == "systemStatus":
                    logger.info(f"Kraken system status: {data}")
                else:
                    logger.debug(f"Unhandled Kraken message: {data}")
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Kraken message: {e}")
        except Exception as e:
            logger.error(f"Error handling Kraken message: {e}")
    
    async def _handle_order_book_update(self, data: list):
        """Handle order book update from Kraken"""
        try:
            # Kraken format: [channelID, data, channel_name, pair]
            if len(data) >= 4 and data[2] == "book":
                book_data = data[1]
                
                # Create order book from update
                order_book = OrderBookNormalizer.normalize_kraken(book_data, "kraken")
                
                # Update latest book
                self.latest_book = order_book
                
                # Notify callback if set
                if self.on_book_update:
                    self.on_book_update(order_book)
                    
                logger.debug(f"Kraken order book update: bid={order_book.best_bid} ask={order_book.best_ask}")
            
        except Exception as e:
            logger.error(f"Failed to handle Kraken order book update: {e}")
    
    async def _handle_reconnect(self):
        """Handle reconnection with exponential backoff"""
        if self.reconnect_attempts >= Config.WS_MAX_RECONNECT_ATTEMPTS:
            logger.error("Max reconnection attempts reached for Kraken")
            return
        
        self.reconnect_attempts += 1
        delay = Config.WS_RECONNECT_DELAY * (2 ** (self.reconnect_attempts - 1))
        delay = min(delay, 60)  # Cap at 60 seconds
        
        logger.info(f"Reconnecting to Kraken in {delay} seconds (attempt {self.reconnect_attempts})")
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
        
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        
        if self.websocket:
            await self.websocket.close()
        
        self.is_connected = False
        self.subscribed = False
        logger.info("Kraken adapter stopped")
