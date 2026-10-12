# PULSE Server — Threat Model

**Version:** 0.1.0  
**Classification:** Internal Engineering  
**Date:** October 2026  

---

## 1. Scope

This document covers the attack surface of the PULSE server and Virtual Container
Engine when deployed on Vercel. It enumerates threat actors, assets, attack vectors,
mitigations, and residual risks.

---

## 2. Assets

| Asset                    | Sensitivity | Location           |
|--------------------------|-------------|--------------------|
| Secret key (`PULSE_SECRET_KEY`) | Critical | Environment variable (Vercel) |
| Ed25519 signing keypair  | Critical    | Environment variable |
| Bearer tokens            | High        | HTTP Authorization header |
| Job payloads             | Medium      | Request body / Redis |
| Dataset output           | Medium      | `/tmp` or Redis |
| Execution metrics        | Low         | Redis / SSE stream |

---

## 3. Trust Boundary Diagram

```
[Internet]
    │
    ▼ HTTPS (TLS by Vercel edge)
[Vercel Edge / CDN]
    │
    ▼ Internal routing
[api/index.py — Python Serverless Function]
    │  ← TRUST BOUNDARY: all inputs treated as untrusted
    ├── Auth Cell: validates Bearer token
    ├── Signature Cell: verifies Ed25519 body signature
    ├── Replay Guard: checks nonce window
    ├── Validation Cell: validates schema
    ▼
[VDC Engine — in-process, same trust domain]
    │
    ▼
[Upstash Redis] ← External service, authenticated via HTTPS + token
```

---

## 4. Threat Catalogue (STRIDE)

### 4.1 Spoofing

| ID    | Threat                              | Mitigation                                | Test |
|-------|-------------------------------------|-------------------------------------------|------|
| S-01  | Forged Bearer token                 | HMAC-SHA256 with 32-byte secret; constant-time compare | `test_tampered_token_signature` |
| S-02  | Forged request body signature       | Ed25519 request signature in `X-Pulse-Signature` header | `test_ed25519_sign_verify_and_tamper` |
| S-03  | Cross-tenant job result retrieval   | Job IDs scoped to authenticated token tenant | `test_cross_tenant_job_access_prevention` |

### 4.2 Tampering

| ID    | Threat                              | Mitigation                                | Test |
|-------|-------------------------------------|-------------------------------------------|------|
| T-01  | Request body modification in transit| Ed25519 signature covers raw body bytes   | `test_ed25519_sign_verify_and_tamper` |
| T-02  | Response payload tampering          | Ed25519 response signature in `X-Pulse-Result-Signature` | `test_e2e_pulse_server_workflow` |
| T-03  | Dataset output corruption           | SHA-256 checksum verified post-generation | `test_container_end_to_end_lifecycle` |
| T-04  | AES-GCM ciphertext tampering        | GCM authentication tag rejection         | `test_aes_256_gcm_aead_and_tampered_ciphertext` |

### 4.3 Repudiation

| ID    | Threat                              | Mitigation                                |
|-------|-------------------------------------|-------------------------------------------|
| R-01  | Denial of job submission            | Structured JSON audit log per request     |
| R-02  | Replay of completed transactions    | Sliding-window nonce deduplication (5-min window) |

### 4.4 Information Disclosure

| ID    | Threat                              | Mitigation                                | Test |
|-------|-------------------------------------|-------------------------------------------|------|
| I-01  | Secret key leakage via error message| ErrorNormalizationCell strips internal tracebacks | `test_e2e_pulse_server_workflow` |
| I-02  | Cross-tenant data leakage via Redis | Job records keyed by `{tenant}:{job_id}`; token validates tenant | `test_cross_tenant_job_access_prevention` |
| I-03  | Dataset content leakage via SSE     | SSE stream only emits to authenticated connection | — |
| I-04  | Encrypted envelope key leakage      | X25519 ephemeral key per message; HKDF-derived AES key | `test_envelope_roundtrip` |

### 4.5 Denial of Service

