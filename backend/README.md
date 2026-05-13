# Backend

FastAPI backend for AOJ Command OS.

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies:
   pip install -r requirements.txt
3. Start API server:
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

## API authentication (optional)

Authentication is disabled by default for backward compatibility.

Enable it with:

```bash
export AOJ_AUTH_ENABLED=true
export AOJ_API_KEYS="viewer-key:viewer,operator-key:operator,admin-key:admin"
```

Use either header:

- `Authorization: Bearer <key>`
- `X-API-Key: <key>`

Role policy (middleware-based):

- `GET/HEAD/OPTIONS` under `/api/**`: `viewer`+
- Mutating methods under `/api/**`: `operator`+
- `/api/update-center`, `/api/system-settings`, `/api/custom-admin`: `admin`

Health endpoint `/api/health` remains open.

## Request observability

All HTTP responses now include:

- `X-Request-ID`
- `X-Process-Time-ms`

Server logs are emitted as JSON lines and include `request_id` for request tracing.

## Database migrations (Alembic)

Alembic scaffold is available under `backend/alembic`.

```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

## Dependency lock workflow

Use pip-tools to refresh the backend lock file:

```bash
./scripts/lock_backend_requirements.sh
```

This updates `backend/requirements.lock.txt` from `backend/requirements.in`.

## LoRa hardware mode (dual SX1262 recommended)

The backend LoRa service supports 3 modes via environment variables:

- `LORA_MODE=mock` (default) - development loopback
- `LORA_MODE=serial-single` - one serial modem for TX+RX
- `LORA_MODE=serial-dual` - dedicated TX modem + dedicated RX modem

Recommended for two Waveshare Core1262 modules:

```bash
export LORA_MODE=serial-dual
export LORA_SERIAL_BAUDRATE=115200
export LORA_TX_SERIAL_PORT=/dev/ttyUSB0
export LORA_RX_SERIAL_PORT=/dev/ttyUSB1
export LORA_FALLBACK_TO_SINGLE=1
# optional override (default is RX port)
export LORA_SINGLE_FALLBACK_PORT=/dev/ttyUSB1
```

Then start the backend normally.

Health diagnostics are available at `/api/health` under the `lora` object,
including `effective_mode`, `fallback_in_use`, `tx_alive`, `rx_alive`,
`tx_count`, and `rx_count`.

Recent inbound frame traces are available at:

- `/api/system/lora/inbound-frames`
- `/api/system/lora/inbound-frames?device_id=BD-001&limit=50`
