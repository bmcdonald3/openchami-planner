#!/bin/bash

# Prompt for the OpenAI API Key (input is hidden for security)
echo -n "Enter your OPENAI_API_KEY: "
read -s OPENAI_API_KEY
echo ""
export OPENAI_API_KEY

echo "Starting Backend Server..."

# Activate the virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "backend/venv/bin/activate" ]; then
    source backend/venv/bin/activate
else
    echo "Warning: venv not found. Ensure your Python environment is active."
fi

# Determine backend directory and start FastAPI
if [ -d "backend" ]; then
    cd backend
    uvicorn main:app --reload --port 8000 &
    BACKEND_PID=$!
    cd ..
elif [ -f "main.py" ]; then
    uvicorn main:app --reload --port 8000 &
    BACKEND_PID=$!
else
    echo "Error: Could not locate backend main.py"
    exit 1
fi

echo "Starting Frontend Server..."

# Start Vite frontend
if [ -d "frontend" ]; then
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
else
    echo "Error: Could not locate frontend directory"
    kill $BACKEND_PID
    exit 1
fi

echo ""
echo "========================================="
echo "Servers are running!"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press [CTRL+C] to stop both servers."
echo "========================================="

# Trap SIGINT (Ctrl+C) to gracefully shut down the background processes
trap "echo -e '\nStopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# Keep the script running to hold the background processes open
wait