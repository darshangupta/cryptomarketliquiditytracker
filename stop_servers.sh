#!/bin/bash

echo "🛑 Stopping all servers..."

# Kill all processes
pkill -f "uvicorn|next|node|python.*main" || true
pkill -f "python.*main.py" || true

# Kill processes on our ports
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true

echo "✅ All servers stopped"
