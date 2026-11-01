import pytest
import httpx
from pulse.app import create_pulse_app
from pulse.config import PulseConfig


@pytest.mark.asyncio
async def test_custom_dataset_and_ml_api_workflow(tmp_path):
    config = PulseConfig(
        env="test",
        host="127.0.0.1",
        port=8000,
        debug=True,
        secret_key=b"01234567890123456789012345678901",
        backend="INLINE",
        max_inline_dataset_bytes=10 * 1024 * 1024,
        max_execution_duration_seconds=30.0,
        storage_root=str(tmp_path / "storage"),
        redis_url=None,
    )
    app = create_pulse_app(config)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Generate Custom Dataset via HTTP
        gen_resp = await client.post(
            "/api/v1/datasets/generate",
            json={
                "dataset_name": "api_test_dataset",
                "target_records": 100,
                "modality": "numeric_telemetry",
                "drift_factor": 0.05,
                "anomaly_ratio": 0.05,
                "seed": 42,
            },
        )
        assert gen_resp.status_code == 200
        gen_data = gen_resp.json()["payload"]
        assert gen_data["records_generated"] == 100

        # 2. List Datasets
        list_resp = await client.get("/api/v1/datasets")
        assert list_resp.status_code == 200
        list_data = list_resp.json()["payload"]
        assert list_data["count"] >= 1

        # 3. Trigger ML Training over HTTP
        train_resp = await client.post(
            "/api/v1/ml/train",
            json={
                "dataset_name": "api_test_dataset",
                "epochs": 10,
                "learning_rate": 0.05,
            },
        )
        assert train_resp.status_code == 200
        train_data = train_resp.json()["payload"]
        assert train_data["final_accuracy"] > 0.80

        # 4. Trigger Realtime ML Inference over HTTP
        predict_resp = await client.post(
            "/api/v1/ml/predict",
            json={
                "dataset_name": "api_test_dataset",
                "features": [
                    [0.55, 0.60, 0.20, 0.10, 0.05],
                    [0.95, 0.90, 0.85, 2.50, 0.90], # Anomaly profile
                ],
            },
        )
        assert predict_resp.status_code == 200
        pred_data = predict_resp.json()["payload"]
        assert len(pred_data["predictions"]) == 2
        assert len(pred_data["probabilities"]) == 2

