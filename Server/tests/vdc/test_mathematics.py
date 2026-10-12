"""
tests/vdc/test_mathematics.py

Unit tests for pure computational mathematics engine functions.
Validates conservation, integer rounding, throughput min, progress integration,
completion verification, and invalid input rejection (NaN, Inf, negatives).
"""

import pytest

from vdc.mathematics.dataset_size import estimate_dataset_size, calculate_actual_size
from vdc.mathematics.allocation_formula import hierarchical_allocation, weighted_allocation
from vdc.mathematics.throughput_formula import (
    calculate_effective_throughput,
    calculate_measured_throughput,
)
from vdc.mathematics.progress_integrator import (
    integrate_variable_throughput,
    calculate_remaining_bytes,
    calculate_progress_ratio,
)
from vdc.mathematics.completion_formula import validate_completion


class TestDatasetSize:
    def test_estimate_dataset_size_valid(self):
        assert estimate_dataset_size(1000, 256.0) == 256000
        assert estimate_dataset_size(1, 10.5) == 11

    def test_estimate_dataset_size_invalid_inputs(self):
        with pytest.raises(ValueError):
            estimate_dataset_size(-1, 256.0)
        with pytest.raises(ValueError):
            estimate_dataset_size(100, -10.0)
        with pytest.raises(ValueError):
            estimate_dataset_size(100, float("nan"))
        with pytest.raises(ValueError):
            estimate_dataset_size(100, float("inf"))

    def test_calculate_actual_size_valid(self):
        records = [b"hello", b" ", b"world!"]
        assert calculate_actual_size(records) == 12
        assert calculate_actual_size([]) == 0


class TestAllocationFormula:
    def test_hierarchical_allocation_exact_conservation(self):
        total = 1000000
        chunks = 7
        res = hierarchical_allocation(total, chunks)
        assert len(res) == chunks
        assert sum(res) == total
        assert all(x > 0 for x in res)

    def test_weighted_allocation_conservation(self):
        total = 1000000
        weights = [0.25, 0.35, 0.40]
        res = weighted_allocation(total, weights)
        assert len(res) == 3
        assert sum(res) == total
        assert res == [250000, 350000, 400000]

    def test_weighted_allocation_fractional_remainder_rounding(self):
        # 10 bytes divided among 3 equal weights
        total = 10
        weights = [1/3, 1/3, 1/3]
        res = weighted_allocation(total, weights)
        assert len(res) == 3
        assert sum(res) == 10
        assert res == [4, 3, 3]

    def test_weighted_allocation_invalid_inputs(self):
        with pytest.raises(ValueError):
            weighted_allocation(-100, [0.5, 0.5])
        with pytest.raises(ValueError):
            weighted_allocation(100, [0.3, 0.3]) # sum != 1.0
        with pytest.raises(ValueError):
            weighted_allocation(100, [-0.2, 1.2]) # negative
        with pytest.raises(ValueError):
            weighted_allocation(100, [float("nan"), 1.0])


class TestThroughputFormula:
    def test_calculate_effective_throughput_minimum(self):
        dec = calculate_effective_throughput(
            desired_bps=1000.0,
            cpu_bps=500.0,
            ram_bps=800.0,
            io_bps=300.0,
        )
        assert dec.actual_throughput_bps == 300.0
        assert dec.limiting_resource == "io"

    def test_calculate_effective_throughput_skips_none(self):
        dec = calculate_effective_throughput(
            desired_bps=1000.0,
            cpu_bps=None,
            ram_bps=450.0,
            io_bps=None,
        )
        assert dec.actual_throughput_bps == 450.0
        assert dec.limiting_resource == "ram"

    def test_calculate_effective_throughput_invalid(self):
        with pytest.raises(ValueError):
            calculate_effective_throughput(-50.0)
        with pytest.raises(ValueError):
            calculate_effective_throughput(100.0, cpu_bps=float("nan"))

    def test_calculate_measured_throughput(self):
        rate = calculate_measured_throughput(1000000, 2.0)
        assert rate == 500000.0

        with pytest.raises(ValueError):
            calculate_measured_throughput(100, 0.0)
        with pytest.raises(ValueError):
            calculate_measured_throughput(-10, 1.0)


class TestProgressIntegrator:
    def test_integrate_variable_throughput_trapezoidal(self):
        # Linear ramp: t from 0 to 2, rate from 10 to 20
        # Integral = 0.5 * (10 + 20) * 2 = 30.0
        samples = [(0.0, 10.0), (2.0, 20.0)]
        assert integrate_variable_throughput(samples) == 30.0

    def test_calculate_remaining_bytes(self):
        assert calculate_remaining_bytes(1000, 400) == 600
        assert calculate_remaining_bytes(1000, 1200) == 0

    def test_calculate_progress_ratio_bounded(self):
        assert calculate_progress_ratio(500, 1000) == 0.5
        assert calculate_progress_ratio(1500, 1000) == 1.0 # Clamped to 1.0
        assert calculate_progress_ratio(0, 1000) == 0.0


class TestCompletionFormula:
    def test_validate_completion_success(self):
        expected_chunks = {"chk_1", "chk_2"}
        actual_chunks = ["chk_1", "chk_2"]
        rep = validate_completion(
            expected_records=100,
            actual_records=100,
            expected_bytes=1024,
            actual_bytes=1024,
            expected_chunk_ids=expected_chunks,
            actual_chunk_ids=actual_chunks,
            output_verified=True,
        )
        assert rep.is_complete is True
        assert len(rep.failure_reasons) == 0

    def test_validate_completion_missing_and_duplicate_chunks(self):
        expected_chunks = {"chk_1", "chk_2", "chk_3"}
        actual_chunks = ["chk_1", "chk_1", "chk_2"] # missing chk_3, dup chk_1
        rep = validate_completion(
            expected_records=100,
            actual_records=100,
            expected_bytes=1024,
            actual_bytes=1024,
            expected_chunk_ids=expected_chunks,
            actual_chunk_ids=actual_chunks,
            output_verified=True,
        )
        assert rep.is_complete is False
        assert rep.all_chunks_present is False
        assert rep.no_duplicate_chunks is False
        assert "chk_3" in rep.missing_chunk_ids
        assert "chk_1" in rep.duplicate_chunk_ids
