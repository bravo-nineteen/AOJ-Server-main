# Testing Guide for AOJ Command OS

## Local Development Testing

### Backend Unit Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api_smoke.py -v

# Run with coverage
pytest --cov=app tests/

# Run specific test
pytest tests/test_api_smoke.py::test_health_check -v
```

### Backend Smoke Tests

```bash
cd backend
python -m pytest tests/test_api_smoke.py -v

# Expected: All health checks pass
```

### Manual API Testing

#### Health Check
```bash
curl http://localhost:8000/api/health | jq .

# Expected response:
# {
#   "status": "ok",
#   "database": "connected",
#   "lora": {...}
# }
```

#### With API Documentation
```bash
# Open interactive Swagger UI
browser http://localhost:8000/docs

# Or ReDoc
browser http://localhost:8000/redoc

# Try endpoints directly from UI
```

### Frontend Tests

```bash
cd frontend

# (If vitest is installed)
npm run test

# Build test
npm run build

# Visual smoke test
npm run dev
# Visit http://localhost:5173
# Verify pages load without console errors
```

### Database Testing

```bash
cd backend

# Test database initialization
python -c "
from app.database import init_db, SessionLocal
from app import models

init_db()
db = SessionLocal()

# Verify migrations worked
tables = db.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall()
print(f'✓ Database has {len(tables)} tables')

db.close()
"

# Verify schema
sqlite3 aoj_command_os.db ".schema"
```

## Integration Testing

### WebSocket Connection Test

```python
# Create test_websocket.py
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/live"
    try:
        async with websockets.connect(uri) as websocket:
            # Receive initial message
            msg = await websocket.recv()
            print(f"✓ Received: {msg}")
            
            # Send echo
            await websocket.send(json.dumps({"test": "data"}))
            
            # Receive echo back
            response = await websocket.recv()
            print(f"✓ Echo received: {response}")
            
            # Simulate heartbeat
            for i in range(5):
                msg = await asyncio.wait_for(websocket.recv(), timeout=35)
                print(f"✓ Message {i+1}: {json.loads(msg)['event']}")
                
    except Exception as e:
        print(f"✗ WebSocket test failed: {e}")

asyncio.run(test_websocket())
```

Run it:
```bash
pip install websockets
python test_websocket.py
```

### API Response Validation Test

```javascript
// test_api_client.js
import api from './frontend/src/utils/apiClient.js';

// Test error handling
async function testErrorHandling() {
  try {
    console.log("Testing API client...");
    
    // This should fail (404)
    await api.get('/api/nonexistent');
  } catch (error) {
    console.log("✓ Error caught correctly:", {
      code: error.code,
      message: api.getErrorMessage(error)
    });
  }
}

testErrorHandling();
```

### LoRa Service Mock Test

```bash
# Set mock mode
export LORA_MODE=mock

# Start backend
python -m uvicorn app.main:app --reload

# Test LoRa endpoints
curl -X POST http://localhost:8000/api/lora/send \
  -H "Content-Type: application/json" \
  -d '{"device_id":"prop_001","command":"TEST","value":"1"}'
```

## Load & Performance Testing

### WebSocket Load Test

```python
# test_load_websockets.py
import asyncio
import websockets
import time

async def client():
    """Single WebSocket client"""
    try:
        async with websockets.connect("ws://localhost:8000/ws/live") as ws:
            await ws.recv()  # Initial message
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=60)
    except Exception as e:
        print(f"Client error: {e}")

async def load_test(num_connections=50):
    """Create multiple connections"""
    tasks = [client() for _ in range(num_connections)]
    
    start = time.time()
    await asyncio.gather(*tasks)
    elapsed = time.time() - start
    
    print(f"✓ {num_connections} connections lasted {elapsed:.2f}s")

# Run: 50 concurrent connections
asyncio.run(load_test(50))
```

### HTTP Endpoint Load Test

```bash
# Using Apache Bench
ab -n 1000 -c 100 http://localhost:8000/api/missions

# Or with curl loop
for i in {1..100}; do
  curl -s http://localhost:8000/api/health > /dev/null &
done
wait
echo "✓ 100 concurrent health checks completed"
```

### Database Query Performance

```python
import time
from app.database import SessionLocal
from app import models

db = SessionLocal()

# Time a mission query
start = time.time()
missions = db.query(models.Mission).all()
elapsed = time.time() - start

