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
from metrics.arbitrage import ArbitrageDetector
from metrics.analytics import PortfolioAnalytics
from state.buffers import OrderBookBuffer
from state.portfolio import PortfolioSimulator

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
        self.arbitrage_detector = ArbitrageDetector()
        self.portfolio_simulator = PortfolioSimulator()
        self.portfolio_analytics = PortfolioAnalytics(self.portfolio_simulator)
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
        self.arbitrage_task: Optional[asyncio.Task] = None
        self.analytics_task: Optional[asyncio.Task] = None
    
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
    app_state.arbitrage_task = asyncio.create_task(run_arbitrage_detection())
    app_state.analytics_task = asyncio.create_task(run_analytics_computation())
    
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
    if app_state.arbitrage_task:
        app_state.arbitrage_task.cancel()
    if app_state.analytics_task:
        app_state.analytics_task.cancel()
    
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

async def run_arbitrage_detection():
    """Run arbitrage detection at fixed intervals"""
    while True:
        try:
            await asyncio.sleep(5.0)  # Check every 5 seconds
            
            if app_state.status != "live":
                continue
            
            # Get latest order books for all symbols
            binance_books = {}
            kraken_books = {}
            
            # For now, we only have BTC data, but this structure supports multi-asset
            binance_book = app_state.binance_adapter.get_latest_book()
            kraken_book = app_state.kraken_adapter.get_latest_book()
            
            if binance_book and kraken_book:
                binance_books["BTC-USD"] = binance_book
                kraken_books["BTC-USD"] = kraken_book
                
                # Detect arbitrage opportunities
                opportunities = app_state.arbitrage_detector.detect_opportunities(
                    binance_books, kraken_books
                )
                
                # Add opportunities to portfolio simulator
                for opp in opportunities:
                    app_state.portfolio_simulator.add_arbitrage_opportunity(opp)
                
                if opportunities:
                    logger.info(f"🔍 Detected {len(opportunities)} arbitrage opportunities")
                    
                    # Auto-execute profitable opportunities
                    await auto_execute_arbitrage(opportunities)
                
        except Exception as e:
            logger.error(f"Arbitrage detection failed: {e}")
            await asyncio.sleep(1)

