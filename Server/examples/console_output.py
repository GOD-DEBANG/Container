"""
examples/console_output.py

Console presentation adapter for local terminal demonstrations.
Completely isolated: Never imported by the core Virtual Container engine or PULSE server.
"""

from __future__ import annotations


from vdc.models.execution_metrics import ExecutionReport


class ConsoleOutputAdapter:
    @staticmethod
    def render_report(report: ExecutionReport) -> None:
        """Render a formatted terminal banner and metrics table."""
        status_color = "\033[92m" if report.success else "\033[91m"
        reset = "\033[0m"
        cyan = "\033[96m"
        yellow = "\033[93m"

        print("\n" + "=" * 70)
        print(f"{cyan}  PULSE & VIRTUAL CONTAINER ENGINE - EXECUTION REPORT{reset}")
        print("=" * 70)
        print(f"  Container ID   : {report.container_id}")
        print(f"  Job ID         : {report.job_id}")
        print(f"  Dataset ID     : {report.dataset_id}")
        print(f"  Status         : {status_color}{report.status}{reset}")
        print(f"  Success        : {report.success}")

        if report.error:
            print(f"  Error Detail   : {status_color}{report.error}{reset}")

        m = report.metrics
        print("\n" + "-" * 70)
        print(f"{yellow}  MEASURED PERFORMANCE METRICS{reset}")
        print("-" * 70)
        print(f"  Total Duration       : {m.total_elapsed_seconds:.4f} s")
        print(f"  Generated Output     : {m.actual_generated_bytes:,} bytes")
        print(f"  Persisted Output     : {m.actual_persisted_bytes:,} bytes")
        print(f"  Records Processed    : {m.actual_records_generated:,}")
        print(f"  Generation Rate      : {m.measured_generation_throughput_bytes_per_sec / (1024*1024):.2f} MB/s")
        print(f"  Persistence Rate     : {m.measured_persistence_throughput_bytes_per_sec / (1024*1024):.2f} MB/s")
        print(f"  End-to-End Rate      : {m.end_to_end_throughput_bytes_per_sec / (1024*1024):.2f} MB/s")
        print(f"  Limiting Resource    : {m.limiting_resource}")

        if report.checksum_sha256:
            print(f"\n  SHA-256 Checksum     : {report.checksum_sha256}")
        if report.storage_path:
            print(f"  Persisted Artifact   : {report.storage_path}")

        print("=" * 70 + "\n")


if __name__ == "__main__":
    from vdc.services.dataset_generation_service import DatasetGenerationService
    from vdc.resource_engine.resource_budget import ExecutionPolicy

    svc = DatasetGenerationService()
    print("Running local 10 MB demo via DatasetGenerationService...")
    rep = svc.generate(
        job_id="demo_local_job",
        target_size_bytes=10 * 1024 * 1024,
        chunk_size_bytes=2 * 1024 * 1024,
        subchunk_size_bytes=512 * 1024,
        policy=ExecutionPolicy.BALANCED,
    )
    ConsoleOutputAdapter.render_report(rep)
