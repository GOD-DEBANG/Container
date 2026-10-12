# PULSE Server + Virtual Container Engine — Architecture

**Version:** 0.1.0  
**Date:** October 2026  

---

## 1. System Overview

PULSE is a two-subsystem Python server designed for Vercel serverless deployment
without Docker. Both subsystems share a single deployed unit rooted at `api/index.py`.

```
┌──────────────────────────────────────────────────────────────┐
│                        VERCEL EDGE                           │
│                  api/index.py  (entrypoint)                  │
│                         │                                    │
│          ┌──────────────┴──────────────┐                     │
│          │     Subsystem A — PULSE     │                     │
│          │  ASGI 3.0 + Cell Pipeline   │                     │
│          │  Compiled Router + Fabric   │                     │
│          └──────────────┬──────────────┘                     │
│                         │ calls                              │
│          ┌──────────────┴──────────────┐                     │
│          │  Subsystem B — VDC Engine   │                     │
│          │  Hierarchical Layer Stack   │                     │
│          │  Mathematics + Execution    │                     │
│          └─────────────────────────────┘                     │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Project Directory Layout

```
Server/
├── api/
│   └── index.py              # Vercel entrypoint — exposes `app`
├── src/
│   ├── pulse/                # Subsystem A: PULSE ASGI server
│   │   ├── app.py            # PulseASGIApp assembly
│   │   ├── config.py         # PulseConfig (env-sourced settings)
│   │   ├── core/
│   │   │   ├── pulse.py      # Pulse object (middleware orchestrator)
│   │   │   ├── pipeline.py   # Cell pipeline (sequential composition)
│   │   │   ├── router.py     # CompiledRouter (radix trie)
│   │   │   ├── registry.py   # CellRegistry
│   │   │   └── errors.py     # Domain exception hierarchy
│   │   ├── cells/            # Processing cells (12 total)
│   │   │   ├── auth_cell.py
│   │   │   ├── signature_cell.py
│   │   │   ├── replay_cell.py
│   │   │   ├── validation_cell.py
│   │   │   ├── resource_policy_cell.py
│   │   │   ├── job_creation_cell.py
│   │   │   ├── execution_dispatch_cell.py
│   │   │   ├── result_auth_cell.py
│   │   │   ├── progress_cell.py
│   │   │   ├── error_cell.py
│   │   │   ├── response_encoding_cell.py
│   │   │   └── signature_cell.py
│   │   ├── security/
│   │   │   ├── crypto.py       # Ed25519, X25519, AES-256-GCM
│   │   │   ├── tokens.py       # HMAC-SHA256 bearer tokens
│   │   │   ├── replay_guard.py # Sliding-window nonce deduplication
│   │   │   └── envelope.py     # Hybrid encryption envelope
│   │   ├── fabric/
│   │   │   ├── store_interface.py    # Abstract StoreInterface
│   │   │   ├── memory_store.py       # In-process dict store (dev/test)
│   │   │   ├── upstash_redis_store.py# HTTP-based Upstash Redis (prod)
│   │   │   ├── l1_cache.py           # LRU+TTL local cache
│   │   │   └── coalescing.py         # SingleFlight request coalescer
│   │   ├── streams/
│   │   │   ├── sse.py          # SSE streaming (chunked ASGI)
│   │   │   ├── delta_encoder.py# Delta-diff event encoder
│   │   │   └── event_buffer.py # Fixed-capacity ring buffer
│   │   ├── flow_control/
│   │   │   ├── admission.py    # Server-level admission controller
│   │   │   └── backpressure.py # Semaphore-based concurrency limiter
│   │   └── observability/
│   │       ├── logger.py       # Structured JSON logger
│   │       ├── metrics.py      # In-process atomic metric counters
│   │       └── tracer.py       # Span/trace context
│   └── vdc/                  # Subsystem B: Virtual Container Engine
│       ├── mathematics/        # Pure, side-effect-free math
│       │   ├── dataset_size.py
│       │   ├── allocation_formula.py
│       │   ├── throughput_formula.py
│       │   ├── progress_integrator.py
│       │   └── completion_formula.py
│       ├── models/             # Pydantic data models
│       ├── container_core/     # VirtualContainer lifecycle
│       ├── resource_engine/    # Budget, monitor, admission, enforcer
│       ├── layer1_hierarchical/# Chunk + subchunk allocation
│       ├── layer2_processing/  # Streaming worker manager + queue
│       ├── layer3_reconstruction/# Dataset rebuild + integrity
│       ├── execution/          # Adaptive scheduler + backend
│       ├── storage/            # Ephemeral + persistent storage
│       └── services/           # DatasetGenerationService (facade)
├── tests/
│   ├── unit/                 # 21 pure unit tests
│   ├── integration/          # 1 end-to-end ASGI integration test
│   ├── security/             # 2 threat-model tests
│   └── vdc/                  # 21 VDC subsystem tests
├── bench/
│   └── benchmark.py          # 6-section benchmark runner
├── clients/
│   ├── python_client.py      # Python SDK with streaming support
│   └── js_client.js          # JavaScript/Node SDK
├── docs/
│   ├── VERCEL_CONSTRAINTS.md
│   ├── ARCHITECTURE.md       # This file
│   ├── THREAT_MODEL.md
│   ├── DEPLOYMENT.md
│   └── BENCHMARK_RESULTS.md
├── examples/
│   └── console_output.py     # Terminal demo adapter
├── scripts/
│   └── run_benchmarks.py     # Human-readable benchmark runner
├── api/index.py              # Vercel entrypoint
├── vercel.json
├── requirements.txt
├── pyproject.toml
├── .python-version           # 3.12
└── .env.example
```

---

## 3. Subsystem A — PULSE ASGI Server

### 3.1 Request Lifecycle

Every inbound HTTP request passes through an ordered Cell pipeline:

```
HTTP Request
    │
    ▼
