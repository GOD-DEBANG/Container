# PULSE Server — Deployment Guide

**Version:** 0.1.0  
**Target Platform:** Vercel (Python 3.12 Serverless)  
**Date:** October 2026

---

## 1. Prerequisites

| Tool | Minimum Version | Check |
|------|-----------------|-------|
| Python | 3.12 | `python --version` |
| pip | 24.0 | `pip --version` |
| Node.js | 18 | `node --version` (for Vercel CLI) |
| Vercel CLI | 34+ | `vercel --version` |
| Git | 2.40 | `git --version` |

---

## 2. Local Development

### 2.1 Install dependencies

```bash
cd Server/
pip install -r requirements.txt
pip install -e .          # installs src/pulse and src/vdc as editable packages
```

### 2.2 Configure environment

```bash
cp .env.example .env
# Edit .env and fill in real values:
#   PULSE_SECRET_KEY  — 32 random hex bytes
#   PULSE_ED25519_PRIVATE_KEY — Ed25519 private key (hex)
#   PULSE_ED25519_PUBLIC_KEY  — Ed25519 public key (hex)
```

Generate keys:
```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
key = Ed25519PrivateKey.generate()
priv = key.private_bytes_raw().hex()
pub  = key.public_key().public_bytes_raw().hex()
print(f"PULSE_ED25519_PRIVATE_KEY={priv}")
print(f"PULSE_ED25519_PUBLIC_KEY={pub}")
```

### 2.3 Run locally with Uvicorn

```bash
cd Server/
PYTHONPATH=src uvicorn pulse.app:app --host 127.0.0.1 --port 8000 --reload
```

The server will be reachable at `http://127.0.0.1:8000`.

### 2.4 Run tests

```bash
cd Server/
python -m pytest tests/ -v
```

Expected output: **44 passed** in ~1.5 s.

### 2.5 Run benchmarks

```bash
cd Server/
PYTHONPATH=src python scripts/run_benchmarks.py
```

---

## 3. Deploying to Vercel

### 3.1 One-time Vercel project setup

```bash
cd Server/
vercel login          # authenticate
vercel link           # link to existing project OR create new
```

When prompted:
- **Root directory**: `Server/` (or the directory containing `vercel.json`)
- **Framework**: Other
- **Build command**: *(leave empty)*
- **Output directory**: *(leave empty)*

### 3.2 Set environment variables (Vercel Dashboard or CLI)

**Required:**
```bash
vercel env add PULSE_SECRET_KEY production
vercel env add PULSE_ED25519_PRIVATE_KEY production
vercel env add PULSE_ED25519_PUBLIC_KEY production
```

**Optional (for durable storage):**
```bash
vercel env add UPSTASH_REDIS_URL production
vercel env add UPSTASH_REDIS_TOKEN production
```

> **Warning:** Never commit real secrets to `vercel.json` or `.env`.
> All secrets must be added via `vercel env` or the Vercel Dashboard.

### 3.3 Deploy

**Preview deployment (staging):**
```bash
vercel
```

**Production deployment:**
```bash
vercel --prod
```

Vercel will:
1. Detect `vercel.json` routing config
2. Build Python 3.12 runtime from `requirements.txt`
3. Set `api/index.py` as the serverless function entrypoint
4. Route all paths (`/(.*)`) to the ASGI handler

### 3.4 Verify deployment health

```bash
curl https://your-deployment.vercel.app/health
```