async def auto_execute_arbitrage(opportunities):
    """Automatically execute profitable arbitrage opportunities"""
    try:
        for opp in opportunities:
            if opp.is_profitable(Config.MIN_PROFIT_THRESHOLD_BPS):
                # Calculate trade size (use 10% of available cash or max trade size, whichever is smaller)
                available_cash = float(app_state.portfolio_simulator.cash_usd)
                trade_size_usd = min(available_cash * 0.1, float(opp.max_trade_size))
                
                if trade_size_usd >= 100:  # Minimum $100 trade
                    logger.info(f"🚀 Auto-executing arbitrage: {opp.symbol} ${trade_size_usd:.2f}")
                    
                    trade = app_state.portfolio_simulator.execute_arbitrage(opp, trade_size_usd)
                    if trade:
                        logger.info(f"✅ Arbitrage executed successfully: {trade.id}")
                    else:
                        logger.warning(f"❌ Arbitrage execution failed for {opp.symbol}")
                        
    except Exception as e:
        logger.error(f"Auto-execute arbitrage failed: {e}")

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
    await websocket.accept()
    logger.info("🔌 New WebSocket client connected")
    
    try:
        # Send initial connection status
        await websocket.send_text(json.dumps({
            "type": "connection_status",
            "data": {
                "status": "connected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "WebSocket connection established"
            }
        }))
        
        # Stream live market data
        while True:
            try:
                # Get latest order books
                binance_book = app_state.order_book_buffer.get_latest_binance_book()
                kraken_book = app_state.order_book_buffer.get_latest_kraken_book()
                
                if binance_book and kraken_book:
                    # Analyze order book depth
                    binance_depth = binance_book.analyze_depth()
                    kraken_depth = kraken_book.analyze_depth()
                    
                    # Get top levels for display
                    binance_top_bids, binance_top_asks = binance_book.get_top_levels(20)
                    kraken_top_bids, kraken_top_asks = kraken_book.get_top_levels(20)
                    
                    # Calculate market impact for different trade sizes
                    trade_sizes = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
                    binance_impact = {}
                    kraken_impact = {}
                    
                    for size in trade_sizes:
                        # Binance impact
                        buy_price, buy_impact = binance_depth.get_market_impact(size, "buy")
                        sell_price, sell_impact = binance_depth.get_market_impact(size, "sell")
                        binance_impact[str(size)] = {
                            "buy": {"price": buy_price, "impact_bps": buy_impact * 100},
                            "sell": {"price": sell_price, "impact_bps": sell_impact * 100}
                        }
                        
                        # Kraken impact
                        buy_price, buy_impact = kraken_depth.get_market_impact(size, "buy")
                        sell_price, sell_impact = kraken_depth.get_market_impact(size, "sell")
                        kraken_impact[str(size)] = {
                            "buy": {"price": buy_price, "impact_bps": buy_impact * 100},
                            "sell": {"price": sell_price, "impact_bps": sell_impact * 100}
                        }
                    
                    # Get optimal trade sizes
                    binance_optimal = binance_depth.get_optimal_trade_size(10.0)  # 10 bps max impact
                    kraken_optimal = kraken_depth.get_optimal_trade_size(10.0)
                    
                    # Calculate liquidity scores
                    binance_liquidity = binance_book.calculate_liquidity_score(50.0)  # ±50 bps window
                    kraken_liquidity = kraken_book.calculate_liquidity_score(50.0)
                    
                    # Send comprehensive market data
                    await websocket.send_text(json.dumps({
                        "type": "market_metrics",
                        "data": {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "binance": {
                                "bid": binance_book.best_bid,
                                "ask": binance_book.best_ask,
                                "spread": binance_book.best_ask - binance_book.best_bid if binance_book.best_bid and binance_book.best_ask else 0,
                                "mid_price": binance_book.mid_price,
                                "spread_bps": binance_book.spread_bps,
                                "depth": binance_depth.total_bid_depth + binance_depth.total_ask_depth,
                                "liquidity_score": binance_liquidity,
                                "optimal_trade_size": binance_optimal[0],
                                "optimal_impact_bps": binance_optimal[1],
                                "top_bids": [{"price": level.price, "size": level.size} for level in binance_top_bids],
                                "top_asks": [{"price": level.price, "size": level.size} for level in binance_top_asks],
                                "market_impact": binance_impact
                            },
                            "kraken": {
                                "bid": kraken_book.best_bid,
                                "ask": kraken_book.best_ask,
                                "spread": kraken_book.best_ask - kraken_book.best_bid if kraken_book.best_bid and kraken_book.best_ask else 0,
                                "mid_price": kraken_book.mid_price,
                                "spread_bps": kraken_book.spread_bps,
                                "depth": kraken_depth.total_bid_depth + kraken_depth.total_ask_depth,
                                "liquidity_score": kraken_liquidity,
                                "optimal_trade_size": kraken_optimal[0],
                                "optimal_impact_bps": kraken_optimal[1],
                                "top_bids": [{"price": level.price, "size": level.size} for level in kraken_top_bids],
                                "top_asks": [{"price": level.price, "size": level.size} for level in kraken_top_asks],
                                "market_impact": kraken_impact
                            },
                            "metrics": {
                                "mid": (binance_book.mid_price + kraken_book.mid_price) / 2 if binance_book.mid_price and kraken_book.mid_price else 0,
                                "spread_bps": (binance_book.spread_bps + kraken_book.spread_bps) / 2 if binance_book.spread_bps and kraken_book.spread_bps else 0,
                                "depth": (binance_depth.total_bid_depth + binance_depth.total_ask_depth + kraken_depth.total_bid_depth + kraken_depth.total_ask_depth),
                                "hhi": app_state.metrics_computer.compute_metrics(binance_book, kraken_book).get("hhi", 0),
                                "imbalance": app_state.metrics_computer.compute_metrics(binance_book, kraken_book).get("imbalance", 0),
                                "total_liquidity_score": binance_liquidity + kraken_liquidity
                            }
                        }
                    }))
                    
                    logger.info("📊 Sent comprehensive market data via WebSocket")
                
                # Wait before next update
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Error in WebSocket data streaming: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {
                        "message": f"Error processing market data: {str(e)}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }))
                break
                
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket client disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": {
                    "message": f"WebSocket error: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }))
        except:
            pass

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

@app.get("/api/portfolio/summary")
async def get_portfolio_summary():
    """Get current portfolio summary"""
    try:
        return app_state.portfolio_simulator.get_portfolio_summary()
    except Exception as e:
        logger.error(f"Failed to get portfolio summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/portfolio/positions")
async def get_portfolio_positions():
    """Get all portfolio positions"""
    try:
        summary = app_state.portfolio_simulator.get_portfolio_summary()
        return {
            "timestamp": summary["timestamp"],
            "positions": summary["positions"]
        }
    except Exception as e:
        logger.error(f"Failed to get portfolio positions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/portfolio/trades")
async def get_portfolio_trades(limit: int = 50):
    """Get recent portfolio trades"""
    try:
        trades = app_state.portfolio_simulator.trades[-limit:] if app_state.portfolio_simulator.trades else []
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trades": [
                {
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": float(trade.quantity),
                    "price_usd": float(trade.price_usd),
                    "total_usd": float(trade.total_usd),
                    "venue": trade.venue,
                    "timestamp": trade.timestamp.isoformat(),
                    "fees_usd": float(trade.fees_usd),
                    "arbitrage_profit_bps": float(trade.arbitrage_profit_bps) if trade.arbitrage_profit_bps else None
                }
                for trade in trades
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get portfolio trades: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/portfolio/reset")
async def reset_portfolio():
    """Reset portfolio to initial state"""
    try:
        app_state.portfolio_simulator.reset_portfolio()
        return {
            "message": "Portfolio reset successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to reset portfolio: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/arbitrage/opportunities")
async def get_arbitrage_opportunities(symbol: Optional[str] = None, limit: int = 20):
    """Get current arbitrage opportunities"""
    try:
        if symbol:
            opportunities = app_state.portfolio_simulator.get_arbitrage_opportunities(symbol)
        else:
            opportunities = app_state.arbitrage_detector.get_best_opportunities(limit)
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "opportunities": [
                {
                    "symbol": opp.symbol,
                    "buy_venue": opp.buy_venue,
                    "sell_venue": opp.sell_venue,
                    "buy_price": float(opp.buy_price),
                    "sell_price": float(opp.sell_price),
                    "spread_bps": float(opp.spread_bps),
                    "estimated_profit_usd": float(opp.estimated_profit_usd),
                    "max_trade_size": float(opp.max_trade_size),
                    "confidence_score": opp.confidence_score,
                    "timestamp": opp.timestamp.isoformat(),
                    "expires_at": opp.expires_at.isoformat()
                }
                for opp in opportunities
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get arbitrage opportunities: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/arbitrage/summary")
async def get_arbitrage_summary():
    """Get arbitrage detection summary"""
    try:
        return app_state.arbitrage_detector.get_opportunities_summary()
    except Exception as e:
        logger.error(f"Failed to get arbitrage summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/arbitrage/execute")
async def execute_arbitrage_manual(request: dict):
    """Manually execute arbitrage opportunity"""
    try:
        symbol = request.get("symbol")
        trade_size_usd = request.get("trade_size_usd")
        
        if not symbol or not trade_size_usd:
            raise HTTPException(status_code=400, detail="Missing symbol or trade_size_usd")
        
        # Find the best opportunity for this symbol
        opportunities = app_state.portfolio_simulator.get_arbitrage_opportunities(symbol)
        if not opportunities:
            raise HTTPException(status_code=404, detail="No arbitrage opportunities found for symbol")
        
        best_opportunity = opportunities[0]  # Get the best one
        
        # Execute the arbitrage
        trade = app_state.portfolio_simulator.execute_arbitrage(best_opportunity, trade_size_usd)
        
        if trade:
            return {
                "message": "Arbitrage executed successfully",
                "trade_id": trade.id,
                "symbol": trade.symbol,
                "profit_bps": float(trade.arbitrage_profit_bps) if trade.arbitrage_profit_bps else None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to execute arbitrage")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute arbitrage: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/assets/status")
async def get_assets_status():
    """Get status of all configured assets"""
    try:
        assets_status = {}
        
        for symbol in Config.SYMBOLS:
            # Get latest order books for this symbol
            binance_book = app_state.binance_adapter.get_latest_book() if symbol == "BTC-USD" else None
            kraken_book = app_state.kraken_adapter.get_latest_book() if symbol == "BTC-USD" else None
            
            if binance_book and kraken_book:
                # Calculate cross-exchange metrics
                binance_mid = binance_book.mid_price
                kraken_mid = kraken_book.mid_price
                
                if binance_mid and kraken_mid:
                    spread = abs(binance_mid - kraken_mid)
                    spread_bps = (spread / min(binance_mid, kraken_mid)) * 10000
                    
                    assets_status[symbol] = {
                        "status": "active",
                        "binance_mid": binance_mid,
                        "kraken_mid": kraken_mid,
                        "cross_exchange_spread_bps": spread_bps,
                        "last_update": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    assets_status[symbol] = {
                        "status": "no_data",
                        "last_update": datetime.now(timezone.utc).isoformat()
                    }
            else:
                assets_status[symbol] = {
                    "status": "no_data",
                    "last_update": datetime.now(timezone.utc).isoformat()
                }
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "assets": assets_status
        }
        
    except Exception as e:
        logger.error(f"Failed to get assets status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def run_analytics_computation():
    """Run portfolio analytics computation at fixed intervals"""
    while True:
        try:
            await asyncio.sleep(Config.PERFORMANCE_METRICS_INTERVAL)  # Update every 5 minutes
            
            if app_state.status != "live":
                continue
            
            # Calculate all analytics metrics
            analytics_data = app_state.portfolio_analytics.calculate_all_metrics()
            
            if analytics_data:
                logger.info(f"📊 Analytics computed: {len(analytics_data)} metrics calculated")
                
                # Broadcast analytics to WebSocket clients
                await broadcast_analytics(analytics_data)
                
        except Exception as e:
            logger.error(f"Analytics computation failed: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error

async def broadcast_analytics(analytics_data: dict):
    """Broadcast analytics data to all connected WebSocket clients"""
    try:
        analytics_frame = {
            "type": "analytics_update",
            "data": analytics_data
        }
        await broadcast_frame(analytics_frame)
    except Exception as e:
        logger.error(f"Failed to broadcast analytics: {e}")

@app.get("/api/analytics/performance")
async def get_performance_analytics():
    """Get comprehensive performance analytics"""
    try:
        analytics_data = app_state.portfolio_analytics.calculate_all_metrics()
        return analytics_data
    except Exception as e:
        logger.error(f"Failed to get performance analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/analytics/performance/summary")
async def get_performance_summary():
    """Get performance summary metrics"""
    try:
        analytics_data = app_state.portfolio_analytics.calculate_all_metrics()
        
        # Extract key performance metrics
        performance = analytics_data.get("performance", {})
        risk = analytics_data.get("risk", {})
        
        return {
            "timestamp": analytics_data.get("timestamp"),
            "key_metrics": {
                "total_return_pct": performance.get("total_return", 0) * 100,
                "annualized_return_pct": performance.get("annualized_return", 0) * 100,
                "sharpe_ratio": performance.get("sharpe_ratio", 0),
                "max_drawdown_pct": performance.get("max_drawdown", 0) * 100,
                "win_rate_pct": performance.get("win_rate", 0),
                "volatility_pct": performance.get("volatility", 0) * 100
            },
            "risk_metrics": {
                "var_95_pct": risk.get("var_95", 0) * 100,
                "var_99_pct": risk.get("var_99", 0) * 100,
                "ulcer_index": risk.get("ulcer_index", 0),
                "gain_to_pain_ratio": risk.get("gain_to_pain_ratio", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/analytics/allocation")
async def get_allocation_analytics():
    """Get asset allocation and diversification analytics"""
    try:
        analytics_data = app_state.portfolio_analytics.calculate_all_metrics()
        return {
            "timestamp": analytics_data.get("timestamp"),
            "allocation": analytics_data.get("allocation", {}),
            "diversification": analytics_data.get("diversification", {})
        }
    except Exception as e:
        logger.error(f"Failed to get allocation analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/analytics/arbitrage")
async def get_arbitrage_analytics():
    """Get arbitrage-specific performance analytics"""
    try:
        analytics_data = app_state.portfolio_analytics.calculate_all_metrics()
        return {
            "timestamp": analytics_data.get("timestamp"),
            "arbitrage": analytics_data.get("arbitrage", {})
        }
    except Exception as e:
        logger.error(f"Failed to get arbitrage analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/analytics/risk")
async def get_risk_analytics():
    """Get comprehensive risk analytics"""
    try:
        analytics_data = app_state.portfolio_analytics.calculate_all_metrics()
        return {
            "timestamp": analytics_data.get("timestamp"),
            "risk": analytics_data.get("risk", {}),
            "performance": {
                "volatility": analytics_data.get("performance", {}).get("volatility", 0),
                "max_drawdown": analytics_data.get("performance", {}).get("max_drawdown", 0)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get risk analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/analytics/historical")
async def get_historical_analytics(days: int = 30):
    """Get historical analytics for specified time period"""
    try:
        # For now, return current analytics
        # In future, this would query historical data from database
        analytics_data = app_state.portfolio_analytics.calculate_all_metrics()
        
        return {
            "timestamp": analytics_data.get("timestamp"),
            "period_days": days,
            "current_metrics": analytics_data,
            "note": "Historical data storage not yet implemented - showing current metrics"
        }
        
    except Exception as e:
        logger.error(f"Failed to get historical analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
