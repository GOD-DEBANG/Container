import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// Insert batch of dataset records
export const insertDatasetBatch = mutation({
  args: {
    record_id: v.string(),
    dataset_name: v.string(),
    rows: v.array(v.any()),
    metadata: v.optional(v.any()),
  },
  handler: async (ctx, args) => {
    const insertedIds = [];
    for (const row of args.rows) {
      const id = await ctx.db.insert("synthesized_datasets", {
        record_id: args.record_id,
        dataset_name: args.dataset_name,
        sample_index: row.sample_index ?? 0,
        timestamp_ms: row.timestamp_ms ?? Date.now(),
        cpu_utilization: row.cpu_utilization ?? 0,
        memory_pressure: row.memory_pressure ?? 0,
        io_throughput: row.io_throughput ?? 0,
        latency_zscore: row.latency_zscore ?? 0,
        queue_depth: row.queue_depth ?? 0,
        target_label: row.target_label ?? 0,
        is_anomaly: row.is_anomaly ?? false,
        metadata: args.metadata,
      });
      insertedIds.push(id);
    }
    return { count: insertedIds.length };
  },
});

// Insert real-time server/container status audit log
export const logSystemStatus = mutation({
  args: {
    record_id: v.string(),
    subsystem: v.string(),
    status: v.string(),
    latency_ms: v.number(),
    throughput_bps: v.number(),
    error: v.string(),
    timestamp: v.number(),
    metadata: v.optional(v.any()),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("system_status_logs", {
      record_id: args.record_id,
      subsystem: args.subsystem,
      status: args.status,
      latency_ms: args.latency_ms,
      throughput_bps: args.throughput_bps,
      error: args.error,
      timestamp: args.timestamp,
      metadata: args.metadata,
    });
  },
});

// Query recent status audits
export const getRecentStatusLogs = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const limit = args.limit ?? 50;
    return await ctx.db.query("system_status_logs").order("desc").take(limit);
  },
});
