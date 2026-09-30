"""
output/output_console.py

Displays ExecutionReport to the console.
This is the ONLY presentation adapter.
It is entirely removable and holds NO core processing logic.
"""

from __future__ import annotations

import sys

from models.execution_metrics import ExecutionReport


class OutputConsole:
    """Formats and prints ExecutionReport."""

    @staticmethod
    def display(report: ExecutionReport) -> None:
        """Print human-readable report."""
        print("=" * 60)
        print("VIRTUAL CONTAINER ENGINE - EXECUTION REPORT")
        print("=" * 60)
        print(f"Container ID: {report.container_id}")
        print(f"Dataset ID:   {report.dataset_id}")
        print(f"Final Status: {report.status}")
        
        if report.error:
            print(f"\nERROR: {report.error}")
        
        print("\n--- ALLOCATION ---")
        print(f"Target Size:  {report.target_size_bytes:,} bytes")
        print(f"Allocated:    {report.allocated_bytes:,} bytes")
        print(f"Processed:    {report.processed_bytes:,} bytes")
        print(f"Chunks:       {report.chunk_count}")
        print(f"Subchunks:    {report.subchunk_count}")
        
        print("\n--- CPU BENCHMARK ---")
        print(f"Methodology:  {report.metrics.cpu_benchmark_methodology}")
        if report.metrics.cpu_benchmark_throughput_bits_per_second:
            print(f"Measured:     {report.metrics.cpu_benchmark_throughput_bits_per_second / 1e6:.2f} Mbps")
        else:
            print("Measured:     Unavailable")

        print("\n--- EXECUTION METRICS ---")
        print(f"Elapsed Time: {report.elapsed_seconds:.3f} s")
        print(f"Throughput:   {report.throughput_bits_per_second / 1e6:.2f} Mbps")
        
        print("\n--- RESOURCE REPORT ---")
        print(f"CPU Budget:   {report.configured_cpu_budget_cores} cores")
        print(f"CPU Detected: {report.detected_cpu_cores} cores")
        print(f"Avg CPU %:    {report.process_cpu_percent:.1f}%")
        print(f"RAM Budget:   {report.configured_ram_budget_bytes:,} bytes")
        print(f"Peak RAM:     {report.process_ram_bytes:,} bytes")
        print(f"Workers:      {report.active_workers}")
        
        print("\n--- RESOURCE CONTROL ---")
        print(f"Limiting Res: {report.metrics.limiting_resource}")
        print(f"V_actual:     {report.metrics.actual_speed_bits_per_second / 1e6:.2f} Mbps")
        
        print("\n--- OUTPUT ---")
        print(f"Checksum:     {report.checksum_sha256}")
        print(f"Integrity:    {'VERIFIED' if report.integrity_verified else 'FAILED'}")
        if report.output_path:
            print(f"Saved to:     {report.output_path}")
        
        print(f"Cleanup:      {'COMPLETED' if report.cleanup_completed else 'PENDING'}")
        
        print("=" * 60)
        sys.stdout.flush()