[AuthCell]              → Validates Bearer token signature
    │
    ▼
[SignatureVerificationCell] → Ed25519 request body signature
    │
    ▼
[ReplayProtectionCell]  → Sliding-window nonce check
    │
    ▼
[RequestValidationCell] → Pydantic schema validation
    │
    ▼
[ResourcePolicyCell]    → Per-request resource budget enforcement
    │
    ▼
[JobCreationCell]       → Allocates VirtualContainer + job record
    │
    ▼
[ExecutionDispatchCell] → Calls DatasetGenerationService
    │
    ▼
[ResultAuthCell]        → Ed25519 signs response payload
    │
    ▼
[ResponseEncodingCell]  → msgpack or JSON serialization
    │
    ▼
HTTP Response / SSE Stream
```

### 3.2 CompiledRouter

The router compiles routes at startup into a radix-trie structure. At match time, no
string-format operations occur — only trie traversal. Measured p50 = 0.001 ms,
p99 = 0.003 ms at >700,000 matches/sec.

### 3.3 State Fabric

| Layer      | Implementation         | Scope             |
|------------|------------------------|-------------------|
| L1 Cache   | LRU + TTL dict         | In-process (warm) |
| L2 Store   | MemoryStore (dev)      | In-process        |
| L2 Store   | UpstashRedisStore (prod)| HTTP REST → Redis |

The `StoreInterface` abstract base ensures swappable backends without coupling.

### 3.4 Streaming (SSE)

Long-running jobs emit Server-Sent Events (SSE) over chunked ASGI transfer.
Delta encoding compresses repeated fields to only transmit changed values.
The `EventBuffer` is a fixed-capacity ring that never allocates unbounded memory.

---

## 4. Subsystem B — Virtual Container Dataset Generation Engine

### 4.1 Layer Stack

```
DatasetGenerationService (facade)
    │
    ├── VirtualContainer (container_core)
    │       └── Lifecycle: CREATED → ALLOCATED → RUNNING → COMPLETED/FAILED
    │
    ├── Layer 1 — Hierarchical Allocation (layer1_hierarchical)
    │       ├── AllocationManager  → computes weighted sub-budgets
    │       ├── ChunkCreator       → produces ChunkModel records
    │       └── SubchunkCreator    → subdivides each chunk
    │
    ├── Layer 2 — Streaming Processing (layer2_processing)
    │       ├── BoundedQueue       → back-pressure bounded FIFO
    │       ├── WorkerManager      → spawns thread-pool workers
    │       └── Processor          → per-chunk data generation
    │
    ├── Layer 3 — Reconstruction (layer3_reconstruction)
    │       ├── DatasetRebuilder   → assembles chunk outputs
    │       ├── IntegrityValidator → SHA-256 + count verification
    │       └── OutputCommitter    → writes to storage
    │
    └── ResourceEngine (resource_engine)
            ├── ResourceBudget     → per-container limits
            ├── ResourceMonitor    → psutil-based live tracking
            ├── ResourceAdmission  → pre-flight admission control
            └── ResourceEnforcer   → mid-execution enforcement
