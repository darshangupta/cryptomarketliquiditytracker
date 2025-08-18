#!/bin/bash

echo "🚀 Starting Crypto Market Liquidity Tracker..."

# Kill all existing processes
echo "🔄 Killing existing processes..."
pkill -f "uvicorn|next|node|python.*main" || true
pkill -f "python.*main.py" || true
sleep 2

# Kill any processes on our ports
echo "🔌 Freeing up ports..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
sleep 1

echo "✅ Ports cleared"

# Start backend
echo "🐍 Starting backend server..."
cd apps/backend
python main.py &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Start frontend
echo "⚛️  Starting frontend server..."
cd ../web
npm run dev &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

# Wait for frontend to start
echo "⏳ Waiting for frontend to start..."
sleep 8

echo ""
echo "🎉 Servers started successfully!"
echo "📊 Backend: http://localhost:8000 (PID: $BACKEND_PID)"
echo "🌐 Frontend: http://localhost:3000 (PID: $FRONTEND_PID)"
echo ""
echo "Press Ctrl+C to stop both servers"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    pkill -f "uvicorn|next|node|python.*main" || true
    echo "✅ Servers stopped"
    exit 0
}

# Trap Ctrl+C
trap cleanup SIGINT

# Keep script running
wait
