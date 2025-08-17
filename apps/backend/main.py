import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import websockets

from config import Config
from ingest.binance import BinanceAdapter
from ingest.kraken import KrakenAdapter
from ingest.normalize import OrderBook
from metrics.compute import MetricsComputer
from metrics.sor import SmartOrderRouter
from state.buffers import OrderBookBuffer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Crypto Market Liquidity Tracker", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
class AppState:
    def __init__(self):
        self.websocket_connections: Set[WebSocket] = set()
        self.order_book_buffer = OrderBookBuffer(max_size=1000)
        self.metrics_computer = MetricsComputer()
        self.sor_router = SmartOrderRouter()
        self.status = "warming"
        self.last_heartbeat = datetime.now(timezone.utc)
        self.venue_status = {"binance": False, "kraken": False}
        
        # Exchange adapters
        self.binance_adapter = BinanceAdapter()
        self.kraken_adapter = KrakenAdapter()
        
        # Background tasks
        self.ingestion_task: Optional[asyncio.Task] = None
        self.metrics_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
    
    def on_binance_update(self, order_book: OrderBook):
        """Callback when Binance order book updates"""
        logger.debug(f"📊 Binance order book update: bid={order_book.best_bid} ask={order_book.best_ask}")
        # Store in buffer for metrics computation
        self.order_book_buffer.add_order_book(order_book)
    
    def on_kraken_update(self, order_book: OrderBook):
        """Callback when Kraken order book updates"""
        logger.debug(f"📊 Kraken order book update: bid={order_book.best_bid} ask={order_book.best_ask}")
        # Store in buffer for metrics computation
        self.order_book_buffer.add_order_book(order_book)

app_state = AppState()

@app.on_event("startup")
async def startup_event():
    """Initialize application state and start background tasks"""
    logger.info("🚀 Starting up...")
    
    # Initialize exchange adapters
    app_state.binance_adapter = BinanceAdapter(on_book_update=app_state.on_binance_update)
    app_state.kraken_adapter = KrakenAdapter(on_book_update=app_state.on_kraken_update)
    
    # Start background tasks
    app_state.ingestion_task = asyncio.create_task(run_exchange_ingestion())
    app_state.metrics_task = asyncio.create_task(run_metrics_computation())
    app_state.heartbeat_task = asyncio.create_task(run_heartbeat())
    
    logger.info("✅ Startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up background tasks"""
    logger.info("Shutting down...")
    
    if app_state.ingestion_task:
        app_state.ingestion_task.cancel()
    if app_state.metrics_task:
        app_state.metrics_task.cancel()
    if app_state.heartbeat_task:
        app_state.heartbeat_task.cancel()
    
    # Close all WebSocket connections
    for websocket in app_state.websocket_connections.copy():
        try:
            await websocket.close()
        except:
            pass

async def run_exchange_ingestion():
    """Run exchange data ingestion in background"""
    try:
        logger.info("🔄 Starting exchange ingestion...")
        
        # Start both adapters completely independently
        binance_task = asyncio.create_task(run_binance_adapter())
        kraken_task = asyncio.create_task(run_kraken_adapter())
        
        # Don't wait for both - let them run independently
        # This way if one fails, the other keeps running
        
    except Exception as e:
        logger.error(f"❌ Exchange ingestion failed: {e}")

async def run_binance_adapter():
    """Run Binance adapter with error handling"""
    try:
        logger.info("🟡 Starting Binance adapter...")
        await app_state.binance_adapter.connect()
    except Exception as e:
        logger.error(f"❌ Binance adapter failed: {e}")
        # Don't re-raise - let other adapters continue

async def run_kraken_adapter():
    """Run Kraken adapter with error handling"""
    try:
        logger.info("🟠 Starting Kraken adapter...")
        await app_state.kraken_adapter.connect()
    except Exception as e:
        logger.error(f"❌ Kraken adapter failed: {e}")
        # Don't re-raise - let other adapters continue

async def run_metrics_computation():
    """Run metrics computation at fixed intervals"""
    while True:
        try:
            await asyncio.sleep(1.0 / Config.TICK_HZ)  # Compute at TICK_HZ
            
            # Get latest order books
            binance_book = app_state.binance_adapter.get_latest_book()
            kraken_book = app_state.kraken_adapter.get_latest_book()
            
            if binance_book and kraken_book:
                # Update venue status
                app_state.venue_status["binance"] = True
                app_state.venue_status["kraken"] = True
                
                # Check if we should transition to "live" status
                if app_state.status == "warming":
                    binance_age = (datetime.now(timezone.utc) - binance_book.timestamp).total_seconds()
                    kraken_age = (datetime.now(timezone.utc) - kraken_book.timestamp).total_seconds()
                    
                    logger.info(f"🔍 Age check - Binance: {binance_age:.2f}s, Kraken: {kraken_age:.2f}s")
                    logger.info(f"🔍 Binance timestamp: {binance_book.timestamp}")
                    logger.info(f"🔍 Kraken timestamp: {kraken_book.timestamp}")
                    
                    # Allow transition to live if both venues have reasonably fresh data (<5 seconds)
                    if binance_age < 5.0 and kraken_age < 5.0:
                        app_state.status = "live"
                        logger.info(f"Status changed to LIVE - Binance age: {binance_age:.2f}s, Kraken age: {kraken_age:.2f}s")
                    else:
                        logger.info(f"⏳ Still warming - Binance age: {binance_age:.2f}s, Kraken age: {kraken_age:.2f}s")
                
                # Compute metrics
                metrics = app_state.metrics_computer.compute_metrics(
                    binance_book, kraken_book
                )
                
                # Add status to metrics
                metrics["status"] = app_state.status
                
                # Broadcast to all WebSocket clients
                await broadcast_metrics(metrics)
                
        except Exception as e:
            logger.error(f"Metrics computation failed: {e}")
            await asyncio.sleep(1)

async def run_heartbeat():
    """Send heartbeat every 5 seconds"""
    while True:
        try:
            await asyncio.sleep(5)
            app_state.last_heartbeat = datetime.now(timezone.utc)
            
            # Send heartbeat frame
            heartbeat_frame = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "type": "heartbeat",
                "status": app_state.status
            }
            
            await broadcast_frame(heartbeat_frame)
            
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")

