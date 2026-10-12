# Vercel Runtime Constraints & Architectural Blueprint

**Verification Date:** October 12, 2026  
**Sources Verified:**
1. Vercel Functions Python Runtime: https://vercel.com/docs/functions/runtimes/python
2. Vercel Fluid Compute & Execution Limits: https://vercel.com/docs/functions/configuring-functions/duration
3. Vercel Streaming Responses & Payloads: https://vercel.com/docs/functions/streaming
4. Vercel File System & Ephemeral `/tmp`: https://vercel.com/docs/functions/limitations#filesystem-limitations
5. Vercel Pricing & Compute Limits: https://vercel.com/docs/plans

---

## 1. Verified Platform Capabilities and Limitations

### 1.1 Python Runtime & ASGI Entrypoint
- **Supported Versions:** Python 3.9, 3.10, 3.11, and 3.12 (managed via `.python-version` or `pyproject.toml`).
- **Entrypoint Discovery:** Vercel automatically detects top-level ASGI/WSGI applications exposed as `app` in standard files:
  - `api/index.py` (file-based routing default)
  - `app.py`, `server.py`, `main.py`, `asgi.py`
  - Explicit configuration via `pyproject.toml` (`[tool.vercel] entrypoint = "api.index:app"`) or `vercel.json`.
- **Packaging:** Standard bundle limit is 500 MB uncompressed (expandable to 5 GB with Large Functions flag `VERCEL_SUPPORT_LARGE_FUNCTIONS=1`). Dependencies are installed automatically from `requirements.txt` or `pyproject.toml`.

### 1.2 Fluid Compute & Resource Allocation
- **Hobby Plan:** Default allocation is 2 GB memory and 1 vCPU per function. Cannot be changed.
- **Pro & Enterprise Plans:** Default memory is 2 GB (1 vCPU), configurable up to 3 GB+ via Project Settings. Memory allocation directly scales allocated CPU share.
- **Concurrency & Re-use:** Fluid compute reuses execution instances across warm requests. However, cold starts can spin up new isolated microVMs without notice.

### 1.3 Execution Duration (Timeout)
- **Default Maximum:** 300 seconds (5 minutes) across all plans.
- **Configurable Maximum:** Up to 800 seconds on Pro/Enterprise.
- **Extended Duration (Beta):** Up to 1,800 seconds (30 minutes) on supported runtimes (including Python) via explicit `maxDuration` in `vercel.json` or function configuration.

### 1.4 Payload & Streaming Limits
- **Maximum Request Body:** 4.5 MB. Larger payloads fail with `413 FUNCTION_PAYLOAD_TOO_LARGE`.
- **Maximum Response Body:** 4.5 MB maximum aggregate response size through Vercel's edge network, even when chunked over Server-Sent Events (SSE) or streaming ASGI responses.
- **Streaming Support:** Supported via native ASGI streaming response body iterators.

### 1.5 Ephemeral Storage (`/tmp`)
- **Read-Only Root:** The entire container filesystem is strictly read-only except for `/tmp`.
- **Temporary Capacity:** `/tmp` is backed by ephemeral tmpfs/disk capped at 512 MB.
- **Non-Durable Lifetime:** Contents of `/tmp` survive only for the lifecycle of the single microVM instance. It is wiped on cold recreation and never shared across concurrent instances.

### 1.6 Background Execution Constraints
- **Termination on Completion:** Once the HTTP response finishes, the execution instance may be paused or terminated immediately.
- **Unreliable In-Process Daemons:** In-process background threads (such as `threading.Thread` or un-awaited asyncio tasks) will be frozen or terminated when the function invocation ends.
- **No Native Background Daemons:** Background daemon workers cannot run continuously inside serverless function instances.

---

## 2. Architectural Consequences for PULSE & Virtual Container

| Constraint | Architectural Decision | Implementation in Code |
| :--- | :--- | :--- |
| **4.5 MB Payload Limit** | Raw generated datasets must not be emitted as inline HTTP response bodies. Dataset output must be committed to object storage or streamed under chunked metadata. | Output committer writes to storage; API returns structured dataset manifest with chunk metadata and download URLs. |
| **512 MB `/tmp` Storage** | Inline container runs on Vercel must be strictly bounded in total size. | `ResourceAdmission` rejects inline generation jobs exceeding 256 MB (safety margin). Bounded streaming processing prevents filling disk. |
| **Max Duration (300s - 800s)** | Bounded inline execution requires deadline enforcement. Long-running jobs must not run inline. | `ExecutionPolicy` checks estimated job duration against deadline before admission. Large jobs require `DURABLE_WORKER` backend. |
| **No In-Memory Background Daemons** | No fake promises of "background processing" surviving invocation termination. | Clear separation of backends: `INLINE` (runs within active request duration), `DURABLE_WORKER` (submits to external queue), and `LOCAL` (CLI). |
| **Ephemeral Filesystem** | Datasets created in `/tmp` are wiped upon cleanup or instance freeze. | Container lifecycle cleans up temporary scratch chunks, and commits final verified artifacts to persistent storage adapter (S3 / Blob / local directory). |
| **Distributed Instances** | Replay protection and rate limiting cannot rely solely on in-process memory in multi-instance production. | Two-tier architecture: In-memory L1 LRU cache for intra-instance low-latency hits; pluggable Upstash Redis store for distributed synchronization. |

---

## 3. Safe Execution Policy Summary

1. **Inline Execution Mode (`INLINE`):**
   - Maximum dataset target size: 256 MB.
   - Maximum execution deadline: 120 seconds (well within the default 300s timeout).
   - Maximum peak RAM allocation: 512 MB.
2. **Durable Worker Mode (`DURABLE_WORKER`):**
   - For jobs exceeding 256 MB or 120 seconds.
   - Enqueues job metadata to a durable queue (e.g., Upstash QStash, SQS) and returns `202 Accepted` with a tracking URI.
3. **Local CLI Execution Mode (`LOCAL`):**
   - Unbounded resources up to the host machine's physical capabilities.
