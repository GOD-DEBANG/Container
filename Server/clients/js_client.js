/**
 * clients/js_client.js
 * 
 * PULSE JavaScript Client SDK (Node.js / Browser compatible).
 * Features:
 *   - Bearer token acquisition
 *   - Job submission
 *   - EventSource / fetch Server-Sent Events (SSE) streaming
 *   - Status checking and dataset download
 */

class PulseClient {
  constructor(baseUrl = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.token = null;
  }

  async authenticate(subject = "js_client", ttlSeconds = 3600) {
    const res = await fetch(`${this.baseUrl}/api/v1/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject, ttl_seconds: ttlSeconds }),
    });
    if (!res.ok) throw new Error(`Auth failed: ${await res.text()}`);
    const data = await res.json();
    this.token = data.payload.access_token;
    return this.token;
  }

  async submitJob({ targetSizeBytes, chunkSize = 1048576, subchunkSize = 262144, policy = "BALANCED" }) {
    if (!this.token) await this.authenticate();

    const payload = {
      target_size_bytes: targetSizeBytes,
      chunk_size_bytes: chunkSize,
      subchunk_size_bytes: subchunkSize,
      policy,
      backend: "INLINE",
    };

    const res = await fetch(`${this.baseUrl}/api/v1/jobs`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.token}`,
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error(`Job submission failed: ${await res.text()}`);
    const body = await res.json();
    return body.payload;
  }

  async getJobStatus(jobId) {
    const res = await fetch(`${this.baseUrl}/api/v1/jobs/${jobId}`);
    if (!res.ok) throw new Error(`Get job status failed: ${await res.text()}`);
    const body = await res.json();
    return body.payload;
  }

  subscribeProgress(jobId, onEvent, onError) {
    const url = `${this.baseUrl}/api/v1/jobs/${jobId}/stream`;
    if (typeof EventSource !== "undefined") {
      const es = new EventSource(url);
      es.onmessage = (e) => {
        try {
          const parsed = JSON.parse(e.data);
          onEvent(parsed);
          if (parsed.status === "COMPLETED" || parsed.status === "FAILED") {
            es.close();
          }
        } catch (err) {
          onError && onError(err);
        }
      };
      es.onerror = (err) => {
        onError && onError(err);
      };
      return () => es.close();
    } else {
      console.warn("EventSource not natively available in this JS runtime.");
    }
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { PulseClient };
}
