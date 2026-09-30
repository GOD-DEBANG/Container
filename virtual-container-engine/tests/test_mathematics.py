"""
tests/test_mathematics.py
"""
import pytest
from mathematics.cpu_formula import CPUFormula
from mathematics.ram_formula import RAMFormula
from mathematics.io_formula import IOFormula
from mathematics.actual_speed import ActualSpeedCalculator, UnavailablePolicy

def test_cpu_formula_calculation():
    # V_CPU = cores * freq * bits_per_cycle
    # 4 cores, 2.5 GHz, 64 bits/cycle = 640 Gbps
    throughput = CPUFormula.calculate_v_cpu_bps(
        cores=4,
        frequency_mhz=2500.0,
        cycles_per_bit=1 / 64.0  # 64 bits per cycle
    )
    assert throughput == 4 * 2500 * 1e6 * 64

def test_ram_formula_calculation():
    # V_RAM = channels * rate * width_bits
    # 2 channels, 3200 MT/s, 64 bits = 409.6 Gbps
    throughput = RAMFormula.calculate_v_ram_bps(
        channels=2,
        transfer_rate_mt_s=3200.0,
        bus_width_bits=64
    )
    assert throughput == 2 * 3200 * 1e6 * 64

def test_actual_speed_minimum_function():
    calc = ActualSpeedCalculator(UnavailablePolicy.SKIP)
    
    # min(V_d, V_CPU, V_RAM, V_IO)
    res1 = calc.calculate(
        desired_speed_bps=100.0,
        cpu_limit_bps=200.0,
        ram_limit_bps=300.0,
        io_limit_bps=400.0
    )
    assert res1.actual_speed_bits_per_second == 100.0
    assert res1.limiting_resource == "desired_speed"
    
    res2 = calc.calculate(
        desired_speed_bps=500.0,
        cpu_limit_bps=50.0,
        ram_limit_bps=300.0,
        io_limit_bps=400.0
    )
    assert res2.actual_speed_bits_per_second == 50.0
    assert res2.limiting_resource == "cpu"

    res3 = calc.calculate(
        desired_speed_bps=500.0,
        cpu_limit_bps=200.0,
        ram_limit_bps=None, # Unavailable, skipped
        io_limit_bps=150.0
    )
    assert res3.actual_speed_bits_per_second == 150.0
    assert res3.limiting_resource == "io"
