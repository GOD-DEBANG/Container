# Professional Pipelines & Execution Guide

This folder provides unified, production-grade scripts to start the server, generate datasets, and audit system diagnostics without path errors.

---

## 📁 Pipeline Overview

| File | Description | Command |
|---|---|---|
| [`start_server.py`](start_server.py) | Bootstraps `.env` & launches PULSE ASGI Server via Uvicorn | `python pipelines/start_server.py` |
| [`create_dataset.py`](create_dataset.py) | Synthesizes datasets, commits to Convex DB, outputs JSON & CSV | `python pipelines/create_dataset.py` |
| [`system_audit.py`](system_audit.py) | Runs diagnostics on Container & Server status | `python pipelines/system_audit.py` |

---

## 🚀 How to Run

> **Note:** Always run commands from the project root (`c:\Users\GOD.DEBANG\Desktop\Container`).

### 1. Start the Server
```powershell
.\.venv\Scripts\python.exe pipelines/start_server.py
```
* Runs the server at `http://127.0.0.1:8000` with live reload.
* Health Check: `http://127.0.0.1:8000/api/v1/health`
* Root Info: `http://127.0.0.1:8000/`

### 2. Generate a Dataset

**Fast preset (1,000 records):**
```powershell
.\.venv\Scripts\python.exe pipelines/create_dataset.py --name telemetry_v1 --records 1000
```

**Interactive mode (wizard prompts for inputs):**
```powershell
.\.venv\Scripts\python.exe pipelines/create_dataset.py -i
```

**Custom parameters:**
```powershell
.\.venv\Scripts\python.exe pipelines/create_dataset.py --name heavy_test --records 5000 --drift 0.10 --anomaly 0.08
```

### 3. Run System Diagnostic Audit
```powershell
.\.venv\Scripts\python.exe pipelines/system_audit.py
```