async def broadcast_metrics(metrics: dict):
    """Broadcast metrics to all connected WebSocket clients"""
    await broadcast_frame(metrics)

async def broadcast_frame(frame: dict):
    """Broadcast any frame to all connected WebSocket clients"""
    if not app_state.websocket_connections:
        return
    
    # Convert to JSON string
    frame_json = json.dumps(frame)
    
    # Send to all connected clients
    disconnected = set()
    for websocket in app_state.websocket_connections:
        try:
            await websocket.send_text(frame_json)
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket: {e}")
            disconnected.add(websocket)
    
    # Remove disconnected clients
    app_state.websocket_connections -= disconnected

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time market data streaming"""
    await websocket.accept()
    app_state.websocket_connections.add(websocket)
    
    logger.info(f"WebSocket client connected. Total clients: {len(app_state.websocket_connections)}")
    
    try:
        # Send initial status
        await websocket.send_text(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "connection_status",
            "status": app_state.status,
            "venue_status": app_state.venue_status
        }))
        
        # Send current market data immediately
        binance_book = app_state.order_book_buffer.get_latest_binance_book()
        kraken_book = app_state.order_book_buffer.get_latest_kraken_book()
        
        if binance_book and kraken_book:
            # Create market metrics for frontend
            market_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "binance": {
                    "bid": float(binance_book.best_bid),
                    "ask": float(binance_book.best_ask),
                    "spread": float(binance_book.best_ask - binance_book.best_bid)
                },
                "kraken": {
                    "bid": float(kraken_book.best_bid),
                    "ask": float(kraken_book.best_ask),
                    "spread": float(kraken_book.best_ask - kraken_book.best_bid)
                },
                "metrics": {
                    "mid": float((binance_book.best_bid + binance_book.best_ask + kraken_book.best_bid + kraken_book.best_ask) / 4),
                    "spread_bps": 0.85,  # Placeholder - will be computed by metrics
                    "depth": 1300000,     # Placeholder - will be computed by metrics
                    "hhi": 0.52,         # Placeholder - will be computed by metrics
                    "imbalance": 0.12    # Placeholder - will be computed by metrics
                }
            }
            
            await websocket.send_text(json.dumps({
                "type": "market_metrics",
                "data": market_data
            }))
        
        # Keep connection alive and send periodic updates
        while True:
            try:
                # Check if connection is still open
                if websocket.client_state.value == 2:  # DISCONNECTED
                    logger.info("WebSocket client disconnected, stopping data loop")
                    break
                
                # Send market data every 30 seconds (instead of 1 second)
                await asyncio.sleep(30)
                
                # Get latest data
                binance_book = app_state.order_book_buffer.get_latest_binance_book()
                kraken_book = app_state.order_book_buffer.get_latest_kraken_book()
                
                if binance_book and kraken_book:
                    # Create updated market data
                    market_data = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "binance": {
                            "bid": float(binance_book.best_bid),
                            "ask": float(binance_book.best_ask),
                            "spread": float(binance_book.best_ask - binance_book.best_bid)
                        },
                        "kraken": {
                            "bid": float(kraken_book.best_bid),
                            "ask": float(kraken_book.best_ask),
                            "spread": float(kraken_book.best_ask - kraken_book.best_bid)
                        },
                        "metrics": {
                            "mid": float((binance_book.best_bid + binance_book.best_ask + kraken_book.best_bid + kraken_book.best_ask) / 4),
                            "spread_bps": 0.85,  # Placeholder - will be computed by metrics
                            "depth": 1300000,     # Placeholder - will be computed by metrics
                            "hhi": 0.52,         # Placeholder - will be computed by metrics
                            "imbalance": 0.12    # Placeholder - will be computed by metrics
                        }
                    }
                    
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "market_metrics",
                            "data": market_data
                        }))
                        logger.info(f"✅ WebSocket: Sent market data to client. Binance: ${market_data['binance']['bid']}, Kraken: ${market_data['kraken']['bid']}")
                    except Exception as send_error:
                        logger.warning(f"Failed to send market data: {send_error}")
                        break  # Exit loop if we can't send
                        
            except Exception as e:
                logger.error(f"Error in WebSocket data loop: {e}")
                # Don't break the loop, just log and continue
                continue
        
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        app_state.websocket_connections.discard(websocket)
        logger.info(f"WebSocket client removed. Total clients: {len(app_state.websocket_connections)}")

@app.post("/api/execute")
async def execute_order(request: dict):
    """Execute a trade using Smart Order Router vs naive baseline"""
    try:
        # Check if system is ready
        if app_state.status != "live":
            raise HTTPException(
                status_code=503, 
                detail={"reason": "warming", "status": app_state.status}
            )
        
        # Extract request parameters
        symbol = request.get("symbol", "BTC-USD")
        side = request.get("side")  # "buy" or "sell"
        notional_usd = request.get("notional_usd")
        fee_bps = request.get("fee_bps", {})
        
        if not all([symbol, side, notional_usd]):
            raise HTTPException(status_code=400, detail="Missing required parameters")
        
        # Get latest order books
        binance_book = app_state.binance_adapter.get_latest_book()
        kraken_book = app_state.kraken_adapter.get_latest_book()
        
        if not (binance_book and kraken_book):
            raise HTTPException(status_code=503, detail="Order books not available")
        
        # Execute SOR
        result = app_state.sor_router.execute_order(
            side=side,
            notional_usd=notional_usd,
            fee_bps=fee_bps,
            binance_book=binance_book,
            coinbase_book=kraken_book
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Order execution failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "websocket_clients": len(app_state.websocket_connections),
        "system_status": app_state.status,
        "venue_status": app_state.venue_status
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
