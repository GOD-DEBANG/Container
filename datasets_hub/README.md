# Datasets Hub & Convex Dual-Persistence Engine

A scientific dataset ingestion, synthesis, output generation, and diagnostic system for the **Virtual Container (`vdc`)** and **Pulse Server**.

All datasets and status reports are persisted simultaneously in **JSON** and **CSV** formats within a database structure named **`convex`** (with automated local persistence and real-time cloud synchronization capabilities).

---

## 🏛️ Directory Architecture

```text
Container/datasets_hub/
├── convex_db/                      # Convex database client & storage schema
│   ├── __init__.py
│   ├── database_engine.py          # Dual JSON/CSV serializer & Convex cloud HTTP sync
│   └── schema.py                   # Formal scientific dataset & modality schemas
├── inputs/                         # Input handling & user parameter validation
│   ├── __init__.py
│   └── user_input_handler.py       # Interactive CLI prompts and programmatic dict parsers
├── outputs/                        # Formatted dataset serializers
│   ├── __init__.py
│   └── dataset_output_writer.py    # Formats tabular rows into dual JSON & CSV records
├── diagnostics/                    # Live health and telemetry probes
│   ├── __init__.py
│   └── status_checker.py           # Container & Server health diagnostics
├── data_store/
│   └── convex_records/             # Convex Database Tables
│       ├── json/                   # JSON document records
│       │   ├── synthesized_datasets/
│       │   └── system_status_logs/
│       └── csv/                    # Standard tabular CSV records
│           ├── synthesized_datasets/
│           └── system_status_logs/
├── cli.py                          # Unified CLI entrypoint
└── README.md                       # Documentation
```

---

## 🚀 How Any User Can Create Datasets

### 1. Interactive CLI Wizard
Users can launch the interactive step-by-step prompt:
```bash
python datasets_hub/cli.py generate --interactive
```

### 2. Scripted / Automated CLI Command
```bash
python datasets_hub/cli.py generate \
  --name my_experiment_data \
  --records 1000 \
  --modality numeric_telemetry \
  --drift 0.25 \
  --anomaly 0.08
```

### 3. Programmatic Python API
```python
from datasets_hub.inputs.user_input_handler import DatasetInputHandler
from datasets_hub.outputs.dataset_output_writer import DatasetOutputWriter
from ml.dataset.generator import AdaptiveDatasetSynthesizer

# 1. Parse user input
spec = DatasetInputHandler.create_spec_from_dict({
    "dataset_name": "lab_experiment_42",
    "target_records": 500,
    "drift_factor": 0.1,
    "anomaly_ratio": 0.05,
})

# 2. Synthesize data
synthesizer = AdaptiveDatasetSynthesizer()
X, y, meta = synthesizer.generate_synthetic_telemetry_batch(
    n_samples=spec.target_records,
    drift_factor=spec.drift_factor,
    anomaly_ratio=spec.anomaly_ratio,
)

# 3. Write outputs to Convex DB in JSON and CSV
writer = DatasetOutputWriter()
result = writer.process_and_persist(spec, X, y, meta["feature_names"])
print("JSON Path:", result["json_path"])
print("CSV Path: ", result["csv_path"])
```

---

## 🔍 Container & Server Status Audit

To run a live health check on the **Virtual Container** and **Pulse Server**, generating dual JSON and CSV audit records in the Convex database:

```bash
python datasets_hub/cli.py status
```

**Output example:**
- Virtual Container: `HEALTHY` (Latency ~150ms, Throughput ~1.8 MB/s)
- Pulse Server: `HEALTHY` (Router & L1 Cache functional)
- Audit saved to `datasets_hub/data_store/convex_records/json/system_status_logs/`
- Audit saved to `datasets_hub/data_store/convex_records/csv/system_status_logs/`
