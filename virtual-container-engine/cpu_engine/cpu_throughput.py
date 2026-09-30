"""
cpu_engine/cpu_throughput.py

Composes the CPU detector, benchmark, and formula to produce a unified
CPU throughput report distinguishing theoretical and measured values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cpu_engine.cpu_detector import CPUDetector, CPUInfo
from cpu_engine.workload_benchmark import WorkloadBenchmark, BenchmarkResult
from cpu_engine.cycles_per_bit import CyclesPerBitEstimator, CyclesPerBitEstimate
from mathematics.cpu_formula import CPUThroughputFormula, TheoreticalCPUResult, MeasuredCPUResult


@dataclass
class CPUThroughputReport:
    """
    Unified CPU throughput report with both theoretical and measured values.
    These two values are intentionally kept separate and clearly labelled.
    """
    cpu_info: CPUInfo
    benchmark: BenchmarkResult
    cycles_per_bit: CyclesPerBitEstimate
    theoretical: TheoreticalCPUResult
    measured: MeasuredCPUResult

    @property
    def best_available_bps(self) -> Optional[float]:
        """Returns measured throughput if available, else theoretical."""
        if self.measured.available and self.measured.throughput_bits_per_second > 0:
            return self.measured.throughput_bits_per_second
        if self.theoretical.available and self.theoretical.throughput_bits_per_second > 0:
            return self.theoretical.throughput_bits_per_second
        return None


class CPUThroughputReporter:
    """Produces a CPUThroughputReport for use by the execution controller."""

    def __init__(
        self,
        cpu_budget_cores: float = 0.0,
        eta_cpu: float = 0.75,
    ) -> None:
        self._cpu_budget_cores = cpu_budget_cores
        self._eta = eta_cpu

    def report(
        self,
        benchmark_size_bytes: int = WorkloadBenchmark.DEFAULT_BENCHMARK_SIZE,
        benchmark_iterations: int = WorkloadBenchmark.DEFAULT_ITERATIONS,
    ) -> CPUThroughputReport:
        cpu_info = CPUDetector.detect()

        benchmark = WorkloadBenchmark().run(
            benchmark_size_bytes=benchmark_size_bytes,
            iterations=benchmark_iterations,
        )

        measured = CPUThroughputFormula.measured(
            benchmark_bytes=benchmark.bytes_per_iteration,
            elapsed_ns=benchmark.median_elapsed_ns,
        )

        cpb = CyclesPerBitEstimator.from_measurement(
            freq_hz=cpu_info.current_freq_hz or cpu_info.max_freq_hz,
            measured_throughput_bps=measured.throughput_bits_per_second
            if measured.available
            else None,
        )

        # Effective CPU budget in Hz
        available_cores = float(cpu_info.logical_cores or 1)
        budget_cores = (
            self._cpu_budget_cores
            if self._cpu_budget_cores > 0
            else available_cores
        )
        budget_cores = min(budget_cores, available_cores)
        effective_freq = budget_cores * (
            cpu_info.current_freq_hz or cpu_info.max_freq_hz or 1e9
        )

        theoretical = CPUThroughputFormula.theoretical(
            f_budget_hz=effective_freq,
            eta_cpu=self._eta,
            cycles_per_bit=cpb.cycles_per_bit,
        )

        return CPUThroughputReport(
            cpu_info=cpu_info,
            benchmark=benchmark,
            cycles_per_bit=cpb,
            theoretical=theoretical,
            measured=measured,
        )
