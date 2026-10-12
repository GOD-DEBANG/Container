"""
src/pulse/app.py

PULSE ASGI 3.0 Application Assembly.
Combines CompiledRouter, Cell pipelines, State Fabric, and SSE streaming.
Compatible with Vercel serverless Python runtime and local Uvicorn.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict

from .config import PulseConfig, config as default_config
from .core.errors import (
    PulseError,
    JobNotFoundError,
)
from .core.pulse import Pulse
from .core.pipeline import Pipeline
from .core.router import CompiledRouter
from .core.registry import CellRegistry
from .security.tokens import TokenManager
from .security.replay_guard import ReplayGuard
from .fabric.store_interface import StoreInterface
from .fabric.memory_store import MemoryStore
from .fabric.upstash_redis_store import UpstashRedisStore
from .fabric.l1_cache import L1Cache
from .fabric.coalescing import RequestCoalescer
from .flow_control.backpressure import ConcurrencyLimiter
from .flow_control.admission import ServerAdmissionController
from .streams.sse import SSEStreamer
from .observability.logger import logger
from .observability.metrics import metrics
from .cells.auth_cell import AuthCell
from .cells.signature_cell import SignatureVerificationCell
from .cells.replay_cell import ReplayProtectionCell
from .cells.validation_cell import RequestValidationCell
from .cells.resource_policy_cell import ResourcePolicyCell
from .cells.job_creation_cell import JobCreationCell
from .cells.execution_dispatch_cell import ExecutionDispatchCell
from .cells.result_auth_cell import ResultAuthCell
from .cells.error_cell import ErrorNormalizationCell
from .cells.response_encoding_cell import ResponseEncodingCell
from vdc.services.dataset_generation_service import DatasetGenerationService


class PulseASGIApp:
    def __init__(self, config: PulseConfig = default_config) -> None:
        self.config = config
        self.token_manager = TokenManager(config.secret_key)
        self.replay_guard = ReplayGuard()
        self.l1_cache = L1Cache(capacity=2000, default_ttl_seconds=30.0)
        self.coalescer = RequestCoalescer()
        self.limiter = ConcurrencyLimiter(max_concurrent=32)

        # Storage & Fabric
        if config.redis_url:
            try:
                self.store: StoreInterface = UpstashRedisStore(config.redis_url)
            except Exception as e:
                logger.warning("Failed to connect to Upstash Redis; falling back to MemoryStore: %s", e)
                self.store = MemoryStore()
        else:
            self.store = MemoryStore()

        self.generation_service = DatasetGenerationService(config.storage_root)
        self.registry = CellRegistry()
        self.router = CompiledRouter()

        self._setup_cells()
        self._setup_routes()

    def _setup_cells(self) -> None:
        """Register and prewarm core pipeline cells."""
        self.registry.register("auth", lambda: AuthCell(self.token_manager), prewarm=True)
        self.registry.register("signature", lambda: SignatureVerificationCell(), prewarm=True)
        self.registry.register("replay", lambda: ReplayProtectionCell(self.replay_guard), prewarm=True)
        self.registry.register("validation", lambda: RequestValidationCell(), prewarm=True)
        self.registry.register("policy", lambda: ResourcePolicyCell(self.config.max_inline_dataset_bytes), prewarm=True)
        self.registry.register("job_create", lambda: JobCreationCell(self.store), prewarm=True)
        self.registry.register(
            "dispatch",
            lambda: ExecutionDispatchCell(self.store, self.generation_service, self.config.max_execution_duration_seconds),
            prewarm=True,
        )
        self.registry.register("result_auth", lambda: ResultAuthCell(self.store), prewarm=True)
        self.registry.register("error_norm", lambda: ErrorNormalizationCell(), prewarm=True)
        self.registry.register("response_enc", lambda: ResponseEncodingCell(), prewarm=True)

    def _setup_routes(self) -> None:
        """Compile deterministic routes table."""
        self.router.add_route("GET", "/", self._handle_root)
        self.router.add_route("GET", "/api/v1/health", self._handle_health)
        self.router.add_route("POST", "/api/v1/auth/token", self._handle_issue_token)
        self.router.add_route("POST", "/api/v1/jobs", self._handle_create_job)
        self.router.add_route("GET", "/api/v1/jobs/{job_id}", self._handle_get_job)
        self.router.add_route("GET", "/api/v1/jobs/{job_id}/stream", self._handle_stream_job)
        self.router.add_route("POST", "/api/v1/jobs/{job_id}/cancel", self._handle_cancel_job)
        self.router.add_route("GET", "/api/v1/jobs/{job_id}/download", self._handle_download_dataset)

    # --- HTTP Handlers ---

    async def _handle_root(self, pulse: Pulse, params: Dict[str, str]) -> Pulse:
        return Pulse.create(
            event_type="pulse_info",
            payload={
                "name": "PULSE Server",
                "version": "0.1.0",
                "description": "Vercel-compatible Server with Virtual Container Engine",
                "backend": self.config.backend,
            },
            request_id=pulse.request_id,
        )

    async def _handle_health(self, pulse: Pulse, params: Dict[str, str]) -> Pulse:
        return Pulse.create(
            event_type="pulse_health",
            payload={
                "status": "healthy",
                "timestamp_utc": time.time(),
                "metrics": metrics.get_summary(),
            },
            request_id=pulse.request_id,
        )

    async def _handle_issue_token(self, pulse: Pulse, params: Dict[str, str]) -> Pulse:
        subject = pulse.payload.get("subject", "demo_user")
        claims = pulse.payload.get("claims", {})
        ttl = pulse.payload.get("ttl_seconds", 3600)
        token = self.token_manager.issue_token(subject, claims=claims, ttl_seconds=ttl)
        return Pulse.create(
            event_type="pulse_token_issued",
            payload={"access_token": token, "token_type": "Bearer", "expires_in": ttl},
            request_id=pulse.request_id,
        )

    async def _handle_create_job(self, pulse: Pulse, params: Dict[str, str]) -> Pulse:
        # Build cell pipeline
        pipeline = Pipeline("CreateJobPipeline")
        pipeline.add_cell(self.registry.get_cell("auth"))

        # Optional signature verification
        if "signature_b64" in pulse.integrity_metadata:
            pipeline.add_cell(self.registry.get_cell("signature"))
        # Optional replay verification
        if "nonce" in pulse.integrity_metadata:
            pipeline.add_cell(self.registry.get_cell("replay"))

        pipeline.add_cell(self.registry.get_cell("validation"))
        pipeline.add_cell(self.registry.get_cell("policy"))
        pipeline.add_cell(self.registry.get_cell("job_create"))
        pipeline.add_cell(self.registry.get_cell("dispatch"))

        ctx = await pipeline.execute(pulse)
        if ctx.error:
            raise ctx.error

        final_job = ctx.state.get("final_job_data", {})
        job_id = ctx.state.get("job_id", "")
        return Pulse.create(
            event_type="pulse_job_accepted",
            payload={
                "job_id": job_id,
                "status": final_job.get("status", "ACCEPTED"),
                "details": final_job,
            },
            job_id=job_id,
            principal_id=ctx.current_pulse.principal_id,
            request_id=pulse.request_id,
        )

    async def _handle_get_job(self, pulse: Pulse, params: Dict[str, str]) -> Pulse:
        job_id = params["job_id"]

        # Request coalescing & L1 cache
        cached = self.l1_cache.get(f"job:{job_id}")
        if cached:
            return Pulse.create(
                event_type="pulse_job_status",
                payload=cached,
                job_id=job_id,
                request_id=pulse.request_id,
            )

        async def load_job() -> Dict[str, Any]:
            job_data = await self.store.get_job(job_id)
            if not job_data:
                raise JobNotFoundError(f"Job {job_id} not found")
            return job_data

        job_record = await self.coalescer.execute(f"get_job:{job_id}", load_job)
        self.l1_cache.set(f"job:{job_id}", job_record, ttl_seconds=10.0)

        return Pulse.create(
            event_type="pulse_job_status",
            payload=job_record,
            job_id=job_id,
            request_id=pulse.request_id,
        )

    async def _handle_cancel_job(self, pulse: Pulse, params: Dict[str, str]) -> Pulse:
        job_id = params["job_id"]
        job_data = await self.store.get_job(job_id)
        if not job_data:
            raise JobNotFoundError(f"Job {job_id} not found")

        job_data["status"] = "CANCELLED"
        job_data["updated_at_utc"] = time.time()
        await self.store.save_job(job_id, job_data)
        await self.store.append_event(
            job_id,
            {"event_type": "pulse_cancelled", "job_id": job_id, "timestamp": time.time()},
        )
        self.l1_cache.delete(f"job:{job_id}")

        return Pulse.create(
            event_type="pulse_job_cancelled",
            payload={"job_id": job_id, "status": "CANCELLED"},
            job_id=job_id,
            request_id=pulse.request_id,
        )

    async def _handle_download_dataset(self, pulse: Pulse, params: Dict[str, str]) -> Pulse:
        job_id = params["job_id"]
        job_data = await self.store.get_job(job_id)
        if not job_data:
            raise JobNotFoundError(f"Job {job_id} not found")

        if job_data.get("status") != "COMPLETED":
            raise PulseError("Dataset is not yet completed or generation failed", details={"status": job_data.get("status")})

        rel_path = job_data.get("storage_path")
        if not rel_path or not self.generation_service.persistent_storage_dir.joinpath(rel_path).exists():
            raise PulseError("Dataset file not found on storage")

        file_path = self.generation_service.persistent_storage_dir.joinpath(rel_path)
        size_bytes = file_path.stat().st_size

        return Pulse.create(
            event_type="pulse_download_meta",
            payload={
                "job_id": job_id,
                "dataset_id": job_data.get("dataset_id"),
                "file_path": str(file_path),
                "size_bytes": size_bytes,
                "checksum_sha256": job_data.get("checksum_sha256"),
            },
            job_id=job_id,
            request_id=pulse.request_id,
        )

    async def _handle_stream_job(self, pulse: Pulse, params: Dict[str, str]) -> Pulse:
        # Special marker for streaming
        return Pulse.create(
            event_type="pulse_stream_marker",
            payload={"job_id": params["job_id"]},
            job_id=params["job_id"],
            request_id=pulse.request_id,
        )

    # --- ASGI 3.0 Handler ---

    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope["type"] == "lifespan":
            # Handle ASGI lifespan
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return

        if scope["type"] != "http":
            return

        t_start = time.perf_counter()
        metrics.increment("http_requests_total")

        method = scope["method"]
        path = scope["path"]
        headers = {k.decode("latin1").lower(): v.decode("latin1") for k, v in scope.get("headers", [])}

        # Handle CORS Preflight
        if method == "OPTIONS":
            await self._send_cors_preflight(send)
            return

        # Receive body
        body_chunks = []
        while True:
            msg = await receive()
            body_chunks.append(msg.get("body", b""))
            if not msg.get("more_body", False):
                break
        raw_body = b"".join(body_chunks)

        # Enforce body size limit
        try:
            ServerAdmissionController.validate_request_body_size(len(raw_body))
        except PulseError as pe:
            metrics.increment("http_errors_total")
            await self._send_json_error(send, pe)
            return

        # Parse JSON payload if applicable
        payload: Dict[str, Any] = {}
        if raw_body and headers.get("content-type", "").startswith("application/json"):
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except Exception:
                await self._send_json_error(send, PulseError("Malformed JSON request body", details={"status_code": 400}))
                return

        # Build Pulse
        pulse = Pulse.create(
            event_type=f"http_{method.lower()}",
            payload=payload,
            integrity_metadata={
                "authorization": headers.get("authorization", ""),
                "signature_b64": headers.get("x-pulse-signature", ""),
                "public_key_b64": headers.get("x-pulse-public-key", ""),
                "nonce": headers.get("x-pulse-nonce", ""),
                "accept": headers.get("accept", ""),
            },
        )

        # Route matching
        try:
            async with self.limiter:
                handler, path_params = self.router.match(method, path)

                # Special SSE Streaming Route
                if path.endswith("/stream") and method == "GET":
                    last_event_id = 0
                    if "last-event-id" in headers:
                        try:
                            last_event_id = int(headers["last-event-id"])
                        except ValueError:
                            pass
                    await self._stream_sse_response(send, path_params["job_id"], last_event_id)
                    metrics.record_latency("http_request_duration", time.perf_counter() - t_start)
                    return

                # Normal Pulse pipeline dispatch
                response_pulse = await handler(pulse, path_params)
                
                # Check for binary download route
                if response_pulse.event_type == "pulse_download_meta":
                    await self._send_file_download(send, response_pulse.payload["file_path"])
                    metrics.record_latency("http_request_duration", time.perf_counter() - t_start)
                    return

                # Encode and reply
                await self._send_pulse_response(send, response_pulse, headers.get("accept", ""))
                metrics.record_latency("http_request_duration", time.perf_counter() - t_start)

        except PulseError as pe:
            metrics.increment("http_errors_total")
            await self._send_json_error(send, pe)
        except Exception as exc:
            metrics.increment("http_errors_total")
            logger.error("Unhandled ASGI error: %s", exc)
            await self._send_json_error(send, PulseError(f"Internal server error: {str(exc)}"))

    async def _send_pulse_response(self, send: Callable, pulse: Pulse, accept: str) -> None:
        use_msgpack = "application/msgpack" in accept
        data_dict = {
            "pulse_id": pulse.pulse_id,
            "request_id": pulse.request_id,
            "job_id": pulse.job_id,
            "event_type": pulse.event_type,
            "created_at_utc": pulse.created_at_utc,
            "payload": pulse.payload,
        }
        if use_msgpack:
            try:
                import msgpack
                body = msgpack.packb(data_dict, use_bin_type=True)
                content_type = "application/msgpack"
            except ImportError:
                body = json.dumps(data_dict).encode("utf-8")
                content_type = "application/json"
        else:
            body = json.dumps(data_dict).encode("utf-8")
            content_type = "application/json"

        headers = [
            (b"content-type", content_type.encode("latin1")),
            (b"content-length", str(len(body)).encode("latin1")),
            (b"access-control-allow-origin", b"*"),
            (b"x-content-type-options", b"nosniff"),
            (b"x-pulse-request-id", pulse.request_id.encode("latin1")),
        ]
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        await send({"type": "http.response.body", "body": body})

    async def _send_json_error(self, send: Callable, error: PulseError) -> None:
        status_code = getattr(error, "status_code", 500)
        err_body = json.dumps({
            "error": True,
            "status_code": status_code,
            "error_code": getattr(error, "error_code", "INTERNAL_ERROR"),
            "message": str(error.message if hasattr(error, "message") else error),
            "details": getattr(error, "details", {}),
        }).encode("utf-8")

        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(err_body)).encode("latin1")),
            (b"access-control-allow-origin", b"*"),
            (b"x-content-type-options", b"nosniff"),
        ]
        await send({"type": "http.response.start", "status": status_code, "headers": headers})
        await send({"type": "http.response.body", "body": err_body})

    async def _send_cors_preflight(self, send: Callable) -> None:
        headers = [
            (b"access-control-allow-origin", b"*"),
            (b"access-control-allow-methods", b"GET, POST, OPTIONS"),
            (b"access-control-allow-headers", b"Content-Type, Authorization, X-Pulse-Signature, X-Pulse-Public-Key, X-Pulse-Nonce, Last-Event-ID, Accept"),
            (b"content-length", b"0"),
        ]
        await send({"type": "http.response.start", "status": 204, "headers": headers})
        await send({"type": "http.response.body", "body": b""})

    async def _stream_sse_response(self, send: Callable, job_id: str, last_event_id: int) -> None:
        headers = [
            (b"content-type", b"text/event-stream"),
            (b"cache-control", b"no-cache"),
            (b"connection", b"keep-alive"),
            (b"access-control-allow-origin", b"*"),
            (b"x-accel-buffering", b"no"),
        ]
        await send({"type": "http.response.start", "status": 200, "headers": headers})

        stream = SSEStreamer.stream_job_events(
            job_id=job_id,
            store=self.store,
            last_event_id=last_event_id,
            poll_interval_seconds=0.1,
            heartbeat_interval_seconds=10.0,
            max_duration_seconds=self.config.max_execution_duration_seconds,
        )

        async for chunk in stream:
            await send({
                "type": "http.response.body",
                "body": chunk.encode("utf-8"),
                "more_body": True,
            })

        # Close stream
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def _send_file_download(self, send: Callable, file_path_str: str) -> None:
        from pathlib import Path

        p = Path(file_path_str)
        if not p.exists():
            await self._send_json_error(send, PulseError("File not found on server", details={"status_code": 404}))
            return

        file_size = p.stat().st_size
        headers = [
            (b"content-type", b"application/octet-stream"),
            (b"content-disposition", f'attachment; filename="{p.name}"'.encode("latin1")),
            (b"content-length", str(file_size).encode("latin1")),
            (b"access-control-allow-origin", b"*"),
        ]
        await send({"type": "http.response.start", "status": 200, "headers": headers})

        # Bounded streaming file response (64 KB chunks)
        with open(p, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                await send({"type": "http.response.body", "body": chunk, "more_body": True})

        await send({"type": "http.response.body", "body": b"", "more_body": False})


def create_pulse_app(config: PulseConfig = default_config) -> PulseASGIApp:
    return PulseASGIApp(config)


app = create_pulse_app()
