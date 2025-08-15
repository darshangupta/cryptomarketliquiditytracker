# Crypto Market Liquidity Tracker - Backend

Real-time multi-venue liquidity analytics platform backend built with FastAPI and WebSockets.

## Features

- **Real-time Data Ingestion**: WebSocket connections to Binance and Coinbase
- **Market Metrics**: Mid price, spread, depth, HHI, imbalance, venue shares
- **WebSocket Streaming**: Live metrics broadcast to frontend clients
- **Smart Order Router**: Fee-aware execution vs naive baseline
- **Status Management**: Warming → Live progression with venue health monitoring

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Binance WS    │    │  Coinbase WS    │    │   FastAPI App   │
│     Adapter     │    │     Adapter     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Order Book Buffer                           │
│              (Ring buffers for each venue)                     │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Metrics Computer                             │
│              (HHI, depth, shares, etc.)                       │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 WebSocket Broadcast                            │
│              (Real-time to frontend)                          │
└─────────────────────────────────────────────────────────────────┘
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file and customize:

```bash
cp env.example .env
```

Key settings:
- `TICK_HZ`: Metrics computation frequency (2 or 4 Hz)
- `TOP_LEVELS`: Number of order book levels to track
- `API_PORT`: Backend server port (default: 8000)

### 3. Test Exchange Connections

Before starting the full server, test the exchange adapters:

```bash
python test_connection.py
```

This will verify:
- Binance WebSocket connection
- Coinbase WebSocket connection
- Data reception and parsing

## Running the Backend

### Development Mode

```bash
python main.py
```

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### WebSocket

- **`/ws/stream`**: Real-time market data streaming
  - Query params: `symbol=BTC-USD&window=050bps`
  - Frames: `< 2KB` with rounded decimals
  - Heartbeat: Every 5 seconds

### REST

- **`POST /api/execute`**: Smart Order Router execution
  - Returns SOR vs naive baseline
  - Requires `status == "live"`
- **`GET /api/health`**: System health and status
- **`GET /docs`**: Interactive API documentation

## Testing

### Run Unit Tests

```bash
pytest tests/
```

### Test Specific Components

```bash
# Test metrics computation
pytest tests/test_metrics.py -v

# Test with coverage
pytest tests/ --cov=metrics --cov=ingest --cov=state
```

## Data Flow

1. **Exchange Adapters** connect to public WebSocket feeds
2. **Order Book Buffer** stores recent data in ring buffers
3. **Metrics Computer** calculates market metrics at fixed intervals
4. **WebSocket Server** broadcasts metrics to connected clients
5. **Status Management** tracks venue health and system readiness

## Monitoring

### Logs

- Exchange connection status
- Metrics computation timing
- WebSocket client connections
- Error handling and recovery

### Health Checks

- Venue connectivity status
- Buffer utilization
- WebSocket client count
- System status (warming/live)

## Troubleshooting

### Common Issues

1. **Exchange Connection Failures**
   - Check network connectivity
   - Verify WebSocket URLs are accessible
   - Monitor rate limits (public feeds)

2. **High Latency**
   - Reduce `TICK_HZ` if needed
   - Monitor venue staleness thresholds
   - Check system resource usage

3. **WebSocket Disconnections**
   - Verify client reconnection logic
   - Check CORS settings
   - Monitor heartbeat intervals

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python main.py
```

## Next Steps (V1.5)

- [ ] DuckDB persistence for historical data
- [ ] `/api/replay` endpoint for data replay
- [ ] Parquet file export
- [ ] Advanced analytics and alerts
