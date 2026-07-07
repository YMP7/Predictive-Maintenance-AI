# AI Digital Twin Prototype - Step-by-Step Completion Procedure
## Complete Roadmap from Development to Production-Ready Demonstration

> [!IMPORTANT]
> **Document Status (June 21, 2026):** This file is a development roadmap written during initial planning. The inline code blocks were scaffolding aids and may differ from the current source files. For the verified runbook and actual commands, refer to the **Quick Start Checklist**. The current automated suite has **29 passing tests**.

---

## Table of Contents
1. [Phase 1: Foundation Setup](#phase-1-foundation-setup)
2. [Phase 2: Backend Integration](#phase-2-backend-integration)
3. [Phase 3: Frontend Development](#phase-3-frontend-development)
4. [Phase 4: AI Agent Integration](#phase-4-ai-agent-integration)
5. [Phase 5: Testing and Validation](#phase-5-testing-and-validation)
6. [Phase 6: Deployment and Launch](#phase-6-deployment-and-launch)
7. [Phase 7: Demonstration and Documentation](#phase-7-demonstration-and-documentation)

---

## PHASE 1: Foundation Setup
**Duration: 2-3 Days | Status: COMPLETED**

### Step 1.1: Verify Project Structure
**Objective**: Ensure all project files are properly organized

**Actions**:
```bash
# Navigate to project directory
cd /home/ubuntu/ai-digital-twin-prototype

# Verify directory structure
tree -L 2 -I 'node_modules|venv'

# Expected structure:
# ├── client/
# │   ├── src/
# │   │   ├── pages/
# │   │   ├── components/
# │   │   ├── contexts/
# │   │   ├── hooks/
# │   │   ├── lib/
# │   │   ├── App.tsx
# │   │   ├── main.tsx
# │   │   └── index.css
# │   ├── public/
# │   └── index.html
# ├── server/
# ├── shared/
# ├── sensor_simulator.py
# ├── ai_agent.py
# ├── data_service.py
# ├── package.json
# ├── tsconfig.json
# └── vite.config.ts
```

**Verification Checklist**:
- [ ] All Python modules present (sensor_simulator.py, ai_agent.py, data_service.py)
- [ ] React pages created (Home.tsx, Dashboard.tsx)
- [ ] Configuration files present (package.json, tsconfig.json, vite.config.ts)
- [ ] No syntax errors in existing files

**Command to Execute**:
```bash
# Check Python files
python3 -m py_compile sensor_simulator.py ai_agent.py data_service.py
echo "Python files syntax OK"

# Check TypeScript files
npx tsc --noEmit
echo "TypeScript files syntax OK"
```

**Success Criteria**: All files present with no syntax errors

---

### Step 1.2: Install and Configure Dependencies
**Objective**: Set up all required packages and libraries

**Actions**:
```bash
# 1. Install Python dependencies
pip install numpy pandas scikit-learn requests pyyaml python-dotenv

# 2. Verify Python installation
python3 -c "import numpy, pandas, sklearn; print('Python dependencies OK')"

# 3. Install Node.js dependencies
cd /home/ubuntu/ai-digital-twin-prototype
pnpm install

# 4. Verify Node.js installation
npm list react react-dom recharts
```

**Dependency Verification**:
```python
# Create test script: test_dependencies.py
import sys

required_packages = {
    'numpy': '1.19.0',
    'pandas': '1.1.0',
    'scikit-learn': '0.23.0',
    'requests': '2.25.0'
}

for package, min_version in required_packages.items():
    try:
        __import__(package)
        print(f"✓ {package} installed")
    except ImportError:
        print(f"✗ {package} NOT installed")
        sys.exit(1)

print("\nAll dependencies verified!")
```

**Execute**:
```bash
python3 test_dependencies.py
```

**Success Criteria**: All dependencies installed and verified

---

### Step 1.3: Initialize Environment Configuration
**Objective**: Set up environment variables and configuration files

**Actions**:
```bash
# 1. Create .env file
cat > .env << 'EOF'
# AI Agent Configuration
MACHINE_ID=M001
MACHINE_TYPE=Lathe
MACHINE_LOCATION=Section A

# Simulation Configuration
SIMULATION_INTERVAL=1
SIMULATION_ENABLED=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Dashboard Configuration
DASHBOARD_PORT=3000
DASHBOARD_REFRESH_INTERVAL=2000

# Alert Configuration
ALERT_COOLDOWN=300
ALERT_LANGUAGES=en,hi,te,ta,mr

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=./logs/agent.log
EOF

# 2. Create configuration directory
mkdir -p config logs data

# 3. Create machine configuration
cat > config/machines.json << 'EOF'
{
  "machines": {
    "M001": {
      "name": "Lathe Machine",
      "type": "Lathe",
      "location": "Section A",
      "thresholds": {
        "vibration": {"warning": 1.5, "critical": 3.0},
        "temperature": {"warning": 60, "critical": 75},
        "current": {"warning": 3.5, "critical": 4.5}
      }
    },
    "M002": {
      "name": "Pump Motor",
      "type": "Motor",
      "location": "Section B",
      "thresholds": {
        "vibration": {"warning": 1.2, "critical": 2.8},
        "temperature": {"warning": 65, "critical": 80},
        "current": {"warning": 4.0, "critical": 5.0}
      }
    },
    "M003": {
      "name": "Drill Press",
      "type": "Drill",
      "location": "Section C",
      "thresholds": {
        "vibration": {"warning": 1.8, "critical": 3.5},
        "temperature": {"warning": 55, "critical": 70},
        "current": {"warning": 3.0, "critical": 4.2}
      }
    },
    "M004": {
      "name": "Furnace",
      "type": "Heater",
      "location": "Section D",
      "thresholds": {
        "vibration": {"warning": 0.8, "critical": 1.5},
        "temperature": {"warning": 80, "critical": 95},
        "current": {"warning": 5.0, "critical": 6.5}
      }
    }
  }
}
EOF
```

**Verification**:
```bash
# Check files created
ls -la .env config/machines.json logs/

# Verify JSON syntax
python3 -m json.tool config/machines.json > /dev/null && echo "JSON valid"
```

**Success Criteria**: .env file and configuration files created and validated

---

## PHASE 2: Backend Integration
**Duration: 3-4 Days | Status: COMPLETED**

### Step 2.1: Create Backend API Server
**Objective**: Build FastAPI server to expose AI Agent functionality

**Actions**:
```bash
# Create backend API file
cat > backend_api.py << 'EOF'
"""
FastAPI Backend Server for AI Digital Twin
Exposes AI Agent functionality via REST API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import os
from datetime import datetime
from typing import Optional, List, Dict

from data_service import get_data_service

# Initialize FastAPI app
app = FastAPI(
    title="AI Digital Twin API",
    description="Predictive Maintenance System API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get data service instance
service = get_data_service()

# ============================================================================
# Health and Status Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/api/status")
async def system_status():
    """Get system status"""
    return {
        "status": "running",
        "simulation_running": service.is_running,
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# Dashboard Endpoints
# ============================================================================

@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    """Get dashboard summary"""
    summary = service.get_dashboard_summary()
    return JSONResponse(content=summary)

# ============================================================================
# Machine Endpoints
# ============================================================================

@app.get("/api/machines")
async def get_all_machines():
    """Get all machines"""
    machines = service.get_all_machines_info()
    return JSONResponse(content=machines)

@app.get("/api/machines/{machine_id}/status")
async def get_machine_status(machine_id: str):
    """Get machine status"""
    status = service.get_machine_status(machine_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Machine not found")
    return JSONResponse(content=status)

@app.get("/api/machines/{machine_id}/telemetry")
async def get_machine_telemetry(machine_id: str, limit: int = 100):
    """Get machine telemetry data"""
    telemetry = service.get_machine_telemetry(machine_id, limit=limit)
    return JSONResponse(content=telemetry)

@app.get("/api/machines/{machine_id}/trends")
async def get_machine_trends(machine_id: str):
    """Get machine trends"""
    trends = service.get_machine_trends(machine_id)
    return JSONResponse(content=trends)

# ============================================================================
# Alert Endpoints
# ============================================================================

@app.get("/api/alerts/recent")
async def get_recent_alerts(limit: int = 50):
    """Get recent alerts"""
    alerts = service.get_recent_alerts(limit=limit)
    return JSONResponse(content=alerts)

@app.get("/api/alerts/machine/{machine_id}")
async def get_machine_alerts(machine_id: str, limit: int = 20):
    """Get alerts for specific machine"""
    alerts = service.get_alerts_by_machine(machine_id, limit=limit)
    return JSONResponse(content=alerts)

# ============================================================================
# Control Endpoints
# ============================================================================

@app.post("/api/simulation/start")
async def start_simulation(interval: int = 1):
    """Start sensor simulation"""
    service.start_simulation(interval=interval)
    return {"status": "simulation started", "interval": interval}

@app.post("/api/simulation/stop")
async def stop_simulation():
    """Stop sensor simulation"""
    service.stop_simulation()
    return {"status": "simulation stopped"}

if __name__ == "__main__":
    import uvicorn
    
    # Start simulation
    service.start_simulation(interval=1)
    
    # Run server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
EOF

# Verify syntax
python3 -m py_compile backend_api.py
echo "Backend API syntax OK"
```

**Test Backend**:
```bash
# Run backend in background
python3 backend_api.py &
BACKEND_PID=$!

# Wait for server to start
sleep 3

# Test health endpoint
curl http://localhost:8000/health

# Test dashboard endpoint
curl http://localhost:8000/api/dashboard/summary

# Stop backend
kill $BACKEND_PID
```

**Success Criteria**: Backend API server running and responding to requests

---

### Step 2.2: Create Data Synchronization Layer
**Objective**: Ensure real-time data flow between Python backend and React frontend

**Actions**:
```bash
# Create data sync module
cat > data_sync.py << 'EOF'
"""
Data Synchronization Layer
Manages real-time data updates between backend and frontend
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Callable

class DataSyncManager:
    """Manages data synchronization"""
    
    def __init__(self):
        self.subscribers = {}
        self.last_update = {}
        self.update_interval = 2  # seconds
    
    def subscribe(self, channel: str, callback: Callable):
        """Subscribe to data updates"""
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        self.subscribers[channel].append(callback)
    
    def publish(self, channel: str, data: Dict):
        """Publish data to subscribers"""
        self.last_update[channel] = {
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        for callback in self.subscribers.get(channel, []):
            try:
                callback(data)
            except Exception as e:
                print(f"Error in callback: {e}")
    
    async def start_sync_loop(self, service):
        """Start continuous sync loop"""
        while True:
            try:
                # Publish dashboard summary
                summary = service.get_dashboard_summary()
                self.publish("dashboard", summary)
                
                # Publish machine statuses
                statuses = service.get_all_machines_status()
                for status in statuses:
                    self.publish(f"machine:{status['machine_id']}", status)
                
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                print(f"Error in sync loop: {e}")
                await asyncio.sleep(1)

# Global sync manager
_sync_manager = None

def get_sync_manager():
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = DataSyncManager()
    return _sync_manager
EOF

python3 -m py_compile data_sync.py
echo "Data sync module syntax OK"
```

**Success Criteria**: Data synchronization layer created and tested

---

## PHASE 3: Frontend Development
**Duration: 3-4 Days | Status: COMPLETED**

### Step 3.1: Update React App Configuration
**Objective**: Configure React app to connect to backend API

**Actions**:
```bash
# Update App.tsx to include Dashboard route
cat > client/src/App.tsx << 'EOF'
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";

function Router() {
  return (
    <Switch>
      <Route path={"/"} component={Home} />
      <Route path={"/dashboard"} component={Dashboard} />
      <Route path={"/404"} component={NotFound} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="light">
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
EOF

# Verify TypeScript
npx tsc --noEmit
echo "React app configuration OK"
```

**Success Criteria**: React app properly configured with routes

---

### Step 3.2: Implement Real-time Dashboard Updates
**Objective**: Create WebSocket or polling mechanism for live dashboard updates

**Actions**:
```bash
# Create custom hook for data fetching
cat > client/src/hooks/useDashboardData.ts << 'EOF'
import { useState, useEffect } from 'react';

export function useDashboardData(refreshInterval: number = 2000) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/api/dashboard/summary');
        if (!response.ok) throw new Error('Failed to fetch');
        const data = await response.json();
        setSummary(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, refreshInterval);
    
    return () => clearInterval(interval);
  }, [refreshInterval]);

  return { summary, loading, error };
}
EOF

# Verify TypeScript
npx tsc --noEmit
echo "Dashboard hook created"
```

**Success Criteria**: Real-time data fetching implemented

---

### Step 3.3: Build Dashboard Components
**Objective**: Create reusable dashboard components

**Actions**:
```bash
# Create machine card component
cat > client/src/components/MachineCard.tsx << 'EOF'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, CheckCircle, AlertTriangle } from "lucide-react";

interface MachineCardProps {
  machine: {
    machine_id: string;
    status: string;
    fault_type: string;
    rul_days: number | null;
    machine_info: {
      name: string;
      type: string;
      location: string;
    };
  };
  onClick: () => void;
}

export function MachineCard({ machine, onClick }: MachineCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "Critical":
        return "bg-red-100 text-red-800 border-red-300";
      case "Warning":
        return "bg-yellow-100 text-yellow-800 border-yellow-300";
      default:
        return "bg-green-100 text-green-800 border-green-300";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "Critical":
        return <AlertCircle className="w-5 h-5 text-red-600" />;
      case "Warning":
        return <AlertTriangle className="w-5 h-5 text-yellow-600" />;
      default:
        return <CheckCircle className="w-5 h-5 text-green-600" />;
    }
  };

  return (
    <Card
      onClick={onClick}
      className={`cursor-pointer transition-all hover:shadow-lg ${getStatusColor(machine.status)}`}
    >
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">{machine.machine_info.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground">{machine.machine_id}</p>
            <p className="text-xs mt-1">{machine.fault_type}</p>
          </div>
          {getStatusIcon(machine.status)}
        </div>
        {machine.rul_days && (
          <p className="text-xs mt-2 font-semibold">RUL: {machine.rul_days} days</p>
        )}
      </CardContent>
    </Card>
  );
}
EOF

# Verify TypeScript
npx tsc --noEmit
echo "Machine card component created"
```

**Success Criteria**: Dashboard components created and working

---

## PHASE 4: AI Agent Integration
**Duration: 2-3 Days | Status: COMPLETED**

### Step 4.1: Integrate Python Backend with React Frontend
**Objective**: Create unified API layer connecting all components

**Actions**:
```bash
# Create integrated server
cat > integrated_server.py << 'EOF'
"""
Integrated Server combining FastAPI backend with data service
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
import asyncio
import threading

from data_service import get_data_service
from backend_api import app as api_app

# Create main app
app = FastAPI(title="AI Digital Twin Integrated Server")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_app.router, prefix="/api")

# Start data service in background thread
def start_data_service():
    service = get_data_service()
    service.start_simulation(interval=1)

# Start background thread
service_thread = threading.Thread(target=start_data_service, daemon=True)
service_thread.start()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
EOF

python3 -m py_compile integrated_server.py
echo "Integrated server created"
```

**Success Criteria**: Integrated server running with both backend and frontend

---

### Step 4.2: Test AI Agent Processing Pipeline
**Objective**: Verify end-to-end AI processing

**Actions**:
```bash
# Create test script
cat > test_ai_pipeline.py << 'EOF'
"""
Test AI Agent Processing Pipeline
"""

from sensor_simulator import MultiMachineSimulator
from ai_agent import AIAgent
from data_service import get_data_service
import json

def test_pipeline():
    print("Testing AI Agent Processing Pipeline...")
    print("=" * 60)
    
    # Initialize components
    simulator = MultiMachineSimulator()
    agent = AIAgent()
    service = get_data_service()
    
    # Simulate 50 iterations
    for iteration in range(50):
        print(f"\n--- Iteration {iteration + 1} ---")
        
        # Get readings
        readings = simulator.get_all_readings()
        
        # Process with AI agent
        for reading in readings:
            result = agent.process_reading(reading)
            
            # Print summary
            print(f"Machine: {result['machine_id']}")
            print(f"Status: {result['status']}")
            print(f"Fault Type: {result['fault_type']}")
            print(f"RUL: {result['rul_days']} days")
            
            if result['alerts']:
                print(f"Alerts: {len(result['alerts'])}")
                for alert in result['alerts']:
                    print(f"  - {alert['severity']}: {alert['message']}")
        
        # Get dashboard summary
        summary = service.get_dashboard_summary()
        print(f"\nDashboard Summary:")
        print(f"Total Machines: {summary['total_machines']}")
        print(f"Critical: {summary['machine_status_counts']['Critical']}")
        print(f"Warning: {summary['machine_status_counts']['Warning']}")
        print(f"Normal: {summary['machine_status_counts']['Normal']}")
    
    print("\n" + "=" * 60)
    print("Pipeline test completed successfully!")

if __name__ == "__main__":
    test_pipeline()
EOF

# Run test
python3 test_ai_pipeline.py
```

**Success Criteria**: AI pipeline processing correctly with expected outputs

---

### Step 4.3: Implement Alert System
**Objective**: Create alert delivery mechanism

**Actions**:
```bash
# Create alert handler
cat > alert_handler.py << 'EOF'
"""
Alert Handler - Manages alert delivery and notifications
"""

import json
from datetime import datetime
from typing import Dict, List
from enum import Enum

class AlertChannel(Enum):
    """Alert delivery channels"""
    DASHBOARD = "dashboard"
    SMS = "sms"
    EMAIL = "email"
    VOICE = "voice"
    LOG = "log"

class AlertHandler:
    """Handles alert delivery"""
    
    def __init__(self):
        self.alert_queue = []
        self.delivered_alerts = []
    
    def queue_alert(self, alert: Dict, channels: List[AlertChannel] = None):
        """Queue alert for delivery"""
        if channels is None:
            channels = [AlertChannel.DASHBOARD, AlertChannel.LOG]
        
        alert_with_channels = {
            **alert,
            "channels": [c.value for c in channels],
            "queued_at": datetime.now().isoformat()
        }
        
        self.alert_queue.append(alert_with_channels)
        print(f"Alert queued: {alert['message']}")
    
    def process_alerts(self):
        """Process queued alerts"""
        while self.alert_queue:
            alert = self.alert_queue.pop(0)
            self._deliver_alert(alert)
    
    def _deliver_alert(self, alert: Dict):
        """Deliver alert through configured channels"""
        for channel in alert.get("channels", []):
            if channel == "dashboard":
                self._deliver_dashboard(alert)
            elif channel == "sms":
                self._deliver_sms(alert)
            elif channel == "email":
                self._deliver_email(alert)
            elif channel == "voice":
                self._deliver_voice(alert)
            elif channel == "log":
                self._deliver_log(alert)
        
        self.delivered_alerts.append(alert)
    
    def _deliver_dashboard(self, alert: Dict):
        """Deliver to dashboard"""
        print(f"[DASHBOARD] {alert['message']}")
    
    def _deliver_sms(self, alert: Dict):
        """Deliver via SMS"""
        print(f"[SMS] {alert['message']}")
        # TODO: Implement actual SMS delivery
    
    def _deliver_email(self, alert: Dict):
        """Deliver via email"""
        print(f"[EMAIL] {alert['message']}")
        # TODO: Implement actual email delivery
    
    def _deliver_voice(self, alert: Dict):
        """Deliver via voice call"""
        print(f"[VOICE] {alert['message']}")
        # TODO: Implement actual voice delivery
    
    def _deliver_log(self, alert: Dict):
        """Log alert"""
        print(f"[LOG] {json.dumps(alert, indent=2)}")

# Global alert handler
_alert_handler = None

def get_alert_handler():
    global _alert_handler
    if _alert_handler is None:
        _alert_handler = AlertHandler()
    return _alert_handler
EOF

python3 -m py_compile alert_handler.py
echo "Alert handler created"
```

**Success Criteria**: Alert system implemented and tested

---

## PHASE 5: Testing and Validation
**Duration: 3-4 Days | Status: COMPLETED**

### Step 5.1: Unit Testing
**Objective**: Test individual components

**Actions**:
```bash
# Create test suite
cat > test_suite.py << 'EOF'
"""
Comprehensive Test Suite for AI Digital Twin Prototype
"""

import pytest
from sensor_simulator import SensorSimulator, MultiMachineSimulator
from ai_agent import FaultDetector, RULEstimator, AIAgent
from data_service import DataService

class TestSensorSimulator:
    """Test sensor simulator"""
    
    def test_simulator_initialization(self):
        sim = SensorSimulator("M001", "normal")
        assert sim.machine_id == "M001"
        assert sim.fault_mode == "normal"
    
    def test_sensor_reading_generation(self):
        sim = SensorSimulator("M001", "normal")
        reading = sim.get_sensor_reading()
        
        assert "timestamp" in reading
        assert "vibration" in reading
        assert "temperature" in reading
        assert "current" in reading
        assert "status" in reading

class TestFaultDetector:
    """Test fault detection"""
    
    def test_normal_operation(self):
        detector = FaultDetector()
        reading = {
            "vibration": {"x": 0.3, "y": 0.4, "z": 0.2, "rms": 0.5},
            "temperature": 50.0,
            "current": 2.5
        }
        fault_type, issues = detector.detect_fault(reading)
        assert len(issues) == 0
    
    def test_critical_vibration(self):
        detector = FaultDetector()
        reading = {
            "vibration": {"x": 2.5, "y": 2.0, "z": 1.5, "rms": 3.5},
            "temperature": 50.0,
            "current": 2.5
        }
        fault_type, issues = detector.detect_fault(reading)
        assert any("Critical" in issue for issue in issues)

class TestRULEstimator:
    """Test RUL estimation"""
    
    def test_insufficient_data(self):
        estimator = RULEstimator()
        rul_info = estimator.estimate_rul("M001")
        assert rul_info["status"] == "Insufficient Data"

class TestAIAgent:
    """Test AI Agent"""
    
    def test_agent_initialization(self):
        agent = AIAgent()
        assert agent.fault_detector is not None
        assert agent.rul_estimator is not None
        assert agent.alert_generator is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
EOF

# Run tests
python3 -m pytest test_suite.py -v
```

**Success Criteria**: All unit tests passing

---

### Step 5.2: Integration Testing
**Objective**: Test component interactions

**Actions**:
```bash
# Create integration tests
cat > test_integration.py << 'EOF'
"""
Integration Tests for AI Digital Twin
"""

import pytest
import time
from data_service import get_data_service

class TestDataService:
    """Test data service integration"""
    
    def test_simulation_start_stop(self):
        service = get_data_service()
        
        # Start simulation
        service.start_simulation(interval=0.1)
        assert service.is_running == True
        
        # Wait for data
        time.sleep(1)
        
        # Check data collected
        summary = service.get_dashboard_summary()
        assert summary["total_machines"] > 0
        
        # Stop simulation
        service.stop_simulation()
        assert service.is_running == False
    
    def test_machine_status_retrieval(self):
        service = get_data_service()
        service.start_simulation(interval=0.1)
        
        time.sleep(1)
        
        status = service.get_machine_status("M001")
        assert status is not None
        assert "status" in status
        assert "rul_days" in status
        
        service.stop_simulation()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
EOF

# Run integration tests
python3 -m pytest test_integration.py -v
```

**Success Criteria**: All integration tests passing

---

### Step 5.3: Performance Testing
**Objective**: Verify system performance under load

**Actions**:
```bash
# Create performance test
cat > test_performance.py << 'EOF'
"""
Performance Tests for AI Digital Twin
"""

import time
import psutil
from ai_agent import AIAgent
from sensor_simulator import MultiMachineSimulator

def test_processing_latency():
    """Test processing latency"""
    agent = AIAgent()
    simulator = MultiMachineSimulator()
    
    latencies = []
    
    for _ in range(100):
        reading = simulator.get_machine_reading("M001")
        
        start = time.time()
        result = agent.process_reading(reading)
        latency = (time.time() - start) * 1000  # Convert to ms
        
        latencies.append(latency)
    
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    
    print(f"Average latency: {avg_latency:.2f}ms")
    print(f"Max latency: {max_latency:.2f}ms")
    
    assert avg_latency < 100, f"Average latency {avg_latency}ms exceeds 100ms"
    assert max_latency < 500, f"Max latency {max_latency}ms exceeds 500ms"

def test_memory_usage():
    """Test memory usage"""
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    simulator = MultiMachineSimulator()
    agent = AIAgent()
    
    for _ in range(1000):
        readings = simulator.get_all_readings()
        for reading in readings:
            agent.process_reading(reading)
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_growth = final_memory - initial_memory
    
    print(f"Memory growth: {memory_growth:.2f}MB")
    assert memory_growth < 100, f"Memory growth {memory_growth}MB exceeds 100MB"

if __name__ == "__main__":
    test_processing_latency()
    test_memory_usage()
    print("Performance tests passed!")
EOF

# Run performance tests
python3 test_performance.py
```

**Success Criteria**: Performance metrics within acceptable ranges

---

## PHASE 6: Deployment and Launch
**Duration: 2-3 Days | Status: COMPLETED**

### Step 6.1: Build Production Docker Image
**Objective**: Create containerized deployment

**Actions**:
```bash
# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python files
COPY sensor_simulator.py .
COPY ai_agent.py .
COPY data_service.py .
COPY backend_api.py .
COPY integrated_server.py .
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose ports
EXPOSE 8000 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run server
CMD ["python", "integrated_server.py"]
EOF

# Create requirements.txt
cat > requirements.txt << 'EOF'
numpy>=1.19.0
pandas>=1.1.0
scikit-learn>=0.23.0
fastapi>=0.63.0
uvicorn>=0.13.0
requests>=2.25.0
pyyaml>=5.3.0
python-dotenv>=0.15.0
psutil>=5.8.0
EOF

# Build Docker image
docker build -t ai-digital-twin:latest .
echo "Docker image built successfully"
```

**Success Criteria**: Docker image built and tested

---

### Step 6.2: Deploy to Production Environment
**Objective**: Deploy containerized application

**Actions**:
```bash
# Run Docker container
docker run -d \
  --name ai-digital-twin \
  -p 8000:8000 \
  -p 3000:3000 \
  -e LOG_LEVEL=INFO \
  -e SIMULATION_ENABLED=true \
  -v /var/log/ai-digital-twin:/app/logs \
  ai-digital-twin:latest

# Verify container is running
docker ps | grep ai-digital-twin
echo "Container deployed successfully"

# Check logs
docker logs ai-digital-twin
```

**Success Criteria**: Container running and accessible

---

### Step 6.3: Configure Monitoring and Logging
**Objective**: Set up production monitoring

**Actions**:
```bash
# Create monitoring script
cat > setup_monitoring.sh << 'EOF'
#!/bin/bash

# Create log directory
mkdir -p /var/log/ai-digital-twin
chmod 755 /var/log/ai-digital-twin

# Create log rotation config
cat > /etc/logrotate.d/ai-digital-twin << 'LOGROTATE'
/var/log/ai-digital-twin/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
}
LOGROTATE

# Create monitoring script
cat > /usr/local/bin/monitor-ai-digital-twin.sh << 'MONITOR'
#!/bin/bash

# Check if container is running
if ! docker ps | grep -q ai-digital-twin; then
    echo "Container is not running! Restarting..."
    docker start ai-digital-twin
fi

# Check API health
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "API health check failed! Restarting..."
    docker restart ai-digital-twin
fi

echo "Monitoring check passed at $(date)"
MONITOR

chmod +x /usr/local/bin/monitor-ai-digital-twin.sh

# Add to crontab
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/monitor-ai-digital-twin.sh") | crontab -

echo "Monitoring configured successfully"
EOF

chmod +x setup_monitoring.sh
./setup_monitoring.sh
```

**Success Criteria**: Monitoring and logging configured

---

## PHASE 7: Demonstration and Documentation
**Duration: 2-3 Days | Status: PARTIALLY COMPLETED**

### Step 7.1: Create Demonstration Scenarios
**Objective**: Prepare realistic demonstration scenarios

**Actions**:
```bash
# Create demo script
cat > demo_scenarios.py << 'EOF'
"""
Demonstration Scenarios for AI Digital Twin Prototype
"""

from sensor_simulator import MultiMachineSimulator
from ai_agent import AIAgent
from data_service import get_data_service
import time
import json

class DemoScenario:
    """Base demo scenario"""
    
    def __init__(self, name: str, duration: int = 60):
        self.name = name
        self.duration = duration
        self.simulator = MultiMachineSimulator()
        self.agent = AIAgent()
        self.service = get_data_service()
    
    def run(self):
        """Run demonstration"""
        print(f"\n{'='*60}")
        print(f"DEMO: {self.name}")
        print(f"{'='*60}\n")
        
        self.service.start_simulation(interval=1)
        
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < self.duration:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            
            # Get summary
            summary = self.service.get_dashboard_summary()
            
            # Print status
            print(f"Total Machines: {summary['total_machines']}")
            print(f"Status Distribution:")
            print(f"  Normal: {summary['machine_status_counts']['Normal']}")
            print(f"  Warning: {summary['machine_status_counts']['Warning']}")
            print(f"  Critical: {summary['machine_status_counts']['Critical']}")
            
            # Print alerts
            recent_alerts = self.service.get_recent_alerts(limit=3)
            if recent_alerts:
                print(f"\nRecent Alerts ({len(recent_alerts)}):")
                for alert in recent_alerts[-3:]:
                    print(f"  [{alert['severity']}] {alert['message']}")
            
            time.sleep(5)
        
        self.service.stop_simulation()
        print(f"\n{'='*60}")
        print(f"DEMO COMPLETED: {self.name}")
        print(f"{'='*60}\n")

class NormalOperationDemo(DemoScenario):
    """Demonstrate normal operation"""
    
    def __init__(self):
        super().__init__("Normal Operation", duration=30)

class FaultDetectionDemo(DemoScenario):
    """Demonstrate fault detection"""
    
    def __init__(self):
        super().__init__("Fault Detection", duration=60)
    
    def run(self):
        """Run fault detection demo"""
        print(f"\n{'='*60}")
        print(f"DEMO: {self.name}")
        print(f"{'='*60}\n")
        
        # Inject faults
        self.simulator.machines["M002"].fault_mode = "bearing_wear"
        self.simulator.machines["M003"].fault_mode = "misalignment"
        
        self.service.start_simulation(interval=1)
        
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < self.duration:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            
            summary = self.service.get_dashboard_summary()
            
            print(f"Status Distribution:")
            print(f"  Normal: {summary['machine_status_counts']['Normal']}")
            print(f"  Warning: {summary['machine_status_counts']['Warning']}")
            print(f"  Critical: {summary['machine_status_counts']['Critical']}")
            
            # Show machine details
            for machine in summary['machines']:
                if machine['status'] != 'Normal':
                    print(f"\n{machine['machine_info']['name']} ({machine['machine_id']}):")
                    print(f"  Status: {machine['status']}")
                    print(f"  Fault: {machine['fault_type']}")
                    print(f"  Issues: {', '.join(machine['detected_issues'])}")
                    print(f"  RUL: {machine['rul_days']} days")
            
            time.sleep(5)
        
        self.service.stop_simulation()
        print(f"\n{'='*60}")
        print(f"DEMO COMPLETED: {self.name}")
        print(f"{'='*60}\n")

class RULEstimationDemo(DemoScenario):
    """Demonstrate RUL estimation"""
    
    def __init__(self):
        super().__init__("RUL Estimation", duration=120)
    
    def run(self):
        """Run RUL estimation demo"""
        print(f"\n{'='*60}")
        print(f"DEMO: {self.name}")
        print(f"{'='*60}\n")
        
        # Inject degrading fault
        self.simulator.machines["M004"].fault_mode = "overheating"
        
        self.service.start_simulation(interval=1)
        
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < self.duration:
            iteration += 1
            
            if iteration % 10 == 0:  # Print every 10 iterations
                print(f"\n--- Iteration {iteration} ---")
                
                status = self.service.get_machine_status("M004")
                if status:
                    print(f"Machine: {status['machine_info']['name']}")
                    print(f"Status: {status['status']}")
                    print(f"RUL: {status['rul_days']} days")
                    print(f"Confidence: {status['rul_confidence']:.2%}")
                    print(f"Recommendation: {status['recommendation']}")
            
            time.sleep(1)
        
        self.service.stop_simulation()
        print(f"\n{'='*60}")
        print(f"DEMO COMPLETED: {self.name}")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    # Run demonstrations
    print("AI DIGITAL TWIN PROTOTYPE - DEMONSTRATION SUITE")
    print("=" * 60)
    
    # Demo 1: Normal Operation
    demo1 = NormalOperationDemo()
    demo1.run()
    
    # Demo 2: Fault Detection
    demo2 = FaultDetectionDemo()
    demo2.run()
    
    # Demo 3: RUL Estimation
    demo3 = RULEstimationDemo()
    demo3.run()
    
    print("\nAll demonstrations completed!")
EOF

# Run demo
python3 demo_scenarios.py
```

**Success Criteria**: All demonstration scenarios running successfully

---

### Step 7.2: Create User Documentation
**Objective**: Prepare documentation for operators and administrators

**Actions**:
```bash
# Create user guide
cat > USER_GUIDE.md << 'EOF'
# AI Digital Twin - User Guide

## Quick Start

### Accessing the Dashboard
1. Open browser and navigate to `http://localhost:3000`
2. You will see the home page with system overview
3. Click "Launch Dashboard" to access the monitoring interface

### Understanding the Dashboard

#### Machine Status Cards
- **Green (Normal)**: Machine operating normally
- **Yellow (Warning)**: Attention required, schedule maintenance
- **Red (Critical)**: Immediate action required, stop machine

#### Key Metrics
- **RUL (Remaining Useful Life)**: Days until predicted failure
- **Vibration**: Machine vibration level in mm/s
- **Temperature**: Operating temperature in °C
- **Current**: Electrical current draw in Amperes

### Interpreting Alerts

#### Alert Severity Levels
- **Critical**: Immediate action required
- **High**: Urgent attention needed
- **Medium**: Schedule maintenance soon
- **Low**: Informational

### Maintenance Recommendations

Follow the system's recommendations:
1. **RUL < 3 days**: Stop machine, perform emergency maintenance
2. **RUL 3-7 days**: Schedule maintenance within 3-7 days
3. **RUL > 7 days**: Monitor and plan preventive maintenance

## Troubleshooting

### Dashboard Not Loading
- Check internet connection
- Clear browser cache
- Try different browser

### Alerts Not Appearing
- Check alert settings
- Verify sensor connection
- Review system logs

## Support
For technical support, contact the system administrator.
EOF

# Create admin guide
cat > ADMIN_GUIDE.md << 'EOF'
# AI Digital Twin - Administrator Guide

## System Requirements
- Python 3.8+
- 8GB RAM minimum
- 32GB storage
- Linux OS (Ubuntu 20.04+)

## Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/your-org/ai-digital-twin.git
cd ai-digital-twin
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
pnpm install
```

### Step 3: Configure Environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Step 4: Start Services
```bash
# Start backend
python3 integrated_server.py &

# Start frontend (in another terminal)
cd client
pnpm dev
```

## Monitoring

### Check System Health
```bash
curl http://localhost:8000/health
```

### View Logs
```bash
tail -f logs/agent.log
```

### Monitor Performance
```bash
python3 test_performance.py
```

## Maintenance

### Daily Tasks
- Monitor dashboard for alerts
- Check system logs
- Verify data collection

### Weekly Tasks
- Backup data
- Review performance metrics
- Update models if needed

### Monthly Tasks
- Retrain models
- Update dependencies
- Security patches

## Troubleshooting

### High CPU Usage
```bash
# Check process
top -p $(pgrep -f ai-digital-twin)

# Restart service
systemctl restart ai-digital-twin
```

### Memory Issues
```bash
# Check memory
free -h

# Restart service
docker restart ai-digital-twin
```

## Support
For technical support, contact the development team.
EOF

echo "Documentation created"
```

**Success Criteria**: User and admin guides created

---

### Step 7.3: Create Demonstration Video Script
**Objective**: Prepare script for demonstration video

**Actions**:
```bash
# Create video script
cat > DEMO_VIDEO_SCRIPT.md << 'EOF'
# AI Digital Twin Prototype - Demonstration Video Script

## Scene 1: Introduction (0:00 - 1:00)
**Narration**: "Welcome to the AI Digital Twin Predictive Maintenance System. This prototype demonstrates how artificial intelligence can help MSMEs predict machinery failures before they occur, reducing downtime and maintenance costs."

**Visual**: Show home page with system overview

## Scene 2: Dashboard Overview (1:00 - 3:00)
**Narration**: "The dashboard provides real-time monitoring of all machinery. Each machine card shows its current status, fault type, and estimated remaining useful life."

**Visual**: 
- Show machine cards
- Highlight status indicators
- Point out RUL information

## Scene 3: Machine Details (3:00 - 5:00)
**Narration**: "Clicking on a machine shows detailed information including vibration trends, temperature patterns, and current draw. These metrics help identify specific fault types."

**Visual**:
- Click on a machine
- Show detailed metrics
- Display trend charts

## Scene 4: Alert System (5:00 - 7:00)
**Narration**: "The system generates intelligent alerts based on detected faults. Critical alerts require immediate action, while warnings allow for planned maintenance."

**Visual**:
- Show alert panel
- Highlight different severity levels
- Show alert messages

## Scene 5: Predictive Maintenance (7:00 - 9:00)
**Narration**: "The AI agent predicts remaining useful life using machine learning models trained on historical data. This allows operators to schedule maintenance proactively."

**Visual**:
- Show RUL predictions
- Display confidence scores
- Show maintenance recommendations

## Scene 6: Benefits (9:00 - 10:00)
**Narration**: "Key benefits include reduced downtime, optimized maintenance schedules, and lower operational costs. The system is designed for MSMEs with limited technical expertise."

**Visual**: Show summary of benefits

## Scene 7: Conclusion (10:00 - 11:00)
**Narration**: "The AI Digital Twin system brings enterprise-grade predictive maintenance to small and medium enterprises. Contact us to learn more."

**Visual**: Show contact information
EOF

echo "Demo video script created"
```

**Success Criteria**: Video script prepared

---

### Step 7.4: Final Verification Checklist
**Objective**: Verify all components are working

**Actions**:
```bash
# Create final verification script
cat > final_verification.sh << 'EOF'
#!/bin/bash

echo "AI Digital Twin Prototype - Final Verification"
echo "=============================================="

# Check Python modules
echo -e "\n1. Checking Python modules..."
python3 -c "import sensor_simulator, ai_agent, data_service; print('✓ All Python modules OK')" || echo "✗ Python modules failed"

# Check Node.js packages
echo -e "\n2. Checking Node.js packages..."
cd client
npm list react react-dom recharts > /dev/null 2>&1 && echo "✓ All Node.js packages OK" || echo "✗ Node.js packages failed"
cd ..

# Check configuration files
echo -e "\n3. Checking configuration files..."
[ -f .env ] && echo "✓ .env file exists" || echo "✗ .env file missing"
[ -f config/machines.json ] && echo "✓ machines.json exists" || echo "✗ machines.json missing"

# Test Python components
echo -e "\n4. Testing Python components..."
python3 -c "
from sensor_simulator import MultiMachineSimulator
from ai_agent import AIAgent

sim = MultiMachineSimulator()
agent = AIAgent()

readings = sim.get_all_readings()
for reading in readings:
    result = agent.process_reading(reading)
    
print('✓ Python components working')
" || echo "✗ Python components failed"

# Test backend API
echo -e "\n5. Testing backend API..."
python3 backend_api.py &
BACKEND_PID=$!
sleep 3

curl -s http://localhost:8000/health > /dev/null && echo "✓ Backend API responding" || echo "✗ Backend API failed"
kill $BACKEND_PID 2>/dev/null

# Test frontend build
echo -e "\n6. Testing frontend build..."
cd client
npm run build > /dev/null 2>&1 && echo "✓ Frontend builds successfully" || echo "✗ Frontend build failed"
cd ..

# Run tests
echo -e "\n7. Running test suite..."
python3 -m pytest test_suite.py -q > /dev/null 2>&1 && echo "✓ All tests passing" || echo "✗ Some tests failed"

echo -e "\n=============================================="
echo "Verification complete!"
EOF

chmod +x final_verification.sh
./final_verification.sh
```

**Success Criteria**: All components verified and working

---

## FINAL SUMMARY

### Completion Checklist

#### Phase 1: Foundation Setup ✓
- [x] Project structure verified
- [x] Dependencies installed
- [x] Environment configured

#### Phase 2: Backend Integration ✓
- [x] FastAPI server created (`backend_api.py`)
- [x] Data synchronization layer implemented (`data_sync.py`)
- [x] Backend tested (29 automated tests)

#### Phase 3: Frontend Development ✓
- [x] React app configured with Vite and TypeScript
- [x] Polling-based dashboard updates implemented
- [x] Dashboard components built

#### Phase 4: AI Agent Integration ✓
- [x] Backend-frontend integration via integrated server
- [x] AI pipeline tested across four machines
- [x] Alert system implemented with cooldown and localization

#### Phase 5: Testing and Validation ✓
- [x] Unit tests passing
- [x] Integration tests passing
- [x] Performance tests passed

#### Phase 6: Deployment and Launch ✓
- [x] Docker image built
- [x] Compose deployment with health check and restart policy
- [x] Linux host monitoring script created

#### Phase 7: Demonstration and Documentation (Partial)
- [x] Demo scenario classes created (`demo_scenarios.py`)
- [ ] Standalone user guide (USER_GUIDE.md) not yet written
- [ ] Standalone admin guide (ADMIN_GUIDE.md) not yet written
- [ ] Final verification script (`final_verification.sh`) not yet created
- [ ] Demonstration video not yet recorded

### Remaining Work

1. Write USER_GUIDE.md and ADMIN_GUIDE.md as standalone files
2. Create and run `final_verification.sh`
3. Record or script the demonstration video
4. Collect labeled field data for ML model training
5. Complete operator UAT and live provider testing

### Validated Metrics

| Metric | Result | Notes |
|---|---|---|
| Functionality | Rule-based detection, RUL, alerts working | Trained ML models are roadmap items |
| Processing latency | < 100 ms average | Verified by `test_performance.py` |
| Memory growth | < 100 MB over 4,000 readings | Verified by `test_performance.py` |
| Automated tests | 29 passing | As of June 21, 2026 |
| Fault detection accuracy (> 90%) | **Not yet validated** | Requires labeled field dataset |
| RUL MAPE (< 20%) | **Not yet validated** | Requires known-failure histories |
| Uptime (99.5%) | **Not yet validated** | Requires long-duration monitoring |

### Support and Resources

- **Verified Runbook**: See `AI Digital Twin Prototype - Quick Start Checklist.md`
- **Tests**: `python -m pytest test_suite.py test_integration.py test_ai_pipeline.py test_performance.py test_api.py -q`
- **Demo**: `python demo_scenarios.py`
- **API Docs**: `http://localhost:8000/docs`

---

**Last Updated**: June 21, 2026
**Status**: Prototype complete; trained ML, field validation, and operator UAT remain
**Automated Result**: 29 tests passed
