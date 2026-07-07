# AI Digital Twin Prototype - Final Verification (PowerShell)
Write-Output "AI Digital Twin Prototype - Final Verification"
Write-Output "=============================================="

# Determine Python command
$PythonCmd = "python"
try {
    $null = Get-Command python3 -ErrorAction Stop
    $PythonCmd = "python3"
} catch {
    # python3 not found, fallback to python
}
Write-Output "Using Python command: $PythonCmd"

# Check Python modules
Write-Output "`n1. Checking Python modules..."
& $PythonCmd -c "import sensor_simulator, ai_agent, data_service; print('[PASS] All Python modules OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Output "[FAIL] Python modules failed to import"
    Exit 1
}

# Check Node.js packages
Write-Output "`n2. Checking Node.js packages..."
Push-Location client
try {
    # Check package-lock.json or package.json dependencies
    if (Test-Path package.json) {
        $PkgJson = Get-Content package.json | ConvertFrom-Json
        if ($PkgJson.dependencies.react -and $PkgJson.dependencies.recharts) {
            Write-Output "[PASS] All Node.js packages listed in package.json"
        } else {
            Write-Output "[FAIL] Missing dependencies in package.json"
        }
    } else {
        Write-Output "[FAIL] package.json not found in client directory"
    }
} finally {
    Pop-Location
}

# Check configuration files
Write-Output "`n3. Checking configuration files..."
if (Test-Path .env) {
    Write-Output "[PASS] .env file exists"
} else {
    Write-Output "[FAIL] .env file missing"
}
if (Test-Path config/machines.json) {
    Write-Output "[PASS] machines.json exists"
} else {
    Write-Output "[FAIL] machines.json missing"
}

# Test Python components
Write-Output "`n4. Testing Python components..."
& $PythonCmd -c "from sensor_simulator import MultiMachineSimulator; from ai_agent import AIAgent; sim = MultiMachineSimulator(); agent = AIAgent(); readings = sim.get_all_readings(); [agent.process_reading(r) for r in readings]; print('[PASS] Python components working')"
if ($LASTEXITCODE -ne 0) {
    Write-Output "[FAIL] Python components failed"
    Exit 1
}

# Test backend API
Write-Output "`n5. Testing backend API..."
$BackendProc = Start-Process $PythonCmd -ArgumentList "backend_api.py" -NoNewWindow -PassThru -ErrorAction SilentlyContinue
if (-not $BackendProc) {
    Write-Output "[FAIL] Failed to start backend API process"
} else {
    Start-Sleep -Seconds 3
    try {
        $Response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
        Write-Output "[PASS] Backend API responding: $($Response | ConvertTo-Json -Compress)"
    } catch {
        Write-Output "[FAIL] Backend API failed to respond: $_"
    } finally {
        # Terminate backend process
        Stop-Process -Id $BackendProc.Id -Force -ErrorAction SilentlyContinue
    }
}

# Test frontend build
Write-Output "`n6. Testing frontend build (using direct node execution to bypass ampersand path issue)..."
Push-Location client
& node node_modules/typescript/lib/tsc.js -b
$TscExit = $LASTEXITCODE
& node node_modules/vite/bin/vite.js build
$ViteExit = $LASTEXITCODE
Pop-Location

if ($TscExit -eq 0 -and $ViteExit -eq 0) {
    Write-Output "[PASS] Frontend builds successfully"
} else {
    Write-Output "[FAIL] Frontend build failed (tsc code: $TscExit, vite code: $ViteExit)"
}

# Run tests
Write-Output "`n7. Running test suite..."
& $PythonCmd -m pytest tests/ -q
if ($LASTEXITCODE -eq 0) {
    Write-Output "[PASS] All tests passing"
} else {
    Write-Output "[FAIL] Some tests failed"
}

Write-Output "`n=============================================="
Write-Output "Verification complete!"