```

### 4.2 Mathematics Package

All formulas are pure functions with no I/O or state — importable without side-effects.

| Module                 | Functions                                              |
|------------------------|--------------------------------------------------------|
| `dataset_size.py`      | `estimate_dataset_size`, `calculate_actual_size`       |
| `allocation_formula.py`| `hierarchical_allocation`, `weighted_allocation`       |
| `throughput_formula.py`| `calculate_effective_throughput`, `calculate_measured_throughput` |
| `progress_integrator.py`| `integrate_variable_throughput`, `calculate_remaining_bytes`, `calculate_progress_ratio` |
| `completion_formula.py`| `validate_completion`                                  |

### 4.3 Execution Policies

```python
class ExecutionPolicy(str, Enum):
    FAST      = "fast"      # Max parallelism, higher resource usage
    BALANCED  = "balanced"  # Default: balanced CPU and memory use
    EFFICIENT = "efficient" # Low parallelism, minimal resource use
```

---

## 5. Vercel Deployment Architecture

```
Browser / API Client
        │
        ▼
  Vercel Edge Network
        │
        ▼
  api/index.py  ← Python 3.12 Serverless Function
  (ASGI app)    ← max 300s duration, 2048 MB memory
        │
        ├── Handles: /health, /token, /jobs, /jobs/{id}, /jobs/{id}/stream
        │
        └── Calls VDC Engine (in-process, same lambda invocation)
                │
                └── Persists datasets to /tmp (ephemeral, within invocation)
                    or Upstash Redis (durable, cross-invocation)
```

**Critical Vercel constraints honoured:**
- No background threads that outlive the request handler
- No persistent open file handles across invocations
- `/tmp` (512 MB) used only for ephemeral per-invocation storage
- All state requiring durability is delegated to Upstash Redis via HTTP

---

## 6. ASGI 3.0 Conformance

The `PulseASGIApp.__call__` signature:
```python
async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None
```

- `scope["type"] == "http"` → handled by full cell pipeline
- `scope["type"] == "lifespan"` → handled by startup/shutdown hooks
- All other scope types → immediately closed

The entrypoint exports the bare `app` symbol, which Vercel discovers by introspecting
`api/index.py` for a callable named `app`.

---

## 7. Testing Architecture

| Layer       | File                              | Tests | Approach                      |
|-------------|-----------------------------------|-------|-------------------------------|
| Unit        | `test_crypto_security.py`         | 11    | Direct function/class testing |
| Unit        | `test_fabric_streams.py`          | 6     | Async event-loop tests        |
| Unit        | `test_router.py`                  | 5     | Route matching assertions     |
| Integration | `test_e2e_server.py`              | 1     | Full ASGI lifecycle test      |
| Security    | `test_security_threats.py`        | 2     | Threat-model adversarial tests|
| VDC         | `test_mathematics.py`             | 16    | Formula property tests        |
| VDC         | `test_container.py`               | 3     | Container lifecycle tests     |
| VDC         | `test_scheduler.py`               | 3     | Scheduler execution tests     |
| **Total**   |                                   | **44**| All passing in 1.4 s          |
