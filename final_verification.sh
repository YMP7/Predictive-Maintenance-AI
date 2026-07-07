#!/bin/bash

echo "AI Digital Twin Prototype - Final Verification"
echo "=============================================="

# Determine Python command
PYTHON_CMD="python"
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
fi
echo "Using Python command: $PYTHON_CMD"

# Check Python modules
echo -e "\n1. Checking Python modules..."
$PYTHON_CMD -c "import sensor_simulator, ai_agent, data_service; print('✓ All Python modules OK')" || { echo "✗ Python modules failed to import"; exit 1; }

# Check Node.js packages
echo -e "\n2. Checking Node.js packages..."
cd client || { echo "✗ Failed to change directory to client"; exit 1; }
# Note: npm might be npm.cmd on Windows, but in Git Bash it works via npm.
npm list react react-dom recharts > /dev/null 2>&1 && echo "✓ All Node.js packages OK" || echo "✗ Node.js packages check failed (continuing anyway)"
cd ..

# Check configuration files
echo -e "\n3. Checking configuration files..."
[ -f .env ] && echo "✓ .env file exists" || echo "✗ .env file missing"
[ -f config/machines.json ] && echo "✓ machines.json exists" || echo "✗ machines.json missing"

# Test Python components
echo -e "\n4. Testing Python components..."
$PYTHON_CMD -c "
from sensor_simulator import MultiMachineSimulator
from ai_agent import AIAgent

sim = MultiMachineSimulator()
agent = AIAgent()

readings = sim.get_all_readings()
for reading in readings:
    result = agent.process_reading(reading)
    
print('✓ Python components working')
" || { echo "✗ Python components failed"; exit 1; }

# Test backend API
echo -e "\n5. Testing backend API..."
$PYTHON_CMD backend_api.py &
BACKEND_PID=$!
sleep 3

# Check if responding
curl -s http://localhost:8000/health > /dev/null
CURL_STATUS=$?
if [ $CURL_STATUS -eq 0 ]; then
    echo "✓ Backend API responding"
else
    echo "✗ Backend API failed to respond"
fi

# Kill background backend API process
if [ ! -z "$BACKEND_PID" ]; then
    # Works in bash (including Git Bash)
    kill $BACKEND_PID 2>/dev/null
fi

# Test frontend build
echo -e "\n6. Testing frontend build (using direct node execution to bypass ampersand path issue)..."
cd client || exit 1
node node_modules/typescript/lib/tsc.js -b && node node_modules/vite/bin/vite.js build > /dev/null 2>&1
BUILD_STATUS=$?
if [ $BUILD_STATUS -eq 0 ]; then
    echo "✓ Frontend builds successfully"
else
    echo "✗ Frontend build failed"
fi
cd ..

# Run tests
echo -e "\n7. Running test suite..."
$PYTHON_CMD -m pytest tests/ -q && echo "✓ All tests passing" || echo "✗ Some tests failed"

echo -e "\n=============================================="
echo "Verification complete!"