print(f"✓ Query {len(missions)} missions: {elapsed*1000:.2f}ms")

db.close()
```

## CI/CD Pipeline Testing

### Run GitHub Actions Locally

```bash
# Install act
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | bash

# Run CI pipeline
act push

# Run specific job
act -j backend
```

### Manual CI Steps

```bash
# 1. Linting
cd backend
ruff check app/

# 2. Type checking
mypy app/ --ignore-missing-imports

# 3. Test
pytest tests/

# 4. Frontend build
cd ../frontend
npm run build

# 5. Docker build
docker build -t aoj-test:latest .
```

## Docker Testing

### Container Health Check

```bash
# Build and run
docker build -t aoj-test:latest .
docker run --name aoj-test -p 8000:8000 aoj-test:latest

# In another terminal, check health
for i in {1..10}; do
  curl -s http://localhost:8000/api/health | jq .
  sleep 1
done
```

### Volume Mounting Test

```bash
# Run with local code mounted
docker run -it \
  -v $(pwd)/backend:/app/backend \
  -p 8000:8000 \
  aoj-test:latest

# Changes to backend files are reflected without rebuild
```

## Security Testing

### SQL Injection Test

```python
# Test database validation
from app.database import _is_valid_identifier

test_cases = [
    ("mission_id", True),
    ("user_123", True),
    ("_private", True),
    ("123invalid", False),
    ("field; DROP TABLE", False),
    ("field' OR '1'='1", False),
]

for name, expected in test_cases:
    result = _is_valid_identifier(name)
    status = "✓" if result == expected else "✗"
    print(f"{status} '{name}': {result}")
```

### XSS Test

```javascript
// Test frontend XSS prevention
// This should NOT render as HTML
const malicious = "<img src=x onerror='alert(1)'>";

// Your component should escape this
const safe = escapeHtml(malicious);
console.log("✓ XSS test:", safe);  // Should show HTML entities
```

### API Authentication Test

```bash
# With AUTH_ENABLED=true in .env
# Test without key
curl http://localhost:8000/api/missions
# Should get 401

# Test with key
curl -H "X-API-Key: prod-key-1" http://localhost:8000/api/missions
# Should work
```

## Regression Testing

### Before Each Release

1. **Core Workflow**
   - [ ] Create mission
   - [ ] Start game
   - [ ] Update scores
   - [ ] End game
   - [ ] View results

2. **AI Assistant**
   - [ ] Load conversation
   - [ ] Send message
   - [ ] Receive response
   - [ ] Clear history

3. **WebSocket Updates**
   - [ ] Connect multiple clients
   - [ ] Verify all receive updates
   - [ ] Check heartbeat messages

4. **Props Network**
   - [ ] Register mock prop
   - [ ] Send command
   - [ ] Check status update
   - [ ] View history

5. **System Health**
   - [ ] Check database status
   - [ ] Verify LoRa service
   - [ ] Monitor logs
   - [ ] Check CPU/Memory

## Test Data

### Seed Test Database

```python
# backend/tests/fixtures.py
from app.database import SessionLocal
from app import models

def seed_test_data():
    db = SessionLocal()
    
    # Create test mission
    mission = models.Mission(
        title="Test Mission",
        description="For testing",
        status=models.MissionStatus.planned
    )
    db.add(mission)
    db.commit()
    
    db.close()
    return mission.id
```

Use in tests:
```python
def test_mission_creation():
    mission_id = seed_test_data()
    assert mission_id > 0
```

## Coverage Reports

```bash
# Generate coverage report
pytest --cov=app tests/ --cov-report=html

# View report
open htmlcov/index.html

# Target: 80%+ coverage for critical paths
```

## Continuous Testing

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
set -e

echo "Running tests..."
pytest backend/tests/ -q

echo "Linting..."
ruff check backend/app/

echo "✓ All checks passed"
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

**Testing Checklist Before Release:**
- [ ] All unit tests pass
- [ ] Integration tests complete
- [ ] Load test handles 50+ concurrent connections
- [ ] Security tests verify XSS/SQL injection prevention
- [ ] WebSocket stays stable for extended sessions
- [ ] Docker build successful
- [ ] CI/CD pipeline green
- [ ] No critical console errors
- [ ] Response times acceptable (<500ms)
- [ ] Database backups working

---

**Last Updated:** May 12, 2026
