import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  // Table for real-time container and server health status audits
  system_status_logs: defineTable({
    record_id: v.string(),
    subsystem: v.string(),
    status: v.string(),
    latency_ms: v.number(),
    throughput_bps: v.number(),
    error: v.string(),
    timestamp: v.number(),
    metadata: v.optional(v.any()),
  }).index("by_subsystem", ["subsystem"])
    .index("by_timestamp", ["timestamp"]),

  // Table for generated datasets (both features, labels, and telemetry)
  synthesized_datasets: defineTable({
    record_id: v.string(),
    dataset_name: v.string(),
    sample_index: v.number(),
    timestamp_ms: v.number(),
    cpu_utilization: v.number(),
    memory_pressure: v.number(),
    io_throughput: v.number(),
    latency_zscore: v.number(),
    queue_depth: v.number(),
    target_label: v.number(),
    is_anomaly: v.boolean(),
    metadata: v.optional(v.any()),
  }).index("by_dataset", ["dataset_name"])
    .index("by_anomaly", ["is_anomaly"]),

  // Table for cumulative real-time telemetry stream snapshots
  realtime_telemetry_stream: defineTable({
    stream_id: v.string(),
    source: v.string(),
    cpu_load: v.number(),
    memory_ratio: v.number(),
    io_throughput_mb: v.number(),
    latency_ms: v.number(),
    container_id: v.string(),
    is_anomaly: v.boolean(),
    timestamp: v.number(),
  }).index("by_source", ["source"])
    .index("by_timestamp", ["timestamp"]),
});