Expected response:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "production"
}
```

---

## 4. `vercel.json` Configuration Reference

```json
{
  "version": 2,
  "functions": {
    "api/index.py": {
      "maxDuration": 300,
      "memory": 2048
    }
  },
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

| Field | Value | Rationale |
|-------|-------|-----------|
| `maxDuration` | 300 s | Max Vercel Pro tier; covers large dataset generation jobs |
| `memory` | 2048 MB | Required for 10 MB+ dataset generation with headroom |
| Route | `(.*)` → `api/index.py` | All routes handled by the ASGI app router |

---

## 5. API Endpoint Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Health check |
| `POST` | `/token` | None | Issue Bearer token |
| `POST` | `/jobs` | Bearer | Submit dataset generation job |
| `GET` | `/jobs/{job_id}` | Bearer | Get job status/result |
| `GET` | `/jobs/{job_id}/stream` | Bearer | SSE progress stream |

### 5.1 Submit a Job

```bash
# 1. Get token
TOKEN=$(curl -s -X POST https://your-deployment.vercel.app/token \
  -H "Content-Type: application/json" \
  -d '{"tenant":"acme"}' | jq -r .token)

# 2. Submit job
curl -X POST https://your-deployment.vercel.app/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "target_size_bytes": 5242880,
    "chunk_size_bytes": 1048576,
    "subchunk_size_bytes": 262144,
    "policy": "balanced"
  }'
```

Response:
```json
{
  "job_id": "job_abc123",
  "status": "QUEUED"
}
```

### 5.2 Stream Progress (SSE)

```bash
curl -N https://your-deployment.vercel.app/jobs/job_abc123/stream \
  -H "Authorization: Bearer $TOKEN"
```

Events:
```
data: {"job_id":"job_abc123","progress":0.25,"status":"RUNNING"}
data: {"job_id":"job_abc123","progress":0.75,"status":"RUNNING"}
data: {"job_id":"job_abc123","progress":1.0,"status":"COMPLETED","checksum":"sha256:..."}
```

---

## 6. Vercel Operational Constraints Reference

| Constraint | Vercel Free | Vercel Pro | Impact |
|------------|-------------|------------|--------|
| Max duration | 60 s | 300 s | Large jobs need Pro |
| Memory | 1024 MB | Up to 3008 MB | Config uses 2048 MB |
| Request payload | 4.5 MB | 4.5 MB | Hard limit in app |
| Response payload | 4.5 MB | 4.5 MB | Large results use SSE |
| Ephemeral `/tmp` | 512 MB | 512 MB | Cleared per invocation |
| Concurrent executions | Unlimited | Unlimited | App-layer semaphore: 32 |
| Background threads | Must complete before response | Same | Scheduler deadline enforced |

---

## 7. Upstash Redis Setup (Optional, Recommended for Production)

1. Create account at [upstash.com](https://upstash.com)
2. Create a Redis database (free tier: 10,000 req/day)
3. Copy **REST URL** and **REST Token** from the dashboard
4. Add to Vercel:
   ```bash
   vercel env add UPSTASH_REDIS_URL production
   vercel env add UPSTASH_REDIS_TOKEN production
   ```

Without Upstash, the server falls back to `MemoryStore` (in-process dict).
**MemoryStore is NOT durable** — job state is lost between invocations.

---

## 8. Python Client Usage

```python
from clients.python_client import PulseClient

client = PulseClient(
    base_url="https://your-deployment.vercel.app",
    tenant="acme",
)

# Submit + stream
for event in client.submit_and_stream(
    target_size_bytes=10 * 1024 * 1024,
    policy="balanced",
):
    print(event)
```

## 9. JavaScript Client Usage

```javascript
import { PulseClient } from './clients/js_client.js';

const client = new PulseClient('https://your-deployment.vercel.app', 'acme');
await client.authenticate();

const job = await client.submitJob({ targetSizeBytes: 5 * 1024 * 1024 });
await client.streamProgress(job.job_id, (event) => console.log(event));
```

---

## 10. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError: pulse` | Missing PYTHONPATH | `api/index.py` inserts `src/` automatically |
| `403 Forbidden` on all routes | Missing Bearer token | Call `POST /token` first |
| `409 Conflict` on repeated request | Replay nonce collision | Use a unique nonce per request |
| Job stuck in `QUEUED` | Concurrency limit hit | Reduce concurrent requests or raise `maxDuration` |
| `500 Internal Server Error` | Unset `PULSE_SECRET_KEY` | Add env vars via `vercel env add` |
| SSE stream disconnects early | Vercel 300s limit reached | Split large jobs into smaller chunks |