| ID    | Threat                              | Mitigation                                | Test |
|-------|-------------------------------------|-------------------------------------------|------|
| D-01  | Payload size bomb (oversized body)  | Hard 4 MB request body limit (Vercel enforced + app check) | `test_vercel_payload_size_boundary` |
| D-02  | Concurrent request flood            | `ConcurrencyLimiter` (semaphore, max 32)  | — |
| D-03  | Slow-reader SSE connection          | Fixed-capacity `EventBuffer` ring; oldest events dropped | — |
| D-04  | Resource exhaustion per job         | `ResourceBudget` + `ResourceAdmission` pre-flight | `test_resource_admission_rejection` |
| D-05  | Deadline-exceeded long jobs         | Scheduler `deadline_seconds` hard cutoff  | `test_scheduler_deadline_timeout` |

### 4.6 Elevation of Privilege

| ID    | Threat                              | Mitigation                                |
|-------|-------------------------------------|-------------------------------------------|
| E-01  | Token scope escalation              | Tokens carry tenant + expiry; no role elevation path |
| E-02  | Malicious job payload code execution| VDC engine executes no user-supplied code; all payloads are data |

---

## 5. Cryptographic Primitives

| Primitive         | Algorithm           | Key Size | Use Case                    |
|-------------------|---------------------|----------|-----------------------------|
| Signing (request) | Ed25519             | 256-bit  | Request body + response auth|
| Key Agreement     | X25519 + HKDF-SHA256| 256-bit  | Envelope encryption key     |
| Symmetric Enc.    | AES-256-GCM         | 256-bit  | Payload encryption          |
| MAC (tokens)      | HMAC-SHA256         | 256-bit  | Bearer token integrity      |
| Integrity         | SHA-256             | 256-bit  | Dataset checksum            |

All keys are sourced from environment variables; no keys are hardcoded.

---

## 6. Replay Attack Prevention

```python
# ReplayGuard: sliding-window nonce deduplication
class ReplayGuard:
    window_seconds: float = 300.0   # 5-minute window
    _store: dict[str, float]        # nonce → timestamp
```

Each request must include a `X-Pulse-Nonce` header (UUID or random hex).
Nonces seen within the 5-minute window are rejected with `HTTP 409 Conflict`.
Nonces older than the window are pruned from memory.

---

## 7. Vercel-Specific Security Notes

1. **TLS**: All transport is HTTPS-only (enforced by Vercel edge; no HTTP fallback).
2. **Secret storage**: All secrets in Vercel Environment Variables — never in code or `vercel.json`.
3. **Cold-start leak risk**: Environment variables are available at cold start; no secrets in filesystem.
4. **Ephemeral `/tmp`**: Dataset artifacts in `/tmp` are destroyed at invocation end — no cross-tenant persistence.
5. **No persistent processes**: Vercel terminates workers after response; background threads must complete before response returns.

---

## 8. Residual Risks

| Risk                               | Likelihood | Impact | Accepted? |
|------------------------------------|------------|--------|-----------|
| Vercel platform compromise         | Very Low   | High   | Yes (vendor risk) |
| Nonce store memory pressure (DoS)  | Low        | Medium | Yes (pruning mitigates) |
| Timing side-channel on HMAC compare| Very Low   | Medium | Yes (constant-time compare used) |
| Redis store unavailable in prod    | Low        | Medium | Yes (fallback: MemoryStore) |

---

## 9. Security Test Mapping

| Test                                        | STRIDE IDs Covered |
|---------------------------------------------|--------------------|
| `test_ed25519_sign_verify_and_tamper`       | S-02, T-01         |
| `test_x25519_hkdf_key_agreement`            | I-04               |
| `test_aes_256_gcm_aead_and_tampered_ciphertext` | T-04           |
| `test_token_issue_and_verify`               | S-01               |
| `test_token_expiration`                     | S-01               |
| `test_tampered_token_signature`             | S-01               |
| `test_replay_protection_sliding_window`     | R-02               |
| `test_envelope_roundtrip`                   | I-04               |
| `test_cross_tenant_job_access_prevention`   | S-03, I-02         |
| `test_vercel_payload_size_boundary`         | D-01               |
