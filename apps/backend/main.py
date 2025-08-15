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
from ingest.coinbase import CoinbaseAdapter
from ingest.normalize import OrderBook, NormalizedBook
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
        self.venue_status = {"binance": False, "coinbase": False}
        
        # Exchange adapters
        self.binance_adapter = BinanceAdapter()
        self.coinbase_adapter = CoinbaseAdapter()
        
        # Background tasks
        self.ingestion_task: Optional[asyncio.Task] = None
        self.metrics_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None

app_state = AppState()

@app.on_event("startup")
async def startup_event():
    """Start background tasks for data ingestion and metrics computation"""
    logger.info("Starting crypto market liquidity tracker...")
    
    # Start exchange data ingestion
    app_state.ingestion_task = asyncio.create_task(run_exchange_ingestion())
    
    # Start metrics computation
    app_state.metrics_task = asyncio.create_task(run_metrics_computation())
    
    # Start heartbeat
    app_state.heartbeat_task = asyncio.create_task(run_heartbeat())
    
    logger.info("Background tasks started")

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
        # Start both exchange adapters concurrently
        await asyncio.gather(
            app_state.binance_adapter.run(),
            app_state.coinbase_adapter.run()
        )
    except Exception as e:
        logger.error(f"Exchange ingestion failed: {e}")

async def run_metrics_computation():
    """Run metrics computation at fixed intervals"""
    while True:
        try:
            await asyncio.sleep(1.0 / Config.TICK_HZ)  # Compute at TICK_HZ
            
            # Get latest order books
            binance_book = app_state.binance_adapter.get_latest_book()
            coinbase_book = app_state.coinbase_adapter.get_latest_book()
            
            if binance_book and coinbase_book:
                # Update venue status
                app_state.venue_status["binance"] = True
                app_state.venue_status["coinance"] = True
                
                # Check if we should transition to "live" status
                if app_state.status == "warming":
                    binance_age = (datetime.now(timezone.utc) - binance_book.timestamp).total_seconds()
                    coinbase_age = (datetime.now(timezone.utc) - coinbase_book.timestamp).total_seconds()
                    
                    if binance_age < 1.0 and coinbase_age < 1.0:
                        app_state.status = "live"
                        logger.info("Status changed to LIVE")
                
                # Compute metrics
                metrics = app_state.metrics_computer.compute_metrics(
                    binance_book, coinbase_book
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
        
        # Keep connection alive
        while True:
            # Wait for any message (ping/pong or disconnect)
            data = await websocket.receive_text()
            
            # Handle ping/pong if needed
            if data == "ping":
                await websocket.send_text("pong")
                
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
        coinbase_book = app_state.coinbase_adapter.get_latest_book()
        
        if not (binance_book and coinbase_book):
            raise HTTPException(status_code=503, detail="Order books not available")
        
        # Execute SOR
        result = app_state.sor_router.execute_order(
            side=side,
            notional_usd=notional_usd,
            fee_bps=fee_bps,
            binance_book=binance_book,
            coinbase_book=coinbase_book
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
