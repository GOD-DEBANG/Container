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
from .cells.adaptive_policy_cell import AdaptivePolicyCell
from .cells.result_auth_cell import ResultAuthCell
from .cells.error_cell import ErrorNormalizationCell
from .cells.response_encoding_cell import ResponseEncodingCell
from .ml.policy_model import PolicyModel
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
                logger.warning("Failed to connect to Upstash Redis; falling back to MemoryStore", error=str(e))
                self.store = MemoryStore()
        else:
            self.store = MemoryStore()

        self.generation_service = DatasetGenerationService(config.storage_root)
        self.policy_model = PolicyModel()   # shared, retrained by AdaptivePolicyCell
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
        self.registry.register(
            "adaptive_policy",
            lambda: AdaptivePolicyCell(self.store, self.policy_model),
            prewarm=True,
        )
        self.registry.register("policy", lambda: ResourcePolicyCell(self.config.max_inline_dataset_bytes, self.config.backend), prewarm=True)
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
        self.router.add_route("GET", "/dashboard", self._handle_dashboard)
        self.router.add_route("GET", "/api/v1/health", self._handle_health)
        self.router.add_route("POST", "/api/v1/auth/token", self._handle_issue_token)
        self.router.add_route("POST", "/api/v1/jobs", self._handle_create_job)
        self.router.add_route("GET", "/api/v1/jobs/{job_id}", self._handle_get_job)
        self.router.add_route("GET", "/api/v1/jobs/{job_id}/stream", self._handle_stream_job)
        self.router.add_route("POST", "/api/v1/jobs/{job_id}/cancel", self._handle_cancel_job)
        self.router.add_route("GET", "/api/v1/jobs/{job_id}/download", self._handle_download_dataset)
        # Custom Dataset Engine HTTP Endpoints
        self.router.add_route("POST", "/api/v1/datasets/generate", self._handle_custom_dataset_generate)
        self.router.add_route("GET", "/api/v1/datasets", self._handle_list_datasets)
        self.router.add_route("GET", "/api/v1/datasets/{name}/download", self._handle_download_custom_dataset)
        # Machine Learning Model HTTP Endpoints
        self.router.add_route("POST", "/api/v1/ml/train", self._handle_ml_train)
        self.router.add_route("POST", "/api/v1/ml/predict", self._handle_ml_predict)

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
                "adaptive_policy": {
                    "model_trained": self.policy_model.is_trained,
                    "training_samples": self.policy_model.n_samples,
                    "min_samples_required": 10,
                },
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
        pipeline.add_cell(self.registry.get_cell("adaptive_policy"))  # ML policy override
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

    async def _handle_custom_dataset_generate(self, pulse: Pulse, params: Dict[str, str]) -> Pulse:
        """Trigger multi-modality dataset synthesis directly over HTTP."""
        from datasets_hub.inputs.user_input_handler import DatasetInputHandler
        from datasets_hub.outputs.dataset_output_writer import DatasetOutputWriter
        from ml.dataset.generator import AdaptiveDatasetSynthesizer

        data = pulse.payload or {}
        spec = DatasetInputHandler.create_spec_from_dict(data)

        synthesizer = AdaptiveDatasetSynthesizer()
        X, y, meta = synthesizer.generate_by_modality(
            modality=spec.modality.value,
            n_samples=spec.target_records,
            drift_factor=spec.drift_factor,
            anomaly_ratio=spec.anomaly_ratio,
            seed=spec.seed,
        )

        writer = DatasetOutputWriter()
        result = writer.process_and_persist(
            spec=spec,
            features=X,
            labels=y,
            feature_names=meta.get("feature_names", []),
        )

        return Pulse.create(
            event_type="pulse_dataset_created",
            payload={
                "dataset_name": spec.dataset_name,
                "modality": spec.modality.value,
                "records_generated": spec.target_records,
                "csv_path": result["csv_path"],
                "json_path": result["json_path"],
                "download_url_csv": f"/api/v1/datasets/{spec.dataset_name}/download?format=csv",
                "download_url_json": f"/api/v1/datasets/{spec.dataset_name}/download?format=json",
                "convex_status": result["convex_status"],
                "metrics": meta.get("feature_statistics", {}),
                "preview": result["sample_preview"],
            },
            request_id=pulse.request_id,
        )

    async def _handle_list_datasets(self, pulse: Pulse, params: Dict[str, str]) -> Pulse:
        """Lists all synthesized datasets available in Convex and data store."""
        from pathlib import Path
        db_root = Path(__file__).resolve().parent.parent.parent.parent / "datasets_hub" / "data_store" / "convex_records"
        csv_dir = db_root / "csv" / "synthesized_datasets"

        datasets = []
        if csv_dir.exists():
            for item in csv_dir.glob("*.csv"):
                datasets.append({
                    "name": item.stem,
                    "size_bytes": item.stat().st_size,
                    "modified_utc": item.stat().st_mtime,
                    "download_csv": f"/api/v1/datasets/{item.stem}/download?format=csv",
                    "download_json": f"/api/v1/datasets/{item.stem}/download?format=json",
                })

        return Pulse.create(
            event_type="pulse_datasets_list",
            payload={"count": len(datasets), "datasets": datasets},
            request_id=pulse.request_id,
        )

    async def _handle_download_custom_dataset(self, pulse: Pulse, params: Dict[str, str]) -> Pulse:
        """Streams CSV or JSON dataset files for direct browser download."""
        from pathlib import Path
        name = params.get("name", "")
        # Check integrity metadata for format query param if provided
        db_root = Path(__file__).resolve().parent.parent.parent.parent / "datasets_hub" / "data_store" / "convex_records"

        # Check for CSV first
        csv_path = db_root / "csv" / "synthesized_datasets" / f"{name}.csv"
        json_path = db_root / "json" / "synthesized_datasets" / f"{name}.json"

        target_file = csv_path if csv_path.exists() else json_path
        if not target_file.exists():
            raise JobNotFoundError(f"Dataset '{name}' not found on server")

        return Pulse.create(
            event_type="pulse_download_meta",
            payload={
                "file_path": str(target_file),
                "size_bytes": target_file.stat().st_size,
            },
            request_id=pulse.request_id,
        )

    async def _handle_ml_train(self, pulse: Pulse, params: Dict[str, str]) -> Pulse:
        """Triggers ML model training on an existing dataset in Convex records."""
        from pipelines.train_model import train

        data = pulse.payload or {}
        dataset_name = data.get("dataset_name", "telemetry_production_v1")
        epochs = int(data.get("epochs", 20))
        lr = float(data.get("learning_rate", 0.05))
        hidden_dim = int(data.get("hidden_dim", 16))

        result = train(
            dataset_name=dataset_name,
            epochs=epochs,
            lr=lr,
            hidden_dim=hidden_dim,
        )

        return Pulse.create(
            event_type="pulse_ml_train_completed",
            payload={
                "dataset_name": dataset_name,
                "epochs": epochs,
                "learning_rate": lr,
                "weights_path": result["weights_path"],
                "scaler_path": result["scaler_path"],
                "final_accuracy": result["final_accuracy"],
                "final_val_loss": result["final_val_loss"],
            },
            request_id=pulse.request_id,
        )

    async def _handle_ml_predict(self, pulse: Pulse, params: Dict[str, str]) -> Pulse:
        """Runs fast neural inference using the latest trained model & scaler."""
        import numpy as np
        from pathlib import Path
        from ml.models.adaptive_classifier import AdaptiveClassifier

        data = pulse.payload or {}
        features_input = data.get("features", [])
        dataset_name = data.get("dataset_name", "telemetry_production_v1")

        if not features_input:
            raise PulseError("Missing 'features' list in request payload")

        artifacts_dir = Path(__file__).resolve().parent.parent.parent.parent / "ml" / "artifacts"
        weights_path = artifacts_dir / f"{dataset_name}_model_weights.npz"
        scaler_path = artifacts_dir / f"{dataset_name}_scaler.json"

        if not weights_path.exists() or not scaler_path.exists():
            raise PulseError(f"Trained model for '{dataset_name}' not found. Train the model first via /api/v1/ml/train")

        with open(scaler_path, "r", encoding="utf-8") as f:
            scaler = json.load(f)

        mean = np.array(scaler["mean"], dtype=np.float32)
        std = np.array(scaler["std"], dtype=np.float32)

        X = np.array(features_input, dtype=np.float32)
        if X.ndim == 1:
            X = np.expand_dims(X, axis=0)

        X_norm = (X - mean) / std
        model = AdaptiveClassifier.load(weights_path)
        probs, _ = model.forward(X_norm)
        predictions = np.argmax(probs, axis=1)

        return Pulse.create(
            event_type="pulse_ml_inference",
            payload={
                "predictions": predictions.tolist(),
                "probabilities": probs.tolist(),
                "feature_names": scaler.get("feature_names", []),
            },
            request_id=pulse.request_id,
        )

    async def _handle_dashboard(self, pulse: Pulse, params: Dict[str, str]) -> Pulse:
        """Returns the dashboard marker."""
        return Pulse.create(
            event_type="pulse_dashboard_html",
            payload={"dashboard": True},
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

                # Check for interactive Web Dashboard
                if response_pulse.event_type == "pulse_dashboard_html":
                    await self._send_html_dashboard(send)
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
            logger.error("Unhandled ASGI error", error=str(exc))
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

        # Stream file in 64 KB chunks
        chunk_size = 64 * 1024
        with open(p, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                await send({
                    "type": "http.response.body",
                    "body": chunk,
                    "more_body": True,
                })
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def _send_html_dashboard(self, send: Callable) -> None:
        html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PULSE Scientific Hub & Control Center</title>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090d16;
      --card-bg: rgba(18, 24, 38, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --accent: #6366f1;
      --accent-glow: rgba(99, 102, 241, 0.25);
      --accent-2: #06b6d4;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --success: #10b981;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: radial-gradient(circle at 15% 15%, #131b31 0%, var(--bg) 60%);
      color: var(--text);
      font-family: 'Outfit', sans-serif;
      min-height: 100vh;
      padding: 2rem;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 2.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--card-border);
    }
    .badge {
      display: inline-flex; align-items: center; gap: 0.5rem;
      padding: 0.35rem 0.85rem; border-radius: 999px;
      background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3);
      color: var(--success); font-size: 0.85rem; font-weight: 500;
    }
    .badge::before {
      content: ""; width: 8px; height: 8px; border-radius: 50%;
      background: var(--success); box-shadow: 0 0 8px var(--success);
    }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem; }
    @media (max-width: 860px) { .grid { grid-template-columns: 1fr; } }
    .card {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 1.75rem;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    .card h2 { font-size: 1.25rem; font-weight: 600; margin-bottom: 1rem; color: #fff; }
    label { display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.35rem; }
    input, select {
      width: 100%; background: #0f1523; border: 1px solid var(--card-border);
      padding: 0.75rem 1rem; border-radius: 10px; color: #fff;
      font-family: inherit; font-size: 0.95rem; margin-bottom: 1rem;
      outline: none; transition: border 0.2s, box-shadow 0.2s;
    }
    input:focus, select:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }
    .btn {
      width: 100%; background: linear-gradient(135deg, var(--accent), var(--accent-2));
      color: #fff; border: none; padding: 0.85rem; border-radius: 10px;
      font-weight: 600; font-size: 1rem; cursor: pointer;
      box-shadow: 0 4px 15px var(--accent-glow); transition: transform 0.15s, opacity 0.2s;
    }
    .btn:hover { opacity: 0.92; transform: translateY(-1px); }
    .btn:active { transform: translateY(0); }
    table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
    th, td { text-align: left; padding: 0.85rem; border-bottom: 1px solid var(--card-border); font-size: 0.9rem; }
    th { color: var(--text-muted); font-weight: 500; font-size: 0.8rem; text-transform: uppercase; }
    .link-btn {
      color: var(--accent-2); text-decoration: none; font-weight: 500; margin-right: 0.75rem;
      transition: color 0.15s;
    }
    .link-btn:hover { color: #fff; text-decoration: underline; }
    .code-box {
      background: #0b0f19; border: 1px solid var(--card-border); border-radius: 8px;
      padding: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
      color: #38bdf8; overflow-x: auto; max-height: 200px;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1 style="font-size: 1.8rem; font-weight: 700; letter-spacing: -0.5px;">PULSE Control Center</h1>
        <p style="color: var(--text-muted); font-size: 0.95rem;">Virtual Container Engine & Scientific Dataset Hub</p>
      </div>
      <div class="badge">SERVER HEALTHY</div>
    </header>

    <div class="grid">
      <!-- Dataset Generator Form -->
      <div class="card">
        <h2>⚡ Generate New Dataset</h2>
        <form id="genForm">
          <label>Dataset Name</label>
          <input type="text" id="name" placeholder="e.g. cluster_telemetry_v1" required>

          <label>Modality</label>
          <select id="modality">
            <option value="numeric_telemetry">Numeric Telemetry (CPU, memory, IO, latency)</option>
            <option value="container_execution_trace">Container Execution Trace (Chunks, heap, swap)</option>
            <option value="server_event_stream">Server Event Stream (Req/s, SSE, p99 ms)</option>
          </select>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div>
              <label>Record Count</label>
              <input type="number" id="records" value="1000" min="10" max="100000">
            </div>
            <div>
              <label>Anomaly Ratio (e.g. 0.05)</label>
              <input type="number" id="anomaly" value="0.05" step="0.01" min="0.001" max="0.5">
            </div>
          </div>

          <label>Drift Factor (0.0 to 1.0)</label>
          <input type="number" id="drift" value="0.05" step="0.01" min="0" max="1.0">

          <button type="submit" class="btn" id="genBtn">Synthesize Dataset</button>
        </form>
        <div id="genMsg" style="margin-top: 1rem; display: none;"></div>
      </div>

      <!-- Quick Server Info -->
      <div class="card">
        <h2>📊 Server Status & Live Links</h2>
        <div style="display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1.5rem;">
          <div style="display:flex; justify-content: space-between; padding-bottom: 0.5rem; border-bottom: 1px solid var(--card-border);">
            <span style="color: var(--text-muted);">Root API:</span>
            <a href="/" target="_blank" class="link-btn">GET /</a>
          </div>
          <div style="display:flex; justify-content: space-between; padding-bottom: 0.5rem; border-bottom: 1px solid var(--card-border);">
            <span style="color: var(--text-muted);">Health Check:</span>
            <a href="/api/v1/health" target="_blank" class="link-btn">GET /api/v1/health</a>
          </div>
          <div style="display:flex; justify-content: space-between; padding-bottom: 0.5rem; border-bottom: 1px solid var(--card-border);">
            <span style="color: var(--text-muted);">List Datasets API:</span>
            <a href="/api/v1/datasets" target="_blank" class="link-btn">GET /api/v1/datasets</a>
          </div>
        </div>
        <h3 style="font-size: 0.95rem; font-weight: 600; margin-bottom: 0.5rem;">Live CLI Command</h3>
        <div class="code-box">.\\.venv\\Scripts\\python.exe pipelines/create_dataset.py -i</div>
      </div>
    </div>

    <!-- Generated Datasets Table -->
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h2>📁 Stored Datasets (Convex & Local Store)</h2>
        <button onclick="fetchDatasets()" style="background: none; border: 1px solid var(--card-border); color: #fff; padding: 0.35rem 0.75rem; border-radius: 8px; cursor: pointer; font-size: 0.85rem;">🔄 Refresh</button>
      </div>
      <div style="overflow-x: auto;">
        <table id="datasetTable">
          <thead>
            <tr>
              <th>Dataset Name</th>
              <th>Size</th>
              <th>Downloads</th>
            </tr>
          </thead>
          <tbody id="datasetRows">
            <tr><td colspan="3" style="text-align: center; color: var(--text-muted);">Loading datasets...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    async function fetchDatasets() {
      try {
        const res = await fetch('/api/v1/datasets');
        const data = await res.json();
        const rows = document.getElementById('datasetRows');
        const list = data.payload?.datasets || [];
        if (!list.length) {
          rows.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">No datasets found. Create one above!</td></tr>';
          return;
        }
        rows.innerHTML = list.map(d => `
          <tr>
            <td style="font-weight: 500;">${d.name}</td>
            <td style="color: var(--text-muted);">${(d.size_bytes / 1024).toFixed(1)} KB</td>
            <td>
              <a class="link-btn" href="${d.download_csv}" download>📥 Download CSV</a>
              <a class="link-btn" href="${d.download_json}" download>📥 Download JSON</a>
            </td>
          </tr>
        `).join('');
      } catch (err) {
        console.error(err);
      }
    }

    document.getElementById('genForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = document.getElementById('genBtn');
      const msg = document.getElementById('genMsg');
      btn.disabled = true;
      btn.innerText = 'Synthesizing...';
      msg.style.display = 'none';

      try {
        const res = await fetch('/api/v1/datasets/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            dataset_name: document.getElementById('name').value,
            modality: document.getElementById('modality').value,
            target_records: parseInt(document.getElementById('records').value),
            anomaly_ratio: parseFloat(document.getElementById('anomaly').value),
            drift_factor: parseFloat(document.getElementById('drift').value),
          })
        });
        const result = await res.json();
        msg.style.display = 'block';
        if (result.payload?.records_generated) {
          msg.innerHTML = `<div style="background: rgba(16,185,129,0.15); border: 1px solid var(--success); color: var(--success); padding: 0.75rem; border-radius: 8px; font-size: 0.9rem;">
            Successfully generated <b>${result.payload.records_generated}</b> records for <b>${result.payload.dataset_name}</b>!
          </div>`;
          fetchDatasets();
        } else {
          msg.innerHTML = `<div style="color: #ef4444; font-size: 0.9rem;">Error generating dataset: ${result.message || 'Unknown error'}</div>`;
        }
      } catch (err) {
        msg.style.display = 'block';
        msg.innerHTML = `<div style="color: #ef4444; font-size: 0.9rem;">Failed: ${err.message}</div>`;
      } finally {
        btn.disabled = false;
        btn.innerText = 'Synthesize Dataset';
      }
    });

    fetchDatasets();
  </script>
</body>
</html>"""
        body = html.encode("utf-8")
        headers = [
            (b"content-type", b"text/html; charset=utf-8"),
            (b"content-length", str(len(body)).encode("latin1")),
            (b"access-control-allow-origin", b"*"),
        ]
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        await send({"type": "http.response.body", "body": body})


def create_pulse_app(config: PulseConfig = default_config) -> PulseASGIApp:
    return PulseASGIApp(config)


app = create_pulse_app()
